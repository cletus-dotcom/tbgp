from collections import defaultdict

from app.models import Contractor, Member, Supplier


def dashboard_stats():
    members = Member.query.all()
    contractors = Contractor.query.all()
    suppliers = Supplier.query.all()

    by_batch = defaultdict(int)
    for member in members:
        by_batch[member.batch] += 1

    contractor_by_batch = defaultdict(int)
    contractor_referrers = set()
    for contractor in contractors:
        contractor_by_batch[contractor.batch] += 1
        contractor_referrers.add(contractor.member_referrer_id)

    supplier_by_batch = defaultdict(int)
    supplier_referrers = set()
    for supplier in suppliers:
        supplier_by_batch[supplier.batch] += 1
        supplier_referrers.add(supplier.member_referrer_id)

    roots = [m for m in members if m.referrer_id is None]
    with_referrer = [m for m in members if m.referrer_id is not None]

    top_referrers = sorted(
        members,
        key=lambda m: len(m.referrals),
        reverse=True,
    )[:5]

    return {
        "total_members": len(members),
        "root_members": len(roots),
        "referred_members": len(with_referrer),
        "batch_counts": dict(sorted(by_batch.items())),
        "max_batch": max(by_batch.keys()) if by_batch else 0,
        "total_contractors": len(contractors),
        "contractor_batch_counts": dict(sorted(contractor_by_batch.items())),
        "max_contractor_batch": max(contractor_by_batch.keys()) if contractor_by_batch else 0,
        "contractor_member_referrers": len(contractor_referrers),
        "total_suppliers": len(suppliers),
        "supplier_batch_counts": dict(sorted(supplier_by_batch.items())),
        "max_supplier_batch": max(supplier_by_batch.keys()) if supplier_by_batch else 0,
        "supplier_member_referrers": len(supplier_referrers),
        "top_referrers": [
            {
                "member_id": m.member_id,
                "full_name": m.full_name,
                "referral_count": len(m.referrals),
                "batch": m.batch,
            }
            for m in top_referrers
            if len(m.referrals) > 0
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


def _count_downline(member):
    total = 0
    for child in member.referrals:
        total += 1 + _count_downline(child)
    return total


def member_dashboard_stats(member_id):
    member = Member.query.get(member_id)
    if not member:
        return None

    from app.ledger_service import member_ledger_stats

    ledger = member_ledger_stats(member_id)
    return {
        "member_id": member.member_id,
        "full_name": member.full_name,
        "batch": member.batch,
        "membership_type": member.membership_type,
        "status": member.status,
        "direct_referrals": len(member.referrals),
        "downline_count": _count_downline(member),
        "contractor_referrals": len(member.contractor_referrals),
        "supplier_referrals": len(member.supplier_referrals),
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
