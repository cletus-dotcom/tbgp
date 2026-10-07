from datetime import datetime
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import db
from app.config import LEDGER_TRANSACTION_CREDIT, LEDGER_TRANSACTION_DEBIT
from app.models import MarketplaceLead, Member, MemberLedger, SharingBatch, SharingEntry
from app.timeutil import manila_now


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
    created_at = batch.generated_at or manila_now()
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


def member_ledger_rows(member_id=None, limit=None, member_view=False):
    """Ledger rows; member_view hides project titles so members never receive a project list."""
    query = member_ledger_query(member_id)
    if limit:
        query = query.limit(limit)
    rows = query.all()
    references = _project_references(rows) if member_view else {}
    return [_ledger_row_dict(row, references if member_view else None) for row in rows]


def _project_references(rows):
    project_ids = {row.project_id for row in rows if row.project_id}
    if not project_ids:
        return {}
    return dict(
        db.session.query(MarketplaceLead.commission_project_id, MarketplaceLead.reference_number)
        .filter(MarketplaceLead.commission_project_id.in_(project_ids))
        .all()
    )


def _member_safe_title(row, references):
    if row.project_id:
        return references.get(row.project_id) or f"Project no. {row.project_id}"
    if row.product_commission_id:
        return f"Products commission no. {row.product_commission_id}"
    return row.project_title


def _ledger_row_dict(row, references=None):
    amount = float(row.share_amount or 0)
    is_debit = (row.transaction_type or LEDGER_TRANSACTION_CREDIT) == LEDGER_TRANSACTION_DEBIT
    title = row.project_title
    description = row.description
    if references is not None and not is_debit:
        title = _member_safe_title(row, references)
        if description and row.project_title and description.endswith(row.project_title):
            description = description[: -len(row.project_title)] + title
    return {
        "ledger_id": row.ledger_id,
        "member_id": row.member_id,
        "member_name": row.member.full_name if row.member else None,
        "transaction_type": row.transaction_type or LEDGER_TRANSACTION_CREDIT,
        "batch_id": row.batch_id,
        "billing_date": row.billing_date.isoformat() if row.billing_date else None,
        "project_id": row.project_id,
        "project_title": title or ("Fund Release" if is_debit else "—"),
        "recipient_type": row.recipient_type,
        "share_scheme": row.share_scheme,
        "level": row.level,
        "share_amount": amount,
        "signed_amount": -amount if is_debit else amount,
        "description": description,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "payout_request_id": row.payout_request_id,
    }
