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
    "beneficiary_name": "VARCHAR(120)",
    "beneficiary_address": "VARCHAR(255)",
    "beneficiary_phone": "VARCHAR(30)",
    "status": "VARCHAR(20) DEFAULT 'Active'",
    "termination_date": "DATE",
    "termination_type": "VARCHAR(60)",
    "date_joined": "DATE",
    "lifetime_cap_enabled": "BOOLEAN DEFAULT TRUE",
    "lifetime_cap_amount": "NUMERIC(14, 2) DEFAULT 50000000",
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
    }
    for col_name, col_type in alters.items():
        if col_name not in columns:
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
    db.session.commit()
