"""Project delivery pages: staff actions, calendar, contractor portal, ProF view, field agents (projects and products), analytics."""

from datetime import date, datetime
from functools import wraps
from io import BytesIO

from flask import (
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from app import db
from app.auth import login_required, staff_or_admin_required
from app.config import (
    MARKETPLACE_LEAD_STATUS_LABELS,
    PROJECT_DOCUMENT_CONTRACTOR_KINDS,
    PROJECT_DOCUMENT_KINDS,
    PROJECT_EVENT_KINDS,
    PROJECT_EVENT_STATUS_LABELS,
    PROJECT_FIELD_DOCUMENT_KINDS,
    PROJECT_LEAD_STATUSES,
    MARKETPLACE_CATEGORY_PRODUCTS,
    PRODUCT_DOCUMENT_KINDS,
    PRODUCT_FIELD_DOCUMENT_KINDS,
    PRODUCT_LEAD_STATUSES,
    PRODUCT_MEMBER_DUTIES,
    PROJECT_MEMBER_DUTIES,
    is_contractor_role,
    is_member_role,
    is_staff_or_admin,
    is_supplier_role,
    normalize_role,
)
from app.duty_service import duty_label, is_field_agent
from app.models import MarketplaceLead
from app.product_service import field_products, get_product, product_field_documents, supplier_can_view
from app.project_service import (
    add_document,
    add_field_note,
    add_payment,
    calendar_month,
    complete_field_event,
    contractor_can_view,
    contractor_projects,
    contractor_updates,
    delete_document,
    delete_event,
    delete_payment,
    event_ics,
    field_can_see_document,
    field_can_view,
    field_documents,
    field_history,
    field_projects,
    field_roles,
    format_peso,
    generate_payment_schedule,
    get_document,
    get_event,
    get_payment,
    get_project,
    mark_payment_paid,
    member_projects,
    my_scheduled_events,
    post_payment_commission,
    project_analytics,
    project_documents,
    project_events,
    save_contract,
    save_event,
    save_stage_plan,
    set_event_status,
    stage_plan,
    suggest_status,
    unmark_payment_paid,
    unpost_payment_commission,
    update_progress,
)
from app.routes import _dashboard_user, main_routes
from app.timeutil import manila_now, manila_today
from app.transaction_service import field_unread_ids, mark_transaction_read


def _detail_url(lead_id, tab=None):
    url = url_for("main_routes.transaction_detail", lead_id=lead_id)
    return f"{url}#{tab}" if tab else url


def _run(action, success, lead_id, tab):
    """Run a staff action, flash the outcome, and return to the project tab."""
    try:
        result = action()
        if result is not False and success:
            flash(success, "success")
        elif result is False:
            flash("No changes to save.", "info")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
    return redirect(_detail_url(lead_id, tab))


def _project_or_404(lead_id):
    lead = get_project(lead_id)
    if lead is None:
        abort(404)
    return lead


# --------------------------------------------------------------------------- staff: stages / progress


@main_routes.route("/admin/projects/<int:lead_id>/stages", methods=["POST"])
@login_required
@staff_or_admin_required
def project_save_stages(lead_id):
    lead = _project_or_404(lead_id)
    user = _dashboard_user()
    return _run(lambda: save_stage_plan(lead, request.form, user), "Stage plan saved.", lead_id, "tab-stages")


@main_routes.route("/admin/projects/<int:lead_id>/progress", methods=["POST"])
@login_required
@staff_or_admin_required
def project_save_progress(lead_id):
    lead = _project_or_404(lead_id)
    user = _dashboard_user()
    return _run(
        lambda: update_progress(lead, request.form.get("progress_percent"), request.form.get("note"), user),
        "Progress updated.",
        lead_id,
        "tab-stages",
    )


# --------------------------------------------------------------------------- staff: documents


@main_routes.route("/admin/projects/<int:lead_id>/documents", methods=["POST"])
@login_required
@staff_or_admin_required
def project_add_document(lead_id):
    lead = _project_or_404(lead_id)
    user = _dashboard_user()
    return _run(
        lambda: add_document(lead, request.form, request.files.get("file"), user),
        "Document added.",
        lead_id,
        "tab-documents",
    )


@main_routes.route("/admin/projects/documents/<int:document_id>/delete", methods=["POST"])
@login_required
@staff_or_admin_required
def project_delete_document(document_id):
    document = get_document(document_id)
    if document is None:
        abort(404)
    user = _dashboard_user()
    lead_id = document.lead_id
    lead = db.session.get(MarketplaceLead, lead_id)
    tab = "product-documents" if lead and lead.transaction_type == MARKETPLACE_CATEGORY_PRODUCTS else "tab-documents"
    return _run(lambda: delete_document(document, user), "Document removed.", lead_id, tab)


def _contractor_id():
    user = _dashboard_user()
    if user is None or not is_contractor_role(user.role):
        return None
    return user.contractor_id


@main_routes.route("/projects/documents/<int:document_id>")
@login_required
def project_document_download(document_id):
    document = get_document(document_id)
    if document is None:
        abort(404)
    lead = db.session.get(MarketplaceLead, document.lead_id)
    role = session.get("role")
    if is_member_role(role):
        if not field_can_see_document(document, _dashboard_user()):
            abort(403)
    elif is_supplier_role(role):
        user = _dashboard_user()
        if not (document.shared_with_contractor and lead and supplier_can_view(lead, user.supplier_id)):
            abort(403)
    elif not is_staff_or_admin(role):
        contractor_id = _contractor_id()
        if not (document.shared_with_contractor and lead and contractor_can_view(lead, contractor_id)):
            abort(403)
    if document.external_url:
        return redirect(document.external_url)
    inline = (document.content_type or "").startswith("image/") or document.content_type == "application/pdf"
    return send_file(
        BytesIO(document.file_data or b""),
        mimetype=document.content_type or "application/octet-stream",
        as_attachment=not inline,
        download_name=document.file_name or f"document-{document.document_id}",
    )


# --------------------------------------------------------------------------- staff: schedule


@main_routes.route("/admin/projects/<int:lead_id>/events", methods=["POST"])
@login_required
@staff_or_admin_required
def project_add_event(lead_id):
    lead = _project_or_404(lead_id)
    user = _dashboard_user()
    return _run(lambda: save_event(lead, request.form, user), "Schedule saved.", lead_id, "tab-schedule")


@main_routes.route("/admin/projects/events/<int:event_id>/<action>", methods=["POST"])
@login_required
@staff_or_admin_required
def project_event_action(event_id, action):
    event = get_event(event_id)
    if event is None:
        abort(404)
    user = _dashboard_user()
    lead_id = event.lead_id
    if action == "update":
        func, message = (lambda: save_event(event.lead, request.form, user, event=event)), "Schedule updated."
    elif action in ("done", "cancelled", "scheduled"):
        func = lambda: set_event_status(event, action, request.form.get("outcome"), user)  # noqa: E731
        message = f"Marked {PROJECT_EVENT_STATUS_LABELS[action].lower()}."
    elif action == "delete":
        func, message = (lambda: delete_event(event, user)), "Schedule removed."
    else:
        abort(404)
    if request.form.get("next") == "calendar":
        try:
            func()
            flash(message, "success")
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        return redirect(request.referrer or url_for("main_routes.project_calendar"))
    return _run(func, message, lead_id, "tab-schedule")


@main_routes.route("/projects/events/<int:event_id>.ics")
@login_required
def project_event_ics(event_id):
    event = get_event(event_id)
    if event is None:
        abort(404)
    role = session.get("role")
    if is_member_role(role):
        if not field_can_view(event.lead, _dashboard_user()):
            abort(403)
    elif not is_staff_or_admin(role):
        if not contractor_can_view(event.lead, _contractor_id()):
            abort(403)
    return Response(
        event_ics(event),
        mimetype="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="tbgp-schedule-{event.event_id}.ics"'},
    )


@main_routes.route("/admin/projects/calendar")
@login_required
@staff_or_admin_required
def project_calendar():
    user = _dashboard_user()
    today = manila_today()
    raw = (request.args.get("month") or "").strip()
    try:
        first = datetime.strptime(raw, "%Y-%m").date() if raw else today.replace(day=1)
    except ValueError:
        first = today.replace(day=1)
    mine = request.args.get("mine") == "1"
    weeks, by_day = calendar_month(first.year, first.month, user=user, mine_only=mine)
    prev_month = date(first.year - 1, 12, 1) if first.month == 1 else date(first.year, first.month - 1, 1)
    next_month = date(first.year + 1, 1, 1) if first.month == 12 else date(first.year, first.month + 1, 1)
    return render_template(
        "project_calendar.html",
        fullname=user.full_name or "User",
        role=normalize_role(user.role),
        active_page="project_calendar",
        weeks=weeks,
        by_day=by_day,
        month_start=first,
        prev_month=prev_month.strftime("%Y-%m"),
        next_month=next_month.strftime("%Y-%m"),
        today=today,
        mine=mine,
        event_kinds=PROJECT_EVENT_KINDS,
        event_status_labels=PROJECT_EVENT_STATUS_LABELS,
    )


# --------------------------------------------------------------------------- staff: contract / payments


@main_routes.route("/admin/projects/<int:lead_id>/contract", methods=["POST"])
@login_required
@staff_or_admin_required
def project_save_contract(lead_id):
    lead = _project_or_404(lead_id)
    user = _dashboard_user()
    return _run(lambda: save_contract(lead, request.form, user), "Contract details saved.", lead_id, "tab-payments")


@main_routes.route("/admin/projects/<int:lead_id>/payments", methods=["POST"])
@login_required
@staff_or_admin_required
def project_add_payment(lead_id):
    lead = _project_or_404(lead_id)
    user = _dashboard_user()
    if request.form.get("mode") == "schedule":
        return _run(
            lambda: generate_payment_schedule(lead, request.form, user),
            "Payment schedule generated.",
            lead_id,
            "tab-payments",
        )
    return _run(lambda: add_payment(lead, request.form, user), "Payment milestone added.", lead_id, "tab-payments")


@main_routes.route("/admin/projects/payments/<int:payment_id>/<action>", methods=["POST"])
@login_required
@staff_or_admin_required
def project_payment_action(payment_id, action):
    payment = get_payment(payment_id)
    if payment is None:
        abort(404)
    user = _dashboard_user()
    actions = {
        "paid": (lambda: mark_payment_paid(payment, request.form, user), "Payment marked as received."),
        "unpaid": (lambda: unmark_payment_paid(payment, user), "Payment marked unpaid."),
        "delete": (lambda: delete_payment(payment, user), "Payment milestone removed."),
        "post": (
            lambda: post_payment_commission(payment, user),
            "Commission posted to Project Commission. Generate profit sharing for that billing date in Income Management.",
        ),
        "unpost": (lambda: unpost_payment_commission(payment, user), "Commission billing removed."),
    }
    if action not in actions:
        abort(404)
    func, message = actions[action]
    return _run(func, message, payment.lead_id, "tab-payments")


# --------------------------------------------------------------------------- contractor portal


def contractor_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_contractor_role(session.get("role")):
            flash("This page is for contractor accounts.", "warning")
            return redirect(url_for("main_routes.dashboard"))
        return func(*args, **kwargs)

    return wrapper


def _contractor_context(user, **extra):
    context = {
        "fullname": user.full_name or "Contractor",
        "role": normalize_role(user.role),
        "active_page": "contractor_projects",
        "contractor": user.linked_contractor,
        "status_labels": MARKETPLACE_LEAD_STATUS_LABELS,
        "document_kinds": PROJECT_DOCUMENT_KINDS,
        "contractor_document_kinds": PROJECT_DOCUMENT_CONTRACTOR_KINDS,
        "event_kinds": PROJECT_EVENT_KINDS,
        "format_peso": format_peso,
    }
    context.update(extra)
    return context


@main_routes.route("/contractor/projects")
@login_required
@contractor_required
def contractor_projects_list():
    user = _dashboard_user()
    rows = contractor_projects(user.contractor_id) if user.contractor_id else []
    return render_template("contractor_projects.html", **_contractor_context(user, rows=rows))


def _contractor_project_or_404(lead_id, user):
    lead = get_project(lead_id)
    if lead is None or not contractor_can_view(lead, user.contractor_id):
        abort(404)
    return lead


@main_routes.route("/contractor/projects/<int:lead_id>")
@login_required
@contractor_required
def contractor_project_detail(lead_id):
    user = _dashboard_user()
    lead = _contractor_project_or_404(lead_id, user)
    return render_template(
        "contractor_project_detail.html",
        **_contractor_context(
            user,
            lead=lead,
            documents=project_documents(lead.lead_id, contractor_view=True),
            events=[e for e in project_events(lead.lead_id) if e.status != "cancelled"],
            stage_plan=stage_plan(lead),
            updates=contractor_updates(lead.lead_id),
        ),
    )


def _contractor_action(lead_id, action, success):
    user = _dashboard_user()
    lead = _contractor_project_or_404(lead_id, user)
    try:
        action(lead, user)
        flash(success, "success")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
    return redirect(url_for("main_routes.contractor_project_detail", lead_id=lead_id))


@main_routes.route("/contractor/projects/<int:lead_id>/progress", methods=["POST"])
@login_required
@contractor_required
def contractor_report_progress(lead_id):
    def action(lead, user):
        if not update_progress(lead, request.form.get("progress_percent"), request.form.get("note"), user, by_contractor=True):
            raise ValueError("No changes to report.")

    return _contractor_action(lead_id, action, "Progress reported.")


@main_routes.route("/contractor/projects/<int:lead_id>/documents", methods=["POST"])
@login_required
@contractor_required
def contractor_upload_document(lead_id):
    def action(lead, user):
        add_document(lead, request.form, request.files.get("file"), user, by_contractor=True)

    return _contractor_action(lead_id, action, "File uploaded.")


# --------------------------------------------------------------------------- ProF: my referred projects


@main_routes.route("/my-projects")
@login_required
def my_projects():
    user = _dashboard_user()
    if not is_member_role(user.role):
        return redirect(url_for("main_routes.dashboard"))
    leads = member_projects(user.member_id)
    return render_template(
        "my_projects.html",
        fullname=user.full_name or "Member",
        role=normalize_role(user.role),
        active_page="my_projects",
        leads=leads,
        status_labels=MARKETPLACE_LEAD_STATUS_LABELS,
    )


# --------------------------------------------------------------------------- member field agents: my assignments


def field_agent_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_field_agent(_dashboard_user()):
            flash("My Assignments is for members holding a project field duty or the Sales Agent duty.", "warning")
            return redirect(url_for("main_routes.dashboard"))
        return func(*args, **kwargs)

    return wrapper


def _field_lead_or_404(lead_id, user):
    """A project or product transaction where the member holds a team slot."""
    lead = get_project(lead_id) or get_product(lead_id)
    if lead is None or not field_can_view(lead, user):
        abort(404)
    return lead


def _field_context(user, **extra):
    context = {
        "fullname": user.full_name or "Member",
        "role": normalize_role(user.role),
        "active_page": "my_assignments",
        "status_labels": MARKETPLACE_LEAD_STATUS_LABELS,
        "document_kinds": PROJECT_DOCUMENT_KINDS,
        "event_kinds": PROJECT_EVENT_KINDS,
        "event_status_labels": PROJECT_EVENT_STATUS_LABELS,
        "now": manila_now(),
        "current_user_id": user.user_id,
    }
    context.update(extra)
    return context


@main_routes.route("/my-assignments")
@login_required
@field_agent_required
def my_assignments():
    user = _dashboard_user()
    leads = field_projects(user)
    product_leads = field_products(user)
    return render_template(
        "my_assignments.html",
        **_field_context(
            user,
            leads=leads,
            product_leads=product_leads,
            roles={lead.lead_id: field_roles(lead, user) for lead in leads + product_leads},
            unread_ids=field_unread_ids(user.user_id),
            events=my_scheduled_events(user.user_id, limit=20),
            duties=[duty_label(duty) for duty in sorted(user.duty_keys)],
            has_project_duty=bool(user.duty_keys & set(PROJECT_MEMBER_DUTIES)),
            has_product_duty=bool(user.duty_keys & set(PRODUCT_MEMBER_DUTIES)),
        ),
    )


@main_routes.route("/my-assignments/<int:lead_id>")
@login_required
@field_agent_required
def my_assignment_detail(lead_id):
    user = _dashboard_user()
    lead = _field_lead_or_404(lead_id, user)
    mark_transaction_read(lead.lead_id, user.user_id)
    if lead.transaction_type == MARKETPLACE_CATEGORY_PRODUCTS:
        return render_template(
            "my_product_assignment_detail.html",
            **_field_context(
                user,
                lead=lead,
                my_roles=field_roles(lead, user),
                documents=product_field_documents(lead.lead_id),
                document_kinds=PRODUCT_DOCUMENT_KINDS,
                field_document_kinds=PRODUCT_FIELD_DOCUMENT_KINDS,
                history=field_history(lead.lead_id, transaction_type=MARKETPLACE_CATEGORY_PRODUCTS),
                lead_statuses=PRODUCT_LEAD_STATUSES,
            ),
        )
    return render_template(
        "my_assignment_detail.html",
        **_field_context(
            user,
            lead=lead,
            my_roles=field_roles(lead, user),
            stage_plan=stage_plan(lead),
            documents=field_documents(lead.lead_id),
            field_document_kinds=PROJECT_FIELD_DOCUMENT_KINDS,
            events=[event for event in project_events(lead.lead_id) if event.status != "cancelled"],
            history=field_history(lead.lead_id),
            lead_statuses=PROJECT_LEAD_STATUSES,
        ),
    )


@main_routes.route("/my-assignments/<int:lead_id>/<action>", methods=["POST"])
@login_required
@field_agent_required
def my_assignment_action(lead_id, action):
    user = _dashboard_user()
    lead = _field_lead_or_404(lead_id, user)
    form = request.form
    is_product = lead.transaction_type == MARKETPLACE_CATEGORY_PRODUCTS

    def progress():
        if not update_progress(lead, form.get("progress_percent"), form.get("note"), user, by_field_agent=True):
            raise ValueError("No changes to report.")

    actions = {
        "note": (
            lambda: add_field_note(lead, form.get("note"), user),
            f"Note added. The {'product' if is_product else 'project'} team was notified.",
        ),
        "document": (
            lambda: add_document(lead, form, request.files.get("file"), user, by_field_agent=True),
            "File uploaded.",
        ),
        "suggest": (
            lambda: suggest_status(lead, (form.get("status") or "").strip(), form.get("reason"), user),
            f"Status suggestion sent to the {'account officer' if is_product else 'project coordinator'}.",
        ),
    }
    if not is_product:
        actions["progress"] = (progress, "Progress reported.")
    if action not in actions:
        abort(404)
    func, message = actions[action]
    try:
        func()
        flash(message, "success")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
    return redirect(url_for("main_routes.my_assignment_detail", lead_id=lead_id))


@main_routes.route("/my-assignments/events/<int:event_id>/done", methods=["POST"])
@login_required
@field_agent_required
def my_assignment_event_done(event_id):
    user = _dashboard_user()
    event = get_event(event_id)
    if event is None or not field_can_view(event.lead, user):
        abort(404)
    try:
        complete_field_event(event, request.form.get("outcome"), user)
        flash("Schedule marked done.", "success")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
    if request.form.get("next") == "list":
        return redirect(url_for("main_routes.my_assignments"))
    return redirect(url_for("main_routes.my_assignment_detail", lead_id=event.lead_id))


# --------------------------------------------------------------------------- analytics


@main_routes.route("/trends-analysis/projects")
@login_required
@staff_or_admin_required
def trends_projects():
    user = _dashboard_user()

    def _date_arg(key):
        raw = (request.args.get(key) or "").strip()
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date() if raw else None
        except ValueError:
            return None

    date_from, date_to = _date_arg("date_from"), _date_arg("date_to")
    return render_template(
        "trends_projects.html",
        fullname=user.full_name or "User",
        role=normalize_role(user.role),
        active_page="trends_projects",
        analytics=project_analytics(date_from, date_to),
        date_from=date_from.isoformat() if date_from else "",
        date_to=date_to.isoformat() if date_to else "",
        format_peso=format_peso,
    )
