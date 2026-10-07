"""Product orders: team duties, needs-attention alerts, duty dashboard, sales agents, supplier portal."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app import db
from app.config import (
    DUTY_ACCOUNT_OFFICER,
    DUTY_LOGISTICS_COORDINATOR,
    DUTY_PRICING_OFFICER,
    DUTY_PRODUCTS_MANAGER,
    DUTY_SALES_AGENT,
    DUTY_SOURCING_OFFICER,
    MARKETPLACE_CATEGORY_PRODUCTS,
    MARKETPLACE_LEAD_CLOSED_STATUSES,
    MARKETPLACE_LEAD_STATUS_ON_HOLD,
    MARKETPLACE_LEAD_STATUS_QUOTATION_SUBMITTED,
    PRODUCT_DOCUMENT_KINDS,
    PRODUCT_DOCUMENT_SUPPLIER_KINDS,
    PRODUCT_FIELD_DOCUMENT_KINDS,
    PRODUCT_LOGISTICS_STATUSES,
    PRODUCT_PRICING_STATUSES,
    PRODUCT_QUOTE_FOLLOWUP_DAYS,
    PRODUCT_SOURCING_STATUSES,
    PRODUCT_STALE_DAYS,
    PRODUCT_STATUS_DELIVERED,
    PRODUCT_STUCK_DAYS,
    PRODUCT_TEAM_SLOT_LABELS,
    PRODUCT_TEAM_SLOTS,
    PRODUCT_UNASSIGNED_DAYS,
    is_admin_role,
)
from app.duty_service import duty_holders, team_filter
from app.models import MarketplaceLead, MarketplaceLeadHistory
from app.project_service import (
    _notify_team,
    _touch,
    project_documents,
    recent_suggestions,
)
from app.timeutil import manila_today
from app.transaction_service import _append_history, _clean, transaction_status_label

PRODUCT_TEAM_RELATIONS = {
    "assigned_user_id": "assigned_user",
    "sourcing_user_id": "sourcing_user",
    "estimator_user_id": "estimator_user",
    "logistics_user_id": "logistics_user",
    "agent_user_id": "agent_user",
}
# Statuses where the order is with the client and nobody internal is expected to move it.
_NOT_STUCK_STATUSES = (MARKETPLACE_LEAD_STATUS_ON_HOLD, MARKETPLACE_LEAD_STATUS_QUOTATION_SUBMITTED)
_TARGET_DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%m.%d.%y", "%m.%d.%Y", "%B %d, %Y", "%b %d, %Y")


def _products_query():
    return MarketplaceLead.query.filter(MarketplaceLead.transaction_type == MARKETPLACE_CATEGORY_PRODUCTS)


def _team_options():
    return [joinedload(getattr(MarketplaceLead, relation)) for relation in PRODUCT_TEAM_RELATIONS.values()]


def _open_products_query():
    return (
        _products_query()
        .options(*_team_options(), joinedload(MarketplaceLead.supplier))
        .filter(or_(MarketplaceLead.status.is_(None), MarketplaceLead.status.notin_(MARKETPLACE_LEAD_CLOSED_STATUSES)))
    )


def get_product(lead_id):
    lead = (
        _products_query()
        .options(*_team_options(), joinedload(MarketplaceLead.supplier))
        .filter(MarketplaceLead.lead_id == int(lead_id))
        .first()
    )
    return lead


def team_member(lead, slot):
    return getattr(lead, PRODUCT_TEAM_RELATIONS[slot])


def on_product_status_change(lead, status, user_id=None):
    """Tell the product team about a status change (called from set_transaction_status)."""
    if lead.lead_id:
        _notify_team(lead, user_id)


# --------------------------------------------------------------------------- alerts


def parse_target_date(text):
    """The client's target date when the free-text field holds a plain date, else None."""
    value = (text or "").strip()
    if not value:
        return None
    match = re.search(r"\d{4}-\d{2}-\d{2}", value)
    if match:
        value = match.group(0)
    for fmt in _TARGET_DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def product_attention_map(leads=None):
    """lead_id -> list of reasons an open product transaction needs attention."""
    if leads is None:
        leads = _open_products_query().all()
    today = manila_today()
    reasons = defaultdict(list)
    for lead in leads:
        if lead.is_closed:
            continue
        items = reasons[lead.lead_id]
        status = lead.status or "new"
        last = lead.last_activity_at
        idle = (today - last.date()).days if last else 0
        if not lead.assigned_user_id and lead.aging_days >= PRODUCT_UNASSIGNED_DAYS:
            items.append("No account officer assigned")
        if status == MARKETPLACE_LEAD_STATUS_QUOTATION_SUBMITTED and lead.days_in_status > PRODUCT_QUOTE_FOLLOWUP_DAYS:
            items.append(f"Quotation sent {lead.days_in_status} days ago — follow up the client")
        elif status not in _NOT_STUCK_STATUSES and lead.days_in_status > PRODUCT_STUCK_DAYS:
            items.append(f"{lead.days_in_status} days in {transaction_status_label(status)}")
        if idle > PRODUCT_STALE_DAYS:
            items.append(f"No update in {idle} days")
        if lead.delivery_date and lead.delivery_date < today and status != PRODUCT_STATUS_DELIVERED:
            items.append(f"Delivery scheduled {lead.delivery_date.isoformat()} has passed")
        if status in PRODUCT_LOGISTICS_STATUSES and not lead.logistics_user_id:
            items.append("No logistics coordinator for the delivery")
        if status in PRODUCT_LOGISTICS_STATUSES and not lead.delivery_date:
            items.append("Delivery date not scheduled")
        target = parse_target_date(lead.estimated_implementation)
        if target and target < today and status != PRODUCT_STATUS_DELIVERED:
            items.append(f"Client target date {target.isoformat()} has passed")
    return {lead_id: items for lead_id, items in reasons.items() if items}


def products_needing_attention(limit=6):
    leads = _open_products_query().all()
    attention = product_attention_map(leads)
    flagged = [lead for lead in leads if lead.lead_id in attention]
    flagged.sort(key=lambda lead: (-len(attention[lead.lead_id]), -lead.days_in_status))
    return {"count": len(flagged), "items": [(lead, attention[lead.lead_id]) for lead in flagged[:limit]]}


# --------------------------------------------------------------------------- duty dashboard


def product_team_workload(leads, attention):
    """One row per product duty holder / current team member with open-order counts per slot."""
    rows = {}

    def row_for(member):
        if member.user_id not in rows:
            rows[member.user_id] = {"user": member, "attention": 0, "total": 0, **{slot: 0 for slot in PRODUCT_TEAM_SLOTS}}
        return rows[member.user_id]

    for duty in PRODUCT_TEAM_SLOTS.values():
        for member in duty_holders(duty):
            row_for(member)
    for lead in leads:
        members = {}
        for slot in PRODUCT_TEAM_SLOTS:
            member = team_member(lead, slot)
            if member is not None:
                row_for(member)[slot] += 1
                members[member.user_id] = member
        for user_id in members:
            rows[user_id]["total"] += 1
            if lead.lead_id in attention:
                rows[user_id]["attention"] += 1
    return sorted(rows.values(), key=lambda row: (-row["total"], (row["user"].full_name or row["user"].username).lower()))


def _by_attention(leads, attention):
    return sorted(leads, key=lambda lead: (-len(attention.get(lead.lead_id, [])), -lead.days_in_status))


def _unclaimed(statuses, column):
    return (
        _products_query()
        .filter(MarketplaceLead.status.in_(statuses), getattr(MarketplaceLead, column).is_(None))
        .count()
    )


def product_duty_dashboard(user, limit=6):
    """Dashboard cards for the user's product duties (Admins also get the manager view)."""
    duties = user.duty_keys
    is_manager = DUTY_PRODUCTS_MANAGER in duties or is_admin_role(user.role)
    if not (is_manager or duties & set(PRODUCT_TEAM_SLOTS.values())):
        return None
    query = _open_products_query()
    if not is_manager:
        query = query.filter(team_filter(user.user_id))
    leads = query.all()
    attention = product_attention_map(leads)
    uid = user.user_id
    cards = {"attention": attention, "slot_labels": PRODUCT_TEAM_SLOT_LABELS, "status_label": transaction_status_label}

    if is_manager:
        unassigned = [lead for lead in leads if not lead.assigned_user_id]
        cards["manager"] = {
            "workload": product_team_workload(leads, attention),
            "unassigned": sorted(unassigned, key=lambda lead: -lead.aging_days)[:limit],
            "unassigned_count": len(unassigned),
            "attention_count": len(attention),
            "no_sourcing": sum(1 for lead in leads if lead.status in PRODUCT_SOURCING_STATUSES and not lead.sourcing_user_id),
            "no_pricing": sum(1 for lead in leads if lead.status in PRODUCT_PRICING_STATUSES and not lead.estimator_user_id),
            "no_logistics": sum(1 for lead in leads if lead.status in PRODUCT_LOGISTICS_STATUSES and not lead.logistics_user_id),
            "suggestions": recent_suggestions(transaction_type=MARKETPLACE_CATEGORY_PRODUCTS),
        }
    if DUTY_ACCOUNT_OFFICER in duties:
        mine = [lead for lead in leads if lead.assigned_user_id == uid]
        cards["account"] = {
            "count": len(mine),
            "attention_count": sum(1 for lead in mine if lead.lead_id in attention),
            "followups": sum(1 for lead in mine if lead.status == MARKETPLACE_LEAD_STATUS_QUOTATION_SUBMITTED),
            "items": _by_attention(mine, attention)[:limit],
        }
    if DUTY_SOURCING_OFFICER in duties:
        queue = [lead for lead in leads if lead.sourcing_user_id == uid and lead.status in PRODUCT_SOURCING_STATUSES]
        cards["sourcing"] = {
            "count": len(queue),
            "items": sorted(queue, key=lambda lead: -lead.days_in_status)[:limit],
            "unclaimed": _unclaimed(PRODUCT_SOURCING_STATUSES, "sourcing_user_id"),
        }
    if DUTY_PRICING_OFFICER in duties:
        queue = [lead for lead in leads if lead.estimator_user_id == uid and lead.status in PRODUCT_PRICING_STATUSES]
        cards["pricing"] = {
            "count": len(queue),
            "items": sorted(queue, key=lambda lead: -lead.days_in_status)[:limit],
            "unclaimed": _unclaimed(PRODUCT_PRICING_STATUSES, "estimator_user_id"),
        }
    if DUTY_LOGISTICS_COORDINATOR in duties:
        queue = [lead for lead in leads if lead.logistics_user_id == uid and lead.status in PRODUCT_LOGISTICS_STATUSES]
        cards["logistics"] = {
            "count": len(queue),
            "items": sorted(queue, key=lambda lead: (lead.delivery_date is None, lead.delivery_date or date.max))[:limit],
            "unclaimed": _unclaimed(PRODUCT_LOGISTICS_STATUSES, "logistics_user_id"),
        }
    if DUTY_SALES_AGENT in duties:
        mine = [lead for lead in leads if lead.agent_user_id == uid]
        cards["agent"] = {
            "count": len(mine),
            "items": _by_attention(mine, attention)[:limit],
        }
    return cards


# --------------------------------------------------------------------------- staff order panel


def product_detail_context(lead, user):
    return {
        "documents": project_documents(lead.lead_id),
        "document_kinds": PRODUCT_DOCUMENT_KINDS,
        "supplier_document_kinds": PRODUCT_DOCUMENT_SUPPLIER_KINDS,
        "attention_reasons": product_attention_map([lead]).get(lead.lead_id, []),
        "target_date": parse_target_date(lead.estimated_implementation),
        "today": manila_today(),
    }


# --------------------------------------------------------------------------- sales agents (members)


def field_products(user):
    """Product transactions where the member holds a team slot (open first, newest activity first)."""
    leads = (
        _products_query()
        .options(*_team_options())
        .filter(team_filter(user.user_id))
        .order_by(MarketplaceLead.updated_at.desc().nullslast())
        .all()
    )
    return sorted(leads, key=lambda lead: lead.is_closed)


def product_field_documents(lead_id):
    return [doc for doc in project_documents(lead_id) if doc.kind in PRODUCT_FIELD_DOCUMENT_KINDS]


# --------------------------------------------------------------------------- supplier portal

SUPPLIER_HISTORY_TYPES = ("supplier", "document")


def supplier_orders(supplier_id):
    """Product orders assigned to the supplier (newest activity first)."""
    if not supplier_id:
        return []
    return (
        _products_query()
        .options(joinedload(MarketplaceLead.assigned_user), joinedload(MarketplaceLead.logistics_user))
        .filter(MarketplaceLead.supplier_id == supplier_id)
        .order_by(MarketplaceLead.updated_at.desc().nullslast())
        .all()
    )


def supplier_can_view(lead, supplier_id):
    """Only the supplier assigned to the order sees it in the supplier portal."""
    return bool(supplier_id) and lead.supplier_id == supplier_id


def supplier_updates(lead_id):
    """The supplier's own updates and uploads (staff document notes may name internal files)."""
    entries = (
        MarketplaceLeadHistory.query
        .options(joinedload(MarketplaceLeadHistory.created_by))
        .filter(
            MarketplaceLeadHistory.lead_id == lead_id,
            MarketplaceLeadHistory.event_type.in_(SUPPLIER_HISTORY_TYPES),
        )
        .order_by(MarketplaceLeadHistory.created_at.desc())
        .limit(60)
        .all()
    )
    return [
        entry for entry in entries
        if entry.event_type == "supplier" or (entry.note or "").endswith("(uploaded by supplier)")
    ][:30]


def add_supplier_update(lead, note, user):
    text = _clean(note)
    if not text:
        raise ValueError("Write an update first.")
    _touch(lead)
    _append_history(lead, event_type="supplier", note=f"Supplier update: {text}", user_id=user.user_id)
    _notify_team(lead, user.user_id)
    db.session.commit()


def supplier_dashboard_summary(supplier_id):
    rows = supplier_orders(supplier_id)
    active = [lead for lead in rows if not lead.is_closed]
    today = manila_today()
    return {
        "total": len(rows),
        "active": active,
        "for_delivery": [lead for lead in active if lead.status in PRODUCT_LOGISTICS_STATUSES],
        "overdue": sum(
            1 for lead in active
            if lead.delivery_date and lead.delivery_date < today and lead.status != PRODUCT_STATUS_DELIVERED
        ),
        "completed": sum(1 for lead in rows if lead.is_closed),
    }
