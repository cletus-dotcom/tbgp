from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from app.auth import login_required, site_admin_required
from app.config import (
    MARKETPLACE_CATEGORIES,
    MARKETPLACE_CATEGORY_SLUGS,
    MARKETPLACE_FUNNEL_CATEGORY_SLUGS,
    is_portal_admin_role,
    is_site_admin_role,
    normalize_role,
    supabase_storage_config_error,
    supabase_storage_configured,
)
from app.marketplace_service import (
    delete_listing,
    get_listing,
    list_all_for_admin,
    parse_listing_form,
    save_listing,
)
from app.site_content_service import (
    delete_registry_partner,
    get_all_ecosystem_pages,
    get_ecosystem_page,
    get_ecosystem_slugs,
    get_landing_ecosystem_section,
    get_marketplace_products_page,
    get_marketplace_services_page,
    get_marketplace_summaries,
    get_services_contact_cta,
    save_services_contact_cta,
    get_contractors,
    get_suppliers,
    list_registry_partners,
    list_registry_partners_by_type,
    parse_ecosystem_form,
    parse_partner_form,
    partner_portal_link,
    apply_portal_partner_profile,
    save_ecosystem_page,
    save_landing_ecosystem_section,
    save_marketplace_products_page,
    save_marketplace_services_page,
    save_marketplace_summaries,
    save_registry_partner,
)
from app.user_manual_content import resolve_user_manual
from app.supabase_storage_service import (
    upload_marketplace_image as store_marketplace_image,
    upload_partner_image as store_partner_image,
)
site_admin_bp = Blueprint("site_admin", __name__, url_prefix="/site-admin")

REGISTRY_TYPES = {
    "contractors": {
        "title": "Contractor Registry",
        "label": "Contractors",
        "icon": "bi-building",
        "description": "Tier-1 developers, civil works firms, and heavy engineering partners.",
        "active_page": "registry_contractors",
        "code_hint": "TBGP-CON-005",
        "slug_hint": "tbgp-con-005",
    },
    "suppliers": {
        "title": "Supplier Registry",
        "label": "Suppliers",
        "icon": "bi-box-seam",
        "description": "Aggregate, steel, cement, and heavy equipment supply partners.",
        "active_page": "registry_suppliers",
        "code_hint": "TBGP-SUP-005",
        "slug_hint": "tbgp-sup-005",
    },
}


def _registry_meta(partner_type):
    return REGISTRY_TYPES.get(partner_type, REGISTRY_TYPES["contractors"])


def _registry_list_url(partner_type):
    if partner_type == "suppliers":
        return url_for("site_admin.registry_suppliers")
    return url_for("site_admin.registry_contractors")


def _partner_edit_context(partner, registry_type, meta, is_new):
    link = partner_portal_link(partner) if partner else {
        "portal_contractor": None,
        "portal_supplier": None,
        "portal_record": None,
        "member_referrer": None,
    }
    if partner:
        partner = apply_portal_partner_profile(partner, link["portal_record"])
    return {
        "active_page": meta["active_page"],
        "registry_type": registry_type,
        "registry_meta": meta,
        "partner": partner,
        "portal_contractor": link["portal_contractor"],
        "portal_supplier": link["portal_supplier"],
        "member_referrer": link["member_referrer"],
        "portal_profile_synced": link["portal_record"] is not None,
        "is_new": is_new,
        "partner_image_upload_enabled": supabase_storage_configured(),
        "partner_image_upload_url": url_for("site_admin.upload_partner_image"),
    }


@site_admin_bp.route("/")
@login_required
@site_admin_required
def home():
    listings = list_all_for_admin()
    published_count = sum(1 for row in listings if row.status == "published")
    return render_template(
        "site_admin/home.html",
        active_page="home",
        ecosystem_pages=get_all_ecosystem_pages(),
        contractors=get_contractors(),
        suppliers=get_suppliers(),
        landing_section=get_landing_ecosystem_section(),
        contact_cta=get_services_contact_cta(),
        marketplace_count=len(listings),
        marketplace_published=published_count,
    )


@site_admin_bp.route("/user-manual")
@login_required
@site_admin_required
def user_manual():
    role = normalize_role(session.get("role"))
    if not is_site_admin_role(role) and not is_portal_admin_role(role):
        flash("You do not have access to the user manual here.", "warning")
        return redirect(url_for("site_admin.home"))
    manual, manual_role, manual_choices = resolve_user_manual(
        role,
        request.args.get("manual"),
    )
    return render_template(
        "site_admin/user_manual.html",
        active_page="user_manual",
        role=role,
        manual_role=manual_role,
        manual_choices=manual_choices,
        manual_url_endpoint="site_admin.user_manual",
        manual=manual,
    )


@site_admin_bp.route("/landing", methods=["GET", "POST"])
@login_required
@site_admin_required
def edit_landing():
    section = get_landing_ecosystem_section()
    if request.method == "POST":
        section = {
            "subtitle": request.form.get("subtitle", "").strip(),
            "title": request.form.get("title", "").strip(),
        }
        save_landing_ecosystem_section(section)
        flash("Landing ecosystem section updated.", "success")
        return redirect(url_for("site_admin.home"))

    return render_template(
        "site_admin/landing.html",
        active_page="landing",
        section=section,
    )


@site_admin_bp.route("/contact-cta", methods=["GET", "POST"])
@login_required
@site_admin_required
def edit_contact_cta():
    contact_cta = get_services_contact_cta()
    if request.method == "POST":
        contact_cta = save_services_contact_cta({
            "title": request.form.get("title", ""),
            "phone_display": request.form.get("phone_display", ""),
            "phone_tel": request.form.get("phone_tel", ""),
        })
        flash("Services contact card updated.", "success")
        return redirect(url_for("site_admin.edit_contact_cta"))

    return render_template(
        "site_admin/contact_cta.html",
        active_page="contact_cta",
        contact_cta=contact_cta,
    )


@site_admin_bp.route("/ecosystem/<slug>", methods=["GET", "POST"])
@login_required
@site_admin_required
def edit_ecosystem(slug):
    if slug not in get_ecosystem_slugs():
        return redirect(url_for("site_admin.home"))

    page = get_ecosystem_page(slug)
    if request.method == "POST":
        page = parse_ecosystem_form(request.form, slug, existing=page)
        save_ecosystem_page(slug, page)
        flash(f"{page.get('label', slug.title())} page updated.", "success")
        return redirect(url_for("site_admin.edit_ecosystem", slug=slug))

    return render_template(
        "site_admin/ecosystem_edit.html",
        active_page=f"ecosystem_{slug}",
        page=page,
        slug=slug,
    )


@site_admin_bp.route("/registry")
@login_required
@site_admin_required
def registry_list():
    return redirect(url_for("site_admin.registry_contractors"))


@site_admin_bp.route("/registry/contractors")
@login_required
@site_admin_required
def registry_contractors():
    meta = _registry_meta("contractors")
    return render_template(
        "site_admin/registry.html",
        active_page=meta["active_page"],
        registry_type="contractors",
        registry_meta=meta,
        partners=list_registry_partners_by_type("contractors"),
    )


@site_admin_bp.route("/registry/suppliers")
@login_required
@site_admin_required
def registry_suppliers():
    meta = _registry_meta("suppliers")
    return render_template(
        "site_admin/registry.html",
        active_page=meta["active_page"],
        registry_type="suppliers",
        registry_meta=meta,
        partners=list_registry_partners_by_type("suppliers"),
    )


@site_admin_bp.route("/registry/partner-image", methods=["POST"])
@login_required
@site_admin_required
def upload_partner_image():
    if not supabase_storage_configured():
        return jsonify({
            "error": supabase_storage_config_error()
            or "Supabase Storage is not configured on this server."
        }), 503

    file = request.files.get("file")
    kind = request.form.get("kind", "gallery")
    slug = request.form.get("slug", "draft")
    try:
        result = store_partner_image(file, slug, kind)
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc) or "Image upload failed. Try again or paste an image URL."}), 500


@site_admin_bp.route("/registry/<partner_type>/new", methods=["GET", "POST"])
@login_required
@site_admin_required
def registry_new(partner_type):
    if partner_type not in REGISTRY_TYPES:
        return redirect(url_for("site_admin.registry_contractors"))

    meta = _registry_meta(partner_type)
    if request.method == "POST":
        try:
            partner = parse_partner_form(request.form)
        except ValueError as exc:
            flash(str(exc), "danger")
            partner = parse_partner_form(request.form, validate=False)
            partner["sort_order"] = request.form.get("sort_order", type=int) or 0
            return render_template(
                "site_admin/partner_edit.html",
                **_partner_edit_context(partner, partner_type, meta, is_new=True),
            )

        sort_order = request.form.get("sort_order", type=int)
        save_registry_partner(
            partner["slug"],
            partner,
            partner_type,
            sort_order=sort_order,
        )
        flash(f"{meta['label']} registry entry created.", "success")
        return redirect(_registry_list_url(partner_type))

    return render_template(
        "site_admin/partner_edit.html",
        **_partner_edit_context(None, partner_type, meta, is_new=True),
    )


@site_admin_bp.route("/registry/<slug>/edit", methods=["GET", "POST"])
@login_required
@site_admin_required
def registry_edit(slug):
    from app.models import CmsRegistryPartner
    from app.site_content_service import get_partner_by_slug

    partner = get_partner_by_slug(slug)
    if partner is None:
        flash("Partner not found.", "warning")
        return redirect(url_for("site_admin.registry_contractors"))

    row = CmsRegistryPartner.query.filter_by(slug=slug).first()
    partner_type = row.partner_type if row else partner.get("type", "contractors")
    partner["sort_order"] = row.sort_order if row else 0
    meta = _registry_meta(partner_type)
    list_url = _registry_list_url(partner_type)

    if request.method == "POST":
        if request.form.get("_action") == "delete":
            delete_registry_partner(partner["slug"])
            flash(f"{meta['label']} registry entry removed.", "success")
            return redirect(list_url)

        try:
            updated = parse_partner_form(request.form, existing=partner)
        except ValueError as exc:
            flash(str(exc), "danger")
            draft = parse_partner_form(request.form, existing=partner, validate=False)
            draft["sort_order"] = request.form.get("sort_order", type=int)
            if draft["sort_order"] is None:
                draft["sort_order"] = partner.get("sort_order", 0)
            return render_template(
                "site_admin/partner_edit.html",
                **_partner_edit_context(draft, partner_type, meta, is_new=False),
            )

        sort_order = request.form.get("sort_order", type=int)
        new_type = updated.get("type", partner_type)
        if updated["slug"] != partner["slug"]:
            delete_registry_partner(partner["slug"])
        save_registry_partner(
            updated["slug"],
            updated,
            new_type,
            sort_order=sort_order if sort_order is not None else None,
        )
        flash(f"{meta['label']} registry entry updated.", "success")
        return redirect(url_for("site_admin.registry_edit", slug=updated["slug"]))

    return render_template(
        "site_admin/partner_edit.html",
        **_partner_edit_context(partner, partner_type, meta, is_new=False),
    )


def _listing_edit_context(listing, is_new=False):
    image_key = f"listing-{listing.listing_id}" if listing and getattr(listing, "listing_id", None) else "draft"
    return {
        "active_page": "marketplace",
        "listing": listing,
        "is_new": is_new,
        "categories": MARKETPLACE_CATEGORIES,
        "category_slugs": MARKETPLACE_CATEGORY_SLUGS,
        "partner_image_upload_enabled": supabase_storage_configured(),
        "partner_image_upload_url": url_for("site_admin.upload_marketplace_image"),
        "image_key": image_key,
    }


@site_admin_bp.route("/marketplace")
@login_required
@site_admin_required
def marketplace_list():
    category = (request.args.get("category") or "").strip() or None
    if category and category not in MARKETPLACE_CATEGORIES:
        category = None
    listings = list_all_for_admin(category)
    return render_template(
        "site_admin/marketplace_list.html",
        active_page="marketplace",
        listings=listings,
        categories=MARKETPLACE_CATEGORIES,
        category_slugs=MARKETPLACE_CATEGORY_SLUGS,
        filter_category=category,
        marketplace_summaries=get_marketplace_summaries(),
        products_page=get_marketplace_products_page(),
        services_page=get_marketplace_services_page(),
        funnel_category_slugs=MARKETPLACE_FUNNEL_CATEGORY_SLUGS,
        partner_image_upload_enabled=supabase_storage_configured(),
        partner_image_upload_url=url_for("site_admin.upload_marketplace_image"),
        supabase_storage_config_error=supabase_storage_config_error(),
    )


@site_admin_bp.route("/marketplace/summaries", methods=["POST"])
@login_required
@site_admin_required
def marketplace_summaries_save():
    try:
        save_marketplace_summaries(request.form)
        flash("Marketplace executive summaries saved.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("site_admin.marketplace_list") + "#executive-summaries")


@site_admin_bp.route("/marketplace/products-page", methods=["POST"])
@login_required
@site_admin_required
def marketplace_products_page_save():
    try:
        save_marketplace_products_page(request.form)
        flash("Products marketplace page settings saved.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("site_admin.marketplace_list") + "#products-page")


@site_admin_bp.route("/marketplace/services-page", methods=["POST"])
@login_required
@site_admin_required
def marketplace_services_page_save():
    try:
        save_marketplace_services_page(request.form)
        flash("Services marketplace page settings saved.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("site_admin.marketplace_list") + "#services-page")


@site_admin_bp.route("/marketplace/new", methods=["GET", "POST"])
@login_required
@site_admin_required
def marketplace_new():
    if request.method == "POST":
        try:
            data = parse_listing_form(request.form)
            listing = save_listing(data, created_by_user_id=session.get("user_id"))
            flash("Marketplace listing created.", "success")
            return redirect(url_for("site_admin.marketplace_edit", listing_id=listing.listing_id))
        except ValueError as exc:
            flash(str(exc), "danger")
            draft = {
                "category": request.form.get("category") or "products",
                "title": request.form.get("title") or "",
                "summary": request.form.get("summary") or "",
                "body": request.form.get("body") or "",
                "price_label": request.form.get("price_label") or "",
                "location": request.form.get("location") or "",
                "status": request.form.get("status") or "draft",
                "thumbnail_url": request.form.get("thumbnail_url") or "",
                "gallery": [],
                "contact_name": request.form.get("contact_name") or "",
                "contact_phone": request.form.get("contact_phone") or "",
                "contact_email": request.form.get("contact_email") or "",
                "sort_order": request.form.get("sort_order") or 0,
            }
            return render_template(
                "site_admin/marketplace_edit.html",
                **_listing_edit_context(draft, is_new=True),
            )

    default_category = request.args.get("category") or "products"
    if default_category not in MARKETPLACE_CATEGORIES:
        default_category = "products"
    blank = {
        "category": default_category,
        "title": "",
        "summary": "",
        "body": "",
        "price_label": "",
        "location": "",
        "status": "draft",
        "thumbnail_url": "",
        "gallery": [],
        "contact_name": "",
        "contact_phone": "",
        "contact_email": "",
        "sort_order": 0,
    }
    return render_template(
        "site_admin/marketplace_edit.html",
        **_listing_edit_context(blank, is_new=True),
    )


@site_admin_bp.route("/marketplace/<int:listing_id>/edit", methods=["GET", "POST"])
@login_required
@site_admin_required
def marketplace_edit(listing_id):
    listing = get_listing(listing_id)
    if not listing:
        flash("Listing not found.", "danger")
        return redirect(url_for("site_admin.marketplace_list"))

    if request.method == "POST":
        if request.form.get("_action") == "delete":
            delete_listing(listing_id)
            flash("Listing deleted.", "success")
            return redirect(url_for("site_admin.marketplace_list"))
        try:
            data = parse_listing_form(request.form, existing=listing)
            save_listing(data, listing=listing)
            flash("Marketplace listing updated.", "success")
            return redirect(url_for("site_admin.marketplace_edit", listing_id=listing_id))
        except ValueError as exc:
            flash(str(exc), "danger")

    return render_template(
        "site_admin/marketplace_edit.html",
        **_listing_edit_context(listing, is_new=False),
    )


@site_admin_bp.route("/marketplace/image", methods=["POST"])
@login_required
@site_admin_required
def upload_marketplace_image():
    if not supabase_storage_configured():
        return jsonify({
            "error": supabase_storage_config_error()
            or "Supabase Storage is not configured on this server."
        }), 503

    file = request.files.get("file")
    kind = (request.form.get("kind") or "gallery").strip().lower()
    if kind not in {"thumb", "gallery", "hero"}:
        kind = "gallery"
    slug = request.form.get("slug", "draft")
    try:
        result = store_marketplace_image(file, slug, kind)
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc) or "Image upload failed. Try again or paste an image URL."}), 500


@site_admin_bp.errorhandler(413)
def marketplace_upload_too_large(_exc):
    return jsonify({"error": "Image is too large (max 5 MB)."}), 413