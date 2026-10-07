"""Audit log viewers: the full trail for Admin/PortalAdmin in the portal and for SiteAdmin in Site Content."""

from flask import Response, render_template, request

from app.audit_service import (
    CATEGORY_LABELS,
    OUTCOME_LABELS,
    audit_csv,
    audit_filters_from,
    audit_page,
    audit_target_types,
    describe_changes,
)
from app.auth import admin_required, login_required, site_admin_required
from app.config import normalize_role
from app.routes import _dashboard_user, main_routes
from app.site_admin_routes import site_admin_bp
from app.timeutil import manila_today

PER_PAGE = 50


def _context(export_endpoint, list_endpoint):
    filters = audit_filters_from(request.args)
    page = request.args.get("page", type=int) or 1
    rows, total = audit_page(filters, page=page, per_page=PER_PAGE)
    return {
        "rows": rows,
        "total": total,
        "page": page,
        "pages": max(1, (total + PER_PAGE - 1) // PER_PAGE),
        "filters": filters,
        "query_filters": {key: value for key, value in filters.items() if value},
        "category_labels": CATEGORY_LABELS,
        "category_choices": CATEGORY_LABELS,
        "outcome_labels": OUTCOME_LABELS,
        "target_types": audit_target_types(),
        "describe_changes": describe_changes,
        "export_endpoint": export_endpoint,
        "list_endpoint": list_endpoint,
        "today": manila_today(),
    }


def _csv_response():
    body = audit_csv(audit_filters_from(request.args))
    return Response(
        "\ufeff" + body,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=tbgp-audit-log-{manila_today().isoformat()}.csv"},
    )


@main_routes.route("/admin/audit-log")
@login_required
@admin_required
def audit_log():
    user = _dashboard_user()
    return render_template(
        "audit_log.html",
        fullname=user.full_name or "User",
        role=normalize_role(user.role),
        active_page="audit_log",
        **_context("main_routes.audit_log_export", "main_routes.audit_log"),
    )


@main_routes.route("/admin/audit-log/export.csv")
@login_required
@admin_required
def audit_log_export():
    return _csv_response()


@site_admin_bp.route("/audit-log", endpoint="audit_log")
@login_required
@site_admin_required
def site_audit_log():
    return render_template(
        "site_admin/audit_log.html",
        active_page="audit_log",
        **_context("site_admin.audit_log_export", "site_admin.audit_log"),
    )


@site_admin_bp.route("/audit-log/export.csv", endpoint="audit_log_export")
@login_required
@site_admin_required
def site_audit_log_export():
    return _csv_response()
