from collections import defaultdict

from sqlalchemy import func

from app import db
from app.models import Contractor, Member, Supplier


def dashboard_stats():
    member_batch_rows = (
        db.session.query(Member.batch, func.count(Member.member_id))
        .group_by(Member.batch)
        .all()
    )
    by_batch = {batch: count for batch, count in member_batch_rows}
    total_members = sum(by_batch.values())

    root_members = (
        db.session.query(func.count(Member.member_id))
        .filter(Member.referrer_id.is_(None))
        .scalar()
        or 0
    )

    referral_leader_rows = (
        db.session.query(
            Member.referrer_id,
            func.count(Member.member_id).label("referral_count"),
        )
        .filter(Member.referrer_id.isnot(None))
        .group_by(Member.referrer_id)
        .order_by(func.count(Member.member_id).desc())
        .limit(5)
        .all()
    )
    leader_ids = [row.referrer_id for row in referral_leader_rows if row.referral_count > 0]
    leaders = {
        member.member_id: member
        for member in Member.query.filter(Member.member_id.in_(leader_ids)).all()
    } if leader_ids else {}

    contractor_batch_rows = (
        db.session.query(Contractor.batch, func.count(Contractor.contractor_id))
        .group_by(Contractor.batch)
        .all()
    )
    contractor_by_batch = {batch: count for batch, count in contractor_batch_rows}
    contractor_referrers = (
        db.session.query(func.count(func.distinct(Contractor.member_referrer_id))).scalar()
        or 0
    )

    supplier_batch_rows = (
        db.session.query(Supplier.batch, func.count(Supplier.supplier_id))
        .group_by(Supplier.batch)
        .all()
    )
    supplier_by_batch = {batch: count for batch, count in supplier_batch_rows}
    supplier_referrers = (
        db.session.query(func.count(func.distinct(Supplier.member_referrer_id))).scalar()
        or 0
    )

    return {
        "total_members": total_members,
        "root_members": root_members,
        "referred_members": total_members - root_members,
        "batch_counts": dict(sorted(by_batch.items())),
        "max_batch": max(by_batch.keys()) if by_batch else 0,
        "total_contractors": sum(contractor_by_batch.values()),
        "contractor_batch_counts": dict(sorted(contractor_by_batch.items())),
        "max_contractor_batch": max(contractor_by_batch.keys()) if contractor_by_batch else 0,
        "contractor_member_referrers": contractor_referrers,
        "total_suppliers": sum(supplier_by_batch.values()),
        "supplier_batch_counts": dict(sorted(supplier_by_batch.items())),
        "max_supplier_batch": max(supplier_by_batch.keys()) if supplier_by_batch else 0,
        "supplier_member_referrers": supplier_referrers,
        "top_referrers": [
            {
                "member_id": row.referrer_id,
                "full_name": leaders[row.referrer_id].full_name,
                "referral_count": row.referral_count,
                "batch": leaders[row.referrer_id].batch,
            }
            for row in referral_leader_rows
            if row.referral_count > 0 and row.referrer_id in leaders
        ],
    }


def build_hierarchy_tree():
    members = Member.query.order_by(Member.batch.asc(), Member.member_id.asc()).all()
    children_map = defaultdict(list)
    roots = []

    for member in members:
        if member.referrer_id is None:
            roots.append(member)
        else:
            children_map[member.referrer_id].append(member)

    def serialize(member):
        children = children_map.get(member.member_id, [])
        return {
            "member_id": member.member_id,
            "full_name": member.full_name,
            "batch": member.batch,
            "membership_type": member.membership_type,
            "status": member.status,
            "date_joined": member.date_joined.isoformat() if member.date_joined else None,
            "referral_count": len(children),
            "children": [serialize(child) for child in sorted(children, key=lambda m: m.member_id)],
        }

    return [serialize(root) for root in sorted(roots, key=lambda m: m.member_id)]


def build_member_hierarchy_tree(member_id):
    """Hierarchy subtree rooted at one member (their downline network)."""
    member = Member.query.get(member_id)
    if not member:
        return []

    members = Member.query.order_by(Member.batch.asc(), Member.member_id.asc()).all()
    children_map = defaultdict(list)
    for row in members:
        if row.referrer_id is not None:
            children_map[row.referrer_id].append(row)

    def serialize(node):
        children = children_map.get(node.member_id, [])
        return {
            "member_id": node.member_id,
            "full_name": node.full_name,
            "batch": node.batch,
            "membership_type": node.membership_type,
            "status": node.status,
            "date_joined": node.date_joined.isoformat() if node.date_joined else None,
            "referral_count": len(children),
            "children": [serialize(child) for child in sorted(children, key=lambda m: m.member_id)],
        }

    return [serialize(member)]


def _downline_count(root_member_id):
    """Count all descendants using one referral map query."""
    rows = (
        db.session.query(Member.member_id, Member.referrer_id)
        .filter(Member.referrer_id.isnot(None))
        .all()
    )
    children_map = defaultdict(list)
    for member_id, referrer_id in rows:
        children_map[referrer_id].append(member_id)

    total = 0
    stack = list(children_map.get(root_member_id, []))
    while stack:
        node = stack.pop()
        total += 1
        stack.extend(children_map.get(node, []))
    return total


def member_dashboard_stats(member_id):
    member = Member.query.get(member_id)
    if not member:
        return None

    from app.ledger_service import member_ledger_stats

    direct_referrals = (
        db.session.query(func.count(Member.member_id))
        .filter(Member.referrer_id == member_id)
        .scalar()
        or 0
    )
    contractor_referrals = (
        db.session.query(func.count(Contractor.contractor_id))
        .filter(Contractor.member_referrer_id == member_id)
        .scalar()
        or 0
    )
    supplier_referrals = (
        db.session.query(func.count(Supplier.supplier_id))
        .filter(Supplier.member_referrer_id == member_id)
        .scalar()
        or 0
    )
    ledger = member_ledger_stats(member_id)
    return {
        "member_id": member.member_id,
        "full_name": member.full_name,
        "batch": member.batch,
        "membership_type": member.membership_type,
        "status": member.status,
        "direct_referrals": direct_referrals,
        "downline_count": _downline_count(member_id),
        "contractor_referrals": contractor_referrals,
        "supplier_referrals": supplier_referrals,
        "ledger_transactions": ledger["transaction_count"],
        "ledger_total": ledger["total_earnings"],
    }


def member_lineage(member_id):
    member = Member.query.get(member_id)
    if not member:
        return None

    upline = []
    current = member.referrer
    while current:
        upline.append(current.to_dict())
        current = current.referrer

    return {
        "member": member.to_dict(),
        "upline": upline,
        "downline": [r.to_dict() for r in sorted(member.referrals, key=lambda m: m.member_id)],
    }
