"""Project delivery: stage plan, contractor portal, documents, schedule, payments/commission, alerts, analytics."""

from __future__ import annotations

import calendar
import mimetypes
import re
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from app import db
from app.config import (
    DUTY_ESTIMATOR,
    DUTY_PROJECT_COORDINATOR,
    DUTY_PROJECTS_MANAGER,
    DUTY_SITE_ENGINEER,
    MARKETPLACE_LEAD_CLOSED_STATUSES,
    MARKETPLACE_LEAD_STATUS_COMPLETED,
    MARKETPLACE_LEAD_STATUS_ON_HOLD,
    MARKETPLACE_LEAD_STATUS_TERMINATED,
    PRODUCT_DOCUMENT_KINDS,
    PRODUCT_DOCUMENT_SUPPLIER_KINDS,
    PRODUCT_FIELD_DOCUMENT_KINDS,
    PROJECT_DEFAULT_COMMISSION_PERCENT,
    PROJECT_DELIVERY_STATUSES,
    PROJECT_DOCUMENT_CONTRACTOR_KINDS,
    PROJECT_DOCUMENT_EXTENSIONS,
    PROJECT_DOCUMENT_KINDS,
    PROJECT_DOCUMENT_MAX_BYTES,
    PROJECT_EVENT_KINDS,
    PROJECT_EVENT_STATUS_LABELS,
    PROJECT_FIELD_DOCUMENT_KINDS,
    PROJECT_LEAD_STATUSES,
    PROJECT_PLAN_STAGES,
    PROJECT_QUOTE_STATUSES,
    PROJECT_REMINDER_DAYS,
    PROJECT_SCOPE_SUGGESTIONS,
    PROJECT_STALE_DAYS,
    PROJECT_STUCK_DAYS,
    PROJECT_TEAM_SLOT_LABELS,
    PROJECT_TEAM_SLOTS,
    PROJECT_WON_STATUSES,
    TRANSACTION_TYPE_PROJECTS,
    is_admin_role,
    team_slot_labels_for_type,
    team_slots_for_type,
)
from app.models import (
    Contractor,
    MarketplaceLead,
    MarketplaceLeadHistory,
    ProjectBilling,
    ProjectCommission,
    ProjectDocument,
    ProjectEvent,
    ProjectPayment,
    ProjectStagePlan,
    SharingEntry,
    User,
)
from app.timeutil import MANILA_UTC_OFFSET_HOURS, manila_now, manila_today
from app.sanction_service import endorsement_credit_member_id
from app.duty_service import (
    can_be_assigned,
    duty_holders,
    field_agents,
    person_key,
    staff_users,
    team_filter,
    team_slots_for,
)
from app.transaction_service import (
    _append_history,
    _clean,
    _notify_assignee,
    _parse_form_date,
    transaction_status_choices,
    transaction_status_label,
)

CENT = Decimal("0.01")


# --------------------------------------------------------------------------- helpers


def _parse_money(raw, label, required=False):
    text = re.sub(r"[,\s₱]", "", str(raw or "")).replace("PHP", "").replace("php", "")
    if not text:
        if required:
            raise ValueError(f"{label} is required.")
        return None
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"{label} must be a number.") from exc
    if value < 0:
        raise ValueError(f"{label} cannot be negative.")
    return value.quantize(CENT)


def _parse_int(raw, label, minimum=None, maximum=None):
    text = str(raw or "").strip()
    if not text:
        return None
    if not re.fullmatch(r"-?\d+", text):
        raise ValueError(f"{label} must be a whole number.")
    value = int(text)
    if minimum is not None and value < minimum:
        raise ValueError(f"{label} must be at least {minimum}.")
    if maximum is not None and value > maximum:
        raise ValueError(f"{label} must be at most {maximum}.")
    return value


def _parse_datetime_local(raw, label, required=False):
    text = (raw or "").strip()
    if not text:
        if required:
            raise ValueError(f"{label} is required.")
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"{label} must be a valid date and time.")


def format_peso(value):
    if value is None:
        return "—"
    return f"₱{Decimal(value):,.2f}"


def _touch(lead):
    lead.updated_at = manila_now()


def _notify_team(lead, acting_user_id):
    """Mark the transaction unread for everyone on its team (project or product slots)."""
    for user_id in {getattr(lead, slot) for slot in team_slots_for_type(lead.transaction_type)}:
        _notify_assignee(lead, user_id, acting_user_id)


def _actor_name(user):
    if user is None:
        return "System"
    return user.full_name or user.username


def get_project(lead_id):
    lead = (
        MarketplaceLead.query
        .options(
            joinedload(MarketplaceLead.awarded_contractor),
            joinedload(MarketplaceLead.assigned_user),
            joinedload(MarketplaceLead.attributed_member),
        )
        .filter(MarketplaceLead.lead_id == int(lead_id))
        .first()
    )
    if lead is None or lead.transaction_type != TRANSACTION_TYPE_PROJECTS:
        return None
    return lead


def _projects_query():
    return MarketplaceLead.query.filter(MarketplaceLead.transaction_type == TRANSACTION_TYPE_PROJECTS)


def commission_percent_for(lead):
    if lead.commission_percent is not None:
        return Decimal(lead.commission_percent)
    return PROJECT_DEFAULT_COMMISSION_PERCENT


# --------------------------------------------------------------------------- stage plan / progress


def on_project_status_change(lead, status, on_date, user_id=None):
    """Record when a project reaches a planned stage (called from set_transaction_status)."""
    if status in PROJECT_PLAN_STAGES and lead.lead_id:
        plan = ProjectStagePlan.query.filter_by(lead_id=lead.lead_id, stage=status).first()
        if plan is None:
            plan = ProjectStagePlan(lead_id=lead.lead_id, stage=status)
            db.session.add(plan)
        if plan.reached_on is None:
            plan.reached_on = on_date
    if status == MARKETPLACE_LEAD_STATUS_COMPLETED:
        lead.progress_percent = 100
    elif status in PROJECT_DELIVERY_STATUSES and lead.progress_percent is None:
        lead.progress_percent = 0


def stage_plan(lead):
    rows = {plan.stage: plan for plan in ProjectStagePlan.query.filter_by(lead_id=lead.lead_id)}
    today = manila_today()
    current = lead.status or "new"
    result = []
    for stage in PROJECT_PLAN_STAGES:
        plan = rows.get(stage)
        target = plan.target_date if plan else None
        reached = plan.reached_on if plan else None
        if stage == current:
            state = "current"
        elif reached:
            state = "done"
        elif target and target < today:
            state = "overdue"
        else:
            state = "upcoming"
        if stage == current and target and target < today and not reached:
            state = "overdue"
        result.append({
            "stage": stage,
            "label": transaction_status_label(stage),
            "target_date": target,
            "reached_on": reached,
            "state": state,
            "days_late": (today - target).days if state == "overdue" and target else 0,
            "days_in_stage": lead.days_in_status if stage == current else None,
        })
    return result


def save_stage_plan(lead, form, user):
    rows = {plan.stage: plan for plan in ProjectStagePlan.query.filter_by(lead_id=lead.lead_id)}
    changes = []
    for stage in PROJECT_PLAN_STAGES:
        label = transaction_status_label(stage)
        target = _parse_form_date(form.get(f"target_{stage}"), f"{label} target date")
        reached = _parse_form_date(form.get(f"reached_{stage}"), f"{label} reached date")
        plan = rows.get(stage)
        if plan is None:
            if not target and not reached:
                continue
            plan = ProjectStagePlan(lead_id=lead.lead_id, stage=stage)
            db.session.add(plan)
        if plan.target_date != target:
            changes.append(f"{label} target {target.isoformat() if target else 'cleared'}")
            plan.target_date = target
        if plan.reached_on != reached:
            changes.append(f"{label} reached {reached.isoformat() if reached else 'cleared'}")
            plan.reached_on = reached
    if not changes:
        return False
    _touch(lead)
    _append_history(lead, event_type="stage_plan", note="Stage plan: " + "; ".join(changes), user_id=user.user_id)
    db.session.commit()
    return True


def update_progress(lead, raw_percent, note, user, by_contractor=False, by_field_agent=False):
    percent = _parse_int(raw_percent, "Progress", 0, 100)
    if percent is None:
        raise ValueError("Enter the progress percentage (0–100).")
    text = (note or "").strip()
    if percent == (lead.progress_percent or 0) and not text:
        return False
    previous = lead.progress_percent
    lead.progress_percent = percent
    _touch(lead)
    summary = f"Progress {previous if previous is not None else 0}% -> {percent}%"
    if by_contractor:
        summary = f"{summary} (reported by contractor {_actor_name(user)})"
    elif by_field_agent:
        summary = f"{summary} (reported by field agent {_actor_name(user)})"
    if text:
        summary = f"{summary}. {text}"
    _append_history(lead, event_type="progress", note=summary, user_id=user.user_id)
    if by_contractor or by_field_agent:
        _notify_team(lead, user.user_id)
    db.session.commit()
    return True


# --------------------------------------------------------------------------- contractors


def contractor_options():
    return Contractor.query.order_by(Contractor.company_name.asc()).all()


# --------------------------------------------------------------------------- documents


def project_documents(lead_id, contractor_view=False):
    query = (
        ProjectDocument.query
        .options(joinedload(ProjectDocument.uploaded_by))
        .filter_by(lead_id=lead_id)
    )
    if contractor_view:
        query = query.filter(ProjectDocument.shared_with_contractor.is_(True))
    return query.order_by(ProjectDocument.created_at.desc(), ProjectDocument.document_id.desc()).all()


def get_document(document_id):
    return db.session.get(ProjectDocument, int(document_id))


def document_kinds_for(transaction_type):
    return PRODUCT_DOCUMENT_KINDS if transaction_type == "products" else PROJECT_DOCUMENT_KINDS


def partner_document_kinds_for(transaction_type):
    """Types the contractor (projects) or supplier (products) may upload."""
    return PRODUCT_DOCUMENT_SUPPLIER_KINDS if transaction_type == "products" else PROJECT_DOCUMENT_CONTRACTOR_KINDS


def field_document_kinds_for(transaction_type):
    return PRODUCT_FIELD_DOCUMENT_KINDS if transaction_type == "products" else PROJECT_FIELD_DOCUMENT_KINDS


def document_kind_label(kind):
    return PROJECT_DOCUMENT_KINDS.get(kind) or PRODUCT_DOCUMENT_KINDS.get(kind) or (kind or "")


def add_document(lead, form, file_storage, user, by_contractor=False, by_field_agent=False, by_supplier=False):
    kinds = document_kinds_for(lead.transaction_type)
    kind = (form.get("kind") or "other").strip()
    if kind not in kinds:
        raise ValueError("Invalid document type.")
    if (by_contractor or by_supplier) and kind not in partner_document_kinds_for(lead.transaction_type):
        kind = "photo" if by_supplier else "progress_photo"
    if by_field_agent and kind not in field_document_kinds_for(lead.transaction_type):
        raise ValueError("Field agents cannot upload that document type.")
    url = _clean(form.get("external_url"), 500)
    has_file = file_storage is not None and bool(file_storage.filename)
    if not has_file and not url:
        raise ValueError("Choose a file to upload or paste a link.")
    if url and not re.match(r"https?://", url, re.I):
        raise ValueError("Links must start with http:// or https://.")

    document = ProjectDocument(
        lead_id=lead.lead_id,
        kind=kind,
        uploaded_by_user_id=user.user_id,
        created_at=manila_now(),
        shared_with_contractor=(
            by_contractor or by_supplier or (not by_field_agent and form.get("shared_with_contractor") == "1")
        ),
    )
    if has_file:
        file_name = Path(file_storage.filename).name[:255]
        extension = Path(file_name).suffix.lower()
        if extension not in PROJECT_DOCUMENT_EXTENSIONS:
            raise ValueError("Unsupported file type. Use PDF, images, Office files, CAD (DWG/DXF), CSV, or ZIP.")
        payload = file_storage.read()
        if not payload:
            raise ValueError("The selected file is empty.")
        if len(payload) > PROJECT_DOCUMENT_MAX_BYTES:
            raise ValueError(f"Files must be {PROJECT_DOCUMENT_MAX_BYTES // (1024 * 1024)} MB or smaller.")
        content_type = (file_storage.mimetype or "").split(";", 1)[0].strip()
        if not content_type or content_type == "application/octet-stream":
            content_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        document.file_name = file_name
        document.content_type = content_type
        document.size_bytes = len(payload)
        document.file_data = payload
    else:
        document.external_url = url
    document.title = _clean(form.get("title"), 255) or document.file_name or url[:255]

    db.session.add(document)
    _touch(lead)
    note = f"{document_kind_label(kind)} added: {document.title}"
    if by_contractor:
        note += " (uploaded by contractor)"
    elif by_supplier:
        note += " (uploaded by supplier)"
    elif by_field_agent:
        note += " (uploaded by field agent)"
    _append_history(lead, event_type="document", note=note, user_id=user.user_id)
    if by_contractor or by_field_agent or by_supplier:
        _notify_team(lead, user.user_id)
    db.session.commit()
    return document


def delete_document(document, user):
    lead = db.session.get(MarketplaceLead, document.lead_id)
    title = document.title
    db.session.delete(document)
    _touch(lead)
    _append_history(lead, event_type="document", note=f"Removed document: {title}", user_id=user.user_id)
    db.session.commit()


# --------------------------------------------------------------------------- schedule


def event_kind_label(kind):
    return PROJECT_EVENT_KINDS.get(kind, kind or "")


def project_events(lead_id):
    return (
        ProjectEvent.query
        .options(joinedload(ProjectEvent.assigned_user))
        .filter_by(lead_id=lead_id)
        .order_by(ProjectEvent.starts_at.desc())
        .all()
    )


def get_event(event_id):
    return db.session.get(ProjectEvent, int(event_id))


def save_event(lead, form, user, event=None):
    kind = (form.get("kind") or "site_visit").strip()
    if kind not in PROJECT_EVENT_KINDS:
        raise ValueError("Invalid schedule type.")
    starts_at = _parse_datetime_local(form.get("starts_at"), "Start", required=True)
    ends_at = _parse_datetime_local(form.get("ends_at"), "End")
    if ends_at and ends_at < starts_at:
        raise ValueError("End must be after the start.")
    meeting_link = _clean(form.get("meeting_link"), 500)
    if meeting_link and not re.match(r"https?://", meeting_link, re.I):
        raise ValueError("Meeting links must start with http:// or https://.")
    assignee_id = None
    raw_assignee = (form.get("assigned_user_id") or "").strip()
    if raw_assignee:
        assignee = db.session.get(User, int(raw_assignee)) if raw_assignee.isdigit() else None
        if not can_be_assigned(assignee, TRANSACTION_TYPE_PROJECTS):
            raise ValueError("Assign the schedule to an Admin or Staff user, or a member field agent.")
        assignee_id = assignee.user_id

    is_new = event is None
    if is_new:
        event = ProjectEvent(lead_id=lead.lead_id, created_by_user_id=user.user_id, created_at=manila_now())
        db.session.add(event)
    event.kind = kind
    event.title = _clean(form.get("title"), 255) or f"{event_kind_label(kind)} — {lead.display_item}"[:255]
    event.starts_at = starts_at
    event.ends_at = ends_at
    event.location = _clean(form.get("location"), 255)
    event.meeting_link = meeting_link
    event.assigned_user_id = assignee_id
    event.notes = _clean(form.get("notes"))
    _touch(lead)
    verb = "Scheduled" if is_new else "Rescheduled"
    _append_history(
        lead,
        event_type="schedule",
        note=f"{verb} {event_kind_label(kind).lower()} on {starts_at.strftime('%Y-%m-%d %H:%M')}: {event.title}",
        user_id=user.user_id,
    )
    if assignee_id:
        _notify_assignee(lead, assignee_id, user.user_id)
    db.session.commit()
    return event


def set_event_status(event, status, outcome, user):
    if status not in PROJECT_EVENT_STATUS_LABELS:
        raise ValueError("Invalid schedule status.")
    event.status = status
    event.outcome = _clean(outcome) or event.outcome
    lead = event.lead
    _touch(lead)
    note = f"{event_kind_label(event.kind)} {PROJECT_EVENT_STATUS_LABELS[status].lower()}: {event.title}"
    if event.outcome and status == "done":
        note += f". Outcome: {event.outcome}"
    _append_history(lead, event_type="schedule", note=note, user_id=user.user_id)
    db.session.commit()


def delete_event(event, user):
    lead = event.lead
    title = event.title
    db.session.delete(event)
    _touch(lead)
    _append_history(lead, event_type="schedule", note=f"Removed schedule: {title}", user_id=user.user_id)
    db.session.commit()


def _events_scope(query, user):
    if user is not None and not is_admin_role(user.role):
        query = query.filter(or_(ProjectEvent.assigned_user_id == user.user_id, ProjectEvent.assigned_user_id.is_(None)))
    return query


def upcoming_events(user=None, days=PROJECT_REMINDER_DAYS, limit=8):
    """Scheduled events from overdue (not closed) up to `days` ahead; Staff see theirs and unassigned."""
    horizon = datetime.combine(manila_today() + timedelta(days=days), datetime.max.time())
    query = (
        ProjectEvent.query
        .options(joinedload(ProjectEvent.lead), joinedload(ProjectEvent.assigned_user))
        .filter(ProjectEvent.status == "scheduled", ProjectEvent.starts_at <= horizon)
    )
    query = _events_scope(query, user)
    return query.order_by(ProjectEvent.starts_at.asc()).limit(limit).all()


def calendar_month(year, month, user=None, mine_only=False):
    weeks = calendar.Calendar(firstweekday=6).monthdatescalendar(year, month)
    start = datetime.combine(weeks[0][0], datetime.min.time())
    end = datetime.combine(weeks[-1][-1], datetime.max.time())
    query = (
        ProjectEvent.query
        .options(joinedload(ProjectEvent.lead), joinedload(ProjectEvent.assigned_user))
        .filter(ProjectEvent.starts_at >= start, ProjectEvent.starts_at <= end)
    )
    if mine_only and user is not None:
        query = query.filter(ProjectEvent.assigned_user_id == user.user_id)
    by_day = defaultdict(list)
    for event in query.order_by(ProjectEvent.starts_at.asc()).all():
        by_day[event.starts_at.date()].append(event)
    return weeks, by_day


def _ics_escape(text):
    return (
        str(text or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _ics_utc(moment):
    return (moment - timedelta(hours=MANILA_UTC_OFFSET_HOURS)).strftime("%Y%m%dT%H%M%SZ")


def event_ics(event):
    lead = event.lead
    ends_at = event.ends_at or (event.starts_at + timedelta(hours=1))
    description = [f"{lead.reference_number} — {lead.display_item}"]
    if event.meeting_link:
        description.append(f"Link: {event.meeting_link}")
    if event.notes:
        description.append(event.notes)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//TBGP//Project schedule//EN",
        "BEGIN:VEVENT",
        f"UID:tbgp-project-event-{event.event_id}@tbgp",
        f"DTSTAMP:{_ics_utc(manila_now())}",
        f"DTSTART:{_ics_utc(event.starts_at)}",
        f"DTEND:{_ics_utc(ends_at)}",
        f"SUMMARY:{_ics_escape(event.title)}",
        f"LOCATION:{_ics_escape(event.location or event.meeting_link or '')}",
        f"DESCRIPTION:{_ics_escape(chr(10).join(description))}",
        "BEGIN:VALARM",
        "TRIGGER:-PT1H",
        "ACTION:DISPLAY",
        f"DESCRIPTION:{_ics_escape(event.title)}",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines) + "\r\n"


# --------------------------------------------------------------------------- contract / payments / commission


def save_contract(lead, form, user):
    amount = _parse_money(form.get("contract_amount"), "Contract amount")
    signed = _parse_form_date(form.get("contract_signed_on"), "Contract signed on")
    percent_raw = (form.get("commission_percent") or "").strip()
    percent = None
    if percent_raw:
        try:
            percent = Decimal(percent_raw).quantize(CENT)
        except InvalidOperation as exc:
            raise ValueError("Commission % must be a number.") from exc
        if percent < 0 or percent > 100:
            raise ValueError("Commission % must be between 0 and 100.")
    changes = []
    if amount != lead.contract_amount:
        changes.append(f"Contract amount {format_peso(amount)}")
        lead.contract_amount = amount
    if signed != lead.contract_signed_on:
        changes.append(f"Contract signed {signed.isoformat() if signed else 'cleared'}")
        lead.contract_signed_on = signed
    if percent != lead.commission_percent:
        changes.append(f"Commission rate {percent}%" if percent is not None else "Commission rate reset to default")
        lead.commission_percent = percent
    if not changes:
        return False
    _touch(lead)
    _append_history(lead, event_type="contract", note="; ".join(changes), user_id=user.user_id)
    db.session.commit()
    return True


def project_payments(lead_id):
    return (
        ProjectPayment.query
        .filter_by(lead_id=lead_id)
        .order_by(ProjectPayment.due_date.asc().nullslast(), ProjectPayment.payment_id.asc())
        .all()
    )


def get_payment(payment_id):
    return db.session.get(ProjectPayment, int(payment_id))


def payment_commission(payment, lead=None):
    if payment.commission_amount is not None:
        return Decimal(payment.commission_amount)
    lead = lead or payment.lead
    return (Decimal(payment.amount) * commission_percent_for(lead) / Decimal("100")).quantize(CENT)


def add_payment(lead, form, user):
    title = _clean(form.get("title"), 160)
    if not title:
        raise ValueError("Payment milestone title is required.")
    amount = _parse_money(form.get("amount"), "Amount", required=True)
    payment = ProjectPayment(
        lead_id=lead.lead_id,
        title=title,
        amount=amount,
        due_date=_parse_form_date(form.get("due_date"), "Due date"),
        notes=_clean(form.get("notes")),
        created_by_user_id=user.user_id,
        created_at=manila_now(),
    )
    db.session.add(payment)
    _touch(lead)
    _append_history(lead, event_type="payment", note=f"Payment milestone added: {title} {format_peso(amount)}", user_id=user.user_id)
    db.session.commit()
    return payment


def generate_payment_schedule(lead, form, user):
    if not lead.contract_amount:
        raise ValueError("Set the contract amount first.")
    parts = [p for p in re.split(r"[,\s/]+", form.get("percentages") or "") if p]
    try:
        percents = [Decimal(p.rstrip("%")) for p in parts]
    except InvalidOperation as exc:
        raise ValueError("Enter percentages like 30, 40, 30.") from exc
    if not percents or any(p <= 0 for p in percents):
        raise ValueError("Enter percentages like 30, 40, 30.")
    if sum(percents) != Decimal("100"):
        raise ValueError(f"Percentages must add up to 100 (now {sum(percents)}).")
    total = Decimal(lead.contract_amount)
    amounts = [(total * p / Decimal("100")).quantize(CENT) for p in percents]
    amounts[-1] += total - sum(amounts)
    count = len(percents)
    labels = [format(p.normalize(), "f") for p in percents]
    for index, (label, amount) in enumerate(zip(labels, amounts), start=1):
        if index == 1:
            title = f"Downpayment ({label}%)"
        elif index == count:
            title = f"Final payment ({label}%)"
        else:
            title = f"Progress billing {index - 1} ({label}%)"
        db.session.add(ProjectPayment(
            lead_id=lead.lead_id,
            title=title,
            amount=amount,
            created_by_user_id=user.user_id,
            created_at=manila_now(),
        ))
    _touch(lead)
    _append_history(
        lead,
        event_type="payment",
        note=f"Payment schedule generated ({', '.join(labels)}%) on {format_peso(total)}",
        user_id=user.user_id,
    )
    db.session.commit()


def mark_payment_paid(payment, form, user):
    paid_on = _parse_form_date(form.get("paid_on"), "Paid on") or manila_today()
    payment.paid_on = paid_on
    payment.reference = _clean(form.get("reference"), 120) or payment.reference
    override = _parse_money(form.get("commission_amount"), "Commission amount")
    if override is not None:
        payment.commission_amount = override
    lead = payment.lead
    _touch(lead)
    _append_history(
        lead,
        event_type="payment",
        note=f"Payment received: {payment.title} {format_peso(payment.amount)} on {paid_on.isoformat()}"
        + (f" (ref {payment.reference})" if payment.reference else ""),
        user_id=user.user_id,
    )
    db.session.commit()


def unmark_payment_paid(payment, user):
    if payment.billing_id:
        raise ValueError("Unpost the commission billing first.")
    payment.paid_on = None
    _touch(payment.lead)
    _append_history(payment.lead, event_type="payment", note=f"Payment marked unpaid: {payment.title}", user_id=user.user_id)
    db.session.commit()


def delete_payment(payment, user):
    if payment.billing_id:
        raise ValueError("Unpost the commission billing before deleting this milestone.")
    lead = payment.lead
    title = payment.title
    db.session.delete(payment)
    _touch(lead)
    _append_history(lead, event_type="payment", note=f"Payment milestone removed: {title}", user_id=user.user_id)
    db.session.commit()


def _client_referrer_id(lead):
    if lead.attributed_member_id:
        return lead.attributed_member_id
    from app.prof_sharing_service import get_admin_member

    admin_member = get_admin_member()
    if admin_member is None:
        raise ValueError("This project has no ProF member and no admin member is configured for direct inquiries.")
    return admin_member.member_id


def ensure_commission_project(lead):
    """The Income Management project-commission record that receives this project's billings."""
    if lead.commission_project_id:
        project = db.session.get(ProjectCommission, lead.commission_project_id)
        if project is not None:
            return project
    contractor = lead.awarded_contractor
    if contractor is None:
        raise ValueError("Assign a registered portal contractor to the project before posting commission.")
    if not contractor.member_referrer_id:
        raise ValueError(f"{contractor.company_name} has no member referrer; set it on the Contractors page.")
    project = ProjectCommission(
        project_title=f"{lead.reference_number} {lead.display_item}".strip()[:200],
        address=(lead.delivery_location or "")[:255] or None,
        contractor_id=contractor.contractor_id,
        client_referrer_id=_client_referrer_id(lead),
        contractor_referrer_id=endorsement_credit_member_id(contractor.member_referrer_id),
    )
    if project.contractor_referrer_id != contractor.member_referrer_id:
        _append_history(
            lead,
            event_type="commission",
            note=(
                f"Contractor-endorsement credit went to the admin member because "
                f"{contractor.member_referrer.full_name if contractor.member_referrer else 'the endorser'} "
                "is suspended from endorsing contractors."
            ),
        )
    db.session.add(project)
    db.session.flush()
    lead.commission_project_id = project.project_id
    return project


def post_payment_commission(payment, user):
    if not payment.is_paid:
        raise ValueError("Mark the payment as received before posting commission.")
    if payment.billing_id:
        raise ValueError("Commission for this payment is already posted.")
    lead = payment.lead
    commission = payment_commission(payment, lead)
    if commission <= 0:
        raise ValueError("Commission amount must be greater than zero.")
    project = ensure_commission_project(lead)
    billing = ProjectBilling(project_id=project.project_id, billing_date=payment.paid_on, billing_amount=commission)
    db.session.add(billing)
    db.session.flush()
    payment.billing_id = billing.billing_id
    if payment.commission_amount is None:
        payment.commission_amount = commission
    _touch(lead)
    _append_history(
        lead,
        event_type="commission",
        note=(
            f"Commission {format_peso(commission)} posted for {payment.title} "
            f"(billing date {payment.paid_on.isoformat()}, project commission #{project.project_id})"
        ),
        user_id=user.user_id,
    )
    db.session.commit()
    return billing


def unpost_payment_commission(payment, user):
    if not payment.billing_id:
        return False
    if SharingEntry.query.filter_by(billing_id=payment.billing_id).count():
        raise ValueError(
            "Profit sharing was already generated for this billing. Delete the sharing batch first."
        )
    billing = db.session.get(ProjectBilling, payment.billing_id)
    payment.billing_id = None
    if billing is not None:
        db.session.delete(billing)
    _touch(payment.lead)
    _append_history(payment.lead, event_type="commission", note=f"Commission unposted for {payment.title}", user_id=user.user_id)
    db.session.commit()
    return True


def payments_summary(lead, payments):
    scheduled = sum((Decimal(p.amount) for p in payments), Decimal("0"))
    paid = sum((Decimal(p.amount) for p in payments if p.is_paid), Decimal("0"))
    posted = sum((payment_commission(p, lead) for p in payments if p.billing_id), Decimal("0"))
    contract = Decimal(lead.contract_amount) if lead.contract_amount is not None else None
    return {
        "contract": contract,
        "scheduled": scheduled,
        "paid": paid,
        "balance": (contract - paid) if contract is not None else None,
        "unscheduled": (contract - scheduled) if contract is not None else None,
        "commission_percent": commission_percent_for(lead),
        "commission_posted": posted,
        "paid_percent": int(paid * 100 / contract) if contract else 0,
    }


# --------------------------------------------------------------------------- overdue alerts


def project_attention_map(leads=None):
    """lead_id -> list of reasons an open project needs attention."""
    if leads is None:
        leads = _projects_query().filter(MarketplaceLead.status.notin_(MARKETPLACE_LEAD_CLOSED_STATUSES)).all()
    open_leads = [lead for lead in leads if not lead.is_closed]
    if not open_leads:
        return {}
    ids = [lead.lead_id for lead in open_leads]
    today = manila_today()
    now = manila_now()
    reasons = defaultdict(list)

    for plan in ProjectStagePlan.query.filter(
        ProjectStagePlan.lead_id.in_(ids),
        ProjectStagePlan.target_date < today,
        ProjectStagePlan.reached_on.is_(None),
    ):
        reasons[plan.lead_id].append(
            f"{transaction_status_label(plan.stage)} target {plan.target_date.isoformat()} passed"
        )
    for payment in ProjectPayment.query.filter(
        ProjectPayment.lead_id.in_(ids),
        ProjectPayment.paid_on.is_(None),
        ProjectPayment.due_date < today,
    ):
        reasons[payment.lead_id].append(f"Payment '{payment.title}' was due {payment.due_date.isoformat()}")
    for event in ProjectEvent.query.filter(
        ProjectEvent.lead_id.in_(ids),
        ProjectEvent.status == "scheduled",
        ProjectEvent.starts_at < now,
    ):
        reasons[event.lead_id].append(
            f"{event_kind_label(event.kind)} on {event.starts_at.strftime('%Y-%m-%d')} not marked done"
        )

    for lead in open_leads:
        last = lead.last_activity_at
        idle = (today - last.date()).days if last else 0
        if idle > PROJECT_STALE_DAYS:
            reasons[lead.lead_id].insert(0, f"No update in {idle} days")
        if lead.status != MARKETPLACE_LEAD_STATUS_ON_HOLD and lead.days_in_status > PROJECT_STUCK_DAYS:
            reasons[lead.lead_id].insert(
                0, f"{lead.days_in_status} days in {transaction_status_label(lead.status)}"
            )
    return {lead_id: items for lead_id, items in reasons.items() if items}


def projects_needing_attention(limit=6):
    leads = (
        _projects_query()
        .options(joinedload(MarketplaceLead.assigned_user))
        .filter(MarketplaceLead.status.notin_(MARKETPLACE_LEAD_CLOSED_STATUSES))
        .all()
    )
    attention = project_attention_map(leads)
    flagged = [lead for lead in leads if lead.lead_id in attention]
    flagged.sort(key=lambda lead: (-len(attention[lead.lead_id]), -lead.days_in_status))
    return {"count": len(flagged), "items": [(lead, attention[lead.lead_id]) for lead in flagged[:limit]]}


def dashboard_project_overview(user):
    return {
        "attention": projects_needing_attention(),
        "events": upcoming_events(user),
        "stale_days": PROJECT_STALE_DAYS,
        "stuck_days": PROJECT_STUCK_DAYS,
        "reminder_days": PROJECT_REMINDER_DAYS,
    }


# --------------------------------------------------------------------------- detail page context


def project_detail_context(lead, user):
    payments = project_payments(lead.lead_id)
    return {
        "stage_plan": stage_plan(lead),
        "documents": project_documents(lead.lead_id),
        "document_kinds": PROJECT_DOCUMENT_KINDS,
        "contractor_document_kinds": PROJECT_DOCUMENT_CONTRACTOR_KINDS,
        "events": project_events(lead.lead_id),
        "event_kinds": PROJECT_EVENT_KINDS,
        "event_status_labels": PROJECT_EVENT_STATUS_LABELS,
        "payments": payments,
        "payment_summary": payments_summary(lead, payments),
        "payment_commission": payment_commission,
        "attention_reasons": project_attention_map([lead]).get(lead.lead_id, []),
        "event_assignees": event_assignees(lead),
        "format_peso": format_peso,
        "now": manila_now(),
    }


def event_assignees(lead=None):
    """Staff/Admin plus member field agents (and whoever already holds a team slot)."""
    users = staff_users() + field_agents()
    seen = {u.user_id for u in users}
    if lead is not None:
        for slot in PROJECT_TEAM_SLOTS:
            member = getattr(lead, slot.removesuffix("_id"))
            if member is not None and member.user_id not in seen:
                users.append(member)
                seen.add(member.user_id)
    return users


# --------------------------------------------------------------------------- contractor portal / ProF view


def contractor_projects(contractor_id):
    """Projects assigned to the contractor (newest activity first)."""
    if not contractor_id:
        return []
    return (
        _projects_query()
        .options(joinedload(MarketplaceLead.assigned_user))
        .filter(MarketplaceLead.awarded_contractor_id == contractor_id)
        .order_by(MarketplaceLead.updated_at.desc().nullslast())
        .all()
    )


def contractor_can_view(lead, contractor_id):
    """Only the contractor assigned to the project sees it in the contractor portal."""
    return bool(contractor_id) and lead.awarded_contractor_id == contractor_id


def contractor_updates(lead_id):
    """Progress reports plus the contractor's own uploads; titles of internal TBGP files stay hidden."""
    entries = (
        MarketplaceLeadHistory.query
        .options(joinedload(MarketplaceLeadHistory.created_by))
        .filter(
            MarketplaceLeadHistory.lead_id == lead_id,
            MarketplaceLeadHistory.event_type.in_(("progress", "document")),
        )
        .order_by(MarketplaceLeadHistory.created_at.desc())
        .limit(60)
        .all()
    )
    return [
        entry for entry in entries
        if entry.event_type == "progress" or (entry.note or "").endswith("(uploaded by contractor)")
    ][:30]


def contractor_dashboard_summary(contractor_id):
    rows = contractor_projects(contractor_id)
    active = [lead for lead in rows if not lead.is_closed]
    ids = [lead.lead_id for lead in active]
    events = []
    if ids:
        horizon = datetime.combine(manila_today() + timedelta(days=PROJECT_REMINDER_DAYS), datetime.max.time())
        events = (
            ProjectEvent.query
            .options(joinedload(ProjectEvent.lead))
            .filter(
                ProjectEvent.lead_id.in_(ids),
                ProjectEvent.status == "scheduled",
                ProjectEvent.starts_at >= datetime.combine(manila_today(), datetime.min.time()),
                ProjectEvent.starts_at <= horizon,
            )
            .order_by(ProjectEvent.starts_at.asc())
            .all()
        )
    return {
        "total": len(rows),
        "active": active,
        "completed": sum(1 for lead in rows if lead.is_closed),
        "events": events,
    }


def member_projects(member_id):
    if not member_id:
        return []
    return (
        _projects_query()
        .options(joinedload(MarketplaceLead.awarded_contractor))
        .filter(MarketplaceLead.attributed_member_id == member_id)
        .order_by(MarketplaceLead.inquiry_no.desc().nullslast(), MarketplaceLead.created_at.desc())
        .all()
    )


# --------------------------------------------------------------------------- duty dashboards


def _open_projects_query():
    return (
        _projects_query()
        .options(
            joinedload(MarketplaceLead.assigned_user),
            joinedload(MarketplaceLead.estimator_user),
            joinedload(MarketplaceLead.site_engineer_user),
        )
        .filter(or_(MarketplaceLead.status.is_(None), MarketplaceLead.status.notin_(MARKETPLACE_LEAD_CLOSED_STATUSES)))
    )


def _by_attention(leads, attention):
    return sorted(leads, key=lambda lead: (-len(attention.get(lead.lead_id, [])), -lead.days_in_status))


def my_scheduled_events(user_id, days=PROJECT_REMINDER_DAYS, limit=8):
    """Scheduled events assigned to the user, overdue ones included, up to `days` ahead."""
    horizon = datetime.combine(manila_today() + timedelta(days=days), datetime.max.time())
    return (
        ProjectEvent.query
        .options(joinedload(ProjectEvent.lead))
        .filter(
            ProjectEvent.assigned_user_id == user_id,
            ProjectEvent.status == "scheduled",
            ProjectEvent.starts_at <= horizon,
        )
        .order_by(ProjectEvent.starts_at.asc())
        .limit(limit)
        .all()
    )


def recent_suggestions(days=14, limit=8, transaction_type=TRANSACTION_TYPE_PROJECTS):
    since = manila_now() - timedelta(days=days)
    return (
        MarketplaceLeadHistory.query
        .options(joinedload(MarketplaceLeadHistory.created_by), joinedload(MarketplaceLeadHistory.lead))
        .join(MarketplaceLead, MarketplaceLead.lead_id == MarketplaceLeadHistory.lead_id)
        .filter(
            MarketplaceLeadHistory.event_type == "suggestion",
            MarketplaceLeadHistory.created_at >= since,
            MarketplaceLead.transaction_type == transaction_type,
        )
        .order_by(MarketplaceLeadHistory.created_at.desc())
        .limit(limit)
        .all()
    )


def team_workload(leads, attention):
    """One row per duty holder / current team member with open-project counts per slot."""
    rows = {}

    def row_for(member):
        if member.user_id not in rows:
            rows[member.user_id] = {"user": member, "attention": 0, "total": 0, **{slot: 0 for slot in PROJECT_TEAM_SLOTS}}
        return rows[member.user_id]

    for duty in PROJECT_TEAM_SLOTS.values():
        for member in duty_holders(duty):
            row_for(member)
    for lead in leads:
        members = {}
        for slot in PROJECT_TEAM_SLOTS:
            member = getattr(lead, slot.removesuffix("_id"))
            if member is not None:
                row_for(member)[slot] += 1
                members[member.user_id] = member
        for user_id in members:
            rows[user_id]["total"] += 1
            if lead.lead_id in attention:
                rows[user_id]["attention"] += 1
    return sorted(rows.values(), key=lambda row: (-row["total"], (row["user"].full_name or row["user"].username).lower()))


def duty_dashboard(user, limit=6):
    """Dashboard cards for the user's project duties (Admins also get the manager view)."""
    duties = user.duty_keys
    is_manager = DUTY_PROJECTS_MANAGER in duties or is_admin_role(user.role)
    if not (is_manager or duties & set(PROJECT_TEAM_SLOTS.values())):
        return None
    query = _open_projects_query()
    if not is_manager:
        query = query.filter(team_filter(user.user_id))
    leads = query.all()
    attention = project_attention_map(leads)
    uid = user.user_id
    cards = {"attention": attention, "slot_labels": PROJECT_TEAM_SLOT_LABELS, "status_label": transaction_status_label}

    if is_manager:
        unassigned = [lead for lead in leads if not lead.assigned_user_id]
        cards["manager"] = {
            "workload": team_workload(leads, attention),
            "unassigned": sorted(unassigned, key=lambda lead: -lead.aging_days)[:limit],
            "unassigned_count": len(unassigned),
            "no_estimator": sum(1 for lead in leads if lead.status in PROJECT_QUOTE_STATUSES and not lead.estimator_user_id),
            "no_site_engineer": sum(
                1 for lead in leads if lead.status in PROJECT_DELIVERY_STATUSES and not lead.site_engineer_user_id
            ),
            "suggestions": recent_suggestions(),
        }
    if DUTY_PROJECT_COORDINATOR in duties:
        mine = [lead for lead in leads if lead.assigned_user_id == uid]
        cards["coordinator"] = {
            "count": len(mine),
            "attention_count": sum(1 for lead in mine if lead.lead_id in attention),
            "items": _by_attention(mine, attention)[:limit],
        }
    if DUTY_ESTIMATOR in duties:
        queue = [lead for lead in leads if lead.estimator_user_id == uid and lead.status in PROJECT_QUOTE_STATUSES]
        unclaimed = (
            _projects_query()
            .filter(MarketplaceLead.status.in_(PROJECT_QUOTE_STATUSES), MarketplaceLead.estimator_user_id.is_(None))
            .count()
        )
        cards["estimator"] = {
            "count": len(queue),
            "items": sorted(queue, key=lambda lead: -lead.days_in_status)[:limit],
            "unclaimed": unclaimed,
        }
    if DUTY_SITE_ENGINEER in duties:
        sites = [lead for lead in leads if lead.site_engineer_user_id == uid]
        delivery = [lead for lead in sites if lead.status in PROJECT_DELIVERY_STATUSES]
        cards["site_engineer"] = {
            "count": len(sites),
            "delivery": sorted(delivery, key=lambda lead: lead.progress_percent or 0)[:limit],
            "events": my_scheduled_events(uid),
        }
    return cards


# --------------------------------------------------------------------------- member field agents

FIELD_HISTORY_TYPES = ("created", "progress", "document", "schedule", "stage_plan", "note", "suggestion")


def field_projects(user):
    """Projects where the member holds a team slot (open first, newest activity first)."""
    leads = (
        _projects_query()
        .options(
            joinedload(MarketplaceLead.assigned_user),
            joinedload(MarketplaceLead.estimator_user),
            joinedload(MarketplaceLead.site_engineer_user),
        )
        .filter(team_filter(user.user_id))
        .order_by(MarketplaceLead.updated_at.desc().nullslast())
        .all()
    )
    return sorted(leads, key=lambda lead: lead.is_closed)


def field_can_view(lead, user):
    return user is not None and bool(team_slots_for(lead, user.user_id))


def field_roles(lead, user):
    labels = team_slot_labels_for_type(lead.transaction_type)
    return [labels[slot] for slot in team_slots_for(lead, user.user_id)]


def field_documents(lead_id, transaction_type=TRANSACTION_TYPE_PROJECTS):
    allowed = field_document_kinds_for(transaction_type)
    return [doc for doc in project_documents(lead_id) if doc.kind in allowed]


def field_can_see_document(document, user):
    lead = db.session.get(MarketplaceLead, document.lead_id)
    if lead is None or document.kind not in field_document_kinds_for(lead.transaction_type):
        return False
    return field_can_view(lead, user)


def field_history(lead_id, limit=30, transaction_type=TRANSACTION_TYPE_PROJECTS):
    allowed = field_document_kinds_for(transaction_type)
    hidden = tuple(
        f"{label} added:" for kind, label in document_kinds_for(transaction_type).items() if kind not in allowed
    ) + ("Removed document:",)
    entries = (
        MarketplaceLeadHistory.query
        .options(joinedload(MarketplaceLeadHistory.created_by))
        .filter(
            MarketplaceLeadHistory.lead_id == lead_id,
            MarketplaceLeadHistory.event_type.in_(FIELD_HISTORY_TYPES),
        )
        .order_by(MarketplaceLeadHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        entry for entry in entries
        if not (entry.event_type == "document" and (entry.note or "").startswith(hidden))
    ]


def add_field_note(lead, note, user):
    text = _clean(note)
    if not text:
        raise ValueError("Write a note first.")
    _touch(lead)
    _append_history(lead, event_type="note", note=f"Field note: {text}", user_id=user.user_id)
    _notify_team(lead, user.user_id)
    db.session.commit()


def complete_field_event(event, outcome, user):
    if event.assigned_user_id != user.user_id:
        raise ValueError("You can only update schedules assigned to you.")
    if event.status != "scheduled":
        raise ValueError("This schedule is already closed.")
    _notify_team(event.lead, user.user_id)
    set_event_status(event, "done", outcome, user)


def suggest_status(lead, status, reason, user):
    """Field agents propose a status change; the coordinator / account officer applies it."""
    if status not in transaction_status_choices(lead.transaction_type):
        raise ValueError("Choose a valid status.")
    if status == (lead.status or "new"):
        raise ValueError("The transaction is already in that status.")
    note = f"Suggested status change: {transaction_status_label(lead.status)} -> {transaction_status_label(status)}"
    text = _clean(reason)
    if text:
        note = f"{note}. {text}"
    _touch(lead)
    _append_history(lead, event_type="suggestion", note=note, user_id=user.user_id)
    _notify_team(lead, user.user_id)
    db.session.commit()


# --------------------------------------------------------------------------- analytics


_SCOPE_RULES = (
    (r"MICRO\s*PIL", "Micropiling"),
    (r"BORED\s*PIL|BOREDPIL|BORED\s*PILE|BOREDPILE", "Bored piling"),
    (r"SHEET\s*PIL", "Sheet piling"),
    (r"PUSH\s*PILE", "Push pile"),
    (r"SOIL\s*NAIL|SHOTCRET", "Soil nailing & shotcreting"),
    (r"ROCK\s*ANCHOR", "Rock anchoring"),
    (r"ROCK\s*FALL", "Rock fall netting"),
    (r"SLOPE", "Slope protection"),
    (r"EXCAVAT", "Excavation"),
    (r"RETROFIT", "Retrofitting"),
    (r"SITE\s*DEV|PIPE\s*LAY", "Site development / pipelaying"),
    (r"CLEARING", "Clearing services"),
    (r"DESIGN", "Design and build"),
    (r"WAREHOUSE|BUILDING|CONSTRUCTION", "Building / warehouse construction"),
    (r"GLASS|ALUMIN|GLAZING", "Glass & aluminum works"),
)
_NOT_A_CONTRACTOR = re.compile(r"^(TERMINATED|N/?A|NONE|TBA|REFER TO .*)$", re.I)


def project_scope(name):
    text = (name or "").upper()
    for pattern, label in _SCOPE_RULES:
        if re.search(pattern, text):
            return label
    return "Other"


def _location_key(text):
    parts = [p.strip() for p in re.split(r"[,/]", text or "") if p.strip()]
    if not parts:
        return None
    return " ".join(parts[-1].split()).title()


def _bar_rows(counter, limit=None):
    rows = sorted(counter.items(), key=lambda kv: (-kv[1]["total"], kv[0]))
    if limit:
        rows = rows[:limit]
    peak = max((row["total"] for _key, row in rows), default=0) or 1
    return [{"label": key, **row, "pct": int(row["total"] * 100 / peak)} for key, row in rows]


def _stage_durations(leads):
    ids = [lead.lead_id for lead in leads]
    if not ids:
        return []
    by_lead = defaultdict(list)
    for entry in (
        MarketplaceLeadHistory.query
        .filter(MarketplaceLeadHistory.lead_id.in_(ids), MarketplaceLeadHistory.status.isnot(None))
        .order_by(MarketplaceLeadHistory.lead_id, MarketplaceLeadHistory.created_at, MarketplaceLeadHistory.history_id)
    ):
        by_lead[entry.lead_id].append(entry)
    totals = defaultdict(lambda: [0, 0])
    now = manila_now()
    lead_map = {lead.lead_id: lead for lead in leads}
    for lead_id, entries in by_lead.items():
        current, since = entries[0].status, entries[0].created_at
        for entry in entries[1:]:
            if entry.status != current:
                totals[current][0] += max(0, (entry.created_at - since).days)
                totals[current][1] += 1
                current, since = entry.status, entry.created_at
        lead = lead_map.get(lead_id)
        if lead is not None and not lead.is_closed:
            totals[current][0] += max(0, (now - since).days)
            totals[current][1] += 1
    rows = []
    for status in PROJECT_LEAD_STATUSES:
        days, count = totals.get(status, (0, 0))
        if count and status not in MARKETPLACE_LEAD_CLOSED_STATUSES:
            rows.append({"status": status, "label": transaction_status_label(status), "avg_days": round(days / count, 1), "count": count})
    peak = max((row["avg_days"] for row in rows), default=0) or 1
    for row in rows:
        row["pct"] = int(row["avg_days"] * 100 / peak)
    return rows


def project_analytics(date_from=None, date_to=None):
    query = _projects_query().options(
        joinedload(MarketplaceLead.awarded_contractor), joinedload(MarketplaceLead.assigned_user)
    )
    requested = func.coalesce(MarketplaceLead.date_requested, func.date(MarketplaceLead.created_at))
    if date_from:
        query = query.filter(requested >= date_from)
    if date_to:
        query = query.filter(requested <= date_to)
    leads = query.all()

    won = [lead for lead in leads if lead.status in PROJECT_WON_STATUSES]
    lost = [lead for lead in leads if lead.status == MARKETPLACE_LEAD_STATUS_TERMINATED]
    open_leads = [lead for lead in leads if not lead.is_closed]
    decided = len(won) + len(lost)
    contract_value = sum((Decimal(lead.contract_amount) for lead in won if lead.contract_amount), Decimal("0"))

    status_counts = defaultdict(int)
    for lead in leads:
        status_counts[lead.status or "new"] += 1
    peak = max(status_counts.values(), default=0) or 1
    pipeline = [
        {"status": status, "label": transaction_status_label(status), "count": status_counts.get(status, 0),
         "pct": int(status_counts.get(status, 0) * 100 / peak)}
        for status in PROJECT_LEAD_STATUSES
    ]

    def bucket():
        return {"total": 0, "open": 0, "won": 0}

    def add(counter, key, lead):
        row = counter[key]
        row["total"] += 1
        row["open"] += 0 if lead.is_closed else 1
        row["won"] += 1 if lead.status in PROJECT_WON_STATUSES else 0

    coordinators, coordinator_names = defaultdict(bucket), {}
    contractors = defaultdict(bucket)
    scopes = defaultdict(bucket)
    locations = defaultdict(bucket)
    for lead in leads:
        if lead.assigned_user is not None:
            name = lead.assigned_user.full_name or lead.assigned_user.username
        else:
            key = person_key(lead.project_coordinator)
            name = coordinator_names.setdefault(key, key.title()) if key else "Unassigned"
        add(coordinators, name, lead)
        if lead.awarded_contractor is not None:
            names = [lead.awarded_contractor.company_name]
        else:
            names = [n.strip() for n in (lead.assigned_contractor or "").split("/") if n.strip()]
        for name in names:
            if not _NOT_A_CONTRACTOR.match(name):
                add(contractors, " ".join(name.upper().replace(".", " ").split()), lead)
        add(scopes, project_scope(lead.item_name), lead)
        location = _location_key(lead.delivery_location)
        if location:
            add(locations, location, lead)

    return {
        "total": len(leads),
        "open": len(open_leads),
        "won": len(won),
        "lost": len(lost),
        "win_rate": round(len(won) * 100 / decided, 1) if decided else None,
        "contract_value": contract_value,
        "avg_open_aging": round(sum(lead.aging_days for lead in open_leads) / len(open_leads), 1) if open_leads else 0,
        "pipeline": pipeline,
        "stage_durations": _stage_durations(leads),
        "coordinators": _bar_rows(coordinators),
        "contractors": _bar_rows(contractors, limit=15),
        "scopes": _bar_rows(scopes),
        "locations": _bar_rows(locations, limit=12),
        "scope_choices": PROJECT_SCOPE_SUGGESTIONS,
    }
