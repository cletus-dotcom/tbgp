from functools import wraps

from flask import flash, jsonify, redirect, request, session, url_for

from app.config import is_admin_role, is_staff_or_admin


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("main_routes.login", next=request.path))
        return func(*args, **kwargs)

    return wrapper


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_admin_role(session.get("role")):
            if request.is_json or request.method in ("POST", "PUT", "DELETE"):
                return jsonify({
                    "status": "error",
                    "msg": "Unauthorized",
                    "success": False,
                }), 403
            flash("Access denied. Admins only.", "danger")
            return redirect(url_for("main_routes.dashboard"))
        return func(*args, **kwargs)

    return wrapper


def staff_or_admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_staff_or_admin(session.get("role")):
            if request.is_json or request.method in ("POST", "PUT", "DELETE"):
                return jsonify({
                    "status": "error",
                    "msg": "Unauthorized",
                    "success": False,
                }), 403
            flash("Access denied. Staff or Admin only.", "danger")
            return redirect(url_for("main_routes.dashboard"))
        return func(*args, **kwargs)

    return wrapper
