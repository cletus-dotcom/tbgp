"""Load and persist public landing / ecosystem CMS content."""

import copy
import re
from datetime import datetime

from app import db
from app.ecosystem_content import ECOSYSTEM_PAGES, ECOSYSTEM_SLUGS
from app.models import CmsEcosystemPage, CmsLandingSection, CmsRegistryPartner
from app.partners_registry import ALL_PARTNERS, CONTRACTORS, SUPPLIERS

LANDING_ECOSYSTEM_KEY = "ecosystem_pillars"
SERVICES_CONTACT_CTA_KEY = "services_contact_cta"

DEFAULT_LANDING_ECOSYSTEM = {
    "subtitle": "The Cooperative Ecosystem",
    "title": "Products, Services & Partners",
}

DEFAULT_SERVICES_CONTACT_CTA = {
    "title": "LET'S TALK FOR YOUR REQUIRED SERVICES:",
    "phone_display": "0920 202 3891",
    "phone_tel": "+639202023891",
}


def _deepcopy_defaults():
    return copy.deepcopy(ECOSYSTEM_PAGES)


def seed_cms_content():
    """Populate CMS tables from Python defaults when empty."""
    if CmsLandingSection.query.get(LANDING_ECOSYSTEM_KEY) is None:
        db.session.add(
            CmsLandingSection(
                section_key=LANDING_ECOSYSTEM_KEY,
                data=copy.deepcopy(DEFAULT_LANDING_ECOSYSTEM),
            )
        )

    if CmsLandingSection.query.get(SERVICES_CONTACT_CTA_KEY) is None:
        db.session.add(
            CmsLandingSection(
                section_key=SERVICES_CONTACT_CTA_KEY,
                data=copy.deepcopy(DEFAULT_SERVICES_CONTACT_CTA),
            )
        )

    defaults = _deepcopy_defaults()
    for slug in ECOSYSTEM_SLUGS:
        if CmsEcosystemPage.query.get(slug) is None:
            db.session.add(CmsEcosystemPage(slug=slug, data=defaults[slug]))

    if CmsRegistryPartner.query.count() == 0:
        for index, partner in enumerate(CONTRACTORS):
            db.session.add(
                CmsRegistryPartner(
                    slug=partner["slug"],
                    partner_type="contractors",
                    sort_order=index,
                    data=copy.deepcopy(partner),
                )
            )
        for index, partner in enumerate(SUPPLIERS):
            db.session.add(
                CmsRegistryPartner(
                    slug=partner["slug"],
                    partner_type="suppliers",
                    sort_order=index,
                    data=copy.deepcopy(partner),
                )
            )

    db.session.commit()


def get_landing_ecosystem_section():
    row = CmsLandingSection.query.get(LANDING_ECOSYSTEM_KEY)
    if row and row.data:
        return copy.deepcopy(row.data)
    return copy.deepcopy(DEFAULT_LANDING_ECOSYSTEM)


def save_landing_ecosystem_section(data):
    row = CmsLandingSection.query.get(LANDING_ECOSYSTEM_KEY)
    if row is None:
        row = CmsLandingSection(section_key=LANDING_ECOSYSTEM_KEY)
    row.data = data
    row.updated_at = datetime.utcnow()
    db.session.add(row)
    db.session.commit()
    return row.data


def _normalize_phone_tel(phone_display, phone_tel=""):
    explicit = re.sub(r"[^\d+]", "", (phone_tel or "").strip())
    if explicit.startswith("+"):
        return explicit
    digits = re.sub(r"\D", "", phone_display or "")
    if not digits:
        return DEFAULT_SERVICES_CONTACT_CTA["phone_tel"]
    if digits.startswith("63"):
        return f"+{digits}"
    if digits.startswith("0"):
        return f"+63{digits[1:]}"
    return f"+63{digits}"


def get_services_contact_cta():
    row = CmsLandingSection.query.get(SERVICES_CONTACT_CTA_KEY)
    if row and row.data:
        data = copy.deepcopy(row.data)
    else:
        data = copy.deepcopy(DEFAULT_SERVICES_CONTACT_CTA)
    data["phone_tel"] = _normalize_phone_tel(
        data.get("phone_display", ""),
        data.get("phone_tel", ""),
    )
    return data


def save_services_contact_cta(data):
    phone_display = (data.get("phone_display") or "").strip()
    phone_tel = _normalize_phone_tel(phone_display, data.get("phone_tel", ""))
    payload = {
        "title": (data.get("title") or DEFAULT_SERVICES_CONTACT_CTA["title"]).strip(),
        "phone_display": phone_display or DEFAULT_SERVICES_CONTACT_CTA["phone_display"],
        "phone_tel": phone_tel,
    }
    row = CmsLandingSection.query.get(SERVICES_CONTACT_CTA_KEY)
    if row is None:
        row = CmsLandingSection(section_key=SERVICES_CONTACT_CTA_KEY)
    row.data = payload
    row.updated_at = datetime.utcnow()
    db.session.add(row)
    db.session.commit()
    return payload


def get_ecosystem_page(slug):
    row = CmsEcosystemPage.query.get(slug)
    if row and row.data:
        return copy.deepcopy(row.data)
    defaults = _deepcopy_defaults()
    return defaults.get(slug)


def get_all_ecosystem_pages():
    defaults = _deepcopy_defaults()
    result = {}
    for slug in ECOSYSTEM_SLUGS:
        row = CmsEcosystemPage.query.get(slug)
        result[slug] = copy.deepcopy(row.data) if row and row.data else defaults[slug]
    return result


def get_ecosystem_slugs():
    return ECOSYSTEM_SLUGS


def save_ecosystem_page(slug, data):
    if slug not in ECOSYSTEM_SLUGS:
        raise ValueError(f"Unknown ecosystem slug: {slug}")
    row = CmsEcosystemPage.query.get(slug)
    if row is None:
        row = CmsEcosystemPage(slug=slug)
    payload = copy.deepcopy(data)
    payload["slug"] = slug
    row.data = payload
    row.updated_at = datetime.utcnow()
    db.session.add(row)
    db.session.commit()
    return row.data


def _registry_rows(partner_type):
    return (
        CmsRegistryPartner.query.filter_by(partner_type=partner_type)
        .order_by(CmsRegistryPartner.sort_order, CmsRegistryPartner.id)
        .all()
    )


def _default_partners_by_type(partner_type):
    source = CONTRACTORS if partner_type == "contractors" else SUPPLIERS
    return copy.deepcopy(source)


def get_contractors():
    rows = _registry_rows("contractors")
    if rows:
        return [copy.deepcopy(row.data) for row in rows]
    return _default_partners_by_type("contractors")


def get_suppliers():
    rows = _registry_rows("suppliers")
    if rows:
        return [copy.deepcopy(row.data) for row in rows]
    return _default_partners_by_type("suppliers")


def list_registry_partners_by_type(partner_type):
    """Registry entries for site admin, including sort_order metadata."""
    partner_type = partner_type if partner_type in ("contractors", "suppliers") else "contractors"
    rows = _registry_rows(partner_type)
    if rows:
        return [
            {
                "slug": row.slug,
                "partner_type": row.partner_type,
                "sort_order": row.sort_order,
                **copy.deepcopy(row.data),
            }
            for row in rows
        ]
    return [
        {**copy.deepcopy(partner), "partner_type": partner_type, "sort_order": index}
        for index, partner in enumerate(_default_partners_by_type(partner_type))
    ]


def get_partner_by_slug(partner_slug):
    slug = (partner_slug or "").lower().strip()
    row = CmsRegistryPartner.query.filter_by(slug=slug).first()
    if row and row.data:
        return copy.deepcopy(row.data)
    for partner in ALL_PARTNERS:
        if partner["slug"] == slug:
            return copy.deepcopy(partner)
    return None


def parse_portal_contractor_id(partner):
    """Map ecosystem registry contractor entry to portal contractors.contractor_id."""
    if not partner or partner.get("type") != "contractors":
        return None

    explicit = partner.get("portal_contractor_id")
    if explicit is not None and str(explicit).strip() != "":
        try:
            return int(explicit)
        except (TypeError, ValueError):
            pass

    for key in ("slug", "code"):
        value = (partner.get(key) or "").lower()
        match = re.search(r"con-(\d+)$", value)
        if match:
            return int(match.group(1), 10)
    return None


def get_portal_contractor_for_partner(partner):
    from sqlalchemy.orm import joinedload

    from app.models import Contractor

    contractor_id = parse_portal_contractor_id(partner)
    if not contractor_id:
        return None
    return (
        Contractor.query.options(joinedload(Contractor.member_referrer))
        .filter_by(contractor_id=contractor_id)
        .first()
    )


def parse_portal_supplier_id(partner):
    """Map ecosystem registry supplier entry to portal suppliers.supplier_id."""
    if not partner or partner.get("type") != "suppliers":
        return None

    explicit = partner.get("portal_supplier_id")
    if explicit is not None and str(explicit).strip() != "":
        try:
            return int(explicit)
        except (TypeError, ValueError):
            pass

    for key in ("slug", "code"):
        value = (partner.get(key) or "").lower()
        match = re.search(r"sup-(\d+)$", value)
        if match:
            return int(match.group(1), 10)
    return None


def get_portal_supplier_for_partner(partner):
    from sqlalchemy.orm import joinedload

    from app.models import Supplier

    supplier_id = parse_portal_supplier_id(partner)
    if not supplier_id:
        return None
    return (
        Supplier.query.options(joinedload(Supplier.member_referrer))
        .filter_by(supplier_id=supplier_id)
        .first()
    )


def get_portal_record_for_partner(partner):
    partner_type = (partner or {}).get("type")
    if partner_type == "contractors":
        return get_portal_contractor_for_partner(partner)
    if partner_type == "suppliers":
        return get_portal_supplier_for_partner(partner)
    return None


def apply_portal_contractor_profile(partner, portal_contractor=None):
    """For linked contractors, show portal DB company name and address on public profiles."""
    if not partner or partner.get("type") != "contractors":
        return partner

    if portal_contractor is None:
        portal_contractor = get_portal_contractor_for_partner(partner)
    if portal_contractor is None:
        return partner

    profile = copy.deepcopy(partner)
    _sync_partner_identity_from_portal(profile, portal_contractor, location_fallback=True)
    profile["company_name"] = portal_contractor.company_name
    profile["company_address"] = portal_contractor.company_address
    return profile


def apply_portal_supplier_profile(partner, portal_supplier=None):
    """For linked suppliers, show portal DB company name and address on public profiles."""
    if not partner or partner.get("type") != "suppliers":
        return partner

    if portal_supplier is None:
        portal_supplier = get_portal_supplier_for_partner(partner)
    if portal_supplier is None:
        return partner

    profile = copy.deepcopy(partner)
    _sync_partner_identity_from_portal(profile, portal_supplier, location_fallback=True)
    profile["company_name"] = portal_supplier.company_name
    profile["company_address"] = portal_supplier.company_address
    return profile


def apply_portal_partner_profile(partner, portal_record=None):
    if not partner:
        return partner
    if partner.get("type") == "contractors":
        return apply_portal_contractor_profile(partner, portal_record)
    if partner.get("type") == "suppliers":
        return apply_portal_supplier_profile(partner, portal_record)
    return partner


def _sync_contractor_identity_from_portal(partner, contractor=None, *, location_fallback=True):
    return _sync_partner_identity_from_portal(partner, contractor, location_fallback=location_fallback)


def _sync_partner_identity_from_portal(partner, portal_record=None, *, location_fallback=True):
    """Copy portal company name and address into registry partner fields."""
    if not partner or partner.get("type") not in ("contractors", "suppliers"):
        return partner

    if portal_record is None:
        portal_record = get_portal_record_for_partner(partner)
    if portal_record is None:
        return partner

    if portal_record.company_name:
        partner["name"] = portal_record.company_name
    if portal_record.company_address:
        partner["location"] = portal_record.company_address
    elif not location_fallback:
        partner["location"] = ""
    return partner


def list_registry_partners():
    rows = CmsRegistryPartner.query.order_by(
        CmsRegistryPartner.partner_type,
        CmsRegistryPartner.sort_order,
        CmsRegistryPartner.id,
    ).all()
    if rows:
        return [
            {
                "slug": row.slug,
                "partner_type": row.partner_type,
                "sort_order": row.sort_order,
                **copy.deepcopy(row.data),
            }
            for row in rows
        ]
    return copy.deepcopy(ALL_PARTNERS)


def _normalize_slug(value):
    slug = re.sub(r"[^a-z0-9-]+", "-", (value or "").lower()).strip("-")
    return slug or "partner"


def save_registry_partner(slug, data, partner_type, sort_order=None):
    partner_type = partner_type if partner_type in ("contractors", "suppliers") else "contractors"
    slug = _normalize_slug(slug or data.get("slug"))
    row = CmsRegistryPartner.query.filter_by(slug=slug).first()
    if row is None:
        row = CmsRegistryPartner(slug=slug, partner_type=partner_type)
    payload = copy.deepcopy(data)
    payload["slug"] = slug
    payload["type"] = partner_type
    payload["type_label"] = "Contractors" if partner_type == "contractors" else "Suppliers"
    row.data = payload
    row.partner_type = partner_type
    if sort_order is not None:
        row.sort_order = sort_order
    elif row.sort_order is None:
        row.sort_order = CmsRegistryPartner.query.filter_by(partner_type=partner_type).count()
    row.updated_at = datetime.utcnow()
    db.session.add(row)
    db.session.commit()
    return payload


def delete_registry_partner(slug):
    row = CmsRegistryPartner.query.filter_by(slug=slug).first()
    if row is None:
        return False
    db.session.delete(row)
    db.session.commit()
    return True


def parse_ecosystem_form(form, slug, existing=None):
    """Build ecosystem page dict from an HTML form submission."""
    page = copy.deepcopy(existing or get_ecosystem_page(slug) or {})

    text_fields = [
        "meta_title",
        "label",
        "subtitle",
        "title",
        "hero_lead",
        "intro",
        "portal_title",
        "portal_body",
        "portal_cta_label",
        "portal_cta_url",
        "portal_next",
    ]
    for field in text_fields:
        if field in form:
            page[field] = form.get(field, "").strip()

    page["highlights"] = _parse_repeater(form, "highlight", ("icon", "title", "body"))

    landing_card = page.get("landing_card") or {}
    if "landing_card_desc" in form:
        landing_card["desc"] = form.get("landing_card_desc", "").strip()
    landing_card["bullets"] = _parse_repeater(form, "landing_bullet", ("icon", "text"))
    if "landing_card_cta" in form:
        landing_card["cta"] = form.get("landing_card_cta", "").strip()
    page["landing_card"] = landing_card

    if slug == "products":
        social = page.get("social_feed") or {}
        for key in (
            "subtitle",
            "title",
            "description",
            "facebook_url",
            "facebook_caption",
            "youtube_title",
            "youtube_embed_url",
            "youtube_placeholder",
        ):
            form_key = f"social_{key}"
            if form_key in form:
                social[key] = form.get(form_key, "").strip()
        page["social_feed"] = social

    if slug == "partners":
        registry = page.get("registry_section") or {}
        for key in ("subtitle", "title", "description"):
            form_key = f"registry_{key}"
            if form_key in form:
                registry[key] = form.get(form_key, "").strip()
        contractors_head = registry.get("contractors_head") or {}
        suppliers_head = registry.get("suppliers_head") or {}
        if "registry_contractors_title" in form:
            contractors_head["title"] = form.get("registry_contractors_title", "").strip()
        if "registry_contractors_description" in form:
            contractors_head["description"] = form.get("registry_contractors_description", "").strip()
        if "registry_suppliers_title" in form:
            suppliers_head["title"] = form.get("registry_suppliers_title", "").strip()
        if "registry_suppliers_description" in form:
            suppliers_head["description"] = form.get("registry_suppliers_description", "").strip()
        registry["contractors_head"] = contractors_head
        registry["suppliers_head"] = suppliers_head
        page["registry_section"] = registry

    page["slug"] = slug
    return page


def parse_partner_form(form, existing=None, validate=True):
    partner = copy.deepcopy(existing or {})
    for field in (
        "code",
        "name",
        "specialty",
        "location",
        "thumb_url",
        "logo_url",
        "background",
        "capacity",
        "tbgp_relationship",
    ):
        if field in form:
            partner[field] = form.get(field, "").strip()

    partner_type = form.get("partner_type", partner.get("type", "contractors"))
    partner["type"] = partner_type
    partner["type_label"] = "Contractors" if partner_type == "contractors" else "Suppliers"
    partner["gallery"] = _parse_repeater(form, "gallery", ("url", "alt"))
    slug = form.get("slug", partner.get("slug", "")).strip()
    partner["slug"] = _normalize_slug(slug or partner.get("code", ""))

    if validate:
        error = _apply_portal_partner_id(partner, form)
        if error:
            raise ValueError(error)
    else:
        _apply_portal_partner_id_draft(partner, form)
    _sync_partner_identity_from_portal(partner, location_fallback=False)
    return partner


def _apply_portal_partner_id_draft(partner, form):
    if partner.get("type") == "contractors":
        _apply_portal_contractor_id_draft(partner, form)
        partner.pop("portal_supplier_id", None)
        return
    if partner.get("type") == "suppliers":
        _apply_portal_supplier_id_draft(partner, form)
        partner.pop("portal_contractor_id", None)
        return
    partner.pop("portal_contractor_id", None)
    partner.pop("portal_supplier_id", None)


def _apply_portal_supplier_id_draft(partner, form):
    if partner.get("type") != "suppliers":
        partner.pop("portal_supplier_id", None)
        return
    raw = (form.get("portal_supplier_id") or "").strip()
    if not raw:
        partner.pop("portal_supplier_id", None)
        return
    try:
        partner["portal_supplier_id"] = int(raw)
    except ValueError:
        partner["portal_supplier_id"] = raw


def partner_portal_link(partner):
    if not partner:
        return {
            "portal_contractor": None,
            "portal_supplier": None,
            "portal_record": None,
            "member_referrer": None,
        }
    if partner.get("type") == "suppliers":
        portal_supplier = get_portal_supplier_for_partner(partner)
        return {
            "portal_contractor": None,
            "portal_supplier": portal_supplier,
            "portal_record": portal_supplier,
            "member_referrer": portal_supplier.member_referrer if portal_supplier else None,
        }
    portal_contractor = get_portal_contractor_for_partner(partner)
    return {
        "portal_contractor": portal_contractor,
        "portal_supplier": None,
        "portal_record": portal_contractor,
        "member_referrer": portal_contractor.member_referrer if portal_contractor else None,
    }


def _apply_portal_partner_id(partner, form):
    if partner.get("type") == "contractors":
        partner.pop("portal_supplier_id", None)
        return _apply_portal_contractor_id(partner, form)
    if partner.get("type") == "suppliers":
        partner.pop("portal_contractor_id", None)
        return _apply_portal_supplier_id(partner, form)
    partner.pop("portal_contractor_id", None)
    partner.pop("portal_supplier_id", None)
    return None


def _apply_portal_supplier_id(partner, form):
    from app.models import Supplier

    if partner.get("type") != "suppliers":
        partner.pop("portal_supplier_id", None)
        return None

    raw = (form.get("portal_supplier_id") or "").strip()
    if not raw:
        partner.pop("portal_supplier_id", None)
        return None

    try:
        supplier_id = int(raw)
    except ValueError:
        return "Portal supplier ID must be a whole number."

    if supplier_id <= 0:
        return "Portal supplier ID must be greater than zero."

    supplier = Supplier.query.get(supplier_id)
    if supplier is None:
        return f"Portal supplier #{supplier_id} was not found in the database."

    partner["portal_supplier_id"] = supplier_id
    _sync_partner_identity_from_portal(partner, supplier, location_fallback=False)
    return None
    from app.models import Contractor

    if partner.get("type") != "contractors":
        partner.pop("portal_contractor_id", None)
        return None

    raw = (form.get("portal_contractor_id") or "").strip()
    if not raw:
        partner.pop("portal_contractor_id", None)
        return None

    try:
        contractor_id = int(raw)
    except ValueError:
        return "Portal contractor ID must be a whole number."

    if contractor_id <= 0:
        return "Portal contractor ID must be greater than zero."

    contractor = Contractor.query.get(contractor_id)
    if contractor is None:
        return f"Portal contractor #{contractor_id} was not found in the database."

    partner["portal_contractor_id"] = contractor_id
    _sync_partner_identity_from_portal(partner, contractor, location_fallback=False)
    return None


def _apply_portal_contractor_id_draft(partner, form):
    if partner.get("type") != "contractors":
        partner.pop("portal_contractor_id", None)
        return
    raw = (form.get("portal_contractor_id") or "").strip()
    if not raw:
        partner.pop("portal_contractor_id", None)
        return
    try:
        partner["portal_contractor_id"] = int(raw)
    except ValueError:
        partner["portal_contractor_id"] = raw


def _apply_portal_contractor_id(partner, form):
    from app.models import Contractor

    if partner.get("type") != "contractors":
        partner.pop("portal_contractor_id", None)
        return None

    raw = (form.get("portal_contractor_id") or "").strip()
    if not raw:
        partner.pop("portal_contractor_id", None)
        return None

    try:
        contractor_id = int(raw)
    except ValueError:
        return "Portal contractor ID must be a whole number."

    if contractor_id <= 0:
        return "Portal contractor ID must be greater than zero."

    contractor = Contractor.query.get(contractor_id)
    if contractor is None:
        return f"Portal contractor #{contractor_id} was not found in the database."

    partner["portal_contractor_id"] = contractor_id
    _sync_partner_identity_from_portal(partner, contractor, location_fallback=False)
    return None


def _parse_repeater(form, prefix, fields):
    items = []
    index = 0
    while True:
        keys = [f"{prefix}_{field}_{index}" for field in fields]
        if not any(key in form for key in keys):
            break
        item = {field: form.get(f"{prefix}_{field}_{index}", "").strip() for field in fields}
        if any(item.values()):
            items.append(item)
        index += 1
    return items
