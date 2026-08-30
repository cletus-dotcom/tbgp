"""Marketplace listings, share attribution, and inquiry CRM."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from flask import request
from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import joinedload

from app import db
from app.config import (
    MARKETPLACE_ATTRIBUTION_COOKIE,
    MARKETPLACE_ATTRIBUTION_DAYS,
    MARKETPLACE_CATEGORIES,
    MARKETPLACE_CATEGORY_PRODUCTS,
    MARKETPLACE_CATEGORY_SERVICES,
    MARKETPLACE_CATEGORY_SLUGS,
    MARKETPLACE_FUNNEL_CATEGORY_SLUGS,
    MARKETPLACE_STATUS_DRAFT,
    MARKETPLACE_STATUS_PUBLISHED,
    MARKETPLACE_STATUSES,
)
from app.models import MarketplaceLead, MarketplaceListing, Member


def get_marketplace_category(slug):
    return MARKETPLACE_CATEGORIES.get(slug)


def require_marketplace_category(slug):
    meta = get_marketplace_category(slug)
    if not meta:
        raise ValueError("Unknown marketplace category.")
    return meta


def list_published_by_category(category, limit=None):
    require_marketplace_category(category)
    query = (
        MarketplaceListing.query
        .filter_by(category=category, status=MARKETPLACE_STATUS_PUBLISHED)
        .order_by(
            MarketplaceListing.sort_order.asc(),
            MarketplaceListing.updated_at.desc(),
            MarketplaceListing.listing_id.desc(),
        )
    )
    if limit:
        query = query.limit(int(limit))
    return query.all()


def list_all_for_admin(category=None):
    query = MarketplaceListing.query
    if category:
        require_marketplace_category(category)
        query = query.filter_by(category=category)
    return query.order_by(
        MarketplaceListing.category.asc(),
        MarketplaceListing.sort_order.asc(),
        MarketplaceListing.updated_at.desc(),
    ).all()


def get_listing(listing_id, published_only=False):
    listing = db.session.get(MarketplaceListing, int(listing_id))
    if not listing:
        return None
    if published_only and listing.status != MARKETPLACE_STATUS_PUBLISHED:
        return None
    return listing


def get_published_listing(category, listing_id):
    listing = get_listing(listing_id, published_only=True)
    if not listing or listing.category != category:
        return None
    return listing


def _parse_gallery(form):
    gallery = []
    for key in sorted(form.keys()):
        if not key.startswith("gallery_url_"):
            continue
        url = (form.get(key) or "").strip()
        if not url:
            continue
        idx = key.replace("gallery_url_", "", 1)
        alt = (form.get(f"gallery_alt_{idx}") or "").strip()
        gallery.append({"url": url, "alt": alt})
    return gallery


def parse_listing_form(form, existing=None):
    category = (form.get("category") or "").strip()
    require_marketplace_category(category)
    title = (form.get("title") or "").strip()
    if not title:
        raise ValueError("Title is required.")
    status = (form.get("status") or MARKETPLACE_STATUS_DRAFT).strip().lower()
    if status not in MARKETPLACE_STATUSES:
        raise ValueError("Status must be draft or published.")
    try:
        sort_order = int(form.get("sort_order") or 0)
    except (TypeError, ValueError):
        sort_order = 0

    return {
        "category": category,
        "title": title,
        "summary": (form.get("summary") or "").strip() or None,
        "body": (form.get("body") or "").strip() or None,
        "price_label": (form.get("price_label") or "").strip() or None,
        "location": (form.get("location") or "").strip() or None,
        "status": status,
        "thumbnail_url": (form.get("thumbnail_url") or "").strip() or None,
        "gallery": _parse_gallery(form),
        "contact_name": (form.get("contact_name") or "").strip() or None,
        "contact_phone": (form.get("contact_phone") or "").strip() or None,
        "contact_email": (form.get("contact_email") or "").strip() or None,
        "sort_order": sort_order,
    }


def save_listing(data, listing=None, created_by_user_id=None):
    if listing is None:
        listing = MarketplaceListing(created_by_user_id=created_by_user_id)
        db.session.add(listing)

    listing.category = data["category"]
    listing.title = data["title"]
    listing.summary = data.get("summary")
    listing.body = data.get("body")
    listing.price_label = data.get("price_label")
    listing.location = data.get("location")
    listing.status = data["status"]
    listing.thumbnail_url = data.get("thumbnail_url")
    listing.gallery = data.get("gallery") or []
    listing.contact_name = data.get("contact_name")
    listing.contact_phone = data.get("contact_phone")
    listing.contact_email = data.get("contact_email")
    listing.sort_order = data.get("sort_order") or 0
    listing.updated_at = datetime.utcnow()
    if not listing.created_at:
        listing.created_at = datetime.utcnow()

    db.session.commit()
    return listing


def delete_listing(listing_id):
    listing = get_listing(listing_id)
    if not listing:
        raise ValueError("Listing not found.")
    db.session.delete(listing)
    db.session.commit()


def ensure_member_share_code(member):
    if member.marketplace_share_code:
        return member.marketplace_share_code
    for _ in range(12):
        code = secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:10].lower()
        exists = Member.query.filter_by(marketplace_share_code=code).first()
        if not exists:
            member.marketplace_share_code = code
            db.session.commit()
            return code
    raise ValueError("Unable to generate a marketplace share code.")


def get_member_by_share_code(share_code):
    code = (share_code or "").strip().lower()
    if not code:
        return None
    return (
        Member.query
        .filter(Member.marketplace_share_code == code, Member.status == "Active")
        .first()
    )


def set_attribution_cookie(response, member):
    if not member:
        return response
    max_age = MARKETPLACE_ATTRIBUTION_DAYS * 24 * 60 * 60
    response.set_cookie(
        MARKETPLACE_ATTRIBUTION_COOKIE,
        str(member.member_id),
        max_age=max_age,
        expires=datetime.utcnow() + timedelta(days=MARKETPLACE_ATTRIBUTION_DAYS),
        httponly=True,
        samesite="Lax",
        path="/",
    )
    return response


def clear_attribution_cookie(response):
    """Remove marketplace referral attribution (e.g. on portal logout)."""
    response.delete_cookie(
        MARKETPLACE_ATTRIBUTION_COOKIE,
        path="/",
        samesite="Lax",
        httponly=True,
    )
    return response


def get_attributed_member_id():
    try:
        raw = request.cookies.get(MARKETPLACE_ATTRIBUTION_COOKIE)
    except RuntimeError:
        return None
    if not raw:
        return None
    try:
        member_id = int(raw)
    except (TypeError, ValueError):
        return None
    member = db.session.get(Member, member_id)
    if not member or member.status != "Active":
        return None
    return member.member_id


def get_attributed_member():
    member_id = get_attributed_member_id()
    if not member_id:
        return None
    return db.session.get(Member, member_id)


def create_lead(
    listing=None,
    guest_name=None,
    guest_phone=None,
    guest_email=None,
    message=None,
    source_path=None,
    interest_category=None,
):
    name = (guest_name or "").strip()
    if not name:
        raise ValueError("Your name is required.")
    phone = (guest_phone or "").strip() or None
    email = (guest_email or "").strip() or None
    if not phone and not email:
        raise ValueError("Provide a phone number or email so we can contact you.")
    note = (message or "").strip() or None
    category = (interest_category or "").strip() or None
    if category:
        require_marketplace_category(category)
    listing_id = listing.listing_id if listing is not None else None
    if listing is not None and not category:
        category = listing.category

    lead = MarketplaceLead(
        listing_id=listing_id,
        interest_category=category,
        attributed_member_id=get_attributed_member_id(),
        guest_name=name,
        guest_phone=phone,
        guest_email=email,
        message=note,
        source_path=(source_path or "")[:255] or None,
        created_at=datetime.utcnow(),
    )
    db.session.add(lead)
    db.session.commit()
    return lead


def create_products_funnel_lead(form, source_path=None):
    """Create a Products marketplace lead from the multi-step funnel form."""
    business_type = (form.get("business_type") or "").strip()
    interest = (form.get("interest") or "").strip()
    timeline = (form.get("timeline") or "").strip()
    listing_id_raw = (form.get("listing_id") or "").strip()
    notes = (form.get("notes") or "").strip()

    listing = None
    if listing_id_raw.isdigit():
        listing = get_published_listing(MARKETPLACE_CATEGORY_PRODUCTS, int(listing_id_raw))

    parts = []
    if business_type:
        parts.append(f"Business type: {business_type}")
    if interest:
        parts.append(f"Looking for: {interest}")
    if timeline:
        parts.append(f"Timeline: {timeline}")
    if listing:
        parts.append(f"Selected listing: #{listing.listing_id} — {listing.title}")
    if notes:
        parts.append(f"Notes: {notes}")
    message = "\n".join(parts) if parts else None

    return create_lead(
        listing=listing,
        guest_name=form.get("guest_name"),
        guest_phone=form.get("guest_phone"),
        guest_email=form.get("guest_email"),
        message=message,
        source_path=source_path,
        interest_category=MARKETPLACE_CATEGORY_PRODUCTS,
    )


def products_page_content():
    return funnel_page_content(MARKETPLACE_CATEGORY_PRODUCTS)


def funnel_page_content(category):
    """Copy + CMS settings for Products/Services marketplace funnel pages."""
    from app.site_content_service import get_marketplace_funnel_page

    meta = get_marketplace_category(category) or {}
    label = meta.get("label") or category.replace("_", " ").title()
    cms = get_marketplace_funnel_page(category)
    hero_image_url = cms.get("hero_image_url") or ""

    if category == MARKETPLACE_CATEGORY_SERVICES:
        return {
            "hero_image_url": hero_image_url,
            "hero_title": "TBGP Services Marketplace",
            "hero_lead": (
                "We help members and guests connect with curated service partners "
                "from the TBGP network—browse offerings, tell us what you need, and get a follow-up."
            ),
            "hero_bullets": [
                "Save time finding vetted service partners",
                "Reduce risk with network-backed inquiry follow-up",
                "Get matched based on your project or operational needs",
            ],
            "featured_heading": "Featured services",
            "featured_lead": (
                "Browse published service listings and open one for details or to send an inquiry."
            ),
            "empty_listings": "No published service listings yet. Check back soon.",
            "referral_note": "Inquiries you submit on a service are logged to this member’s marketplace CRM.",
            "subtitle_label": label,
        }

    return {
        "hero_image_url": hero_image_url,
        "hero_title": "TBGP Products Marketplace",
        "hero_lead": (
            "We help members and guests connect with curated product opportunities "
            "from the TBGP network—browse listings, tell us what you need, and get a follow-up."
        ),
        "hero_bullets": [
            "Save time browsing vetted product opportunities",
            "Reduce risk with network-backed inquiry follow-up",
            "Get matched based on what you are looking for",
        ],
        "featured_heading": "Featured products",
        "featured_lead": (
            "Browse published listings and open a product for details or to send an inquiry."
        ),
        "empty_listings": "No published product listings yet. Check back soon.",
        "referral_note": "Inquiries you submit on a product are logged to this member’s marketplace CRM.",
        "subtitle_label": label,
    }


def member_leads(member_id, limit=100):
    return (
        MarketplaceLead.query
        .options(joinedload(MarketplaceLead.listing))
        .filter_by(attributed_member_id=int(member_id))
        .order_by(MarketplaceLead.created_at.desc())
        .limit(limit)
        .all()
    )


def member_lead_count(member_id):
    return MarketplaceLead.query.filter_by(attributed_member_id=int(member_id)).count()


def landing_featured_counts():
    counts = {}
    for slug in MARKETPLACE_CATEGORY_SLUGS:
        counts[slug] = (
            MarketplaceListing.query
            .filter_by(category=slug, status=MARKETPLACE_STATUS_PUBLISHED)
            .count()
        )
    return counts


def _parse_optional_date(value, end_of_day=False):
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        if "T" in raw:
            dt = datetime.fromisoformat(raw)
        else:
            dt = datetime.strptime(raw[:10], "%Y-%m-%d")
        if end_of_day and dt.hour == 0 and dt.minute == 0 and dt.second == 0:
            dt = dt.replace(hour=23, minute=59, second=59)
        return dt
    except ValueError:
        return None


def marketplace_crm_overview():
    """Aggregate KPIs and ranking tables for the Admin marketplace CRM."""
    total_listings = MarketplaceListing.query.count()
    published_listings = MarketplaceListing.query.filter_by(
        status=MARKETPLACE_STATUS_PUBLISHED
    ).count()
    total_leads = MarketplaceLead.query.count()
    attributed_leads = MarketplaceLead.query.filter(
        MarketplaceLead.attributed_member_id.isnot(None)
    ).count()
    unattributed_leads = total_leads - attributed_leads
    listings_with_leads = (
        db.session.query(MarketplaceLead.listing_id)
        .distinct()
        .count()
    )

    by_category = []
    for slug in MARKETPLACE_CATEGORY_SLUGS:
        listing_ids = [
            row.listing_id
            for row in MarketplaceListing.query.filter_by(category=slug).with_entities(
                MarketplaceListing.listing_id
            )
        ]
        lead_filters = [MarketplaceLead.interest_category == slug]
        if listing_ids:
            lead_filters.append(MarketplaceLead.listing_id.in_(listing_ids))
        lead_count = MarketplaceLead.query.filter(or_(*lead_filters)).count()
        by_category.append({
            "category": slug,
            "label": MARKETPLACE_CATEGORIES[slug]["label"],
            "listings": len(listing_ids),
            "published": MarketplaceListing.query.filter_by(
                category=slug, status=MARKETPLACE_STATUS_PUBLISHED
            ).count(),
            "leads": lead_count,
        })

    lead_counts = (
        db.session.query(
            MarketplaceLead.listing_id,
            func.count(MarketplaceLead.lead_id).label("lead_count"),
        )
        .group_by(MarketplaceLead.listing_id)
        .subquery()
    )
    top_listings = (
        db.session.query(
            MarketplaceListing,
            lead_counts.c.lead_count,
        )
        .join(lead_counts, MarketplaceListing.listing_id == lead_counts.c.listing_id)
        .order_by(lead_counts.c.lead_count.desc(), MarketplaceListing.title.asc())
        .limit(10)
        .all()
    )

    referrer_counts = (
        db.session.query(
            MarketplaceLead.attributed_member_id,
            func.count(MarketplaceLead.lead_id).label("lead_count"),
        )
        .filter(MarketplaceLead.attributed_member_id.isnot(None))
        .group_by(MarketplaceLead.attributed_member_id)
        .order_by(func.count(MarketplaceLead.lead_id).desc())
        .limit(10)
        .all()
    )
    top_referrers = []
    for member_id, lead_count in referrer_counts:
        member = db.session.get(Member, member_id)
        top_referrers.append({
            "member_id": member_id,
            "member_name": member.full_name if member else f"Member #{member_id}",
            "lead_count": lead_count,
        })

    recent_leads = (
        MarketplaceLead.query
        .options(
            joinedload(MarketplaceLead.listing),
            joinedload(MarketplaceLead.attributed_member),
        )
        .order_by(MarketplaceLead.created_at.desc())
        .limit(8)
        .all()
    )

    return {
        "total_listings": total_listings,
        "published_listings": published_listings,
        "total_leads": total_leads,
        "attributed_leads": attributed_leads,
        "unattributed_leads": unattributed_leads,
        "listings_with_leads": listings_with_leads,
        "by_category": by_category,
        "top_listings": [
            {
                "listing": listing,
                "lead_count": int(lead_count or 0),
            }
            for listing, lead_count in top_listings
        ],
        "top_referrers": top_referrers,
        "recent_leads": recent_leads,
    }


def listing_crm_stats(listing_id):
    listing = get_listing(listing_id)
    if not listing:
        return None
    leads = (
        MarketplaceLead.query
        .options(joinedload(MarketplaceLead.attributed_member))
        .filter_by(listing_id=int(listing_id))
        .order_by(MarketplaceLead.created_at.desc())
        .all()
    )
    attributed = sum(1 for lead in leads if lead.attributed_member_id)
    referrer_map = {}
    for lead in leads:
        if not lead.attributed_member_id:
            continue
        key = lead.attributed_member_id
        row = referrer_map.setdefault(key, {
            "member_id": key,
            "member_name": lead.attributed_member.full_name if lead.attributed_member else f"Member #{key}",
            "lead_count": 0,
        })
        row["lead_count"] += 1
    top_referrers = sorted(
        referrer_map.values(),
        key=lambda item: (-item["lead_count"], item["member_name"].lower()),
    )
    return {
        "listing": listing,
        "lead_count": len(leads),
        "attributed_leads": attributed,
        "unattributed_leads": len(leads) - attributed,
        "top_referrers": top_referrers,
        "leads": leads,
    }


def search_marketplace_leads(
    q=None,
    category=None,
    listing_id=None,
    referrer_id=None,
    attribution=None,
    date_from=None,
    date_to=None,
    limit=500,
):
    """
    Filter marketplace inquiry CRM rows.

    attribution: 'attributed' | 'unattributed' | None/all
    """
    query = (
        MarketplaceLead.query
        .options(
            joinedload(MarketplaceLead.listing),
            joinedload(MarketplaceLead.attributed_member),
        )
        .outerjoin(MarketplaceListing, MarketplaceLead.listing_id == MarketplaceListing.listing_id)
    )

    if category:
        require_marketplace_category(category)
        query = query.filter(
            or_(
                MarketplaceListing.category == category,
                MarketplaceLead.interest_category == category,
            )
        )

    if listing_id:
        query = query.filter(MarketplaceLead.listing_id == int(listing_id))

    if referrer_id:
        query = query.filter(MarketplaceLead.attributed_member_id == int(referrer_id))

    attribution = (attribution or "").strip().lower()
    if attribution == "attributed":
        query = query.filter(MarketplaceLead.attributed_member_id.isnot(None))
    elif attribution == "unattributed":
        query = query.filter(MarketplaceLead.attributed_member_id.is_(None))

    start = _parse_optional_date(date_from, end_of_day=False)
    end = _parse_optional_date(date_to, end_of_day=True)
    if start:
        query = query.filter(MarketplaceLead.created_at >= start)
    if end:
        query = query.filter(MarketplaceLead.created_at <= end)

    needle = (q or "").strip()
    if needle:
        like = f"%{needle}%"
        clauses = [
            MarketplaceLead.guest_name.ilike(like),
            MarketplaceLead.guest_phone.ilike(like),
            MarketplaceLead.guest_email.ilike(like),
            MarketplaceLead.message.ilike(like),
            MarketplaceListing.title.ilike(like),
            MarketplaceListing.location.ilike(like),
            cast(MarketplaceLead.attributed_member_id, String).ilike(like),
        ]
        member_ids = [
            row.member_id
            for row in Member.query.filter(
                or_(
                    Member.first_name.ilike(like),
                    Member.last_name.ilike(like),
                    Member.middle_name.ilike(like),
                    cast(Member.member_id, String).ilike(like),
                )
            ).with_entities(Member.member_id).all()
        ]
        if member_ids:
            clauses.append(MarketplaceLead.attributed_member_id.in_(member_ids))
        query = query.filter(or_(*clauses))

    return (
        query
        .order_by(MarketplaceLead.created_at.desc(), MarketplaceLead.lead_id.desc())
        .limit(int(limit))
        .all()
    )


def marketplace_listing_options(category=None):
    query = MarketplaceListing.query
    if category:
        require_marketplace_category(category)
        query = query.filter_by(category=category)
    return query.order_by(
        MarketplaceListing.category.asc(),
        MarketplaceListing.title.asc(),
    ).all()
