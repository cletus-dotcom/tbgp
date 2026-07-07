import logging
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
        )
        if path == "/" or any(path.startswith(prefix) for prefix in allowed):
            return None
        return redirect(url_for("site_admin.home"))

    @app.context_processor
    def inject_globals():
        from app.payout_service import payout_queue_counts
        from app.platform_about import PLATFORM_DEVELOPER
        from app.site_content_service import get_services_contact_cta

        role = session.get("role")
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
        }

    from app.routes import main_routes
    from app.site_admin_routes import site_admin_bp

    app.register_blueprint(main_routes)
    app.register_blueprint(site_admin_bp)

    with app.app_context():
        from app import models  # noqa: F401

        db.create_all()
        from app.db_migrate import (
            migrate_commission_levels_table,
            migrate_member_ledger_table,
            migrate_payout_tables,
            migrate_payout_ompd,
            migrate_users_table,
            migrate_members_table,
            migrate_project_commissions_table,
            migrate_project_billings_table,
            migrate_sharing_entries_table,
        )

        migrate_members_table()
        migrate_project_commissions_table()
        migrate_project_billings_table()
        migrate_member_ledger_table()
        migrate_payout_tables()
        migrate_payout_ompd()
        migrate_users_table()
        migrate_commission_levels_table()
        migrate_sharing_entries_table()
        _seed_admin()
        _seed_portal_admin()
        _seed_site_admin()
        from app.site_content_service import seed_cms_content

        seed_cms_content()
        _seed_members()
        _seed_contractors()
        _seed_commission_levels()

    log = logging.getLogger("werkzeug")
    log.setLevel(logging.WARNING)

    return app


def _seed_admin():
    from app.models import User

    admin = User.query.filter_by(username="Admin").first()
    if not admin:
        admin = User(
            username="Admin",
            full_name="System Administrator",
            role="Admin",
            status="Active",
        )
        admin.set_password("123")
        db.session.add(admin)
        db.session.commit()


def _seed_portal_admin():
    from app.models import User

    portal_admin = User.query.filter_by(username="PortalAdmin").first()
    if not portal_admin:
        portal_admin = User(
            username="PortalAdmin",
            full_name="Portal Administrator",
            role="PortalAdmin",
            status="Active",
        )
        db.session.add(portal_admin)
    portal_admin.full_name = portal_admin.full_name or "Portal Administrator"
    portal_admin.role = "PortalAdmin"
    portal_admin.status = "Active"
    portal_admin.member_id = None
    portal_admin.set_password("portal123")
    db.session.commit()


def _seed_site_admin():
    from app.models import User

    site_admin = User.query.filter_by(username="SiteAdmin").first()
    if not site_admin:
        site_admin = User(
            username="SiteAdmin",
            full_name="Site Administrator",
            role="SiteAdmin",
            status="Active",
        )
        db.session.add(site_admin)
    site_admin.full_name = site_admin.full_name or "Site Administrator"
    site_admin.role = "SiteAdmin"
    site_admin.status = "Active"
    site_admin.member_id = None
    site_admin.set_password("siteadmin123")
    db.session.commit()


def _seed_members():
    from app.import_service import import_members_from_xlsx
    from app.models import Member

    if Member.query.count() == 0:
        try:
            import_members_from_xlsx()
        except Exception as exc:
            logging.getLogger(__name__).warning("Member import skipped: %s", exc)


def _seed_contractors():
    from app.contractor_import_service import import_contractors_from_xlsx
    from app.models import Contractor, Member

    if Member.query.count() == 0:
        return
    if Contractor.query.count() == 0:
        try:
            import_contractors_from_xlsx()
        except Exception as exc:
            logging.getLogger(__name__).warning("Contractor import skipped: %s", exc)


def _seed_commission_levels():
    from app.config import (
        COMMISSION_SCHEME_CLIENT,
        COMMISSION_SCHEME_CONTRACTOR,
        DEFAULT_CLIENT_COMMISSION_LEVELS,
        DEFAULT_CONTRACTOR_COMMISSION_LEVELS,
        MAX_SHARING_LEVELS,
    )
    from app.models import CommissionLevel

    defaults = {
        COMMISSION_SCHEME_CLIENT: DEFAULT_CLIENT_COMMISSION_LEVELS,
        COMMISSION_SCHEME_CONTRACTOR: DEFAULT_CONTRACTOR_COMMISSION_LEVELS,
    }
    existing = {(row.scheme, row.level): row for row in CommissionLevel.query.all()}

    for scheme, levels in defaults.items():
        for level, percentage, description in levels:
            row = existing.get((scheme, level))
            if row:
                row.percentage = percentage
                row.description = description
                row.scheme = scheme
            else:
                db.session.add(CommissionLevel(
                    scheme=scheme,
                    level=level,
                    percentage=percentage,
                    description=description,
                ))

    for (scheme, level), row in list(existing.items()):
        if level > MAX_SHARING_LEVELS or scheme not in defaults:
            db.session.delete(row)

    db.session.commit()
