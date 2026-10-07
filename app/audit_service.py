"""Central audit trail: who did what, when, from where, the outcome, and which records changed.

Every write request (POST/PUT/PATCH/DELETE), every data export or download, sign-ins and
sign-outs, and every access-denied attempt is recorded by an after_request hook. Field-level
changes come from SQLAlchemy flush events and are kept only for transactions that committed.
"""

import csv
import io
import logging
import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from flask import g, has_request_context, request, session
from flask.signals import message_flashed
from sqlalchemy import event, inspect as sa_inspect, or_
from sqlalchemy.orm import Session

from app import db
from app.models import AuditLog
from app.timeutil import manila_now

logger = logging.getLogger(__name__)

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

CATEGORY_LABELS = {
    "auth": "Sign-in",
    "users": "Users & access",
    "members": "Members",
    "suspensions": "Suspensions",
    "partners": "Contractors & suppliers",
    "income": "Income & commission",
    "payouts": "Payouts",
    "transactions": "Transactions & projects",
    "notices": "Notices",
    "site": "Site content",
    "exports": "Exports & downloads",
    "other": "Other",
}

OUTCOME_LABELS = {"success": "Success", "failed": "Failed", "denied": "Denied"}

# endpoint -> (category, action label). GET endpoints listed here are logged because they hand out data.
ACTIONS = {
    "main_routes.login": ("auth", "Signed in"),
    "main_routes.logout": ("auth", "Signed out"),
    "main_routes.member_change_own_password": ("auth", "Changed own password"),
    "main_routes.add_user": ("users", "Added user"),
    "main_routes.update_user": ("users", "Updated user"),
    "main_routes.delete_user": ("users", "Deleted user"),
    "main_routes.admin_create_member": ("members", "Added member"),
    "main_routes.add_member": ("members", "Imported members"),
    "main_routes.admin_update_member": ("members", "Updated member"),
    "main_routes.admin_delete_member": ("members", "Deleted member"),
    "main_routes.member_update_own_profile": ("members", "Updated own profile"),
    "main_routes.member_positions": ("members", "Changed portal positions"),
    "main_routes.reimport_members": ("members", "Re-imported members"),
    "main_routes.purge_members": ("members", "Deleted all members"),
    "main_routes.member_suspensions": ("suspensions", "Changed member suspension"),
    "main_routes.admin_create_contractor": ("partners", "Added contractor"),
    "main_routes.admin_update_contractor": ("partners", "Updated contractor"),
    "main_routes.admin_delete_contractor": ("partners", "Deleted contractor"),
    "main_routes.add_contractor": ("partners", "Imported contractors"),
    "main_routes.reimport_contractors": ("partners", "Re-imported contractors"),
    "main_routes.admin_create_supplier": ("partners", "Added supplier"),
    "main_routes.admin_update_supplier": ("partners", "Updated supplier"),
    "main_routes.admin_delete_supplier": ("partners", "Deleted supplier"),
    "main_routes.add_supplier": ("partners", "Imported suppliers"),
    "main_routes.prof_ad_split_members_save": ("income", "Saved AD-split member"),
    "main_routes.prof_ad_split_members_delete": ("income", "Removed AD-split member"),
    "main_routes.prof_commission_levels_save": ("income", "Saved commission level"),
    "main_routes.prof_commission_levels_delete": ("income", "Deleted commission level"),
    "main_routes.prof_generate_sharing_run": ("income", "Generated project commission sharing"),
    "main_routes.prof_generate_sharing_delete": ("income", "Deleted sharing batch"),
    "main_routes.prof_products_commission_save": ("income", "Saved products commission"),
    "main_routes.prof_products_commission_delete": ("income", "Deleted products commission"),
    "main_routes.prof_project_commission_save": ("income", "Saved project commission"),
    "main_routes.prof_project_commission_delete": ("income", "Deleted project commission"),
    "main_routes.member_payout_request": ("payouts", "Requested payout"),
    "main_routes.payout_request_approve": ("payouts", "Approved payout request"),
    "main_routes.payout_request_reject": ("payouts", "Rejected payout request"),
    "main_routes.payout_request_release": ("payouts", "Submitted payout release"),
    "main_routes.payout_release_approve": ("payouts", "Approved payout release"),
    "main_routes.payout_release_reject": ("payouts", "Rejected payout release"),
    "main_routes.transaction_new": ("transactions", "Created transaction"),
    "main_routes.transaction_detail": ("transactions", "Updated transaction"),
    "main_routes.transaction_assign_me": ("transactions", "Took transaction"),
    "main_routes.transaction_add_note": ("transactions", "Logged transaction note"),
    "main_routes.transactions_import": ("transactions", "Imported monitoring sheet"),
    "main_routes.project_save_contract": ("transactions", "Saved project contract"),
    "main_routes.project_add_document": ("transactions", "Added project document"),
    "main_routes.product_add_document": ("transactions", "Added product document"),
    "main_routes.project_delete_document": ("transactions", "Deleted document"),
    "main_routes.project_add_event": ("transactions", "Scheduled project event"),
    "main_routes.project_event_action": ("transactions", "Updated project event"),
    "main_routes.project_add_payment": ("transactions", "Added payment milestone"),
    "main_routes.project_payment_action": ("transactions", "Updated payment milestone"),
    "main_routes.project_save_progress": ("transactions", "Updated project progress"),
    "main_routes.project_save_stages": ("transactions", "Saved stage plan"),
    "main_routes.my_assignment_action": ("transactions", "Field agent update"),
    "main_routes.my_assignment_event_done": ("transactions", "Field agent completed schedule"),
    "main_routes.contractor_upload_document": ("transactions", "Contractor uploaded file"),
    "main_routes.contractor_report_progress": ("transactions", "Contractor reported progress"),
    "main_routes.supplier_upload_document": ("transactions", "Supplier uploaded file"),
    "main_routes.supplier_post_update": ("transactions", "Supplier posted update"),
    "main_routes.marketplace_category": ("transactions", "Guest inquiry submitted"),
    "main_routes.marketplace_detail": ("transactions", "Guest inquiry submitted"),
    "main_routes.project_inquiry": ("transactions", "Guest project inquiry submitted"),
    "main_routes.notices_manage": ("notices", "Changed notice"),
    "site_admin.edit_landing": ("site", "Edited landing section"),
    "site_admin.edit_ecosystem": ("site", "Edited ecosystem page"),
    "site_admin.edit_contact_cta": ("site", "Edited services contact card"),
    "site_admin.registry_new": ("site", "Added registry partner"),
    "site_admin.registry_edit": ("site", "Edited registry partner"),
    "site_admin.upload_partner_image": ("site", "Uploaded partner image"),
    "site_admin.marketplace_new": ("site", "Added marketplace listing"),
    "site_admin.marketplace_edit": ("site", "Edited marketplace listing"),
    "site_admin.upload_marketplace_image": ("site", "Uploaded listing image"),
    "site_admin.marketplace_summaries_save": ("site", "Edited marketplace summaries"),
    "site_admin.marketplace_products_page_save": ("site", "Edited products page"),
    "site_admin.marketplace_services_page_save": ("site", "Edited services page"),
    "site_admin.gallery_new": ("site", "Added gallery folder"),
    "site_admin.gallery_edit": ("site", "Edited gallery folder"),
    "site_admin.upload_gallery_image": ("site", "Uploaded gallery image"),
    "main_routes.marketplace_crm_export": ("exports", "Exported Marketplace CRM (CSV)"),
    "main_routes.transactions_export": ("exports", "Exported transactions (Excel)"),
    "main_routes.prof_reports_commission_summary_pdf": ("exports", "Downloaded commission summary PDF"),
    "main_routes.prof_reports_project_pdf": ("exports", "Downloaded project report PDF"),
    "main_routes.payout_reports_pdf": ("exports", "Downloaded fund release report PDF"),
    "main_routes.project_document_download": ("exports", "Opened project document"),
    "main_routes.project_event_ics": ("exports", "Downloaded calendar event"),
    "main_routes.audit_log_export": ("exports", "Exported audit log (CSV)"),
    "site_admin.audit_log_export": ("exports", "Exported audit log (CSV)"),
}

LOGGED_READ_ENDPOINTS = {endpoint for endpoint, (category, _) in ACTIONS.items() if category == "exports"} | {
    "main_routes.logout",
}

SKIPPED_ENDPOINTS = {
    "static",
    "main_routes.accessibility_preferences",
    "main_routes.preview_members",
    "main_routes.preview_contractors",
    "main_routes.preview_suppliers",
    "main_routes.prof_products_commission_preview",
    "main_routes.transactions_mark_all_read",
}

# Guest forms carry client contact details; record which fields were sent, not the values.
VALUE_FREE_ENDPOINTS = {
    "main_routes.marketplace_category",
    "main_routes.marketplace_detail",
    "main_routes.project_inquiry",
}

PATH_CATEGORIES = (
    ("/site-admin", "site"),
    ("/admin/prof", "income"),
    ("/payout", "payouts"),
    ("/admin/transactions", "transactions"),
    ("/admin/projects", "transactions"),
    ("/admin/products", "transactions"),
    ("/members", "members"),
    ("/admin/members", "members"),
    ("/admin/contractors", "partners"),
    ("/admin/suppliers", "partners"),
    ("/notices", "notices"),
)

# view arg / form field -> target type
TARGET_KEYS = (
    ("lead_id", "transaction"),
    ("member_id", "member"),
    ("user_id", "user"),
    ("contractor_id", "contractor"),
    ("supplier_id", "supplier"),
    ("listing_id", "listing"),
    ("folder_id", "gallery folder"),
    ("payout_id", "payout"),
    ("project_id", "project commission"),
    ("product_commission_id", "products commission"),
    ("batch_id", "sharing batch"),
    ("document_id", "document"),
    ("event_id", "project event"),
    ("payment_id", "payment"),
    ("level_id", "commission level"),
    ("ad_split_id", "AD-split member"),
    ("sanction_id", "suspension"),
    ("notice_id", "notice"),
    ("position_id", "position"),
    ("slug", "page"),
    ("partner_type", "registry"),
)

MASKED_FIELD_RE = re.compile(r"pass|secret|token|csrf", re.I)
MAX_VALUE_LENGTH = 300
MAX_FORM_FIELDS = 60
MAX_CHANGE_RECORDS = 40

UNTRACKED_MODELS = {"AuditLog", "MarketplaceLeadRead", "PortalNoticeRead"}
IGNORED_COLUMNS = {"updated_at", "comfort_text_size", "comfort_high_contrast"}
MASKED_COLUMNS = {"password_hash"}
LABEL_COLUMNS = (
    "reference_number", "username", "company_name", "title", "project_title", "product_title",
    "slug", "last_name", "first_name", "duty", "event_type", "kind", "status",
)


# --------------------------------------------------------------------------- value helpers


def _plain(value):
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    text = value if isinstance(value, str) else repr(value)
    return text if len(text) <= MAX_VALUE_LENGTH else text[:MAX_VALUE_LENGTH] + "…"


def _client_ip():
    # The hosting proxy appends the real client address last; earlier entries can be forged by the client.
    forwarded = request.headers.get("X-Forwarded-For", "")
    return (forwarded.split(",")[-1].strip() or request.remote_addr or "")[:64]


# --------------------------------------------------------------------------- change capture


def _change_buffer():
    if not has_request_context():
        return None
    buffer = g.get("_audit_changes")
    if buffer is None:
        buffer = g._audit_changes = {"pending": [], "committed": []}
    return buffer


def _identity(obj):
    state = sa_inspect(obj)
    key = state.identity or state.mapper.primary_key_from_instance(obj)
    values = [v for v in (key or ()) if v is not None]
    return "-".join(str(v) for v in values) if values else None


def _label(obj):
    parts = []
    for column in LABEL_COLUMNS:
        value = getattr(obj, column, None)
        if value not in (None, "") and isinstance(value, (str, int)):
            parts.append(str(value))
        if len(parts) == 2:
            break
    return _plain(" · ".join(parts)) if parts else None


def _field_changes(obj):
    state = sa_inspect(obj)
    fields = {}
    for attr in state.mapper.column_attrs:
        if attr.key in IGNORED_COLUMNS:
            continue
        history = state.attrs[attr.key].history
        if not history.has_changes():
            continue
        old = history.deleted[0] if history.deleted else None
        new = history.added[0] if history.added else None
        if old == new:
            continue
        if attr.key in MASKED_COLUMNS:
            fields[attr.key] = ["••••", "(changed)"]
        else:
            fields[attr.key] = [_plain(old), _plain(new)]
    return fields


def _on_after_flush(session, _flush_context):
    buffer = _change_buffer()
    if buffer is None:
        return
    try:
        for op, objects in (("created", session.new), ("updated", session.dirty), ("deleted", session.deleted)):
            for obj in objects:
                model = type(obj).__name__
                if model in UNTRACKED_MODELS:
                    continue
                record = {"op": op, "model": model, "id": _identity(obj), "label": _label(obj)}
                if op == "updated":
                    fields = _field_changes(obj)
                    if not fields:
                        continue
                    record["fields"] = fields
                buffer["pending"].append(record)
    except Exception:
        logger.exception("audit change capture failed")


def _on_after_commit(_session):
    buffer = _change_buffer()
    if buffer is not None and buffer["pending"]:
        buffer["committed"].extend(buffer["pending"])
        buffer["pending"] = []


def _on_after_rollback(_session):
    buffer = _change_buffer()
    if buffer is not None:
        buffer["pending"] = []


def _committed_changes():
    buffer = g.get("_audit_changes")
    if not buffer or not buffer["committed"]:
        return None
    records = buffer["committed"]
    kept = records[:MAX_CHANGE_RECORDS]
    overflow = {}
    for record in records[MAX_CHANGE_RECORDS:]:
        key = (record["op"], record["model"])
        overflow[key] = overflow.get(key, 0) + 1
    kept.extend({"op": op, "model": model, "count": count} for (op, model), count in overflow.items())
    return kept


# --------------------------------------------------------------------------- request hooks


def _on_flash(_app, message, category, **_extra):
    if has_request_context():
        g.setdefault("_audit_flashes", []).append((category, str(message)))


def _snapshot_actor():
    """Remember the signed-in user before views like logout clear the session."""
    if request.method not in WRITE_METHODS and request.endpoint not in LOGGED_READ_ENDPOINTS:
        return
    g._audit_actor = {
        "user_id": session.get("user_id"),
        "username": session.get("username"),
        "full_name": session.get("fullname"),
        "role": session.get("role"),
    }


def _request_details(endpoint):
    details = {}
    if request.view_args:
        details["view_args"] = {k: _plain(v) for k, v in request.view_args.items()}
    if request.method == "GET":
        if request.args:
            details["query"] = {k: _plain(v) for k, v in list(request.args.items())[:MAX_FORM_FIELDS]}
        return details
    payload = request.get_json(silent=True) if request.is_json else request.form
    if isinstance(payload, dict) or hasattr(payload, "items"):
        fields = {}
        for key in list(payload.keys())[:MAX_FORM_FIELDS]:
            if MASKED_FIELD_RE.search(key):
                fields[key] = "••••"
            elif endpoint in VALUE_FREE_ENDPOINTS:
                fields[key] = "(sent)"
            elif endpoint == "main_routes.login" and key != "username":
                continue
            else:
                value = payload.getlist(key) if hasattr(payload, "getlist") else payload.get(key)
                if isinstance(value, list) and len(value) == 1:
                    value = value[0]
                fields[key] = [_plain(v) for v in value] if isinstance(value, list) else _plain(value)
        if fields:
            details["form"] = fields
    if request.files:
        details["files"] = [f.filename for f in request.files.values() if f and f.filename][:10]
    return details


def _target(details, changes):
    sources = (("url", details.get("view_args") or {}), ("form", details.get("form") or {}))
    for source_name, source in sources:
        for key, target_type in TARGET_KEYS:
            if source_name == "form" and not key.endswith("_id"):
                continue
            value = source.get(key)
            if value not in (None, "", "(sent)") and not isinstance(value, list):
                return target_type, str(value)[:60]
    for record in changes or ():
        if record.get("op") == "created" and record.get("id"):
            return record["model"], record["id"]
    return None, None


def _target_label(target_type, target_id, changes):
    for record in changes or ():
        if record.get("id") == target_id and record.get("label"):
            return record["label"][:200]
    return None


def _response_message(response):
    if not response.is_json or response.direct_passthrough:
        return None, False
    data = response.get_json(silent=True)
    if not isinstance(data, dict):
        return None, False
    failed = (
        data.get("status") == "error"
        or data.get("success") is False
        or ("error" in data and not data.get("status"))
    )
    message = data.get("msg") or data.get("message") or (data.get("error") if isinstance(data.get("error"), str) else None)
    return (str(message) if message else None), failed


def _record_request(response):
    try:
        endpoint = request.endpoint
        if not endpoint or endpoint in SKIPPED_ENDPOINTS:
            return response
        flashes = g.get("_audit_flashes", [])
        denied = response.status_code == 403 or any(m.startswith("Access denied") for _, m in flashes)
        is_write = request.method in WRITE_METHODS
        is_logged_read = request.method == "GET" and endpoint in LOGGED_READ_ENDPOINTS
        if not (is_write or is_logged_read or denied):
            return response

        message, json_failed = _response_message(response)
        danger = [m for c, m in flashes if c in ("danger", "error")]
        if denied:
            outcome = "denied"
        elif response.status_code >= 400 or json_failed or danger:
            outcome = "failed"
        else:
            outcome = "success"

        category, action = ACTIONS.get(endpoint, (None, None))
        if category is None:
            category = next((c for prefix, c in PATH_CATEGORIES if request.path.startswith(prefix)), "other")
            action = endpoint.split(".")[-1].replace("_", " ").capitalize()
        if endpoint == "main_routes.login" and outcome != "success":
            action = "Sign-in failed"
        if denied and not is_write and not is_logged_read:
            action = f"Access denied: {request.path}"
        if request.view_args and request.view_args.get("action"):
            action = f"{action} ({request.view_args['action']})"

        details = _request_details(endpoint)
        changes = _committed_changes()
        target_type, target_id = _target(details, changes)
        summary = message or (danger[0] if danger else (flashes[0][1] if flashes else None))

        actor = {
            "user_id": session.get("user_id"),
            "username": session.get("username"),
            "full_name": session.get("fullname"),
            "role": session.get("role"),
        }
        if not actor["user_id"]:
            actor = g.get("_audit_actor") or actor
        if not actor.get("username") and endpoint == "main_routes.login":
            actor = dict(actor, username=((details.get("form") or {}).get("username") or None))

        row = {
            "created_at": manila_now(),
            "user_id": actor.get("user_id"),
            "username": (actor.get("username") or None) and str(actor["username"])[:80],
            "full_name": (actor.get("full_name") or None) and str(actor["full_name"])[:120],
            "role": actor.get("role"),
            "ip_address": _client_ip(),
            "user_agent": (request.user_agent.string or "")[:255],
            "method": request.method,
            "path": request.full_path.rstrip("?")[:500] if request.method == "GET" else request.path[:500],
            "endpoint": endpoint[:120],
            "category": category,
            "action": action[:160],
            "target_type": target_type,
            "target_id": target_id,
            "target_label": _target_label(target_type, target_id, changes),
            "outcome": outcome,
            "status_code": response.status_code,
            "summary": summary[:2000] if summary else None,
            "details": details or None,
            "changes": changes,
        }
        with db.engine.begin() as connection:
            connection.execute(AuditLog.__table__.insert().values(**row))
    except Exception:
        logger.exception("audit log write failed")
    return response


def init_audit(app):
    event.listen(Session, "after_flush", _on_after_flush)
    event.listen(Session, "after_commit", _on_after_commit)
    event.listen(Session, "after_rollback", _on_after_rollback)
    message_flashed.connect(_on_flash, app)
    app.before_request(_snapshot_actor)
    app.after_request(_record_request)


# --------------------------------------------------------------------------- search and export


def _parse_day(raw):
    try:
        return datetime.strptime((raw or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def audit_filters_from(args):
    return {
        "date_from": (args.get("date_from") or "").strip(),
        "date_to": (args.get("date_to") or "").strip(),
        "user": (args.get("user") or "").strip(),
        "category": (args.get("category") or "").strip(),
        "outcome": (args.get("outcome") or "").strip(),
        "q": (args.get("q") or "").strip(),
        "target_type": (args.get("target_type") or "").strip(),
        "target_id": (args.get("target_id") or "").strip(),
        "ip": (args.get("ip") or "").strip(),
    }


def audit_query(filters):
    query = AuditLog.query
    day_from = _parse_day(filters.get("date_from"))
    day_to = _parse_day(filters.get("date_to"))
    if day_from:
        query = query.filter(AuditLog.created_at >= datetime.combine(day_from, time.min))
    if day_to:
        query = query.filter(AuditLog.created_at < datetime.combine(day_to + timedelta(days=1), time.min))
    if filters.get("user"):
        like = f"%{filters['user']}%"
        query = query.filter(or_(AuditLog.username.ilike(like), AuditLog.full_name.ilike(like)))
    if filters.get("category"):
        query = query.filter(AuditLog.category == filters["category"])
    if filters.get("outcome"):
        query = query.filter(AuditLog.outcome == filters["outcome"])
    if filters.get("target_type"):
        query = query.filter(AuditLog.target_type == filters["target_type"])
    if filters.get("target_id"):
        query = query.filter(AuditLog.target_id == filters["target_id"])
    if filters.get("ip"):
        query = query.filter(AuditLog.ip_address.ilike(f"%{filters['ip']}%"))
    if filters.get("q"):
        like = f"%{filters['q']}%"
        query = query.filter(or_(
            AuditLog.action.ilike(like),
            AuditLog.summary.ilike(like),
            AuditLog.path.ilike(like),
            AuditLog.target_label.ilike(like),
            AuditLog.target_id.ilike(like),
        ))
    return query.order_by(AuditLog.created_at.desc(), AuditLog.log_id.desc())


def audit_page(filters, page=1, per_page=50):
    query = audit_query(filters)
    total = query.count()
    page = max(1, page)
    rows = query.offset((page - 1) * per_page).limit(per_page).all()
    return rows, total


def audit_target_types():
    query = db.session.query(AuditLog.target_type).filter(AuditLog.target_type.isnot(None))
    return sorted({row[0] for row in query.distinct().all()})


def describe_changes(changes):
    """Readable lines for the change list stored on an entry."""
    lines = []
    for record in changes or ():
        if "count" in record:
            lines.append(f"+ {record['count']} more {record['model']} {record['op']}")
            continue
        head = f"{record['model']} #{record.get('id') or '?'}"
        if record.get("label"):
            head += f" ({record['label']})"
        if record["op"] == "updated":
            fields = "; ".join(f"{key}: {old!s} → {new!s}" for key, (old, new) in record.get("fields", {}).items())
            lines.append(f"Updated {head}: {fields}")
        else:
            lines.append(f"{record['op'].capitalize()} {head}")
    return lines


def _csv_cell(value):
    text = str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def audit_csv(filters, limit=10000):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Date/time", "User", "Name", "Role", "IP", "Category", "Action", "Target type", "Target id",
        "Target", "Outcome", "Summary", "Method", "Path", "Changes",
    ])
    for row in audit_query(filters).limit(limit).all():
        writer.writerow(_csv_cell(cell) for cell in [
            row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else "",
            row.username or "", row.full_name or "", row.role or "", row.ip_address or "",
            CATEGORY_LABELS.get(row.category, row.category or ""), row.action or "",
            row.target_type or "", row.target_id or "", row.target_label or "",
            OUTCOME_LABELS.get(row.outcome, row.outcome or ""), row.summary or "",
            row.method or "", row.path or "", " | ".join(describe_changes(row.changes)),
        ])
    return buffer.getvalue()
