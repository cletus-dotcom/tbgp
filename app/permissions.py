"""Role-based access helpers for routes and templates."""

from flask import flash, jsonify, redirect, request, session, url_for

from app.config import is_member_role, is_staff_or_admin


def session_member_id():
    return session.get("member_id")


def _member_in_downline(root_member_id, target_member_id):
    if int(root_member_id) == int(target_member_id):
        return True
    from app.models import Member

    member = Member.query.get(root_member_id)
    if not member:
        return False
    for child in member.referrals:
        if _member_in_downline(child.member_id, target_member_id):
            return True
    return False


def member_may_view_ledger(member_id):
    if is_staff_or_admin(session.get("role")):
        return True
    if is_member_role(session.get("role")):
        linked = session_member_id()
        return linked is not None and int(linked) == int(member_id)
    return False


def member_may_view_profile(member_id):
    if is_staff_or_admin(session.get("role")):
        return True
    if is_member_role(session.get("role")):
        linked = session_member_id()
        if not linked:
            return False
        return _member_in_downline(int(linked), int(member_id))
    return False


def member_may_access(member_id):
    return member_may_view_profile(member_id)


def require_linked_member():
    """Return linked member_id for Member role users, or None if misconfigured."""
    if not is_member_role(session.get("role")):
        return None
    member_id = session_member_id()
    if not member_id:
        return None
    return int(member_id)


def access_denied_response(message="Access denied."):
    if request.is_json or request.method in ("POST", "PUT", "DELETE"):
        return jsonify({"status": "error", "msg": message, "success": False}), 403
    flash(message, "danger")
    return redirect(url_for("main_routes.dashboard"))


def forbid_member_portal_users():
    if is_member_role(session.get("role")):
        return access_denied_response("You do not have access to this section.")
    return None


def forbid_unless_staff_or_admin():
    if not is_staff_or_admin(session.get("role")):
        return access_denied_response("Access denied. Staff or Admin only.")
    return None


def forbid_unless_member_self(member_id):
    if member_may_view_profile(member_id):
        return None
    return access_denied_response("You may only view records in your referral network.")


def forbid_unless_own_ledger(member_id):
    if member_may_view_ledger(member_id):
        return None
    return access_denied_response("You may only view your own ledger.")
