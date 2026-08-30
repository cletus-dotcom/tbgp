import logging
import os
from pathlib import Path

from flask import Flask, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

from app.config import (
    ADMIN_ACCOUNT_PERCENT,
    BRAND_BLUE,
    BRAND_BLUE_DARK,
    BRAND_BLUE_LIGHT,
    CLIENT_POOL_PERCENT,
    CONTRACTOR_POOL_PERCENT,
    MAX_SHARING_LEVELS,
    MEMBER_EARNINGS_CAP_FIRST_PROJECT,
    MEMBER_LIFETIME_EARNINGS_CAP,
    MEMBER_LIFETIME_PROJECT_CAP_AFTER_LIMIT,
    MEMBER_EARNINGS_CAP_NTH_PROJECT,
    MEMBER_EARNINGS_CAP_SECOND_PROJECT,
    MEMBER_SEPARATION_TYPES,
    MEMBER_STATUSES,
    PAYOUT_OMPD_PERCENT,
    PAYOUT_RELEASE_METHODS,
    SECRET_KEY,
    THEME_BG,
    THEME_BG_ALT,
    THEME_BLACK,
    THEME_DARK,
    THEME_GRAY,
    THEME_GRAY_LIGHT,
    THEME_WHITE,
    is_admin_role,
    is_member_role,
    is_staff_or_admin,
    can_access_admin_options,
    can_delete_sharing_batch,
    can_view_sharing_result,
    can_manage_commission_levels,
    can_access_prof_reports,
    can_approve_payout_release,
    can_approve_payout_request,
    can_request_payout,
    can_submit_payout_release,
    can_view_payout_reports,
    can_view_payout_scheme,
    can_manage_data,
    can_purge_member_database,
    assignable_user_roles,
    can_manage_site_content,
    can_view_marketplace_help,
    can_view_features_process_flow,
    can_access_marketplace_crm,
    is_site_admin_role,
    post_login_redirect,
    USER_ROLES,
    database_uri,
    payout_scheme_summary,
)

db = SQLAlchemy()


def create_app():
    base = Path(__file__).parent
    template_folder = str((base.parent / "templates").resolve())
    static_folder = str((base.parent / "static").resolve())

    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    app.secret_key = SECRET_KEY
    CORS(app)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

    from app.config import SUPABASE_PARTNER_IMAGES_BUCKET

    app.config["SUPABASE_PARTNER_IMAGES_BUCKET"] = SUPABASE_PARTNER_IMAGES_BUCKET
    # Partner/marketplace image uploads are capped at 5 MB; allow a little headroom for multipart wrappers.
    app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024

    db.init_app(app)

    @app.before_request
    def restrict_site_admin_portal_access():
        from flask import redirect, request, session, url_for

        if not session.get("username") or not is_site_admin_role(session.get("role")):
            return None
        path = request.path or ""
        allowed = (
            "/site-admin",
            "/logout",
            "/static/",
            "/login",
            "/ecosystem/",
            "/partners/",
            "/marketplace/",
            "/m/",
            "/help/marketplace-crm",
            "/about/features-process-flow",
            "/admin/marketplace-crm",
        )
        if path == "/" or any(path.startswith(prefix) for prefix in allowed):
            return None
        return redirect(url_for("site_admin.home"))

    @app.errorhandler(413)
    def request_entity_too_large(_exc):
        from flask import jsonify, request

        if request.path.startswith("/site-admin/") and request.path.endswith("/image"):
            return jsonify({"error": "Image is too large (max 5 MB)."}), 413
        if request.path.startswith("/site-admin/") and "partner-image" in request.path:
            return jsonify({"error": "Image is too large (max 5 MB)."}), 413
        return ("File too large.", 413)

    @app.context_processor
    def inject_globals():
        from flask import session, url_for

        from app.accessibility_service import DEFAULT_ACCESSIBILITY_PREFS, get_user_accessibility_prefs
        from app.payout_service import payout_queue_counts
        from app.platform_about import PLATFORM_DEVELOPER
        from app.site_content_service import get_services_contact_cta

        role = session.get("role")
        user_id = session.get("user_id")
        if user_id:
            user_accessibility_prefs = get_user_accessibility_prefs(user_id)
        else:
            user_accessibility_prefs = dict(DEFAULT_ACCESSIBILITY_PREFS)
        return {
            "brand_blue": BRAND_BLUE,
            "brand_blue_dark": BRAND_BLUE_DARK,
            "brand_blue_light": BRAND_BLUE_LIGHT,
            "theme_black": THEME_BLACK,
            "theme_dark": THEME_DARK,
            "theme_gray": THEME_GRAY,
            "theme_gray_light": THEME_GRAY_LIGHT,
            "theme_white": THEME_WHITE,
            "theme_bg": THEME_BG,
            "theme_bg_alt": THEME_BG_ALT,
            "is_admin_role": is_admin_role,
            "is_site_admin_role": is_site_admin_role,
            "can_manage_site_content": can_manage_site_content,
            "can_view_marketplace_help": can_view_marketplace_help,
            "can_view_features_process_flow": can_view_features_process_flow,
            "can_access_marketplace_crm": can_access_marketplace_crm,
            "is_member_role": is_member_role,
            "is_staff_or_admin": is_staff_or_admin,
            "can_manage_data": can_manage_data,
            "can_access_admin_options": can_access_admin_options,
            "can_delete_sharing_batch": can_delete_sharing_batch,
            "can_view_sharing_result": can_view_sharing_result,
            "can_manage_commission_levels": can_manage_commission_levels,
            "can_access_prof_reports": can_access_prof_reports,
            "can_request_payout": can_request_payout,
            "can_approve_payout_request": can_approve_payout_request,
            "can_submit_payout_release": can_submit_payout_release,
            "can_approve_payout_release": can_approve_payout_release,
            "can_view_payout_reports": can_view_payout_reports,
            "can_view_payout_scheme": can_view_payout_scheme,
            "can_purge_member_database": can_purge_member_database,
            "payout_release_methods": PAYOUT_RELEASE_METHODS,
            "payout_ompd_percent": PAYOUT_OMPD_PERCENT,
            "payout_scheme": payout_scheme_summary(),
            "payout_queue_counts": payout_queue_counts(role),
            "assignable_user_roles": assignable_user_roles(session.get("role")),
            "user_roles": USER_ROLES,
            "member_statuses": MEMBER_STATUSES,
            "member_separation_types": MEMBER_SEPARATION_TYPES,
            "sharing_pool_percent": CLIENT_POOL_PERCENT,
            "client_pool_percent": CLIENT_POOL_PERCENT,
            "contractor_pool_percent": CONTRACTOR_POOL_PERCENT,
            "admin_account_percent": ADMIN_ACCOUNT_PERCENT,
            "max_sharing_levels": MAX_SHARING_LEVELS,
            "member_earnings_cap_first": float(MEMBER_EARNINGS_CAP_FIRST_PROJECT),
            "member_earnings_cap_second": float(MEMBER_EARNINGS_CAP_SECOND_PROJECT),
            "member_earnings_cap_nth": float(MEMBER_EARNINGS_CAP_NTH_PROJECT),
            "member_lifetime_earnings_cap": float(MEMBER_LIFETIME_EARNINGS_CAP),
            "member_lifetime_project_cap_after_limit": float(MEMBER_LIFETIME_PROJECT_CAP_AFTER_LIMIT),
            "services_contact_cta": get_services_contact_cta(),
            "platform_developer": PLATFORM_DEVELOPER,
            "user_accessibility_prefs": user_accessibility_prefs,
            "accessibility_user_logged_in": bool(user_id),
            "accessibility_api_url": url_for("main_routes.accessibility_preferences"),
        }

    from app.routes import main_routes
    from app.site_admin_routes import site_admin_bp

    app.register_blueprint(main_routes)
    app.register_blueprint(site_admin_bp)

    from app.startup import (
        initialize_database,
        run_schema_migrations,
        should_run_startup_tasks,
    )

    with app.app_context():
        if should_run_startup_tasks():
            initialize_database()
        else:
            # Keep schema in sync even when seeds are skipped on Render.
            run_schema_migrations()

    log = logging.getLogger("werkzeug")
    log.setLevel(logging.WARNING)

    return app
