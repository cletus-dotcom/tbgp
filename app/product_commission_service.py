"""Products Commission computation and persistence."""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from app import db
from app.config import (
    AD_FUND_RECIPIENT_LABEL,
    ADMIN_RECIPIENT_LABEL,
    ADMIN_SHARING_LEVEL,
    COMMISSION_SCHEME_PRODUCT_AD_FUND,
    COMMISSION_SCHEME_PRODUCT_AD_SPLIT,
    COMMISSION_SCHEME_PRODUCT_BUYER_BONUS,
    COMMISSION_SCHEME_PRODUCT_PLATFORM,
    COMMISSION_SCHEME_PRODUCT_POP,
    COMMISSION_SCHEME_PRODUCT_REF_BUYER,
    COMMISSION_SCHEME_PRODUCT_REF_SELLER,
    DEFAULT_PRODUCT_POOL_LEVELS,
    LEDGER_TRANSACTION_CREDIT,
    MAX_SHARING_LEVELS,
    POP_RECIPIENT_LABEL,
    PRODUCT_AD_CHARGE_AD_FUND,
    PRODUCT_AD_CHARGE_PLATFORM,
    PRODUCT_AD_CHARGE_SOURCES,
    PRODUCT_AD_FUND_PERCENT,
    PRODUCT_BONUS_AD_DEFAULT_PERCENT,
    PRODUCT_BONUS_AUTO_PERCENT,
    PRODUCT_BONUS_TYPE_AD,
    PRODUCT_BONUS_TYPE_AUTO,
    PRODUCT_BONUS_TYPES,
    PRODUCT_PLATFORM_PERCENT,
    PRODUCT_POP_PERCENT,
    PRODUCT_REF_BUYER_PERCENT,
    PRODUCT_REF_SELLER_PERCENT,
    mandate_subaccount_label,
)
from app.models import (
    AdSplitMember,
    Member,
    MemberLedger,
    ProductCommission,
    ProductCommissionAdAllocation,
    ProductCommissionShare,
)
from app.prof_sharing_service import build_sharing_chain, get_admin_member


def _quantize_money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _money_float(value):
    return float(_quantize_money(value))


def product_top_level_split_total():
    return (
        PRODUCT_REF_SELLER_PERCENT
        + PRODUCT_REF_BUYER_PERCENT
        + PRODUCT_POP_PERCENT
        + PRODUCT_AD_FUND_PERCENT
        + PRODUCT_PLATFORM_PERCENT
    )


def assert_product_split_totals_100():
    total = product_top_level_split_total()
    if total != Decimal("100"):
        raise ValueError(
            f"Products Commission split must total 100% (currently {total}%)."
        )


def product_pool_level_map():
    return {level: pct for level, pct, _desc in DEFAULT_PRODUCT_POOL_LEVELS}


def resolve_product_bonus_percent(bonus_type, ad_bonus_percent=None):
    """Return bonus type and percent-of-commission taken from the PLATFORM slice."""
    bonus_type = (bonus_type or PRODUCT_BONUS_TYPE_AUTO).strip().lower()
    if bonus_type not in PRODUCT_BONUS_TYPES:
        raise ValueError("Bonus type must be Auto-Bonus or AD-Bonus.")
    if bonus_type == PRODUCT_BONUS_TYPE_AUTO:
        return PRODUCT_BONUS_TYPE_AUTO, PRODUCT_BONUS_AUTO_PERCENT
    if ad_bonus_percent is None or str(ad_bonus_percent).strip() == "":
        percent = PRODUCT_BONUS_AD_DEFAULT_PERCENT
    else:
        percent = Decimal(str(ad_bonus_percent).replace(",", "").strip())
    if percent < 0:
        raise ValueError("AD-Bonus percent cannot be negative.")
    if percent > PRODUCT_PLATFORM_PERCENT:
        raise ValueError(
            f"AD-Bonus cannot exceed PLATFORM share ({PRODUCT_PLATFORM_PERCENT}%)."
        )
    return PRODUCT_BONUS_TYPE_AD, _quantize_money(percent)


def summarize_product_account_earnings(share_items):
    """Aggregate share lines into total earnings per account, with expandable details."""
    account_totals = {}
    for item in share_items:
        amount_value = Decimal(str(item.get("share_amount") or 0))
        if amount_value <= 0:
            continue

        recipient_type = item.get("recipient_type") or "member"
        member_id = item.get("member_id")
        member_name = item.get("member_name")
        recipient_label = item.get("recipient_label")
        share_scheme = item.get("share_scheme")
        level = item.get("level") or 0
        percentage = item.get("percentage") or 0

        if recipient_type == "member" and member_id:
            key = ("member", int(member_id))
            account_name = member_name or f"Member #{member_id}"
            account_id = int(member_id)
            display_type = "member"
        elif recipient_type == "admin":
            key = ("admin", int(member_id) if member_id else 0)
            account_name = ADMIN_RECIPIENT_LABEL
            account_id = int(member_id) if member_id else None
            display_type = "platform"
        elif recipient_type == "mandate":
            key = ("mandate", 0)
            account_name = "Mandate Account"
            account_id = None
            display_type = "mandate"
        elif recipient_type == "pop":
            key = ("pop", 0)
            account_name = POP_RECIPIENT_LABEL
            account_id = None
            display_type = "pop"
        elif recipient_type == "ad_fund":
            key = ("ad_fund", 0)
            account_name = AD_FUND_RECIPIENT_LABEL
            account_id = None
            display_type = "ad_fund"
        else:
            key = (recipient_type, recipient_label or "")
            account_name = recipient_label or recipient_type
            account_id = int(member_id) if member_id else None
            display_type = recipient_type

        scheme_labels = {
            COMMISSION_SCHEME_PRODUCT_REF_SELLER: "Ref-Seller pool",
            COMMISSION_SCHEME_PRODUCT_REF_BUYER: "Ref-Buyer pool",
            COMMISSION_SCHEME_PRODUCT_BUYER_BONUS: "Ref-Buyer bonus",
            COMMISSION_SCHEME_PRODUCT_PLATFORM: "PLATFORM",
            COMMISSION_SCHEME_PRODUCT_POP: "POP",
            COMMISSION_SCHEME_PRODUCT_AD_FUND: "AD-Fund",
            COMMISSION_SCHEME_PRODUCT_AD_SPLIT: "AD-Member split",
        }
        detail_label = scheme_labels.get(share_scheme, share_scheme or display_type)
        if level and int(level) > 0:
            detail_label = f"{detail_label} - Level {level}"
        elif recipient_label and display_type in ("platform", "mandate", "pop", "ad_fund"):
            # Keep a short note when label adds useful context beyond the account name.
            note = str(recipient_label).strip()
            if note and note != account_name and "(" in note:
                detail_label = f"{detail_label} - {note}"

        row = account_totals.setdefault(key, {
            "account_id": account_id,
            "account_name": account_name,
            "recipient_type": display_type,
            "total_amount": Decimal("0"),
            "line_count": 0,
            "details": [],
        })
        row["total_amount"] += amount_value
        row["line_count"] += 1
        row["details"].append({
            "label": detail_label,
            "share_scheme": share_scheme,
            "level": int(level) if level else 0,
            "percentage": _money_float(percentage),
            "share_amount": _money_float(amount_value),
            "recipient_label": recipient_label,
        })

    type_order = {"member": 0, "platform": 1, "mandate": 2, "pop": 3, "ad_fund": 4}
    return sorted(
        [
            {
                "account_id": row["account_id"],
                "account_name": row["account_name"],
                "recipient_type": row["recipient_type"],
                "total_amount": _money_float(row["total_amount"]),
                "line_count": row["line_count"],
                "details": row["details"],
            }
            for row in account_totals.values()
        ],
        key=lambda row: (
            type_order.get(row["recipient_type"], 99),
            -(row["total_amount"] or 0),
            (row["account_name"] or "").lower(),
        ),
    )


def compute_platform_bonus_split(commission_amount, bonus_type, ad_bonus_percent=None):
    """
    Bonus is carved from the PLATFORM slice of the product commission (default 65%).

    Examples on a 100% commission base:
    - Auto-Bonus 10%  → PLATFORM net 55% (65 − 10), Ref-Buyer bonus 10%
    - AD-Bonus 34%    → PLATFORM net 31% (65 − 34), Ref-Buyer bonus 34%
    """
    amount = _quantize_money(commission_amount)
    bonus_type, bonus_percent = resolve_product_bonus_percent(bonus_type, ad_bonus_percent)
    platform_gross_percent = PRODUCT_PLATFORM_PERCENT
    platform_net_percent = _quantize_money(platform_gross_percent - bonus_percent)
    if platform_net_percent < 0:
        raise ValueError("Bonus percent cannot exceed PLATFORM share.")

    platform_gross_amount = _portion(amount, platform_gross_percent)
    bonus_amount = _portion(amount, bonus_percent)
    platform_net_amount = _quantize_money(platform_gross_amount - bonus_amount)

    return {
        "bonus_type": bonus_type,
        "bonus_percent": bonus_percent,
        "bonus_amount": bonus_amount,
        "platform_gross_percent": platform_gross_percent,
        "platform_net_percent": platform_net_percent,
        "platform_gross_amount": platform_gross_amount,
        "platform_net_amount": platform_net_amount,
    }


def _portion(amount, percent):
    return _quantize_money(Decimal(str(amount)) * Decimal(str(percent)) / Decimal("100"))


def _share_from_pool(pool, percentage):
    return _quantize_money(pool * Decimal(str(percentage)) / Decimal("100"))


def _share_row(
    member=None,
    recipient_type="member",
    recipient_label=None,
    share_scheme=None,
    level=0,
    percentage=Decimal("0"),
    share_amount=Decimal("0"),
):
    return {
        "member": member,
        "member_id": member.member_id if member else None,
        "member_name": member.full_name if member else None,
        "recipient_type": recipient_type,
        "recipient_label": recipient_label,
        "share_scheme": share_scheme,
        "level": level,
        "percentage": _quantize_money(percentage),
        "share_amount": _quantize_money(share_amount),
    }


def normalize_ad_member_allocations(ad_allocations):
    """Normalize AD-member split rows from the entry form / API payload."""
    if not ad_allocations:
        return []
    if not isinstance(ad_allocations, (list, tuple)):
        raise ValueError("AD-member allocations must be a list.")

    allowed_ids = {
        row.member_id
        for row in AdSplitMember.query.all()
    }
    normalized = []
    seen = set()
    for raw in ad_allocations:
        if not isinstance(raw, dict):
            continue
        member_id_raw = raw.get("member_id")
        if member_id_raw in (None, ""):
            continue
        member_id = int(member_id_raw)
        amount_raw = raw.get("amount")
        if amount_raw in (None, ""):
            amount = Decimal("0")
        else:
            amount = _quantize_money(str(amount_raw).replace(",", "").strip())
        if amount < 0:
            raise ValueError("AD-member split amounts cannot be negative.")
        if amount == 0:
            continue
        charge_from = (raw.get("charge_from") or PRODUCT_AD_CHARGE_PLATFORM).strip().lower()
        if charge_from not in PRODUCT_AD_CHARGE_SOURCES:
            raise ValueError("AD-member charge source must be PLATFORM or AD-Fund.")
        if member_id not in allowed_ids:
            raise ValueError(
                f"Member #{member_id} is not on the AD-Members Split Sharing list."
            )
        if member_id in seen:
            raise ValueError(f"Duplicate AD-member allocation for member #{member_id}.")
        seen.add(member_id)
        member = db.session.get(Member, member_id)
        if not member or member.status != "Active":
            raise ValueError(f"AD-member #{member_id} must be an active member.")
        normalized.append({
            "member_id": member_id,
            "member": member,
            "member_name": member.full_name,
            "amount": amount,
            "charge_from": charge_from,
        })
    return normalized


def _available_share_total(shares, recipient_type):
    return sum(
        item["share_amount"]
        for item in shares
        if item["recipient_type"] == recipient_type and item["share_amount"] > 0
    )


def _deduct_from_recipient_type(shares, recipient_type, amount, source_label):
    remaining = _quantize_money(amount)
    available = _available_share_total(shares, recipient_type)
    if remaining > available:
        raise ValueError(
            f"{source_label} available ({available:,.2f}) is less than "
            f"AD-member charge ({remaining:,.2f})."
        )
    rows = [
        item for item in shares
        if item["recipient_type"] == recipient_type and item["share_amount"] > 0
    ]
    rows.sort(key=lambda item: item["share_amount"], reverse=True)
    for row in rows:
        if remaining <= 0:
            break
        take = min(row["share_amount"], remaining)
        row["share_amount"] = _quantize_money(row["share_amount"] - take)
        remaining = _quantize_money(remaining - take)
    if remaining > 0:
        raise ValueError(f"Unable to fully charge {source_label} for AD-member split.")


def _apply_ad_member_allocations(shares, allocations):
    """Credit AD members and deduct from PLATFORM or AD-Fund share rows."""
    applied = []
    for row in allocations:
        amount = row["amount"]
        charge_from = row["charge_from"]
        member = row["member"]
        if charge_from == PRODUCT_AD_CHARGE_PLATFORM:
            _deduct_from_recipient_type(
                shares, "admin", amount, ADMIN_RECIPIENT_LABEL
            )
            charge_label = ADMIN_RECIPIENT_LABEL
        else:
            _deduct_from_recipient_type(
                shares, "ad_fund", amount, AD_FUND_RECIPIENT_LABEL
            )
            charge_label = AD_FUND_RECIPIENT_LABEL

        shares.append(_share_row(
            member=member,
            recipient_type="member",
            recipient_label=f"AD-Member split (from {charge_label})",
            share_scheme=COMMISSION_SCHEME_PRODUCT_AD_SPLIT,
            level=0,
            percentage=Decimal("0"),
            share_amount=amount,
        ))
        applied.append({
            "member_id": member.member_id,
            "member_name": member.full_name,
            "amount": _money_float(amount),
            "charge_from": charge_from,
        })

    # Drop emptied AD-Fund / PLATFORM rows to keep share lists clean.
    shares[:] = [item for item in shares if item["share_amount"] > 0]
    return applied


def _distribute_product_pool(referrer_id, pool, share_scheme, level_map):
    """Distribute a Ref-Seller or Ref-Buyer pool. Unallocated levels go to AD-Fund."""
    entries = []
    ad_fund_pct = Decimal("0")

    if pool <= 0:
        return entries, Decimal("0"), Decimal("0"), Decimal("0")

    if not referrer_id:
        ad_fund_pct = sum(
            level_map.get(slot, Decimal("0")) for slot in range(1, MAX_SHARING_LEVELS + 1)
        )
    else:
        chain = build_sharing_chain(referrer_id)
        for slot in range(1, MAX_SHARING_LEVELS):
            pct = level_map.get(slot, Decimal("0"))
            if pct <= 0:
                continue
            if slot > len(chain):
                ad_fund_pct += pct
                continue
            member = chain[slot - 1]
            entries.append(_share_row(
                member=member,
                recipient_type="member",
                share_scheme=share_scheme,
                level=slot,
                percentage=pct,
                share_amount=_share_from_pool(pool, pct),
            ))

        mandate_pct = level_map.get(MAX_SHARING_LEVELS, Decimal("0"))
        if mandate_pct > 0:
            entries.append(_share_row(
                recipient_type="mandate",
                recipient_label=mandate_subaccount_label(share_scheme),
                share_scheme=share_scheme,
                level=MAX_SHARING_LEVELS,
                percentage=mandate_pct,
                share_amount=_share_from_pool(pool, mandate_pct),
            ))

    ad_fund_amount = Decimal("0")
    if ad_fund_pct > 0:
        ad_fund_amount = _share_from_pool(pool, ad_fund_pct)
        entries.append(_share_row(
            recipient_type="ad_fund",
            recipient_label=f"{AD_FUND_RECIPIENT_LABEL} (unallocated {share_scheme})",
            share_scheme=COMMISSION_SCHEME_PRODUCT_AD_FUND,
            level=0,
            percentage=ad_fund_pct,
            share_amount=ad_fund_amount,
        ))

    total_shared = sum(
        item["share_amount"] for item in entries if item["recipient_type"] == "member"
    )
    total_mandate = sum(
        item["share_amount"] for item in entries if item["recipient_type"] == "mandate"
    )
    return entries, total_shared, total_mandate, ad_fund_amount


def compute_product_commission(
    commission_amount,
    ref_seller_id,
    ref_buyer_id,
    bonus_type=PRODUCT_BONUS_TYPE_AUTO,
    ad_bonus_percent=None,
    product_title="Products Commission",
    commission_date=None,
    ad_allocations=None,
):
    """Compute product commission split and 7-level sharing summary."""
    assert_product_split_totals_100()
    amount = _quantize_money(commission_amount)
    if amount <= 0:
        raise ValueError("Products Commission amount must be greater than zero.")

    seller = db.session.get(Member, int(ref_seller_id))
    if not seller or seller.status != "Active":
        raise ValueError("Ref-Seller must be an active member.")
    buyer = db.session.get(Member, int(ref_buyer_id))
    if not buyer or buyer.status != "Active":
        raise ValueError("Ref-Buyer must be an active member.")

    platform_bonus = compute_platform_bonus_split(amount, bonus_type, ad_bonus_percent)
    bonus_type = platform_bonus["bonus_type"]
    bonus_percent = platform_bonus["bonus_percent"]
    bonus_amount = platform_bonus["bonus_amount"]
    platform_gross = platform_bonus["platform_gross_amount"]
    platform_net = platform_bonus["platform_net_amount"]
    platform_gross_percent = platform_bonus["platform_gross_percent"]
    platform_net_percent = platform_bonus["platform_net_percent"]

    seller_pool = _portion(amount, PRODUCT_REF_SELLER_PERCENT)
    buyer_pool = _portion(amount, PRODUCT_REF_BUYER_PERCENT)
    pop_amount = _portion(amount, PRODUCT_POP_PERCENT)
    ad_fund_base = _portion(amount, PRODUCT_AD_FUND_PERCENT)

    level_map = product_pool_level_map()
    shares = []

    seller_entries, _seller_shared, _seller_mandate, _seller_unallocated = _distribute_product_pool(
        seller.member_id, seller_pool, COMMISSION_SCHEME_PRODUCT_REF_SELLER, level_map
    )
    shares.extend(seller_entries)

    buyer_entries, _buyer_shared, _buyer_mandate, _buyer_unallocated = _distribute_product_pool(
        buyer.member_id, buyer_pool, COMMISSION_SCHEME_PRODUCT_REF_BUYER, level_map
    )
    shares.extend(buyer_entries)

    if bonus_amount > 0:
        bonus_label = (
            "Auto-Bonus"
            if bonus_type == PRODUCT_BONUS_TYPE_AUTO
            else "AD-Bonus"
        )
        shares.append(_share_row(
            member=buyer,
            recipient_type="member",
            recipient_label=f"Ref-Buyer {bonus_label} (from PLATFORM {platform_gross_percent}% - {bonus_percent}% = {platform_net_percent}%)",
            share_scheme=COMMISSION_SCHEME_PRODUCT_BUYER_BONUS,
            level=0,
            percentage=bonus_percent,
            share_amount=bonus_amount,
        ))

    shares.append(_share_row(
        recipient_type="pop",
        recipient_label=f"{POP_RECIPIENT_LABEL} (Products)",
        share_scheme=COMMISSION_SCHEME_PRODUCT_POP,
        level=0,
        percentage=PRODUCT_POP_PERCENT,
        share_amount=pop_amount,
    ))

    shares.append(_share_row(
        recipient_type="ad_fund",
        recipient_label=f"{AD_FUND_RECIPIENT_LABEL} (Products base {PRODUCT_AD_FUND_PERCENT}%)",
        share_scheme=COMMISSION_SCHEME_PRODUCT_AD_FUND,
        level=0,
        percentage=PRODUCT_AD_FUND_PERCENT,
        share_amount=ad_fund_base,
    ))

    admin_member = get_admin_member()
    if platform_net > 0:
        shares.append(_share_row(
            member=admin_member,
            recipient_type="admin",
            recipient_label=(
                f"{ADMIN_RECIPIENT_LABEL} "
                f"({platform_gross_percent}% - {bonus_percent}% bonus = {platform_net_percent}%)"
            ),
            share_scheme=COMMISSION_SCHEME_PRODUCT_PLATFORM,
            level=ADMIN_SHARING_LEVEL,
            percentage=platform_net_percent,
            share_amount=platform_net,
        ))

    allocated = sum(item["share_amount"] for item in shares)
    remainder = _quantize_money(amount - allocated)
    if remainder > 0:
        # Send positive rounding leftover to AD-Fund.
        shares.append(_share_row(
            recipient_type="ad_fund",
            recipient_label=f"{AD_FUND_RECIPIENT_LABEL} (rounding)",
            share_scheme=COMMISSION_SCHEME_PRODUCT_AD_FUND,
            level=0,
            percentage=Decimal("0"),
            share_amount=remainder,
        ))
    elif remainder < 0:
        raise ValueError(
            f"Products Commission shares over-allocate by {abs(remainder):,.2f}. "
            "Check that the top-level split totals 100%."
        )

    normalized_allocations = normalize_ad_member_allocations(ad_allocations)
    applied_allocations = _apply_ad_member_allocations(shares, normalized_allocations)

    total_shared = sum(
        item["share_amount"] for item in shares if item["recipient_type"] == "member"
    )
    total_mandate = sum(
        item["share_amount"] for item in shares if item["recipient_type"] == "mandate"
    )
    total_ad_fund = sum(
        item["share_amount"] for item in shares if item["recipient_type"] == "ad_fund"
    )
    total_pop = sum(
        item["share_amount"] for item in shares if item["recipient_type"] == "pop"
    )
    total_platform = sum(
        item["share_amount"] for item in shares if item["recipient_type"] == "admin"
    )
    total_ad_split = sum(
        item["share_amount"]
        for item in shares
        if item["share_scheme"] == COMMISSION_SCHEME_PRODUCT_AD_SPLIT
    )

    account_summary = summarize_product_account_earnings(shares)

    seller_level_rows = []
    for slot in range(1, MAX_SHARING_LEVELS + 1):
        match = next((e for e in seller_entries if e["level"] == slot), None)
        pct = level_map.get(slot, Decimal("0"))
        if match:
            seller_level_rows.append({
                "level": slot,
                "percentage": _money_float(pct),
                "amount": _money_float(match["share_amount"]),
                "member_id": match["member_id"],
                "label": match["member_name"]
                or match["recipient_label"]
                or ("Mandate" if slot == MAX_SHARING_LEVELS else "—"),
                "recipient_type": match["recipient_type"],
            })
        else:
            seller_level_rows.append({
                "level": slot,
                "percentage": _money_float(pct),
                "amount": _money_float(_share_from_pool(seller_pool, pct)),
                "member_id": None,
                "label": "Unallocated → AD-Fund",
                "recipient_type": "ad_fund",
            })

    buyer_level_rows = []
    for slot in range(1, MAX_SHARING_LEVELS + 1):
        match = next((e for e in buyer_entries if e["level"] == slot), None)
        pct = level_map.get(slot, Decimal("0"))
        if match:
            buyer_level_rows.append({
                "level": slot,
                "percentage": _money_float(pct),
                "amount": _money_float(match["share_amount"]),
                "member_id": match["member_id"],
                "label": match["member_name"]
                or match["recipient_label"]
                or ("Mandate" if slot == MAX_SHARING_LEVELS else "—"),
                "recipient_type": match["recipient_type"],
            })
        else:
            buyer_level_rows.append({
                "level": slot,
                "percentage": _money_float(pct),
                "amount": _money_float(_share_from_pool(buyer_pool, pct)),
                "member_id": None,
                "label": "Unallocated → AD-Fund",
                "recipient_type": "ad_fund",
            })

    return {
        "product_title": product_title or "Products Commission",
        "commission_amount": _money_float(amount),
        "commission_date": commission_date.isoformat() if commission_date else None,
        "ref_seller_id": seller.member_id,
        "ref_seller_name": seller.full_name,
        "ref_buyer_id": buyer.member_id,
        "ref_buyer_name": buyer.full_name,
        "bonus_type": bonus_type,
        "bonus_percent": _money_float(bonus_percent),
        "bonus_amount": _money_float(bonus_amount),
        "platform_gross_percent": _money_float(platform_gross_percent),
        "platform_net_percent": _money_float(platform_net_percent),
        "seller_pool": _money_float(seller_pool),
        "buyer_pool": _money_float(buyer_pool),
        "pop_amount": _money_float(total_pop),
        "ad_fund_amount": _money_float(total_ad_fund),
        "platform_amount": _money_float(total_platform),
        "platform_gross": _money_float(platform_gross),
        "platform_net": _money_float(total_platform),
        "ad_split_amount": _money_float(total_ad_split),
        "ad_allocations": applied_allocations,
        "total_shared": _money_float(total_shared),
        "total_mandate": _money_float(total_mandate),
        "split": {
            "ref_seller_percent": float(PRODUCT_REF_SELLER_PERCENT),
            "ref_buyer_percent": float(PRODUCT_REF_BUYER_PERCENT),
            "pop_percent": float(PRODUCT_POP_PERCENT),
            "ad_fund_percent": float(PRODUCT_AD_FUND_PERCENT),
            "platform_gross_percent": float(platform_gross_percent),
            "platform_net_percent": float(platform_net_percent),
            "bonus_percent": float(bonus_percent),
        },
        "seller_levels": seller_level_rows,
        "buyer_levels": buyer_level_rows,
        "account_summary": account_summary,
        "shares": [
            {
                "member_id": item["member_id"],
                "member_name": item["member_name"],
                "recipient_type": item["recipient_type"],
                "recipient_label": item["recipient_label"],
                "share_scheme": item["share_scheme"],
                "level": item["level"],
                "percentage": _money_float(item["percentage"]),
                "share_amount": _money_float(item["share_amount"]),
            }
            for item in shares
        ],
        "_share_objects": shares,
        "_allocation_objects": normalized_allocations,
    }


def record_ledger_for_product_commission(product):
    """Credit member / PLATFORM ledger rows for a saved products commission."""
    created_at = product.created_at or datetime.utcnow()
    title = product.product_title or "Products Commission"
    for share in product.shares:
        if share.share_amount <= 0:
            continue
        if share.member_id is None:
            continue
        if share.recipient_type in ("pop", "mandate", "ad_fund"):
            continue

        scheme_label = {
            COMMISSION_SCHEME_PRODUCT_REF_SELLER: "Product Ref-Seller",
            COMMISSION_SCHEME_PRODUCT_REF_BUYER: "Product Ref-Buyer",
            COMMISSION_SCHEME_PRODUCT_BUYER_BONUS: "Product Ref-Buyer Bonus",
            COMMISSION_SCHEME_PRODUCT_PLATFORM: "PLATFORM",
            COMMISSION_SCHEME_PRODUCT_AD_SPLIT: "Product AD-Member Split",
        }.get(share.share_scheme, "Products")
        level_label = f"Level {share.level}" if share.level and share.level > 0 else (
            "PLATFORM" if share.recipient_type == "admin"
            else ("AD Split" if share.share_scheme == COMMISSION_SCHEME_PRODUCT_AD_SPLIT else "Bonus")
        )
        description = f"{scheme_label} — {level_label} — {title}"

        db.session.add(MemberLedger(
            member_id=share.member_id,
            transaction_type=LEDGER_TRANSACTION_CREDIT,
            batch_id=None,
            entry_id=None,
            billing_date=product.commission_date,
            project_id=None,
            billing_id=None,
            product_commission_id=product.product_commission_id,
            project_title=title,
            recipient_type=share.recipient_type,
            share_scheme=share.share_scheme,
            level=share.level,
            share_amount=share.share_amount,
            description=description,
            created_at=created_at,
        ))


def save_product_commission(
    commission_amount,
    ref_seller_id,
    ref_buyer_id,
    bonus_type,
    ad_bonus_percent,
    product_title,
    commission_date,
    notes=None,
    created_by_user_id=None,
    ad_allocations=None,
):
    result = compute_product_commission(
        commission_amount=commission_amount,
        ref_seller_id=ref_seller_id,
        ref_buyer_id=ref_buyer_id,
        bonus_type=bonus_type,
        ad_bonus_percent=ad_bonus_percent,
        product_title=product_title,
        commission_date=commission_date,
        ad_allocations=ad_allocations,
    )

    if not get_admin_member():
        raise ValueError(
            "PLATFORM member (ADMIN_MEMBER_ID) is not configured or not Active."
        )

    product = ProductCommission(
        product_title=result["product_title"],
        commission_amount=_quantize_money(result["commission_amount"]),
        commission_date=commission_date,
        ref_seller_id=result["ref_seller_id"],
        ref_buyer_id=result["ref_buyer_id"],
        bonus_type=result["bonus_type"],
        bonus_percent=_quantize_money(result["bonus_percent"]),
        notes=(notes or "").strip() or None,
        seller_pool=_quantize_money(result["seller_pool"]),
        buyer_pool=_quantize_money(result["buyer_pool"]),
        pop_amount=_quantize_money(result["pop_amount"]),
        ad_fund_amount=_quantize_money(result["ad_fund_amount"]),
        platform_amount=_quantize_money(result["platform_amount"]),
        bonus_amount=_quantize_money(result["bonus_amount"]),
        total_shared=_quantize_money(result["total_shared"]),
        total_mandate=_quantize_money(result["total_mandate"]),
        created_at=datetime.utcnow(),
        created_by_user_id=created_by_user_id,
    )
    db.session.add(product)
    db.session.flush()

    for item in result["_share_objects"]:
        db.session.add(ProductCommissionShare(
            product_commission_id=product.product_commission_id,
            member_id=item["member_id"],
            recipient_type=item["recipient_type"],
            recipient_label=item["recipient_label"],
            share_scheme=item["share_scheme"],
            level=item["level"],
            percentage=item["percentage"],
            share_amount=item["share_amount"],
        ))
    for item in result.get("_allocation_objects") or []:
        db.session.add(ProductCommissionAdAllocation(
            product_commission_id=product.product_commission_id,
            member_id=item["member_id"],
            amount=item["amount"],
            charge_from=item["charge_from"],
        ))
    db.session.flush()
    record_ledger_for_product_commission(product)
    db.session.commit()
    return product


def delete_product_commission(product_commission_id):
    product = db.session.get(ProductCommission, product_commission_id)
    if not product:
        raise ValueError("Products commission not found.")

    MemberLedger.query.filter_by(product_commission_id=product_commission_id).delete()
    db.session.delete(product)
    db.session.commit()
