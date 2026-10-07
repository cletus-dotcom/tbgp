"""Product order pages: staff documents and the supplier portal (My Orders)."""

from functools import wraps

from flask import abort, flash, redirect, render_template, request, session, url_for

from app import db
from app.auth import login_required, staff_or_admin_required
from app.config import (
    MARKETPLACE_LEAD_STATUS_LABELS,
    PRODUCT_DOCUMENT_KINDS,
    PRODUCT_DOCUMENT_SUPPLIER_KINDS,
    PRODUCT_ORDER_STATUSES,
    is_supplier_role,
    normalize_role,
)
from app.product_service import (
    add_supplier_update,
    get_product,
    supplier_can_view,
    supplier_orders,
    supplier_updates,
)
from app.project_service import add_document, project_documents
from app.routes import _dashboard_user, main_routes
from app.timeutil import manila_today


def _product_or_404(lead_id):
    lead = get_product(lead_id)
    if lead is None:
        abort(404)
    return lead


# --------------------------------------------------------------------------- staff: documents


@main_routes.route("/admin/products/<int:lead_id>/documents", methods=["POST"])
@login_required
@staff_or_admin_required
def product_add_document(lead_id):
    lead = _product_or_404(lead_id)
    user = _dashboard_user()
    try:
        add_document(lead, request.form, request.files.get("file"), user)
        flash("Document added.", "success")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
    return redirect(url_for("main_routes.transaction_detail", lead_id=lead_id) + "#product-documents")


# --------------------------------------------------------------------------- supplier portal


def supplier_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_supplier_role(session.get("role")):
            flash("This page is for supplier accounts.", "warning")
            return redirect(url_for("main_routes.dashboard"))
        return func(*args, **kwargs)

    return wrapper


def _supplier_context(user, **extra):
    context = {
        "fullname": user.full_name or "Supplier",
        "role": normalize_role(user.role),
        "active_page": "supplier_orders",
        "supplier": user.linked_supplier,
        "status_labels": MARKETPLACE_LEAD_STATUS_LABELS,
        "document_kinds": PRODUCT_DOCUMENT_KINDS,
        "supplier_document_kinds": PRODUCT_DOCUMENT_SUPPLIER_KINDS,
        "product_order_statuses": PRODUCT_ORDER_STATUSES,
        "today": manila_today(),
    }
    context.update(extra)
    return context


@main_routes.route("/supplier/orders")
@login_required
@supplier_required
def supplier_orders_list():
    user = _dashboard_user()
    rows = supplier_orders(user.supplier_id) if user.supplier_id else []
    return render_template("supplier_orders.html", **_supplier_context(user, rows=rows))


def _supplier_order_or_404(lead_id, user):
    lead = get_product(lead_id)
    if lead is None or not supplier_can_view(lead, user.supplier_id):
        abort(404)
    return lead


@main_routes.route("/supplier/orders/<int:lead_id>")
@login_required
@supplier_required
def supplier_order_detail(lead_id):
    user = _dashboard_user()
    lead = _supplier_order_or_404(lead_id, user)
    return render_template(
        "supplier_order_detail.html",
        **_supplier_context(
            user,
            lead=lead,
            documents=project_documents(lead.lead_id, contractor_view=True),
            updates=supplier_updates(lead.lead_id),
        ),
    )


def _supplier_action(lead_id, action, success):
    user = _dashboard_user()
    lead = _supplier_order_or_404(lead_id, user)
    try:
        action(lead, user)
        flash(success, "success")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
    return redirect(url_for("main_routes.supplier_order_detail", lead_id=lead_id))


@main_routes.route("/supplier/orders/<int:lead_id>/update", methods=["POST"])
@login_required
@supplier_required
def supplier_post_update(lead_id):
    return _supplier_action(
        lead_id,
        lambda lead, user: add_supplier_update(lead, request.form.get("note"), user),
        "Update sent to the TBGP product team.",
    )


@main_routes.route("/supplier/orders/<int:lead_id>/documents", methods=["POST"])
@login_required
@supplier_required
def supplier_upload_document(lead_id):
    return _supplier_action(
        lead_id,
        lambda lead, user: add_document(lead, request.form, request.files.get("file"), user, by_supplier=True),
        "File uploaded.",
    )
