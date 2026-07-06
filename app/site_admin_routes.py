from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.auth import login_required, site_admin_required
from app.site_content_service import (
    delete_registry_partner,
    get_all_ecosystem_pages,
    get_ecosystem_page,
    get_ecosystem_slugs,
    get_landing_ecosystem_section,
    get_services_contact_cta,
    save_services_contact_cta,
    get_contractors,
    get_suppliers,
    list_registry_partners,
    list_registry_partners_by_type,
    parse_ecosystem_form,
    parse_partner_form,
    save_ecosystem_page,
    save_landing_ecosystem_section,
    save_registry_partner,
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


@site_admin_bp.route("/")
@login_required
@site_admin_required
def home():
    return render_template(
        "site_admin/home.html",
        active_page="home",
        ecosystem_pages=get_all_ecosystem_pages(),
        contractors=get_contractors(),
        suppliers=get_suppliers(),
        landing_section=get_landing_ecosystem_section(),
        contact_cta=get_services_contact_cta(),
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


@site_admin_bp.route("/registry/<partner_type>/new", methods=["GET", "POST"])
@login_required
@site_admin_required
def registry_new(partner_type):
    if partner_type not in REGISTRY_TYPES:
        return redirect(url_for("site_admin.registry_contractors"))

    meta = _registry_meta(partner_type)
    if request.method == "POST":
        partner = parse_partner_form(request.form)
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
        active_page=meta["active_page"],
        registry_type=partner_type,
        registry_meta=meta,
        partner=None,
        is_new=True,
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

        updated = parse_partner_form(request.form, existing=partner)
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
        active_page=meta["active_page"],
        registry_type=partner_type,
        registry_meta=meta,
        partner=partner,
        is_new=False,
    )
