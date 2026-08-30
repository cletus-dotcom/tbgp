"""Database migrations and seed data run during app startup or via CLI."""

import logging
import os

logger = logging.getLogger(__name__)


def _db():
    from app import db

    return db


def should_run_startup_tasks():
    """Return False when TBGP_SKIP_STARTUP_TASKS=1 (e.g. production after first deploy)."""
    return os.environ.get("TBGP_SKIP_STARTUP_TASKS") != "1"


def initialize_database():
    """Create tables, apply lightweight migrations, and seed required defaults."""
    db = _db()
    from app import models  # noqa: F401

    db.create_all()

    from app.db_migrate import (
        migrate_ad_split_members_table,
        migrate_commission_levels_table,
        migrate_marketplace_tables,
        migrate_member_ledger_table,
        migrate_members_table,
        migrate_payout_ompd,
        migrate_payout_tables,
        migrate_product_commission_ad_allocations_table,
        migrate_product_commissions_table,
        migrate_project_billings_table,
        migrate_project_commissions_table,
        migrate_sharing_entries_table,
        migrate_users_table,
    )

    migrate_members_table()
    migrate_project_commissions_table()
    migrate_project_billings_table()
    migrate_product_commissions_table()
    migrate_ad_split_members_table()
    migrate_product_commission_ad_allocations_table()
    migrate_marketplace_tables()
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

    if not os.environ.get("TBGP_SKIP_DATA_SEED"):
        _seed_members()
        _seed_contractors()
        _seed_suppliers()

    _seed_commission_levels()
    logger.info("Database startup tasks completed")


def _seed_admin():
    db = _db()
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
    db = _db()
    from app.models import User

    portal_admin = User.query.filter_by(username="PortalAdmin").first()
    if not portal_admin:
        portal_admin = User(
            username="PortalAdmin",
            full_name="Portal Administrator",
            role="PortalAdmin",
            status="Active",
        )
        portal_admin.set_password("portal123")
        db.session.add(portal_admin)
    else:
        portal_admin.full_name = portal_admin.full_name or "Portal Administrator"
        portal_admin.role = "PortalAdmin"
        portal_admin.status = "Active"
        portal_admin.member_id = None
    db.session.commit()


def _seed_site_admin():
    db = _db()
    from app.models import User

    site_admin = User.query.filter_by(username="SiteAdmin").first()
    if not site_admin:
        site_admin = User(
            username="SiteAdmin",
            full_name="Site Administrator",
            role="SiteAdmin",
            status="Active",
        )
        site_admin.set_password("siteadmin123")
        db.session.add(site_admin)
    else:
        site_admin.full_name = site_admin.full_name or "Site Administrator"
        site_admin.role = "SiteAdmin"
        site_admin.status = "Active"
        site_admin.member_id = None
    db.session.commit()


def _seed_members():
    db = _db()
    from app.import_service import import_members_from_xlsx
    from app.models import Member

    if Member.query.count() == 0:
        try:
            import_members_from_xlsx()
        except Exception as exc:
            logger.warning("Member import skipped: %s", exc)


def _seed_contractors():
    db = _db()
    from app.contractor_import_service import import_contractors_from_xlsx
    from app.models import Contractor, Member

    if Member.query.count() == 0:
        return
    if Contractor.query.count() == 0:
        try:
            import_contractors_from_xlsx()
        except Exception as exc:
            logger.warning("Contractor import skipped: %s", exc)


def _seed_suppliers():
    db = _db()
    from app.models import Member, Supplier
    from app.supplier_import_service import import_suppliers_from_xlsx

    if Member.query.count() == 0:
        return
    if Supplier.query.count() == 0:
        try:
            import_suppliers_from_xlsx()
        except Exception as exc:
            logger.warning("Supplier import skipped: %s", exc)


def _seed_commission_levels():
    db = _db()
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
