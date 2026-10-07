"""Lightweight schema migrations for development databases."""

import logging

from sqlalchemy import inspect, text

from app import db

logger = logging.getLogger(__name__)

MEMBER_COLUMN_DEFS = {
    "membership_type": "VARCHAR(30)",
    "phone": "VARCHAR(30)",
    "email": "VARCHAR(120)",
    "birth_date": "DATE",
    "gender": "VARCHAR(20)",
    "civil_status": "VARCHAR(30)",
    "highest_education": "VARCHAR(80)",
    "occupation_income_source": "VARCHAR(120)",
    "monthly_income": "VARCHAR(40)",
    "number_of_dependents": "INTEGER",
    "beneficiary_name": "VARCHAR(255)",
    "beneficiary_address": "VARCHAR(255)",
    "beneficiary_phone": "VARCHAR(120)",
    "status": "VARCHAR(20) DEFAULT 'Active'",
    "termination_date": "DATE",
    "termination_type": "VARCHAR(60)",
    "date_joined": "DATE",
    "lifetime_cap_enabled": "BOOLEAN DEFAULT TRUE",
    "lifetime_cap_amount": "NUMERIC(14, 2) DEFAULT 50000000",
    "marketplace_share_code": "VARCHAR(40)",
    "gcash_number": "VARCHAR(40)",
    "bank_account_number": "VARCHAR(60)",
    "bank_name": "VARCHAR(120)",
    "age": "INTEGER",
    "id_picture_location": "VARCHAR(500)",
    "beneficiary_relationship": "VARCHAR(80)",
}


def migrate_members_table():
    inspector = inspect(db.engine)
    if "members" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("members")}

    for col_name, col_type in MEMBER_COLUMN_DEFS.items():
        if col_name not in columns:
            db.session.execute(text(f"ALTER TABLE members ADD COLUMN {col_name} {col_type}"))
            logger.info("Added members.%s", col_name)

    columns = {col["name"] for col in inspector.get_columns("members")}

    if "cp_no" in columns and "phone" in columns:
        db.session.execute(
            text("UPDATE members SET phone = cp_no WHERE phone IS NULL AND cp_no IS NOT NULL")
        )

    if "status" in columns:
        db.session.execute(
            text("UPDATE members SET status = 'Active' WHERE status IS NULL OR status = ''")
        )
        db.session.execute(
            text("UPDATE members SET status = 'Separated' WHERE status = 'Terminated'")
        )

    if "lifetime_cap_enabled" in columns:
        db.session.execute(
            text("UPDATE members SET lifetime_cap_enabled = TRUE WHERE lifetime_cap_enabled IS NULL")
        )
    if "lifetime_cap_amount" in columns:
        db.session.execute(
            text("UPDATE members SET lifetime_cap_amount = 50000000 WHERE lifetime_cap_amount IS NULL")
        )

    widen_columns = {
        "beneficiary_phone": "VARCHAR(120)",
        "beneficiary_name": "VARCHAR(255)",
    }
    for col_name, col_type in widen_columns.items():
        if col_name in columns:
            db.session.execute(text(
                f"ALTER TABLE members ALTER COLUMN {col_name} TYPE {col_type}"
            ))
            logger.info("Widened members.%s to %s", col_name, col_type)

    db.session.commit()

    columns = {col["name"] for col in inspector.get_columns("members")}
    for legacy in ("cp_no",):
        if legacy in columns:
            db.session.execute(text(f"ALTER TABLE members DROP COLUMN {legacy}"))
            logger.info("Dropped legacy members.%s", legacy)
    db.session.commit()


PROJECT_COMMISSION_COLUMN_DEFS = {
    "client_referrer_id": "INTEGER REFERENCES members(member_id)",
    "contractor_referrer_id": "INTEGER REFERENCES members(member_id)",
}


def migrate_project_commissions_table():
    inspector = inspect(db.engine)
    if "project_commissions" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("project_commissions")}
    for col_name, col_type in PROJECT_COMMISSION_COLUMN_DEFS.items():
        if col_name not in columns:
            db.session.execute(text(f"ALTER TABLE project_commissions ADD COLUMN {col_name} {col_type}"))
            logger.info("Added project_commissions.%s", col_name)

    columns = {col["name"] for col in inspector.get_columns("project_commissions")}
    if "contractor_referrer_id" in columns:
        db.session.execute(text("""
            UPDATE project_commissions pc
            SET contractor_referrer_id = c.member_referrer_id
            FROM contractors c
            WHERE pc.contractor_id = c.contractor_id
              AND pc.contractor_referrer_id IS NULL
        """))
    if "client_referrer_id" in columns and "contractor_referrer_id" in columns:
        db.session.execute(text("""
            UPDATE project_commissions
            SET client_referrer_id = contractor_referrer_id
            WHERE client_referrer_id IS NULL
              AND contractor_referrer_id IS NOT NULL
        """))
    if "commission_date" in columns:
        if "billing_date" in columns:
            db.session.execute(text("""
                UPDATE project_commissions
                SET commission_date = COALESCE(commission_date, billing_date, CURRENT_DATE)
                WHERE commission_date IS NULL
            """))
        else:
            db.session.execute(text("""
                UPDATE project_commissions
                SET commission_date = COALESCE(commission_date, CURRENT_DATE)
                WHERE commission_date IS NULL
            """))
    db.session.commit()

    columns = {col["name"] for col in inspector.get_columns("project_commissions")}
    for legacy in ("billing_date", "billing_amount"):
        if legacy in columns:
            db.session.execute(text(f"ALTER TABLE project_commissions DROP COLUMN {legacy}"))
            logger.info("Dropped project_commissions.%s", legacy)
    db.session.commit()


def migrate_project_billings_table():
    inspector = inspect(db.engine)
    if "project_commissions" not in inspector.get_table_names():
        return

    if "project_billings" not in inspector.get_table_names():
        db.session.execute(text("""
            CREATE TABLE project_billings (
                billing_id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL REFERENCES project_commissions(project_id) ON DELETE CASCADE,
                billing_date DATE NOT NULL,
                billing_amount NUMERIC(14, 2) NOT NULL
            )
        """))
        logger.info("Created project_billings table")

    columns = {col["name"] for col in inspector.get_columns("project_commissions")}
    billing_columns = {col["name"] for col in inspector.get_columns("project_billings")}

    if "commission_date" in columns and "commission_amount" in columns:
        db.session.execute(text("""
            INSERT INTO project_billings (project_id, billing_date, billing_amount)
            SELECT pc.project_id, pc.commission_date, pc.commission_amount
            FROM project_commissions pc
            WHERE pc.commission_date IS NOT NULL
              AND pc.commission_amount IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM project_billings pb WHERE pb.project_id = pc.project_id
              )
        """))
        db.session.execute(text("ALTER TABLE project_commissions DROP COLUMN commission_date"))
        db.session.execute(text("ALTER TABLE project_commissions DROP COLUMN commission_amount"))
        logger.info("Migrated project commission date/amount rows to project_billings")

    db.session.commit()

    if "sharing_entries" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("sharing_entries")}
        if "billing_id" not in columns:
            db.session.execute(text(
                "ALTER TABLE sharing_entries ADD COLUMN billing_id INTEGER "
                "REFERENCES project_billings(billing_id)"
            ))
            logger.info("Added sharing_entries.billing_id")
        db.session.commit()


def migrate_member_ledger_table():
    inspector = inspect(db.engine)
    if "member_ledger" not in inspector.get_table_names():
        db.session.execute(text("""
            CREATE TABLE member_ledger (
                ledger_id SERIAL PRIMARY KEY,
                member_id INTEGER NOT NULL REFERENCES members(member_id),
                transaction_type VARCHAR(10) NOT NULL DEFAULT 'credit',
                batch_id INTEGER REFERENCES sharing_batches(batch_id) ON DELETE CASCADE,
                entry_id INTEGER REFERENCES sharing_entries(entry_id) ON DELETE SET NULL,
                billing_date DATE NOT NULL,
                project_id INTEGER REFERENCES project_commissions(project_id),
                billing_id INTEGER REFERENCES project_billings(billing_id),
                project_title VARCHAR(200),
                recipient_type VARCHAR(20) NOT NULL,
                share_scheme VARCHAR(40),
                level INTEGER DEFAULT 0,
                share_amount NUMERIC(14, 2) NOT NULL,
                description VARCHAR(255),
                payout_request_id INTEGER,
                created_at TIMESTAMP NOT NULL
            )
        """))
        logger.info("Created member_ledger table")
        db.session.commit()
        return

    columns = {col["name"] for col in inspector.get_columns("member_ledger")}
    alters = {
        "transaction_type": "VARCHAR(10) NOT NULL DEFAULT 'credit'",
        "payout_request_id": "INTEGER",
        "product_commission_id": "INTEGER REFERENCES product_commissions(product_commission_id)",
    }
    for col_name, col_type in alters.items():
        if col_name not in columns:
            # product_commission_id may be added before product_commissions exists on first run;
            # create_all runs first so the table should exist. Skip FK if table missing.
            if col_name == "product_commission_id":
                table_names = set(inspector.get_table_names())
                if "product_commissions" not in table_names:
                    continue
            db.session.execute(text(f"ALTER TABLE member_ledger ADD COLUMN {col_name} {col_type}"))
            logger.info("Added member_ledger.%s", col_name)

    if "transaction_type" in columns or "transaction_type" in alters:
        db.session.execute(text(
            "UPDATE member_ledger SET transaction_type = 'credit' WHERE transaction_type IS NULL"
        ))

    nullable_columns = ("batch_id", "project_id", "project_title", "level")
    for col_name in nullable_columns:
        db.session.execute(text(
            f"ALTER TABLE member_ledger ALTER COLUMN {col_name} DROP NOT NULL"
        ))

    columns = {col["name"] for col in inspector.get_columns("member_ledger")}
    if "share_scheme" in columns:
        db.session.execute(text(
            "ALTER TABLE member_ledger ALTER COLUMN share_scheme TYPE VARCHAR(40)"
        ))
        logger.info("Widened member_ledger.share_scheme to VARCHAR(40)")

    db.session.commit()


def migrate_payout_tables():
    inspector = inspect(db.engine)
    if "payout_requests" not in inspector.get_table_names():
        db.session.execute(text("""
            CREATE TABLE payout_requests (
                payout_id SERIAL PRIMARY KEY,
                member_id INTEGER NOT NULL REFERENCES members(member_id),
                requested_amount NUMERIC(14, 2) NOT NULL,
                ompd_deduction NUMERIC(14, 2) NOT NULL DEFAULT 0,
                net_release_amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
                status VARCHAR(30) NOT NULL DEFAULT 'pending',
                member_note TEXT,
                requested_at TIMESTAMP NOT NULL,
                requested_by_user_id INTEGER NOT NULL REFERENCES users(user_id),
                request_reviewed_at TIMESTAMP,
                request_reviewed_by_user_id INTEGER REFERENCES users(user_id),
                request_review_note TEXT,
                release_method VARCHAR(40),
                release_reference VARCHAR(120),
                release_account_info VARCHAR(255),
                release_notes TEXT,
                release_submitted_at TIMESTAMP,
                release_submitted_by_user_id INTEGER REFERENCES users(user_id),
                release_approved_at TIMESTAMP,
                release_approved_by_user_id INTEGER REFERENCES users(user_id),
                released_at TIMESTAMP,
                rejected_at TIMESTAMP,
                rejected_by_user_id INTEGER REFERENCES users(user_id),
                rejection_reason TEXT
            )
        """))
        logger.info("Created payout_requests table")

    if "payout_notifications" not in inspector.get_table_names():
        db.session.execute(text("""
            CREATE TABLE payout_notifications (
                notification_id SERIAL PRIMARY KEY,
                payout_id INTEGER NOT NULL REFERENCES payout_requests(payout_id) ON DELETE CASCADE,
                audience_role VARCHAR(20),
                user_id INTEGER REFERENCES users(user_id),
                title VARCHAR(120) NOT NULL,
                message TEXT NOT NULL,
                is_read BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL
            )
        """))
        logger.info("Created payout_notifications table")

    db.session.commit()

    inspector = inspect(db.engine)
    if "member_ledger" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("member_ledger")}
        if "payout_request_id" in columns:
            db.session.execute(text(
                "ALTER TABLE member_ledger DROP CONSTRAINT IF EXISTS member_ledger_payout_request_id_fkey"
            ))
            db.session.execute(text(
                "ALTER TABLE member_ledger ADD CONSTRAINT member_ledger_payout_request_id_fkey "
                "FOREIGN KEY (payout_request_id) REFERENCES payout_requests(payout_id)"
            ))
            db.session.commit()


def migrate_payout_ompd():
    inspector = inspect(db.engine)
    if "payout_requests" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("payout_requests")}
        for col_name, col_type in {
            "ompd_deduction": "NUMERIC(14, 2) DEFAULT 0",
            "net_release_amount": "NUMERIC(14, 2) DEFAULT 0",
        }.items():
            if col_name not in columns:
                db.session.execute(text(
                    f"ALTER TABLE payout_requests ADD COLUMN {col_name} {col_type}"
                ))
                logger.info("Added payout_requests.%s", col_name)

        db.session.execute(text("""
            UPDATE payout_requests
            SET ompd_deduction = ROUND(requested_amount * 0.10, 2),
                net_release_amount = requested_amount - ROUND(requested_amount * 0.10, 2)
            WHERE ompd_deduction IS NULL
               OR net_release_amount IS NULL
               OR (ompd_deduction = 0 AND net_release_amount = 0 AND requested_amount > 0)
        """))
        db.session.commit()

    if "ompd_fund_entries" not in inspector.get_table_names():
        db.session.execute(text("""
            CREATE TABLE ompd_fund_entries (
                entry_id SERIAL PRIMARY KEY,
                payout_id INTEGER NOT NULL UNIQUE REFERENCES payout_requests(payout_id) ON DELETE CASCADE,
                member_id INTEGER NOT NULL REFERENCES members(member_id),
                gross_amount NUMERIC(14, 2) NOT NULL,
                deduction_amount NUMERIC(14, 2) NOT NULL,
                net_released NUMERIC(14, 2) NOT NULL,
                release_method VARCHAR(40),
                release_reference VARCHAR(120),
                recorded_at TIMESTAMP NOT NULL
            )
        """))
        logger.info("Created ompd_fund_entries table")
        db.session.commit()

    if "payout_requests" in inspector.get_table_names() and "ompd_fund_entries" in inspect(db.engine).get_table_names():
        db.session.execute(text("""
            INSERT INTO ompd_fund_entries (
                payout_id, member_id, gross_amount, deduction_amount, net_released,
                release_method, release_reference, recorded_at
            )
            SELECT
                pr.payout_id,
                pr.member_id,
                pr.requested_amount,
                COALESCE(pr.ompd_deduction, ROUND(pr.requested_amount * 0.10, 2)),
                COALESCE(pr.net_release_amount, pr.requested_amount - ROUND(pr.requested_amount * 0.10, 2)),
                pr.release_method,
                pr.release_reference,
                COALESCE(pr.released_at, pr.release_approved_at, pr.requested_at)
            FROM payout_requests pr
            WHERE pr.status = 'released'
              AND NOT EXISTS (
                  SELECT 1 FROM ompd_fund_entries o WHERE o.payout_id = pr.payout_id
              )
        """))
        db.session.commit()


def migrate_commission_levels_table():
    inspector = inspect(db.engine)
    if "commission_levels" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("commission_levels")}
    if "scheme" not in columns:
        db.session.execute(text("ALTER TABLE commission_levels ADD COLUMN scheme VARCHAR(20) DEFAULT 'client'"))
        db.session.execute(text("UPDATE commission_levels SET scheme = 'client' WHERE scheme IS NULL"))
        db.session.execute(text("ALTER TABLE commission_levels ALTER COLUMN scheme SET NOT NULL"))
        logger.info("Added commission_levels.scheme")

    db.session.execute(text(
        "ALTER TABLE commission_levels DROP CONSTRAINT IF EXISTS commission_levels_level_key"
    ))
    db.session.execute(text(
        "ALTER TABLE commission_levels DROP CONSTRAINT IF EXISTS uq_commission_levels_scheme_level"
    ))
    db.session.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_commission_levels_scheme_level "
        "ON commission_levels (scheme, level)"
    ))
    db.session.commit()


def migrate_sharing_entries_table():
    inspector = inspect(db.engine)
    if "sharing_entries" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("sharing_entries")}
    alters = {
        "recipient_type": "VARCHAR(20) DEFAULT 'member'",
        "recipient_label": "VARCHAR(120)",
    }
    for col_name, col_type in alters.items():
        if col_name not in columns:
            db.session.execute(text(f"ALTER TABLE sharing_entries ADD COLUMN {col_name} {col_type}"))
            logger.info("Added sharing_entries.%s", col_name)

    columns = {col["name"] for col in inspector.get_columns("sharing_entries")}
    if "share_scheme" not in columns:
        db.session.execute(text("ALTER TABLE sharing_entries ADD COLUMN share_scheme VARCHAR(40)"))
        logger.info("Added sharing_entries.share_scheme")
    else:
        db.session.execute(text(
            "ALTER TABLE sharing_entries ALTER COLUMN share_scheme TYPE VARCHAR(40)"
        ))
        logger.info("Widened sharing_entries.share_scheme to VARCHAR(40)")
    if "member_id" in columns:
        db.session.execute(text("ALTER TABLE sharing_entries ALTER COLUMN member_id DROP NOT NULL"))
    db.session.commit()

    if "sharing_batches" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("sharing_batches")}
        for col_name, col_type in {
            "total_pool": "NUMERIC(14, 2) DEFAULT 0",
            "total_client_pool": "NUMERIC(14, 2) DEFAULT 0",
            "total_contractor_pool": "NUMERIC(14, 2) DEFAULT 0",
            "total_admin": "NUMERIC(14, 2) DEFAULT 0",
            "total_pop": "NUMERIC(14, 2) DEFAULT 0",
        }.items():
            if col_name not in columns:
                db.session.execute(text(f"ALTER TABLE sharing_batches ADD COLUMN {col_name} {col_type}"))
                logger.info("Added sharing_batches.%s", col_name)
        db.session.commit()
    inspector = inspect(db.engine)
    if "sharing_batches" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("sharing_batches")}
    if "commission_date" not in columns and "billing_date" in columns:
        db.session.execute(text("ALTER TABLE sharing_batches ADD COLUMN commission_date DATE"))
        db.session.execute(text("UPDATE sharing_batches SET commission_date = billing_date"))
        db.session.execute(text("ALTER TABLE sharing_batches DROP COLUMN billing_date"))
        logger.info("Renamed sharing_batches.billing_date to commission_date")
    db.session.commit()


def migrate_users_table():
    inspector = inspect(db.engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("users")}
    if "member_id" not in columns:
        db.session.execute(text(
            "ALTER TABLE users ADD COLUMN member_id INTEGER REFERENCES members(member_id)"
        ))
        logger.info("Added users.member_id")
        db.session.commit()

    columns = {col["name"] for col in inspector.get_columns("users")}
    if "comfort_text_size" not in columns:
        db.session.execute(text(
            "ALTER TABLE users ADD COLUMN comfort_text_size VARCHAR(20) NOT NULL DEFAULT 'standard'"
        ))
        logger.info("Added users.comfort_text_size")
    if "comfort_high_contrast" not in columns:
        db.session.execute(text(
            "ALTER TABLE users ADD COLUMN comfort_high_contrast BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        logger.info("Added users.comfort_high_contrast")
    if "department" not in columns:
        db.session.execute(text("ALTER TABLE users ADD COLUMN department VARCHAR(40)"))
        logger.info("Added users.department")
    db.session.commit()


def migrate_product_commissions_table():
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())

    if "product_commissions" not in table_names:
        db.session.execute(text("""
            CREATE TABLE product_commissions (
                product_commission_id SERIAL PRIMARY KEY,
                product_title VARCHAR(200) NOT NULL DEFAULT 'Products Commission',
                commission_amount NUMERIC(14, 2) NOT NULL,
                commission_date DATE NOT NULL,
                ref_seller_id INTEGER NOT NULL REFERENCES members(member_id),
                ref_buyer_id INTEGER NOT NULL REFERENCES members(member_id),
                bonus_type VARCHAR(10) NOT NULL DEFAULT 'auto',
                bonus_percent NUMERIC(6, 2) NOT NULL DEFAULT 10,
                notes TEXT,
                seller_pool NUMERIC(14, 2) DEFAULT 0,
                buyer_pool NUMERIC(14, 2) DEFAULT 0,
                pop_amount NUMERIC(14, 2) DEFAULT 0,
                ad_fund_amount NUMERIC(14, 2) DEFAULT 0,
                platform_amount NUMERIC(14, 2) DEFAULT 0,
                bonus_amount NUMERIC(14, 2) DEFAULT 0,
                total_shared NUMERIC(14, 2) DEFAULT 0,
                total_mandate NUMERIC(14, 2) DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                created_by_user_id INTEGER REFERENCES users(user_id)
            )
        """))
        logger.info("Created product_commissions table")
        db.session.commit()

    inspector = inspect(db.engine)
    if "product_commission_shares" not in inspector.get_table_names():
        db.session.execute(text("""
            CREATE TABLE product_commission_shares (
                share_id SERIAL PRIMARY KEY,
                product_commission_id INTEGER NOT NULL
                    REFERENCES product_commissions(product_commission_id) ON DELETE CASCADE,
                member_id INTEGER REFERENCES members(member_id),
                recipient_type VARCHAR(20) NOT NULL DEFAULT 'member',
                recipient_label VARCHAR(120),
                share_scheme VARCHAR(40),
                level INTEGER NOT NULL DEFAULT 0,
                percentage NUMERIC(6, 2) NOT NULL DEFAULT 0,
                share_amount NUMERIC(14, 2) NOT NULL DEFAULT 0
            )
        """))
        logger.info("Created product_commission_shares table")
        db.session.commit()

    inspector = inspect(db.engine)
    if "member_ledger" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("member_ledger")}
        if "product_commission_id" not in columns:
            db.session.execute(text(
                "ALTER TABLE member_ledger ADD COLUMN product_commission_id "
                "INTEGER REFERENCES product_commissions(product_commission_id)"
            ))
            logger.info("Added member_ledger.product_commission_id")
            db.session.commit()


def migrate_ad_split_members_table():
    inspector = inspect(db.engine)
    if "ad_split_members" in inspector.get_table_names():
        return

    db.session.execute(text("""
        CREATE TABLE ad_split_members (
            ad_split_id SERIAL PRIMARY KEY,
            member_id INTEGER NOT NULL UNIQUE REFERENCES members(member_id),
            description VARCHAR(255),
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            created_by_user_id INTEGER REFERENCES users(user_id)
        )
    """))
    logger.info("Created ad_split_members table")
    db.session.commit()


def migrate_product_commission_ad_allocations_table():
    inspector = inspect(db.engine)
    if "product_commission_ad_allocations" in inspector.get_table_names():
        return

    db.session.execute(text("""
        CREATE TABLE product_commission_ad_allocations (
            allocation_id SERIAL PRIMARY KEY,
            product_commission_id INTEGER NOT NULL
                REFERENCES product_commissions(product_commission_id) ON DELETE CASCADE,
            member_id INTEGER NOT NULL REFERENCES members(member_id),
            amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
            charge_from VARCHAR(20) NOT NULL DEFAULT 'platform'
        )
    """))
    logger.info("Created product_commission_ad_allocations table")
    db.session.commit()


def migrate_marketplace_tables():
    inspector = inspect(db.engine)
    table_names = inspector.get_table_names()

    if "marketplace_listings" not in table_names:
        db.session.execute(text("""
            CREATE TABLE marketplace_listings (
                listing_id SERIAL PRIMARY KEY,
                category VARCHAR(40) NOT NULL,
                title VARCHAR(200) NOT NULL,
                summary VARCHAR(500),
                body TEXT,
                price_label VARCHAR(120),
                location VARCHAR(255),
                status VARCHAR(20) NOT NULL DEFAULT 'draft',
                thumbnail_url VARCHAR(500),
                gallery JSON NOT NULL DEFAULT '[]',
                contact_name VARCHAR(120),
                contact_phone VARCHAR(40),
                contact_email VARCHAR(120),
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                created_by_user_id INTEGER REFERENCES users(user_id)
            )
        """))
        db.session.execute(text(
            "CREATE INDEX ix_marketplace_listings_category ON marketplace_listings (category)"
        ))
        db.session.execute(text(
            "CREATE INDEX ix_marketplace_listings_status ON marketplace_listings (status)"
        ))
        logger.info("Created marketplace_listings table")
        db.session.commit()

    if "marketplace_leads" not in inspector.get_table_names():
        db.session.execute(text("""
            CREATE TABLE marketplace_leads (
                lead_id SERIAL PRIMARY KEY,
                listing_id INTEGER
                    REFERENCES marketplace_listings(listing_id) ON DELETE CASCADE,
                interest_category VARCHAR(40),
                attributed_member_id INTEGER REFERENCES members(member_id),
                guest_name VARCHAR(120) NOT NULL,
                guest_phone VARCHAR(40),
                guest_email VARCHAR(120),
                message TEXT,
                source_path VARCHAR(255),
                status VARCHAR(20) NOT NULL DEFAULT 'new',
                action_required VARCHAR(60),
                final_result VARCHAR(40),
                created_at TIMESTAMP NOT NULL
            )
        """))
        db.session.execute(text(
            "CREATE INDEX ix_marketplace_leads_member ON marketplace_leads (attributed_member_id)"
        ))
        db.session.execute(text(
            "CREATE INDEX ix_marketplace_leads_interest_category "
            "ON marketplace_leads (interest_category)"
        ))
        db.session.execute(text(
            "CREATE INDEX ix_marketplace_leads_status ON marketplace_leads (status)"
        ))
        logger.info("Created marketplace_leads table")
        db.session.commit()
    else:
        lead_cols = {col["name"] for col in inspector.get_columns("marketplace_leads")}
        listing_col = next(
            (col for col in inspector.get_columns("marketplace_leads") if col["name"] == "listing_id"),
            None,
        )
        if listing_col is not None and not listing_col.get("nullable", True):
            db.session.execute(text(
                "ALTER TABLE marketplace_leads ALTER COLUMN listing_id DROP NOT NULL"
            ))
            logger.info("Made marketplace_leads.listing_id nullable")
            db.session.commit()
        if "interest_category" not in lead_cols:
            db.session.execute(text(
                "ALTER TABLE marketplace_leads ADD COLUMN interest_category VARCHAR(40)"
            ))
            db.session.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_marketplace_leads_interest_category "
                "ON marketplace_leads (interest_category)"
            ))
            logger.info("Added marketplace_leads.interest_category")
            db.session.commit()
        if "status" not in lead_cols:
            db.session.execute(text(
                "ALTER TABLE marketplace_leads "
                "ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'new'"
            ))
            db.session.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_marketplace_leads_status "
                "ON marketplace_leads (status)"
            ))
            logger.info("Added marketplace_leads.status")
            db.session.commit()
            lead_cols.add("status")
        if "action_required" not in lead_cols:
            db.session.execute(text(
                "ALTER TABLE marketplace_leads ADD COLUMN action_required VARCHAR(60)"
            ))
            logger.info("Added marketplace_leads.action_required")
            db.session.commit()
        if "final_result" not in lead_cols:
            db.session.execute(text(
                "ALTER TABLE marketplace_leads ADD COLUMN final_result VARCHAR(40)"
            ))
            logger.info("Added marketplace_leads.final_result")
            db.session.commit()

    if "marketplace_lead_history" not in inspector.get_table_names():
        db.session.execute(text("""
            CREATE TABLE marketplace_lead_history (
                history_id SERIAL PRIMARY KEY,
                lead_id INTEGER NOT NULL
                    REFERENCES marketplace_leads(lead_id) ON DELETE CASCADE,
                event_type VARCHAR(40) NOT NULL DEFAULT 'update',
                status VARCHAR(20),
                action_required VARCHAR(60),
                final_result VARCHAR(40),
                note VARCHAR(500),
                created_by_user_id INTEGER REFERENCES users(user_id),
                created_at TIMESTAMP NOT NULL
            )
        """))
        db.session.execute(text(
            "CREATE INDEX ix_marketplace_lead_history_lead "
            "ON marketplace_lead_history (lead_id)"
        ))
        logger.info("Created marketplace_lead_history table")
        db.session.commit()

    # Unique index for member share codes when column exists.
    member_cols = {col["name"] for col in inspector.get_columns("members")}
    if "marketplace_share_code" in member_cols:
        indexes = {idx["name"] for idx in inspector.get_indexes("members")}
        if "ix_members_marketplace_share_code" not in indexes:
            try:
                db.session.execute(text(
                    "CREATE UNIQUE INDEX ix_members_marketplace_share_code "
                    "ON members (marketplace_share_code) "
                    "WHERE marketplace_share_code IS NOT NULL"
                ))
                logger.info("Created unique index on members.marketplace_share_code")
                db.session.commit()
            except Exception:
                db.session.rollback()

    _purge_retired_marketplace_sites_category()


def _purge_retired_marketplace_sites_category():
    """Remove retired Construction Sites (sites) marketplace listings and clean CMS summaries."""
    inspector = inspect(db.engine)
    if "marketplace_listings" not in inspector.get_table_names():
        return

    deleted = db.session.execute(
        text("DELETE FROM marketplace_listings WHERE category = 'sites'")
    )
    if deleted.rowcount:
        logger.info("Removed %s retired marketplace listings (category=sites)", deleted.rowcount)
        db.session.commit()

    if "cms_landing_sections" not in inspector.get_table_names():
        return
    row = db.session.execute(
        text(
            "SELECT data FROM cms_landing_sections "
            "WHERE section_key = 'marketplace_summaries'"
        )
    ).fetchone()
    if not row or not row[0]:
        return
    data = row[0]
    if isinstance(data, str):
        import json
        try:
            data = json.loads(data)
        except Exception:
            return
    if not isinstance(data, dict) or "sites" not in data:
        return
    data = {key: value for key, value in data.items() if key != "sites"}
    import json
    db.session.execute(
        text(
            "UPDATE cms_landing_sections SET data = CAST(:payload AS json) "
            "WHERE section_key = 'marketplace_summaries'"
        ),
        {"payload": json.dumps(data)},
    )
    logger.info("Removed sites executive summary from marketplace_summaries CMS")
    db.session.commit()


def migrate_gallery_tables():
    inspector = inspect(db.engine)
    if "cms_gallery_folders" in inspector.get_table_names():
        return

    db.session.execute(text("""
        CREATE TABLE cms_gallery_folders (
            folder_id SERIAL PRIMARY KEY,
            slug VARCHAR(80) NOT NULL UNIQUE,
            title VARCHAR(200) NOT NULL,
            description VARCHAR(500),
            status VARCHAR(20) NOT NULL DEFAULT 'published',
            sort_order INTEGER NOT NULL DEFAULT 0,
            images JSON NOT NULL DEFAULT '[]',
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL
        )
    """))
    db.session.execute(text(
        "CREATE INDEX ix_cms_gallery_folders_status ON cms_gallery_folders (status)"
    ))
    logger.info("Created cms_gallery_folders table")
    db.session.commit()


def migrate_portal_positions_tables():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    if "portal_positions" not in tables:
        db.session.execute(text("""
            CREATE TABLE portal_positions (
                position_id SERIAL PRIMARY KEY,
                department VARCHAR(40) NOT NULL,
                title VARCHAR(120) NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                CONSTRAINT uq_portal_positions_department_title UNIQUE (department, title)
            )
        """))
        db.session.execute(text(
            "CREATE INDEX ix_portal_positions_department ON portal_positions (department)"
        ))
        logger.info("Created portal_positions table")

    if "member_positions" not in inspector.get_table_names():
        db.session.execute(text("""
            CREATE TABLE member_positions (
                member_position_id SERIAL PRIMARY KEY,
                member_id INTEGER NOT NULL REFERENCES members(member_id) ON DELETE CASCADE,
                department VARCHAR(40) NOT NULL,
                position_id INTEGER NOT NULL REFERENCES portal_positions(position_id) ON DELETE CASCADE,
                assigned_at TIMESTAMP NOT NULL,
                CONSTRAINT uq_member_positions_member_department UNIQUE (member_id, department)
            )
        """))
        db.session.execute(text(
            "CREATE INDEX ix_member_positions_member_id ON member_positions (member_id)"
        ))
        db.session.execute(text(
            "CREATE INDEX ix_member_positions_position_id ON member_positions (position_id)"
        ))
        logger.info("Created member_positions table")

    db.session.commit()


def merge_departments():
    """Fold retired departments into their replacement (Sales + Marketing -> Sales & Marketing); idempotent."""
    from app.config import MERGED_DEPARTMENTS

    tables = set(inspect(db.engine).get_table_names())

    def scalar(sql, **params):
        return db.session.execute(text(sql), params).scalar()

    for old, new in MERGED_DEPARTMENTS.items():
        params = {"old": old, "new": new}
        if "users" in tables:
            moved = db.session.execute(
                text("UPDATE users SET department = :new WHERE department = :old"), params
            ).rowcount
            if moved:
                logger.info("Moved %s user(s) from %s to %s", moved, old, new)

        duplicate_positions = []
        if "portal_positions" in tables:
            rows = db.session.execute(text(
                "SELECT position_id, title FROM portal_positions WHERE department = :old ORDER BY sort_order, title"
            ), params).all()
            next_order = scalar(
                "SELECT COALESCE(MAX(sort_order), 0) FROM portal_positions WHERE department = :new", new=new
            )
            for position_id, title in rows:
                target = scalar(
                    "SELECT position_id FROM portal_positions WHERE department = :new AND lower(title) = lower(:title)",
                    new=new, title=title,
                )
                if target:
                    if "member_positions" in tables:
                        db.session.execute(text(
                            "UPDATE member_positions SET position_id = :target WHERE position_id = :source"
                        ), {"target": target, "source": position_id})
                    duplicate_positions.append(position_id)
                else:
                    next_order += 1
                    db.session.execute(text(
                        "UPDATE portal_positions SET department = :new, sort_order = :sort WHERE position_id = :id"
                    ), {"new": new, "sort": next_order, "id": position_id})
            if rows:
                logger.info("Moved %s position(s) from %s to %s", len(rows), old, new)

        if "member_positions" in tables:
            rows = db.session.execute(text(
                "SELECT member_position_id, member_id FROM member_positions WHERE department = :old"
            ), params).all()
            for member_position_id, member_id in rows:
                taken = scalar(
                    "SELECT 1 FROM member_positions WHERE member_id = :member AND department = :new",
                    member=member_id, new=new,
                )
                if taken:
                    logger.warning(
                        "Member %s already holds a %s position; dropped their former %s position",
                        member_id, new, old,
                    )
                    db.session.execute(text(
                        "DELETE FROM member_positions WHERE member_position_id = :id"
                    ), {"id": member_position_id})
                else:
                    db.session.execute(text(
                        "UPDATE member_positions SET department = :new WHERE member_position_id = :id"
                    ), {"new": new, "id": member_position_id})

        for position_id in duplicate_positions:
            db.session.execute(text("DELETE FROM portal_positions WHERE position_id = :id"), {"id": position_id})
    db.session.commit()


def migrate_portal_notices_tables():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    if "portal_notices" not in tables:
        db.session.execute(text("""
            CREATE TABLE portal_notices (
                notice_id SERIAL PRIMARY KEY,
                notice_type VARCHAR(20) NOT NULL DEFAULT 'announcement',
                title VARCHAR(200) NOT NULL,
                body TEXT NOT NULL,
                reference_number VARCHAR(60),
                effective_date DATE,
                issued_by VARCHAR(160),
                issued_date DATE,
                audience_roles JSON NOT NULL DEFAULT '[]',
                is_published BOOLEAN NOT NULL DEFAULT TRUE,
                created_by_user_id INTEGER REFERENCES users(user_id),
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """))
        db.session.execute(text(
            "CREATE INDEX ix_portal_notices_notice_type ON portal_notices (notice_type)"
        ))
        logger.info("Created portal_notices table")
    else:
        notice_columns = {col["name"] for col in inspector.get_columns("portal_notices")}
        for column, ddl in (
            ("reference_number", "VARCHAR(60)"),
            ("effective_date", "DATE"),
            ("issued_by", "VARCHAR(160)"),
            ("issued_date", "DATE"),
        ):
            if column not in notice_columns:
                db.session.execute(text(f"ALTER TABLE portal_notices ADD COLUMN {column} {ddl}"))
                logger.info("Added portal_notices.%s", column)

    if "portal_notice_reads" not in inspector.get_table_names():
        db.session.execute(text("""
            CREATE TABLE portal_notice_reads (
                read_id SERIAL PRIMARY KEY,
                notice_id INTEGER NOT NULL REFERENCES portal_notices(notice_id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                read_at TIMESTAMP NOT NULL,
                CONSTRAINT uq_portal_notice_reads_notice_user UNIQUE (notice_id, user_id)
            )
        """))
        db.session.execute(text(
            "CREATE INDEX ix_portal_notice_reads_notice_id ON portal_notice_reads (notice_id)"
        ))
        db.session.execute(text(
            "CREATE INDEX ix_portal_notice_reads_user_id ON portal_notice_reads (user_id)"
        ))
        logger.info("Created portal_notice_reads table")

    db.session.commit()


TIMEZONE_MARKER_KEY = "stored_timestamp_timezone"
TIMEZONE_MIGRATION_LOCK_ID = 81240001


def migrate_timestamps_to_manila():
    """One-time shift of stored UTC timestamps to Asia/Manila local time (+8h)."""
    from sqlalchemy import DateTime

    from app.timeutil import MANILA_UTC_OFFSET_HOURS, manila_now

    if db.engine.dialect.name != "postgresql":
        return

    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS app_meta (
            key VARCHAR(80) PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP
        )
    """))
    db.session.commit()

    # Serialize concurrent workers; the marker row is re-checked under the lock.
    db.session.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": TIMEZONE_MIGRATION_LOCK_ID})
    marker = db.session.execute(
        text("SELECT value FROM app_meta WHERE key = :key"), {"key": TIMEZONE_MARKER_KEY}
    ).scalar()
    if marker:
        db.session.commit()
        return

    inspector = inspect(db.engine)
    existing_tables = set(inspector.get_table_names())
    shifted = 0
    for table in db.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        db_columns = {col["name"] for col in inspector.get_columns(table.name)}
        for column in table.columns:
            if not isinstance(column.type, DateTime) or column.name not in db_columns:
                continue
            result = db.session.execute(text(
                f'UPDATE "{table.name}" SET "{column.name}" = "{column.name}" '
                f"+ INTERVAL '{MANILA_UTC_OFFSET_HOURS} hours' "
                f'WHERE "{column.name}" IS NOT NULL'
            ))
            shifted += result.rowcount or 0

    db.session.execute(
        text("INSERT INTO app_meta (key, value, updated_at) VALUES (:key, :value, :updated_at)"),
        {"key": TIMEZONE_MARKER_KEY, "value": "Asia/Manila", "updated_at": manila_now()},
    )
    db.session.commit()
    logger.info("Shifted %s stored timestamps from UTC to Asia/Manila", shifted)


PROJECT_DELIVERY_COLUMNS = (
    ("status_changed_at", "TIMESTAMP"),
    ("progress_percent", "INTEGER"),
    (
        "awarded_contractor_id",
        "INTEGER REFERENCES contractors(contractor_id) ON DELETE SET NULL",
    ),
    ("contract_amount", "NUMERIC(14, 2)"),
    ("contract_signed_on", "DATE"),
    ("commission_percent", "NUMERIC(6, 2)"),
    (
        "commission_project_id",
        "INTEGER REFERENCES project_commissions(project_id) ON DELETE SET NULL",
    ),
)


def migrate_project_delivery():
    """Project delivery tracking: progress, award, contract value, contractor logins."""
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    if "marketplace_leads" in tables:
        columns = {col["name"] for col in inspector.get_columns("marketplace_leads")}
        for column, ddl in PROJECT_DELIVERY_COLUMNS:
            if column not in columns:
                db.session.execute(text(f"ALTER TABLE marketplace_leads ADD COLUMN {column} {ddl}"))
                logger.info("Added marketplace_leads.%s", column)
        db.session.execute(text(
            "UPDATE marketplace_leads SET status_changed_at = COALESCE(updated_at, created_at) "
            "WHERE status_changed_at IS NULL"
        ))
        db.session.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_marketplace_leads_awarded_contractor_id "
            "ON marketplace_leads (awarded_contractor_id)"
        ))
    if "users" in tables:
        user_columns = {col["name"] for col in inspector.get_columns("users")}
        if "contractor_id" not in user_columns:
            db.session.execute(text(
                "ALTER TABLE users ADD COLUMN contractor_id INTEGER "
                "REFERENCES contractors(contractor_id) ON DELETE SET NULL"
            ))
            logger.info("Added users.contractor_id")
    db.session.commit()


PROJECT_TEAM_COLUMNS = ("estimator_user_id", "site_engineer_user_id")


def migrate_project_team():
    """Project team slots beside the coordinator; user duties live in user_duties (create_all)."""
    inspector = inspect(db.engine)
    if "marketplace_leads" not in set(inspector.get_table_names()):
        return
    columns = {col["name"] for col in inspector.get_columns("marketplace_leads")}
    for column in PROJECT_TEAM_COLUMNS:
        if column not in columns:
            db.session.execute(text(
                f"ALTER TABLE marketplace_leads ADD COLUMN {column} INTEGER "
                "REFERENCES users(user_id) ON DELETE SET NULL"
            ))
            logger.info("Added marketplace_leads.%s", column)
        db.session.execute(text(
            f"CREATE INDEX IF NOT EXISTS ix_marketplace_leads_{column} ON marketplace_leads ({column})"
        ))
    db.session.commit()


PRODUCT_TEAM_COLUMNS = (
    ("sourcing_user_id", "INTEGER REFERENCES users(user_id) ON DELETE SET NULL"),
    ("logistics_user_id", "INTEGER REFERENCES users(user_id) ON DELETE SET NULL"),
    ("agent_user_id", "INTEGER REFERENCES users(user_id) ON DELETE SET NULL"),
    ("supplier_id", "INTEGER REFERENCES suppliers(supplier_id) ON DELETE SET NULL"),
    ("delivery_date", "DATE"),
)


def migrate_product_team():
    """Product team slots, the assigned supplier and delivery date on transactions; supplier logins."""
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    if "marketplace_leads" in tables:
        columns = {col["name"] for col in inspector.get_columns("marketplace_leads")}
        for column, ddl in PRODUCT_TEAM_COLUMNS:
            if column not in columns:
                db.session.execute(text(f"ALTER TABLE marketplace_leads ADD COLUMN {column} {ddl}"))
                logger.info("Added marketplace_leads.%s", column)
            if ddl.startswith("INTEGER"):
                db.session.execute(text(
                    f"CREATE INDEX IF NOT EXISTS ix_marketplace_leads_{column} ON marketplace_leads ({column})"
                ))
    if "users" in tables:
        user_columns = {col["name"] for col in inspector.get_columns("users")}
        if "supplier_id" not in user_columns:
            db.session.execute(text(
                "ALTER TABLE users ADD COLUMN supplier_id INTEGER "
                "REFERENCES suppliers(supplier_id) ON DELETE SET NULL"
            ))
            logger.info("Added users.supplier_id")
    db.session.commit()


def migrate_sanctions():
    """Commission records remember when they were created so suspensions are judged on that date."""
    inspector = inspect(db.engine)
    if "project_commissions" not in set(inspector.get_table_names()):
        return
    columns = {col["name"] for col in inspector.get_columns("project_commissions")}
    if "created_at" not in columns:
        db.session.execute(text("ALTER TABLE project_commissions ADD COLUMN created_at TIMESTAMP"))
        db.session.commit()
        logger.info("Added project_commissions.created_at")


def drop_project_bids_table():
    """Contractor bidding was replaced by staff assigning the contractor; drop the table only while it is empty."""
    if "project_bids" not in set(inspect(db.engine).get_table_names()):
        return
    if db.session.execute(text("SELECT EXISTS (SELECT 1 FROM project_bids)")).scalar():
        logger.warning("project_bids still has rows; leaving the table in place")
        return
    db.session.execute(text("DROP TABLE project_bids"))
    db.session.commit()
    logger.info("Dropped empty project_bids table")


MARKETPLACE_TRANSACTION_COLUMNS = (
    ("transaction_type", "VARCHAR(40)"),
    ("inquiry_no", "INTEGER"),
    ("reference_number", "VARCHAR(30)"),
    ("item_name", "VARCHAR(255)"),
    ("date_requested", "DATE"),
    ("estimated_implementation", "VARCHAR(160)"),
    ("quantity", "TEXT"),
    ("specifications", "TEXT"),
    ("delivery_location", "TEXT"),
    ("referrer_name", "VARCHAR(255)"),
    ("referrer_phone", "VARCHAR(120)"),
    ("referrer_email", "VARCHAR(255)"),
    ("client_company", "TEXT"),
    ("status_detail", "TEXT"),
    ("action_needed", "TEXT"),
    ("project_coordinator", "VARCHAR(160)"),
    ("assigned_contractor", "VARCHAR(255)"),
    ("assigned_user_id", "INTEGER REFERENCES users(user_id) ON DELETE SET NULL"),
    ("date_completed", "DATE"),
    ("remarks", "TEXT"),
    ("source", "VARCHAR(20) NOT NULL DEFAULT 'web'"),
    ("updated_at", "TIMESTAMP"),
)

# Legacy CRM workflow (status, action_required, final_result) -> transaction status.
LEGACY_LEAD_STATUS_SQL = """
    UPDATE {table} SET status = CASE
        WHEN status = 'contacted' THEN 'for_follow_up'
        WHEN status = 'in_progress' AND action_required = 'quote_for_client_submission'
            THEN 'quotation_submitted'
        WHEN status = 'in_progress' AND action_required = 'ordered' THEN 'completed'
        WHEN status = 'in_progress' THEN 'for_quotation'
        WHEN status = 'closed' AND final_result = 'bought' THEN 'completed'
        WHEN status = 'closed' THEN 'terminated'
        ELSE status
    END
    WHERE status IN ('contacted', 'in_progress', 'closed')
"""


def migrate_marketplace_transactions():
    """Extend marketplace inquiries into tracked transactions (monitoring sheet fields)."""
    inspector = inspect(db.engine)
    if "marketplace_leads" not in inspector.get_table_names():
        return

    columns = {col["name"]: col for col in inspector.get_columns("marketplace_leads")}
    for column, ddl in MARKETPLACE_TRANSACTION_COLUMNS:
        if column not in columns:
            db.session.execute(text(f"ALTER TABLE marketplace_leads ADD COLUMN {column} {ddl}"))
            logger.info("Added marketplace_leads.%s", column)

    guest_name = columns.get("guest_name")
    if guest_name is not None and not guest_name.get("nullable", True):
        db.session.execute(text("ALTER TABLE marketplace_leads ALTER COLUMN guest_name DROP NOT NULL"))
    for column, size in (("guest_name", 160), ("guest_phone", 160), ("guest_email", 255), ("status", 30)):
        current = columns.get(column)
        length = getattr(current["type"], "length", None) if current else None
        if length is not None and length < size:
            db.session.execute(text(
                f"ALTER TABLE marketplace_leads ALTER COLUMN {column} TYPE VARCHAR({size})"
            ))
            logger.info("Widened marketplace_leads.%s to %s", column, size)

    history_columns = {
        col["name"]: col for col in inspector.get_columns("marketplace_lead_history")
    }
    status_col = history_columns.get("status")
    if status_col is not None and (getattr(status_col["type"], "length", None) or 30) < 30:
        db.session.execute(text(
            "ALTER TABLE marketplace_lead_history ALTER COLUMN status TYPE VARCHAR(30)"
        ))
    note_col = history_columns.get("note")
    if note_col is not None and getattr(note_col["type"], "length", None):
        db.session.execute(text("ALTER TABLE marketplace_lead_history ALTER COLUMN note TYPE TEXT"))

    # Transactions must survive listing deletion.
    for fk in inspector.get_foreign_keys("marketplace_leads"):
        if fk.get("referred_table") != "marketplace_listings" or not fk.get("name"):
            continue
        if (fk.get("options") or {}).get("ondelete", "").upper() == "SET NULL":
            continue
        db.session.execute(text(f'ALTER TABLE marketplace_leads DROP CONSTRAINT "{fk["name"]}"'))
        db.session.execute(text(
            "ALTER TABLE marketplace_leads ADD CONSTRAINT marketplace_leads_listing_id_fkey "
            "FOREIGN KEY (listing_id) REFERENCES marketplace_listings(listing_id) ON DELETE SET NULL"
        ))
        logger.info("marketplace_leads.listing_id now ON DELETE SET NULL")

    db.session.execute(text(LEGACY_LEAD_STATUS_SQL.format(table="marketplace_leads")))
    db.session.execute(text("""
        UPDATE marketplace_lead_history SET status = CASE
            WHEN status = 'contacted' THEN 'for_follow_up'
            WHEN status = 'in_progress' THEN 'for_quotation'
            WHEN status = 'closed' AND final_result = 'bought' THEN 'completed'
            WHEN status = 'closed' THEN 'terminated'
            ELSE status
        END
        WHERE status IN ('contacted', 'in_progress', 'closed')
    """))

    db.session.execute(text("""
        UPDATE marketplace_leads ml SET
            transaction_type = COALESCE(
                (SELECT l.category FROM marketplace_listings l WHERE l.listing_id = ml.listing_id),
                ml.interest_category,
                'products'
            ),
            item_name = COALESCE(
                ml.item_name,
                (SELECT l.title FROM marketplace_listings l WHERE l.listing_id = ml.listing_id)
            ),
            date_requested = COALESCE(ml.date_requested, CAST(ml.created_at AS DATE)),
            source = 'legacy'
        WHERE ml.transaction_type IS NULL
    """))
    db.session.execute(text("""
        WITH numbered AS (
            SELECT lead_id, transaction_type,
                   COALESCE((SELECT MAX(inquiry_no) FROM marketplace_leads x
                             WHERE x.transaction_type = ml.transaction_type), 0)
                   + ROW_NUMBER() OVER (PARTITION BY transaction_type ORDER BY created_at, lead_id)
                   AS next_no
            FROM marketplace_leads ml
            WHERE inquiry_no IS NULL
        )
        UPDATE marketplace_leads ml SET inquiry_no = numbered.next_no
        FROM numbered WHERE ml.lead_id = numbered.lead_id
    """))
    db.session.execute(text("""
        UPDATE marketplace_leads SET reference_number =
            CASE transaction_type
                WHEN 'services' THEN 'SRV'
                WHEN 'real_property' THEN 'RPT'
                ELSE 'PRD'
            END || '-' || LPAD(CAST(inquiry_no AS TEXT), 4, '0')
        WHERE reference_number IS NULL AND inquiry_no IS NOT NULL
    """))

    indexes = {idx["name"] for idx in inspector.get_indexes("marketplace_leads")}
    constraints = {
        uc["name"] for uc in inspector.get_unique_constraints("marketplace_leads")
    }
    if "uq_marketplace_leads_type_inquiry_no" not in indexes | constraints:
        db.session.execute(text(
            "CREATE UNIQUE INDEX uq_marketplace_leads_type_inquiry_no "
            "ON marketplace_leads (transaction_type, inquiry_no)"
        ))
    if not any(name and "reference_number" in name for name in indexes | constraints):
        db.session.execute(text(
            "CREATE UNIQUE INDEX ix_marketplace_leads_reference_number "
            "ON marketplace_leads (reference_number)"
        ))
    for name, column in (
        ("ix_marketplace_leads_transaction_type", "transaction_type"),
        ("ix_marketplace_leads_assigned_user_id", "assigned_user_id"),
    ):
        if name not in indexes:
            db.session.execute(text(
                f"CREATE INDEX IF NOT EXISTS {name} ON marketplace_leads ({column})"
            ))

    if "marketplace_lead_reads" not in inspector.get_table_names():
        db.session.execute(text("""
            CREATE TABLE marketplace_lead_reads (
                read_id SERIAL PRIMARY KEY,
                lead_id INTEGER NOT NULL REFERENCES marketplace_leads(lead_id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                read_at TIMESTAMP NOT NULL,
                CONSTRAINT uq_marketplace_lead_reads_lead_user UNIQUE (lead_id, user_id)
            )
        """))
        db.session.execute(text(
            "CREATE INDEX ix_marketplace_lead_reads_lead_id ON marketplace_lead_reads (lead_id)"
        ))
        db.session.execute(text(
            "CREATE INDEX ix_marketplace_lead_reads_user_id ON marketplace_lead_reads (user_id)"
        ))
        logger.info("Created marketplace_lead_reads table")

    db.session.commit()
