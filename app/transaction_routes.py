"""Admin/Staff transaction monitoring pages (registered on the main_routes blueprint)."""

from flask import abort, flash, redirect, render_template, request, send_file, url_for

from app import db
from app.auth import admin_required, login_required, staff_or_admin_required
from app.config import (
    MARKETPLACE_CATEGORY_PRODUCTS,
    MARKETPLACE_LEAD_CLOSED_STATUSES,
    MARKETPLACE_LEAD_STATUS_LABELS,
    PRODUCT_ORDER_STATUSES,
    TRANSACTION_NOTE_KINDS,
    TRANSACTION_SOURCE_LABELS,
    TRANSACTION_TYPE_LABELS,
    TRANSACTION_TYPE_PROJECTS,
    is_admin_role,
    normalize_role,
    team_slot_labels_for_type,
)
from app.duty_service import field_agents_for_type
from app.marketplace_service import marketplace_listing_options
from app.product_service import product_attention_map, product_detail_context
from app.project_service import contractor_options, event_assignees, project_attention_map, project_detail_context
from app.routes import _dashboard_user, main_routes
from app.transaction_service import (
    add_followup_note,
    assign_to_user,
    assignee_options,
    create_manual_transaction,
    export_transactions_xlsx,
    get_transaction,
    import_transactions_from_xlsx,
    mark_all_transactions_read,
    mark_transaction_read,
    preview_reference_number,
    search_transactions,
    status_counts,
    supplier_options,
    team_options,
    transaction_field_labels,
    transaction_filters_from_args,
    transaction_status_choices,
    transaction_history,
    unread_transaction_ids,
    update_transaction,
)
from app.timeutil import manila_now


def _common_context(user, transaction_type=None, **extra):
    is_project = transaction_type == TRANSACTION_TYPE_PROJECTS
    is_product = transaction_type == MARKETPLACE_CATEGORY_PRODUCTS
    context = {
        "fullname": user.full_name or "Admin",
        "role": normalize_role(user.role),
        "active_page": "projects" if is_project else "transactions",
        "is_project": is_project,
        "is_product": is_product,
        "has_team": is_project or is_product,
        "field_labels": transaction_field_labels(transaction_type),
        "status_choices": transaction_status_choices(transaction_type),
        "status_labels": MARKETPLACE_LEAD_STATUS_LABELS,
        "closed_statuses": MARKETPLACE_LEAD_CLOSED_STATUSES,
        "transaction_types": TRANSACTION_TYPE_LABELS,
        "source_labels": TRANSACTION_SOURCE_LABELS,
        "note_kinds": TRANSACTION_NOTE_KINDS,
        "assignees": assignee_options(),
        "can_import": is_admin_role(user.role),
        "team_slot_labels": team_slot_labels_for_type(transaction_type),
        "product_order_statuses": PRODUCT_ORDER_STATUSES,
    }
    if is_project or is_product:
        context["team_options"] = team_options(transaction_type, extra.get("lead"))
    if is_project:
        context["contractor_choices"] = contractor_options()
    if is_product:
        context["supplier_choices"] = supplier_options()
    context.update(extra)
    return context


@main_routes.route("/admin/transactions")
@login_required
@staff_or_admin_required
def transactions_list():
    user = _dashboard_user()
    filters = transaction_filters_from_args(request.args)
    if filters["transaction_type"] not in TRANSACTION_TYPE_LABELS and filters["transaction_type"] != "all":
        filters["transaction_type"] = MARKETPLACE_CATEGORY_PRODUCTS
    leads = search_transactions(filters, user=user)
    attention = {}
    extra = {}
    if filters["transaction_type"] == TRANSACTION_TYPE_PROJECTS:
        attention = project_attention_map()
        extra["assignees"] = event_assignees()
    elif filters["transaction_type"] == MARKETPLACE_CATEGORY_PRODUCTS:
        attention = product_attention_map()
        extra["assignees"] = assignee_options() + field_agents_for_type(MARKETPLACE_CATEGORY_PRODUCTS)
    if attention and filters.get("attention"):
        leads = [lead for lead in leads if lead.lead_id in attention]
    return render_template(
        "transactions.html",
        **_common_context(
            user,
            transaction_type=filters["transaction_type"],
            attention=attention,
            leads=leads,
            filters=filters,
            counts=status_counts(filters["transaction_type"]),
            unread_ids=unread_transaction_ids(user.user_id),
            **extra,
        ),
    )


@main_routes.route("/admin/transactions/export.xlsx")
@login_required
@staff_or_admin_required
def transactions_export():
    user = _dashboard_user()
    filters = transaction_filters_from_args(request.args)
    leads = search_transactions(filters, user=user, limit=10000)
    output = export_transactions_xlsx(leads, filters["transaction_type"])
    prefix = "projects" if filters["transaction_type"] == TRANSACTION_TYPE_PROJECTS else "transactions"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"tbgp-{prefix}-{manila_now().strftime('%Y%m%d-%H%M')}.xlsx",
    )


@main_routes.route("/admin/transactions/import", methods=["POST"])
@login_required
@admin_required
def transactions_import():
    user = _dashboard_user()
    upload = request.files.get("file")
    if not upload or not upload.filename:
        flash("Choose the monitoring sheet (.xlsx) to upload.", "warning")
        return redirect(url_for("main_routes.transactions_list"))
    if not upload.filename.lower().endswith((".xlsx", ".xlsm")):
        flash("Upload an Excel .xlsx file.", "danger")
        return redirect(url_for("main_routes.transactions_list"))

    transaction_type = request.form.get("transaction_type") or MARKETPLACE_CATEGORY_PRODUCTS
    try:
        summary = import_transactions_from_xlsx(
            upload.stream,
            transaction_type=transaction_type,
            update_existing=request.form.get("update_existing") == "1",
            user_id=user.user_id,
        )
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
        return redirect(url_for("main_routes.transactions_list"))
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        flash(f"Import failed: {exc}", "danger")
        return redirect(url_for("main_routes.transactions_list"))

    flash(
        f"Imported sheet '{summary['sheet']}': {summary['created']} added, "
        f"{summary['updated']} updated, {summary['skipped']} already existed.",
        "success",
    )
    for message in summary["errors"][:15]:
        flash(message, "warning")
    if len(summary["errors"]) > 15:
        flash(f"…and {len(summary['errors']) - 15} more rows were skipped.", "warning")
    return redirect(url_for("main_routes.transactions_list", type=transaction_type))


@main_routes.route("/admin/transactions/mark-all-read", methods=["POST"])
@login_required
@staff_or_admin_required
def transactions_mark_all_read():
    user = _dashboard_user()
    count = mark_all_transactions_read(user.user_id)
    flash(f"Marked {count} transaction(s) as seen.", "success")
    return redirect(request.referrer or url_for("main_routes.transactions_list"))


@main_routes.route("/admin/transactions/new", methods=["GET", "POST"])
@login_required
@staff_or_admin_required
def transaction_new():
    user = _dashboard_user()
    form_values = request.form if request.method == "POST" else {}
    if request.method == "POST":
        try:
            lead = create_manual_transaction(request.form, user)
            flash(f"Transaction {lead.reference_number} created.", "success")
            return redirect(url_for("main_routes.transaction_detail", lead_id=lead.lead_id))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
    transaction_type = (
        (form_values.get("transaction_type") if form_values else None)
        or request.args.get("transaction_type")
        or MARKETPLACE_CATEGORY_PRODUCTS
    )
    if transaction_type not in TRANSACTION_TYPE_LABELS:
        transaction_type = MARKETPLACE_CATEGORY_PRODUCTS
    return render_template(
        "transaction_form.html",
        **_common_context(
            user,
            transaction_type=transaction_type,
            selected_type=transaction_type,
            lead=None,
            form_values=form_values,
            listing_options=marketplace_listing_options(),
            reference_preview=preview_reference_number(transaction_type),
        ),
    )


@main_routes.route("/admin/transactions/<int:lead_id>", methods=["GET", "POST"])
@login_required
@staff_or_admin_required
def transaction_detail(lead_id):
    user = _dashboard_user()
    lead = get_transaction(lead_id)
    if not lead:
        abort(404)

    if request.method == "POST":
        try:
            changed = update_transaction(lead, request.form, user)
            flash(
                f"Transaction {lead.reference_number} updated." if changed else "No changes to save.",
                "success" if changed else "info",
            )
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        return redirect(url_for("main_routes.transaction_detail", lead_id=lead_id))

    mark_transaction_read(lead.lead_id, user.user_id)
    extra = {}
    if lead.transaction_type == TRANSACTION_TYPE_PROJECTS:
        extra = project_detail_context(lead, user)
    elif lead.transaction_type == MARKETPLACE_CATEGORY_PRODUCTS:
        extra = product_detail_context(lead, user)
    return render_template(
        "transaction_detail.html",
        **_common_context(
            user,
            transaction_type=lead.transaction_type,
            lead=lead,
            history=transaction_history(lead.lead_id),
            **extra,
        ),
    )


@main_routes.route("/admin/transactions/<int:lead_id>/note", methods=["POST"])
@login_required
@staff_or_admin_required
def transaction_add_note(lead_id):
    user = _dashboard_user()
    lead = get_transaction(lead_id)
    if not lead:
        abort(404)
    try:
        add_followup_note(lead, request.form.get("kind"), request.form.get("note"), user)
        flash("Follow-up logged.", "success")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
    return redirect(url_for("main_routes.transaction_detail", lead_id=lead_id) + "#history")


@main_routes.route("/admin/transactions/<int:lead_id>/assign-me", methods=["POST"])
@login_required
@staff_or_admin_required
def transaction_assign_me(lead_id):
    user = _dashboard_user()
    lead = get_transaction(lead_id)
    if not lead:
        abort(404)
    try:
        if assign_to_user(lead, user):
            flash(f"{lead.reference_number} is now assigned to you.", "success")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
    return redirect(request.referrer or url_for("main_routes.transaction_detail", lead_id=lead_id))
