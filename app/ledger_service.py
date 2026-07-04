from datetime import datetime
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import db
from app.config import LEDGER_TRANSACTION_CREDIT, LEDGER_TRANSACTION_DEBIT
from app.models import Member, MemberLedger, SharingBatch, SharingEntry


def _ledger_description(entry, project_title):
    parts = []
    if entry.recipient_type == "admin":
        parts.append("PLATFORM")
    elif entry.share_scheme == "client":
        parts.append("Ref-Client")
    elif entry.share_scheme == "platform_ref_client":
        parts.append("Platform Ref-Client")
    elif entry.share_scheme == "contractor":
        parts.append("Ref-Contractor")
    elif entry.share_scheme == "platform_ref_contractor":
        parts.append("Platform Ref-Contractor")
    elif entry.share_scheme == "platform_pop":
        parts.append("Platform POP")
    if entry.recipient_type == "mandate":
        parts.append("Mandate pool")
    elif entry.level == -1:
        parts.append("PLATFORM")
    elif entry.level:
        parts.append(f"Level {entry.level}")
    parts.append(project_title)
    return " — ".join(parts)


def record_ledger_for_batch(batch):
    """Create member ledger rows from sharing entries in a batch."""
    entries = (
        SharingEntry.query
        .filter_by(batch_id=batch.batch_id)
        .filter(SharingEntry.member_id.isnot(None))
        .filter(SharingEntry.recipient_type.notin_(("pop", "mandate")))
        .filter(SharingEntry.share_amount > 0)
        .all()
    )
    created_at = batch.generated_at or datetime.utcnow()
    for entry in entries:
        project_title = entry.project.project_title if entry.project else "Project"
        db.session.add(MemberLedger(
            member_id=entry.member_id,
            transaction_type=LEDGER_TRANSACTION_CREDIT,
            batch_id=batch.batch_id,
            entry_id=entry.entry_id,
            billing_date=batch.commission_date,
            project_id=entry.project_id,
            billing_id=entry.billing_id,
            project_title=project_title,
            recipient_type=entry.recipient_type,
            share_scheme=entry.share_scheme,
            level=entry.level,
            share_amount=entry.share_amount,
            description=_ledger_description(entry, project_title),
            created_at=created_at,
        ))


def delete_sharing_batch(batch_id):
    batch = db.session.get(SharingBatch, batch_id)
    if not batch:
        raise ValueError("Sharing batch not found.")
    billing_date = batch.commission_date
    db.session.delete(batch)
    db.session.commit()
    return billing_date


def member_ledger_query(member_id=None):
    query = (
        MemberLedger.query
        .options(joinedload(MemberLedger.member))
        .order_by(MemberLedger.billing_date.desc(), MemberLedger.ledger_id.desc())
    )
    if member_id:
        query = query.filter(MemberLedger.member_id == member_id)
    return query


def member_ledger_stats(member_id=None):
    query = db.session.query(MemberLedger)
    if member_id:
        query = query.filter(MemberLedger.member_id == member_id)

    count = query.count()
    credits = (
        db.session.query(func.coalesce(func.sum(MemberLedger.share_amount), 0))
        .filter(MemberLedger.transaction_type == LEDGER_TRANSACTION_CREDIT)
    )
    debits = (
        db.session.query(func.coalesce(func.sum(MemberLedger.share_amount), 0))
        .filter(MemberLedger.transaction_type == LEDGER_TRANSACTION_DEBIT)
    )
    if member_id:
        credits = credits.filter(MemberLedger.member_id == member_id)
        debits = debits.filter(MemberLedger.member_id == member_id)

    credit_total = float(credits.scalar() or 0)
    debit_total = float(debits.scalar() or 0)
    net_balance = credit_total - debit_total

    stats = {
        "transaction_count": int(count or 0),
        "total_earnings": credit_total,
        "total_credits": credit_total,
        "total_debits": debit_total,
        "net_balance": net_balance,
    }

    if member_id:
        from app.payout_service import member_available_balance, member_reserved_payout_total
        stats["reserved_payout"] = member_reserved_payout_total(member_id)
        stats["available_balance"] = member_available_balance(member_id)
    else:
        stats["reserved_payout"] = 0.0
        stats["available_balance"] = net_balance

    return stats


def member_ledger_rows(member_id=None, limit=None):
    query = member_ledger_query(member_id)
    if limit:
        query = query.limit(limit)
    rows = query.all()
    return [_ledger_row_dict(row) for row in rows]


def _ledger_row_dict(row):
    amount = float(row.share_amount or 0)
    is_debit = (row.transaction_type or LEDGER_TRANSACTION_CREDIT) == LEDGER_TRANSACTION_DEBIT
    return {
        "ledger_id": row.ledger_id,
        "member_id": row.member_id,
        "member_name": row.member.full_name if row.member else None,
        "transaction_type": row.transaction_type or LEDGER_TRANSACTION_CREDIT,
        "batch_id": row.batch_id,
        "billing_date": row.billing_date.isoformat() if row.billing_date else None,
        "project_id": row.project_id,
        "project_title": row.project_title or ("Fund Release" if is_debit else "—"),
        "recipient_type": row.recipient_type,
        "share_scheme": row.share_scheme,
        "level": row.level,
        "share_amount": amount,
        "signed_amount": -amount if is_debit else amount,
        "description": row.description,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "payout_request_id": row.payout_request_id,
    }
