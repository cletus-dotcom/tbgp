import os
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DB_CONFIG = {
    "db_user": os.getenv("DB_USER", "postgres"),
    "db_pass": os.getenv("DB_PASS", "password"),
    "db_ip": os.getenv("DB_IP", "127.0.0.1"),
    "db_port": os.getenv("DB_PORT", "5432"),
    "db_name": os.getenv("DB_NAME", "tbgp"),
}


def _normalize_database_url(url):
    if not url:
        return None
    value = url.strip()
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg2://", 1)
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg2://", 1)
    return value


DATABASE_URL = _normalize_database_url(os.getenv("DATABASE_URL"))


def _normalize_supabase_api_url(url):
    """Accept only the HTTPS project API URL used by Storage (not DATABASE_URL)."""
    value = (url or "").strip().rstrip("/")
    if not value:
        return ""
    lower = value.lower()
    if lower.startswith("postgres://") or lower.startswith("postgresql://"):
        return ""
    if not lower.startswith("https://"):
        return ""
    return value


SUPABASE_URL = _normalize_supabase_api_url(os.getenv("SUPABASE_URL"))
SUPABASE_SERVICE_ROLE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_SECRET_KEY")
    or ""
).strip()
SUPABASE_PARTNER_IMAGES_BUCKET = (
    os.getenv("SUPABASE_PARTNER_IMAGES_BUCKET") or "partner-images"
).strip() or "partner-images"

MEMBER_WHATSAPP_MEMBERSHIP = os.getenv("MEMBER_WHATSAPP_MEMBERSHIP", "")
MEMBER_WHATSAPP_OTHER_MATTERS = os.getenv("MEMBER_WHATSAPP_OTHER_MATTERS", "")


def supabase_storage_configured():
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def supabase_storage_config_error():
    """Human-readable reason Storage uploads are unavailable."""
    raw_url = (os.getenv("SUPABASE_URL") or "").strip()
    if not raw_url:
        return "Set SUPABASE_URL to https://YOUR_PROJECT_REF.supabase.co"
    if raw_url.lower().startswith(("postgres://", "postgresql://")):
        return (
            "SUPABASE_URL is a database connection string. "
            "Use the HTTPS API URL instead (https://YOUR_PROJECT_REF.supabase.co)."
        )
    if not SUPABASE_URL:
        return "SUPABASE_URL must be an https://…supabase.co project URL."
    if not SUPABASE_SERVICE_ROLE_KEY:
        return "Set SUPABASE_SERVICE_ROLE_KEY (service_role secret from Supabase API settings)."
    return None


def database_uri():
    if DATABASE_URL:
        return DATABASE_URL
    return (
        f"postgresql+psycopg2://{DB_CONFIG['db_user']}:{DB_CONFIG['db_pass']}@"
        f"{DB_CONFIG['db_ip']}:{DB_CONFIG['db_port']}/{DB_CONFIG['db_name']}"
    )


SECRET_KEY = os.getenv("SECRET_KEY", "tbgp_referral_secret_key")

# Industrial Premium theme — slate/charcoal + construction amber
THEME_CHARCOAL = "#0d0f12"
THEME_SLATE_DEEP = "#14171c"
THEME_SLATE_DARK = "#1c2028"
THEME_SLATE_MID = "#2a303a"
THEME_SLATE_LIGHT = "#3a424f"
THEME_AMBER = "#f0a500"
THEME_AMBER_BRIGHT = "#ffc233"
THEME_AMBER_DIM = "#c48400"
THEME_CARD_SURFACE = "#222830"

THEME_BLACK = THEME_CHARCOAL
THEME_DARK = "#000000"
THEME_GRAY = "#9aa3b0"
THEME_GRAY_LIGHT = THEME_SLATE_LIGHT
THEME_WHITE = "#ffffff"
THEME_BG = THEME_SLATE_DEEP
THEME_BG_ALT = THEME_SLATE_MID

# Primary action color (amber accents)
BRAND_BLUE = THEME_AMBER
BRAND_BLUE_DARK = THEME_AMBER_DIM
BRAND_BLUE_LIGHT = THEME_AMBER_BRIGHT

MEMBERS_XLSX = os.getenv(
    "MEMBERS_XLSX",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "members.xlsx"),
)

MEMBERS_SHEET = "members"
CONTRACTORS_SHEET = "contractors"
SUPPLIERS_SHEET = "suppliers"

MEMBER_STATUSES = ["Active", "Inactive", "Separated"]
MEMBER_SEPARATION_TYPES = [
    "Resigned",
    "End of Contract",
    "Retired",
    "Terminated",
    "Deceased",
]

MEMBER_SELF_EDITABLE_FIELDS = (
    "gender",
    "civil_status",
    "phone",
    "email",
    "address",
    "highest_education",
    "occupation_income_source",
    "monthly_income",
    "number_of_dependents",
    "beneficiary_name",
    "beneficiary_phone",
    "beneficiary_address",
)

MAX_SHARING_LEVELS = 7
CLIENT_POOL_PERCENT = int(os.getenv("CLIENT_POOL_PERCENT", "50"))
CONTRACTOR_POOL_PERCENT = int(os.getenv("CONTRACTOR_POOL_PERCENT", "25"))
ADMIN_ACCOUNT_PERCENT = int(os.getenv("ADMIN_ACCOUNT_PERCENT", "25"))
ADMIN_MEMBER_ID = os.getenv("ADMIN_MEMBER_ID")
ADMIN_RECIPIENT_LABEL = "PLATFORM Account"
MANDATE_RECIPIENT_LABEL = "Mandate Account"
POP_RECIPIENT_LABEL = "Poorest of the Poor (POP)"
AD_FUND_RECIPIENT_LABEL = "AD-Fund"
POP_CAP_FLUSH_LABEL = f"{POP_RECIPIENT_LABEL} (Earnings cap flush)"
POP_LIFETIME_LIMIT_FUND_LABEL = f"{POP_RECIPIENT_LABEL} Lifetime Limit Fund"
ADMIN_SHARING_LEVEL = -1

# Products Commission top-level split (must total 100%).
PRODUCT_REF_SELLER_PERCENT = Decimal("8")
PRODUCT_REF_BUYER_PERCENT = Decimal("12")
PRODUCT_POP_PERCENT = Decimal("10")
PRODUCT_AD_FUND_PERCENT = Decimal("5")
PRODUCT_PLATFORM_PERCENT = Decimal("65")

PRODUCT_BONUS_TYPE_AUTO = "auto"
PRODUCT_BONUS_TYPE_AD = "ad"
PRODUCT_BONUS_TYPES = (PRODUCT_BONUS_TYPE_AUTO, PRODUCT_BONUS_TYPE_AD)
PRODUCT_BONUS_AUTO_PERCENT = Decimal("10")  # Auto-Bonus: 10% of commission from PLATFORM
PRODUCT_BONUS_AD_DEFAULT_PERCENT = Decimal(
    os.getenv("PRODUCT_BONUS_AD_DEFAULT_PERCENT", "5")
)

COMMISSION_SCHEME_PRODUCT_REF_SELLER = "product_ref_seller"
COMMISSION_SCHEME_PRODUCT_REF_BUYER = "product_ref_buyer"
COMMISSION_SCHEME_PRODUCT_BUYER_BONUS = "product_buyer_bonus"
COMMISSION_SCHEME_PRODUCT_POP = "product_pop"
COMMISSION_SCHEME_PRODUCT_AD_FUND = "product_ad_fund"
COMMISSION_SCHEME_PRODUCT_PLATFORM = "product_platform"
COMMISSION_SCHEME_PRODUCT_AD_SPLIT = "product_ad_split"

PRODUCT_AD_CHARGE_PLATFORM = "platform"
PRODUCT_AD_CHARGE_AD_FUND = "ad_fund"
PRODUCT_AD_CHARGE_SOURCES = (PRODUCT_AD_CHARGE_PLATFORM, PRODUCT_AD_CHARGE_AD_FUND)

MARKETPLACE_CATEGORY_PRODUCTS = "products"
MARKETPLACE_CATEGORY_SERVICES = "services"
MARKETPLACE_CATEGORY_REAL_PROPERTY = "real_property"
# Landing carousel / tabs / CRM filters follow this order.
MARKETPLACE_CATEGORIES = {
    MARKETPLACE_CATEGORY_PRODUCTS: {
        "slug": MARKETPLACE_CATEGORY_PRODUCTS,
        "label": "Products",
        "short_label": "Products",
        "icon": "bi-box-seam",
        "tagline": "Curated products from the TBGP network—inquire and get matched with the right offer.",
        "funnel": True,
    },
    MARKETPLACE_CATEGORY_SERVICES: {
        "slug": MARKETPLACE_CATEGORY_SERVICES,
        "label": "Services",
        "short_label": "Services",
        "icon": "bi-tools",
        "tagline": "Project, logistics, and professional services from the TBGP network—inquire and get matched.",
        "funnel": True,
    },
    MARKETPLACE_CATEGORY_REAL_PROPERTY: {
        "slug": MARKETPLACE_CATEGORY_REAL_PROPERTY,
        "label": "Real Property",
        "short_label": "Property",
        "icon": "bi-house-door",
        "tagline": "Lots: FOR SALE, LEASE OR JOINT VENTURE.",
        "funnel": False,
    },
}
MARKETPLACE_CATEGORY_SLUGS = tuple(MARKETPLACE_CATEGORIES.keys())
MARKETPLACE_FUNNEL_CATEGORY_SLUGS = tuple(
    slug for slug, meta in MARKETPLACE_CATEGORIES.items() if meta.get("funnel")
)
MARKETPLACE_STATUS_DRAFT = "draft"
MARKETPLACE_STATUS_PUBLISHED = "published"
MARKETPLACE_STATUSES = (MARKETPLACE_STATUS_DRAFT, MARKETPLACE_STATUS_PUBLISHED)
MARKETPLACE_ATTRIBUTION_COOKIE = "tbgp_mp_ref"
MARKETPLACE_ATTRIBUTION_DAYS = 30

# Marketplace inquiry / transaction monitoring statuses (TBGP color-coded monitoring sheet).
MARKETPLACE_LEAD_STATUS_NEW = "new"
MARKETPLACE_LEAD_STATUS_FOR_RESEARCH = "for_research"
MARKETPLACE_LEAD_STATUS_FOR_QUOTATION = "for_quotation"
MARKETPLACE_LEAD_STATUS_QUOTATION_IN_PROCESS = "quotation_in_process"
MARKETPLACE_LEAD_STATUS_QUOTATION_SUBMITTED = "quotation_submitted"
MARKETPLACE_LEAD_STATUS_FOR_FOLLOW_UP = "for_follow_up"
MARKETPLACE_LEAD_STATUS_FOR_CONTRACTOR = "for_contractor"
MARKETPLACE_LEAD_STATUS_ON_HOLD = "on_hold"
MARKETPLACE_LEAD_STATUS_COMPLETED = "completed"
MARKETPLACE_LEAD_STATUS_TERMINATED = "terminated"
MARKETPLACE_LEAD_STATUSES = (
    MARKETPLACE_LEAD_STATUS_NEW,
    MARKETPLACE_LEAD_STATUS_FOR_RESEARCH,
    MARKETPLACE_LEAD_STATUS_FOR_QUOTATION,
    MARKETPLACE_LEAD_STATUS_QUOTATION_IN_PROCESS,
    MARKETPLACE_LEAD_STATUS_QUOTATION_SUBMITTED,
    MARKETPLACE_LEAD_STATUS_FOR_FOLLOW_UP,
    MARKETPLACE_LEAD_STATUS_FOR_CONTRACTOR,
    MARKETPLACE_LEAD_STATUS_ON_HOLD,
    MARKETPLACE_LEAD_STATUS_COMPLETED,
    MARKETPLACE_LEAD_STATUS_TERMINATED,
)
MARKETPLACE_LEAD_STATUS_LABELS = {
    MARKETPLACE_LEAD_STATUS_NEW: "New inquiry",
    MARKETPLACE_LEAD_STATUS_FOR_RESEARCH: "For research",
    MARKETPLACE_LEAD_STATUS_FOR_QUOTATION: "For costing / quotation",
    MARKETPLACE_LEAD_STATUS_QUOTATION_IN_PROCESS: "Quotation in process",
    MARKETPLACE_LEAD_STATUS_QUOTATION_SUBMITTED: "Quotation submitted",
    MARKETPLACE_LEAD_STATUS_FOR_FOLLOW_UP: "For follow-up",
    MARKETPLACE_LEAD_STATUS_FOR_CONTRACTOR: "For assignment of contractor",
    MARKETPLACE_LEAD_STATUS_ON_HOLD: "On hold",
    MARKETPLACE_LEAD_STATUS_COMPLETED: "Completed",
    MARKETPLACE_LEAD_STATUS_TERMINATED: "Dead / terminated",
}
MARKETPLACE_LEAD_CLOSED_STATUSES = (
    MARKETPLACE_LEAD_STATUS_COMPLETED,
    MARKETPLACE_LEAD_STATUS_TERMINATED,
)

# Project delivery stages (after the quotation is won). Offered on project transactions only.
PROJECT_STATUS_AWARDED = "awarded"
PROJECT_STATUS_MOBILIZATION = "mobilization"
PROJECT_STATUS_ONGOING = "ongoing"
PROJECT_STATUS_TURNOVER = "turnover"
PROJECT_DELIVERY_STATUSES = (
    PROJECT_STATUS_AWARDED,
    PROJECT_STATUS_MOBILIZATION,
    PROJECT_STATUS_ONGOING,
    PROJECT_STATUS_TURNOVER,
)
MARKETPLACE_LEAD_STATUS_LABELS.update({
    PROJECT_STATUS_AWARDED: "Awarded / contract signed",
    PROJECT_STATUS_MOBILIZATION: "Mobilization",
    PROJECT_STATUS_ONGOING: "Ongoing implementation",
    PROJECT_STATUS_TURNOVER: "For turnover",
})
PROJECT_LEAD_STATUSES = (
    MARKETPLACE_LEAD_STATUS_NEW,
    MARKETPLACE_LEAD_STATUS_FOR_RESEARCH,
    MARKETPLACE_LEAD_STATUS_FOR_QUOTATION,
    MARKETPLACE_LEAD_STATUS_QUOTATION_IN_PROCESS,
    MARKETPLACE_LEAD_STATUS_QUOTATION_SUBMITTED,
    MARKETPLACE_LEAD_STATUS_FOR_FOLLOW_UP,
    MARKETPLACE_LEAD_STATUS_FOR_CONTRACTOR,
    *PROJECT_DELIVERY_STATUSES,
    MARKETPLACE_LEAD_STATUS_ON_HOLD,
    MARKETPLACE_LEAD_STATUS_COMPLETED,
    MARKETPLACE_LEAD_STATUS_TERMINATED,
)
# Product order-to-delivery stages (after the client accepts the quotation). Offered on product transactions only.
PRODUCT_STATUS_ORDER_CONFIRMED = "order_confirmed"
PRODUCT_STATUS_FOR_DELIVERY = "for_delivery"
PRODUCT_STATUS_DELIVERED = "delivered"
PRODUCT_ORDER_STATUSES = (
    PRODUCT_STATUS_ORDER_CONFIRMED,
    PRODUCT_STATUS_FOR_DELIVERY,
    PRODUCT_STATUS_DELIVERED,
)
MARKETPLACE_LEAD_STATUS_LABELS.update({
    PRODUCT_STATUS_ORDER_CONFIRMED: "PO / order confirmed",
    PRODUCT_STATUS_FOR_DELIVERY: "For delivery",
    PRODUCT_STATUS_DELIVERED: "Delivered",
})
PRODUCT_LEAD_STATUSES = (
    MARKETPLACE_LEAD_STATUS_NEW,
    MARKETPLACE_LEAD_STATUS_FOR_RESEARCH,
    MARKETPLACE_LEAD_STATUS_FOR_QUOTATION,
    MARKETPLACE_LEAD_STATUS_QUOTATION_IN_PROCESS,
    MARKETPLACE_LEAD_STATUS_QUOTATION_SUBMITTED,
    MARKETPLACE_LEAD_STATUS_FOR_FOLLOW_UP,
    MARKETPLACE_LEAD_STATUS_FOR_CONTRACTOR,
    *PRODUCT_ORDER_STATUSES,
    MARKETPLACE_LEAD_STATUS_ON_HOLD,
    MARKETPLACE_LEAD_STATUS_COMPLETED,
    MARKETPLACE_LEAD_STATUS_TERMINATED,
)
# Work queues per product duty.
PRODUCT_SOURCING_STATUSES = (MARKETPLACE_LEAD_STATUS_FOR_RESEARCH, MARKETPLACE_LEAD_STATUS_FOR_QUOTATION)
PRODUCT_PRICING_STATUSES = (MARKETPLACE_LEAD_STATUS_FOR_QUOTATION, MARKETPLACE_LEAD_STATUS_QUOTATION_IN_PROCESS)
PRODUCT_LOGISTICS_STATUSES = (PRODUCT_STATUS_ORDER_CONFIRMED, PRODUCT_STATUS_FOR_DELIVERY)

ALL_LEAD_STATUSES = (
    *PROJECT_LEAD_STATUSES[: PROJECT_LEAD_STATUSES.index(MARKETPLACE_LEAD_STATUS_ON_HOLD)],
    *PRODUCT_ORDER_STATUSES,
    *PROJECT_LEAD_STATUSES[PROJECT_LEAD_STATUSES.index(MARKETPLACE_LEAD_STATUS_ON_HOLD):],
)
# Won = quotation accepted (delivery stage or completed); lost = dead / terminated.
PROJECT_WON_STATUSES = (*PROJECT_DELIVERY_STATUSES, MARKETPLACE_LEAD_STATUS_COMPLETED)
# Estimator work queue.
PROJECT_QUOTE_STATUSES = (
    MARKETPLACE_LEAD_STATUS_FOR_RESEARCH,
    MARKETPLACE_LEAD_STATUS_FOR_QUOTATION,
    MARKETPLACE_LEAD_STATUS_QUOTATION_IN_PROCESS,
)
# Stages that get a target date on the project stage plan.
PROJECT_PLAN_STAGES = (
    MARKETPLACE_LEAD_STATUS_FOR_QUOTATION,
    MARKETPLACE_LEAD_STATUS_QUOTATION_SUBMITTED,
    MARKETPLACE_LEAD_STATUS_FOR_CONTRACTOR,
    *PROJECT_DELIVERY_STATUSES,
    MARKETPLACE_LEAD_STATUS_COMPLETED,
)

PROJECT_DOCUMENT_KINDS = {
    "layout": "Layout",
    "boq": "BOQ",
    "plan": "Plans / drawings",
    "quotation": "Quotation",
    "contract": "Contract",
    "site_photo": "Site photo",
    "progress_photo": "Progress photo",
    "other": "Other",
}
# Document types the assigned contractor may upload (always shared with them).
PROJECT_DOCUMENT_CONTRACTOR_KINDS = ("layout", "boq", "plan", "site_photo", "progress_photo")
# Member field agents see / upload every document type except the signed contract.
PROJECT_FIELD_DOCUMENT_KINDS = tuple(kind for kind in PROJECT_DOCUMENT_KINDS if kind != "contract")
PRODUCT_DOCUMENT_KINDS = {
    "supplier_quote": "Supplier quotation",
    "quotation": "Client quotation",
    "purchase_order": "Purchase order (PO)",
    "spec_sheet": "Spec sheet / catalog",
    "supplier_invoice": "Supplier invoice",
    "delivery_receipt": "Delivery receipt (DR)",
    "proof_of_delivery": "Proof of delivery",
    "photo": "Photo",
    "other": "Other",
}
# Document types the assigned supplier may upload (always shared with them).
PRODUCT_DOCUMENT_SUPPLIER_KINDS = (
    "supplier_quote", "spec_sheet", "supplier_invoice", "delivery_receipt", "proof_of_delivery", "photo",
)
# Sales agents (members) never see supplier costs.
PRODUCT_FIELD_DOCUMENT_KINDS = tuple(
    kind for kind in PRODUCT_DOCUMENT_KINDS if kind not in ("supplier_quote", "supplier_invoice")
)
PROJECT_DOCUMENT_MAX_BYTES = 10 * 1024 * 1024
PROJECT_DOCUMENT_EXTENSIONS = (
    ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".doc", ".docx", ".xls", ".xlsx",
    ".csv", ".ppt", ".pptx", ".dwg", ".dxf", ".zip",
)
PROJECT_EVENT_KINDS = {
    "site_visit": "Site ocular / visit",
    "meeting": "Meeting",
    "zoom": "Zoom / online meeting",
    "other": "Other",
}
PROJECT_EVENT_STATUS_LABELS = {
    "scheduled": "Scheduled",
    "done": "Done",
    "cancelled": "Cancelled",
}
PROJECT_DEFAULT_COMMISSION_PERCENT = Decimal(os.getenv("PROJECT_DEFAULT_COMMISSION_PERCENT", "5"))
# Overdue alerts: open projects with no update / stuck in one status longer than this.
PROJECT_STALE_DAYS = int(os.getenv("PROJECT_STALE_DAYS", "7"))
PROJECT_STUCK_DAYS = int(os.getenv("PROJECT_STUCK_DAYS", "14"))
PROJECT_REMINDER_DAYS = int(os.getenv("PROJECT_REMINDER_DAYS", "7"))
# Product alerts: idle, stuck, quotation awaiting the client's answer, unassigned inquiries.
PRODUCT_STALE_DAYS = int(os.getenv("PRODUCT_STALE_DAYS", "5"))
PRODUCT_STUCK_DAYS = int(os.getenv("PRODUCT_STUCK_DAYS", "10"))
PRODUCT_QUOTE_FOLLOWUP_DAYS = int(os.getenv("PRODUCT_QUOTE_FOLLOWUP_DAYS", "3"))
PRODUCT_UNASSIGNED_DAYS = int(os.getenv("PRODUCT_UNASSIGNED_DAYS", "1"))

# Transaction type is the marketplace category slug (or "projects"); reference numbers use these prefixes.
TRANSACTION_TYPE_PROJECTS = "projects"
TRANSACTION_TYPE_LABELS = {
    "products": "Product",
    TRANSACTION_TYPE_PROJECTS: "Project",
    "services": "Service",
    "real_property": "Real Property",
}
TRANSACTION_REF_PREFIXES = {
    "products": "PRD",
    TRANSACTION_TYPE_PROJECTS: "PRJ",
    "services": "SRV",
    "real_property": "RPT",
}
# Scope-of-work suggestions on the public project inquiry form (from the PROJECTS monitoring sheet).
PROJECT_SCOPE_SUGGESTIONS = (
    "Bored piling",
    "Micropiling",
    "Sheet piling",
    "Push pile",
    "Soil nailing & shotcreting",
    "Rock anchoring",
    "Rock fall netting",
    "Slope protection",
    "Excavation",
    "Retrofitting",
    "Site development / pipelaying",
    "Clearing services",
    "Design and build",
    "Building / warehouse construction",
    "Glass & aluminum works",
)
TRANSACTION_SOURCE_WEB = "web"
TRANSACTION_SOURCE_MANUAL = "manual"
TRANSACTION_SOURCE_IMPORT = "import"
TRANSACTION_SOURCE_LEGACY = "legacy"
TRANSACTION_SOURCE_LABELS = {
    TRANSACTION_SOURCE_WEB: "Web inquiry",
    TRANSACTION_SOURCE_MANUAL: "Manual entry",
    TRANSACTION_SOURCE_IMPORT: "Excel import",
    TRANSACTION_SOURCE_LEGACY: "Legacy CRM inquiry",
}
TRANSACTION_NOTE_KINDS = {
    "call": "Call",
    "email": "Email",
    "note": "Note",
}

# Ref-Seller / Ref-Buyer pool level table (levels 1–6 upline, level 7 Mandate).
DEFAULT_PRODUCT_POOL_LEVELS = [
    (1, Decimal("50.00"), "Product seller/buyer referrer"),
    (2, Decimal("25.00"), "Upline 1"),
    (3, Decimal("5.00"), "Upline 2"),
    (4, Decimal("5.00"), "Upline 3"),
    (5, Decimal("5.00"), "Upline 4"),
    (6, Decimal("5.00"), "Upline 5"),
    (7, Decimal("5.00"), "Mandate account (Level 7)"),
]

MEMBER_EARNINGS_CAP_FIRST_PROJECT = Decimal(os.getenv("MEMBER_EARNINGS_CAP_FIRST_PROJECT", "15000000"))
MEMBER_EARNINGS_CAP_SECOND_PROJECT = Decimal(os.getenv("MEMBER_EARNINGS_CAP_SECOND_PROJECT", "10000000"))
MEMBER_EARNINGS_CAP_NTH_PROJECT = Decimal(os.getenv("MEMBER_EARNINGS_CAP_NTH_PROJECT", "5000000"))
MEMBER_LIFETIME_EARNINGS_CAP = Decimal(os.getenv("MEMBER_LIFETIME_EARNINGS_CAP", "50000000"))
MEMBER_LIFETIME_PROJECT_CAP_AFTER_LIMIT = Decimal(
    os.getenv("MEMBER_LIFETIME_PROJECT_CAP_AFTER_LIMIT", "1000000")
)

COMMISSION_SCHEME_CLIENT = "client"
COMMISSION_SCHEME_CONTRACTOR = "contractor"
COMMISSION_SCHEMES = [COMMISSION_SCHEME_CLIENT, COMMISSION_SCHEME_CONTRACTOR]

# Internal schemes used for splitting PLATFORM pool sub-accounts.
# These are not exposed in Commission Management UI.
COMMISSION_SCHEME_PLATFORM_REF_CLIENT = "platform_ref_client"
COMMISSION_SCHEME_PLATFORM_REF_CONTRACTOR = "platform_ref_contractor"
COMMISSION_SCHEME_PLATFORM_POP = "platform_pop"

_LEVEL_ROWS = [
    (1, 50.00),
    (2, 12.00),
    (3, 10.00),
    (4, 8.00),
    (5, 8.00),
    (6, 6.00),
    (7, 6.00),
]

DEFAULT_CLIENT_COMMISSION_LEVELS = [
    (1, 50.00, "Project client referrer"),
    (2, 12.00, "Upline 1"),
    (3, 10.00, "Upline 2"),
    (4, 8.00, "Upline 3"),
    (5, 8.00, "Upline 4"),
    (6, 6.00, "Upline 5"),
    (7, 6.00, "Mandate account (Level 7)"),
]

DEFAULT_CONTRACTOR_COMMISSION_LEVELS = [
    (1, 50.00, "Contractor member referrer"),
    (2, 12.00, "Upline 1"),
    (3, 10.00, "Upline 2"),
    (4, 8.00, "Upline 3"),
    (5, 8.00, "Upline 4"),
    (6, 6.00, "Upline 5"),
    (7, 6.00, "Mandate account (Level 7)"),
]

USER_ROLE_PORTAL_ADMIN = "PortalAdmin"
USER_ROLE_SITE_ADMIN = "SiteAdmin"
USER_ROLE_ADMIN = "Admin"
USER_ROLE_STAFF = "Staff"
USER_ROLE_MEMBER = "Member"
USER_ROLE_SUPPLIER = "Supplier"
USER_ROLE_CONTRACTOR = "Contractor"
USER_ROLES = [
    USER_ROLE_PORTAL_ADMIN,
    USER_ROLE_SITE_ADMIN,
    USER_ROLE_ADMIN,
    USER_ROLE_STAFF,
    USER_ROLE_MEMBER,
    USER_ROLE_SUPPLIER,
    USER_ROLE_CONTRACTOR,
]


DEPARTMENT_ADMIN = "Admin"
DEPARTMENT_PROJECTS = "Projects"
DEPARTMENT_SALES_MARKETING = "Sales & Marketing"
DEPARTMENT_ACCOUNTING = "Accounting"
DEPARTMENTS = [
    DEPARTMENT_ADMIN,
    DEPARTMENT_PROJECTS,
    DEPARTMENT_SALES_MARKETING,
    DEPARTMENT_ACCOUNTING,
]
# Former department names still accepted on input (forms, imports) and rewritten by the migration.
MERGED_DEPARTMENTS = {
    "Sales": DEPARTMENT_SALES_MARKETING,
    "Marketing": DEPARTMENT_SALES_MARKETING,
}


def normalize_department(department):
    """Return the canonical department name, or None when blank or unknown."""
    value = (department or "").strip().lower()
    if not value:
        return None
    department_map = {item.lower(): item for item in DEPARTMENTS}
    department_map.update({old.lower(): new for old, new in MERGED_DEPARTMENTS.items()})
    department_map["sales and marketing"] = DEPARTMENT_SALES_MARKETING
    return department_map.get(value)


def normalize_role(role):
    value = (role or USER_ROLE_STAFF).strip().lower()
    role_map = {item.lower(): item for item in USER_ROLES}
    return role_map.get(value, USER_ROLE_STAFF)


def is_portal_admin_role(role=None):
    return normalize_role(role) == USER_ROLE_PORTAL_ADMIN


def is_site_admin_role(role=None):
    return normalize_role(role) == USER_ROLE_SITE_ADMIN


def can_manage_site_content(role=None):
    """Edit public landing pages, ecosystem content, partner registry, and marketplace."""
    return normalize_role(role) in (
        USER_ROLE_PORTAL_ADMIN,
        USER_ROLE_SITE_ADMIN,
        USER_ROLE_ADMIN,
    )


def can_manage_gallery(role=None):
    """Create and edit landing page gallery folders."""
    return normalize_role(role) in (
        USER_ROLE_PORTAL_ADMIN,
        USER_ROLE_SITE_ADMIN,
        USER_ROLE_ADMIN,
        USER_ROLE_STAFF,
    )


def can_view_marketplace_help(role=None):
    """Marketplace & CRM help guide for operational roles (not Members)."""
    return normalize_role(role) in (
        USER_ROLE_PORTAL_ADMIN,
        USER_ROLE_ADMIN,
        USER_ROLE_SITE_ADMIN,
        USER_ROLE_STAFF,
    )


def can_access_marketplace_crm(role=None):
    """View Marketplace CRM and update inquiry follow-up status."""
    return normalize_role(role) in (
        USER_ROLE_PORTAL_ADMIN,
        USER_ROLE_ADMIN,
        USER_ROLE_SITE_ADMIN,
        USER_ROLE_STAFF,
    )


def can_view_features_process_flow(role=None):
    """App Features & Process Flow help for Admin, Staff, and SiteAdmin (not Members)."""
    return normalize_role(role) in (
        USER_ROLE_PORTAL_ADMIN,
        USER_ROLE_ADMIN,
        USER_ROLE_SITE_ADMIN,
        USER_ROLE_STAFF,
    )


def is_admin_role(role=None):
    return normalize_role(role) in (USER_ROLE_PORTAL_ADMIN, USER_ROLE_ADMIN)


def is_staff_role(role=None):
    return normalize_role(role) == USER_ROLE_STAFF


def is_member_role(role=None):
    return normalize_role(role) == USER_ROLE_MEMBER


def is_supplier_role(role=None):
    return normalize_role(role) == USER_ROLE_SUPPLIER


def is_contractor_role(role=None):
    return normalize_role(role) == USER_ROLE_CONTRACTOR


def is_staff_or_admin(role=None):
    return normalize_role(role) in (USER_ROLE_PORTAL_ADMIN, USER_ROLE_ADMIN, USER_ROLE_STAFF)


DEPARTMENT_ROLES = (
    USER_ROLE_PORTAL_ADMIN,
    USER_ROLE_SITE_ADMIN,
    USER_ROLE_ADMIN,
    USER_ROLE_STAFF,
)


def role_uses_department(role=None):
    """Internal accounts belong to a department; Member, Supplier, and Contractor do not."""
    return normalize_role(role) in DEPARTMENT_ROLES


# Duties: work assignments held on top of the login role (several per user).
DUTY_PROJECTS_MANAGER = "projects_manager"
DUTY_PROJECT_COORDINATOR = "project_coordinator"
DUTY_ESTIMATOR = "estimator"
DUTY_SITE_ENGINEER = "site_engineer"
DUTY_PRODUCTS_MANAGER = "products_manager"
DUTY_ACCOUNT_OFFICER = "account_officer"
DUTY_SOURCING_OFFICER = "sourcing_officer"
DUTY_PRICING_OFFICER = "pricing_officer"
DUTY_LOGISTICS_COORDINATOR = "logistics_coordinator"
DUTY_SALES_AGENT = "sales_agent"
DUTY_LABELS = {
    DUTY_PROJECTS_MANAGER: "Projects Manager",
    DUTY_PROJECT_COORDINATOR: "Project Coordinator",
    DUTY_ESTIMATOR: "Estimator / Quantity Surveyor",
    DUTY_SITE_ENGINEER: "Site Engineer / Inspector",
    DUTY_PRODUCTS_MANAGER: "Products Manager",
    DUTY_ACCOUNT_OFFICER: "Account Officer / Sales Coordinator",
    DUTY_SOURCING_OFFICER: "Sourcing / Purchasing Officer",
    DUTY_PRICING_OFFICER: "Pricing / Quotation Officer",
    DUTY_LOGISTICS_COORDINATOR: "Logistics / Delivery Coordinator",
    DUTY_SALES_AGENT: "Sales Agent",
}
DUTY_DESCRIPTIONS = {
    DUTY_PROJECTS_MANAGER: "Team lead: sees team workload and unassigned projects.",
    DUTY_PROJECT_COORDINATOR: "Owns projects from inquiry to turnover.",
    DUTY_ESTIMATOR: "Prepares costing and quotations.",
    DUTY_SITE_ENGINEER: "Handles site visits, inspections, and progress checks.",
    DUTY_PRODUCTS_MANAGER: "Team lead: sees product team workload, unassigned inquiries, and alerts.",
    DUTY_ACCOUNT_OFFICER: "Owns product inquiries: client contact, follow-up, and closing.",
    DUTY_SOURCING_OFFICER: "Finds suppliers, checks specs and stock, and gets supplier prices.",
    DUTY_PRICING_OFFICER: "Prepares product costing, margin, and the client quotation.",
    DUTY_LOGISTICS_COORDINATOR: "Schedules delivery and collects the DR and proof of delivery.",
    DUTY_SALES_AGENT: "Member in the field who follows up assigned product inquiries.",
}
DUTIES = tuple(DUTY_LABELS)
DUTY_GROUPS = {
    "Projects": (DUTY_PROJECTS_MANAGER, DUTY_PROJECT_COORDINATOR, DUTY_ESTIMATOR, DUTY_SITE_ENGINEER),
    "Products": (
        DUTY_PRODUCTS_MANAGER, DUTY_ACCOUNT_OFFICER, DUTY_SOURCING_OFFICER, DUTY_PRICING_OFFICER,
        DUTY_LOGISTICS_COORDINATOR, DUTY_SALES_AGENT,
    ),
}
PROJECT_MEMBER_DUTIES = (DUTY_PROJECT_COORDINATOR, DUTY_ESTIMATOR, DUTY_SITE_ENGINEER)
PRODUCT_MEMBER_DUTIES = (DUTY_SALES_AGENT,)
MEMBER_FIELD_DUTIES = (*PROJECT_MEMBER_DUTIES, *PRODUCT_MEMBER_DUTIES)
# Team slot (lead column) -> duty whose holders are offered for it.
PROJECT_TEAM_SLOTS = {
    "assigned_user_id": DUTY_PROJECT_COORDINATOR,
    "estimator_user_id": DUTY_ESTIMATOR,
    "site_engineer_user_id": DUTY_SITE_ENGINEER,
}
PROJECT_TEAM_SLOT_LABELS = {
    "assigned_user_id": "Project coordinator",
    "estimator_user_id": "Estimator",
    "site_engineer_user_id": "Site engineer",
}
# The pricing officer reuses the estimator column.
PRODUCT_TEAM_SLOTS = {
    "assigned_user_id": DUTY_ACCOUNT_OFFICER,
    "sourcing_user_id": DUTY_SOURCING_OFFICER,
    "estimator_user_id": DUTY_PRICING_OFFICER,
    "logistics_user_id": DUTY_LOGISTICS_COORDINATOR,
    "agent_user_id": DUTY_SALES_AGENT,
}
PRODUCT_TEAM_SLOT_LABELS = {
    "assigned_user_id": "Account officer",
    "sourcing_user_id": "Sourcing officer",
    "estimator_user_id": "Pricing officer",
    "logistics_user_id": "Logistics coordinator",
    "agent_user_id": "Sales agent",
}
TEAM_SLOT_COLUMNS = tuple(dict.fromkeys((*PROJECT_TEAM_SLOTS, *PRODUCT_TEAM_SLOTS)))


def team_slots_for_type(transaction_type):
    """Team slot -> duty for a transaction type (other types only have the assigned staff)."""
    if transaction_type == "projects":
        return PROJECT_TEAM_SLOTS
    if transaction_type == "products":
        return PRODUCT_TEAM_SLOTS
    return {"assigned_user_id": None}


def team_slot_labels_for_type(transaction_type):
    if transaction_type == "projects":
        return PROJECT_TEAM_SLOT_LABELS
    if transaction_type == "products":
        return PRODUCT_TEAM_SLOT_LABELS
    return {"assigned_user_id": "Assigned staff"}


def member_duties_for_type(transaction_type):
    if transaction_type == "projects":
        return PROJECT_MEMBER_DUTIES
    if transaction_type == "products":
        return PRODUCT_MEMBER_DUTIES
    return ()


def duties_allowed_for_role(role=None):
    """Staff and admins may hold any duty; Members only the field duties."""
    normalized = normalize_role(role)
    if normalized in (USER_ROLE_PORTAL_ADMIN, USER_ROLE_ADMIN, USER_ROLE_STAFF):
        return DUTIES
    if normalized == USER_ROLE_MEMBER:
        return MEMBER_FIELD_DUTIES
    return ()


def can_manage_data(role=None):
    """Import/edit members, contractors, project commission, generate sharing."""
    return is_staff_or_admin(role)


def can_access_admin_options(role=None):
    return is_staff_or_admin(role)


def can_purge_member_database(role=None):
    return is_portal_admin_role(role)


def can_delete_sharing_batch(role=None):
    return is_admin_role(role)


def can_view_sharing_result(role=None):
    return is_admin_role(role)


def can_manage_commission_levels(role=None):
    return is_admin_role(role)


def can_access_prof_reports(role=None):
    return is_admin_role(role)


def assignable_user_roles(actor_role=None):
    if is_portal_admin_role(actor_role):
        return list(USER_ROLES)
    if is_admin_role(actor_role):
        return [
            USER_ROLE_ADMIN,
            USER_ROLE_STAFF,
            USER_ROLE_MEMBER,
            USER_ROLE_SUPPLIER,
            USER_ROLE_CONTRACTOR,
        ]
    return [USER_ROLE_STAFF, USER_ROLE_MEMBER, USER_ROLE_SUPPLIER, USER_ROLE_CONTRACTOR]


def post_login_redirect(role, next_param=""):
    """Default landing URL after login, respecting role and optional next path."""
    if next_param.startswith("/") and not next_param.startswith("//"):
        if next_param.startswith("/site-admin"):
            if can_manage_site_content(role):
                return next_param
            return "/dashboard"
        if is_site_admin_role(role) and next_param.startswith("/dashboard"):
            return "/site-admin"
        return next_param
    if is_site_admin_role(role):
        return "/site-admin"
    return "/dashboard"


def staff_may_manage_user(actor_role, target_user_role):
    if is_portal_admin_role(actor_role):
        return True
    if is_portal_admin_role(target_user_role):
        return False
    if is_site_admin_role(target_user_role):
        return False
    if is_admin_role(actor_role):
        return True
    return not is_admin_role(target_user_role)


def mandate_subaccount_label(share_scheme):
    """Human-readable Mandate pool sub-account label for a share scheme."""
    if share_scheme == COMMISSION_SCHEME_CLIENT:
        return f"{MANDATE_RECIPIENT_LABEL} (Ref-Client)"
    if share_scheme == COMMISSION_SCHEME_CONTRACTOR:
        return f"{MANDATE_RECIPIENT_LABEL} (Ref-Contractor)"
    if share_scheme == COMMISSION_SCHEME_PLATFORM_REF_CLIENT:
        return f"{MANDATE_RECIPIENT_LABEL} (Platform Ref-Client)"
    if share_scheme == COMMISSION_SCHEME_PLATFORM_REF_CONTRACTOR:
        return f"{MANDATE_RECIPIENT_LABEL} (Platform Ref-Contractor)"
    if share_scheme == COMMISSION_SCHEME_PRODUCT_REF_SELLER:
        return f"{MANDATE_RECIPIENT_LABEL} (Product Ref-Seller)"
    if share_scheme == COMMISSION_SCHEME_PRODUCT_REF_BUYER:
        return f"{MANDATE_RECIPIENT_LABEL} (Product Ref-Buyer)"
    return MANDATE_RECIPIENT_LABEL


MANDATE_SUBACCOUNT_LABELS = {
    "client": "Ref-Client pool — Level 7 Mandate account",
    "contractor": "Ref-Contractor pool — Level 7 Mandate account",
    "platform_ref_client": "Platform Ref-Client pool — Level 7 Mandate account",
    "platform_ref_contractor": "Platform Ref-Contractor pool — Level 7 Mandate account",
    "product_ref_seller": "Product Ref-Seller pool — Level 7 Mandate account",
    "product_ref_buyer": "Product Ref-Buyer pool — Level 7 Mandate account",
}


PAYOUT_STATUS_PENDING = "pending"
PAYOUT_STATUS_APPROVED = "approved"
PAYOUT_STATUS_RELEASE_SUBMITTED = "release_submitted"
PAYOUT_STATUS_RELEASED = "released"
PAYOUT_STATUS_REJECTED = "rejected"

PAYOUT_STATUSES = [
    PAYOUT_STATUS_PENDING,
    PAYOUT_STATUS_APPROVED,
    PAYOUT_STATUS_RELEASE_SUBMITTED,
    PAYOUT_STATUS_RELEASED,
    PAYOUT_STATUS_REJECTED,
]

PAYOUT_RELEASE_METHOD_BANK_DEPOSIT = "Bank Deposit"
PAYOUT_RELEASE_METHOD_OTHER = "Other"
PAYOUT_RELEASE_METHODS = [
    PAYOUT_RELEASE_METHOD_BANK_DEPOSIT,
    "GCash",
    "Maya",
    "PayPal",
    PAYOUT_RELEASE_METHOD_OTHER,
]

PAYOUT_OMPD_PERCENT = int(os.getenv("PAYOUT_OMPD_PERCENT", "10"))
OMPD_FUND_LABEL = "OMPD Fund"
OMPD_FUND_DESCRIPTION = (
    "Operations, Management, and Platform Development"
)


def payout_ompd_split(gross_amount):
    """Return (ompd_deduction, net_release) for a gross payout request amount."""
    gross = Decimal(str(gross_amount or 0)).quantize(Decimal("0.01"))
    deduction = (
        gross * Decimal(str(PAYOUT_OMPD_PERCENT)) / Decimal("100")
    ).quantize(Decimal("0.01"))
    net = (gross - deduction).quantize(Decimal("0.01"))
    return deduction, net


def payout_scheme_summary():
    deduction_pct = PAYOUT_OMPD_PERCENT
    return {
        "ompd_percent": deduction_pct,
        "ompd_label": OMPD_FUND_LABEL,
        "ompd_description": OMPD_FUND_DESCRIPTION,
        "member_receives_percent": 100 - deduction_pct,
    }

LEDGER_TRANSACTION_CREDIT = "credit"
LEDGER_TRANSACTION_DEBIT = "debit"


def can_request_payout(role=None):
    return is_member_role(role)


def can_approve_payout_request(role=None):
    return is_admin_role(role)


def can_submit_payout_release(role=None):
    return is_staff_or_admin(role)


def can_approve_payout_release(role=None):
    return is_admin_role(role)


def can_view_payout_reports(role=None):
    return is_staff_or_admin(role)


def can_view_payout_scheme(role=None):
    return is_staff_or_admin(role)


NOTICE_TYPE_POLICY = "policy"
NOTICE_TYPE_MEMO = "memo"
NOTICE_TYPE_ANNOUNCEMENT = "announcement"
NOTICE_TYPES = (
    NOTICE_TYPE_POLICY,
    NOTICE_TYPE_MEMO,
    NOTICE_TYPE_ANNOUNCEMENT,
)
NOTICE_TYPE_LABELS = {
    NOTICE_TYPE_POLICY: "Policy",
    NOTICE_TYPE_MEMO: "Memorandum",
    NOTICE_TYPE_ANNOUNCEMENT: "Announcement",
}


def can_manage_notices(role=None):
    """Staff, Admin, and PortalAdmin can post policies, memos, and announcements."""
    return is_staff_or_admin(role)


SANCTION_DEFAULT_DAYS = 30
SANCTION_MAX_DAYS = 365


def can_view_sanctions(role=None):
    """Staff see suspensions so they know who cannot be credited for ads or contractor endorsements."""
    return is_staff_or_admin(role)


def can_manage_sanctions(role=None):
    """Only Admin and PortalAdmin (program management) issue or lift member suspensions."""
    return is_admin_role(role)
