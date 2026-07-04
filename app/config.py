import os
from decimal import Decimal

DB_CONFIG = {
    "db_user": os.getenv("DB_USER", "postgres"),
    "db_pass": os.getenv("DB_PASS", "password"),
    "db_ip": os.getenv("DB_IP", "127.0.0.1"),
    "db_port": os.getenv("DB_PORT", "5432"),
    "db_name": os.getenv("DB_NAME", "tbgp"),
}

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

MEMBER_STATUSES = ["Active", "Inactive", "Separated"]
MEMBER_SEPARATION_TYPES = [
    "Resigned",
    "End of Contract",
    "Retired",
    "Terminated",
    "Deceased",
]

MAX_SHARING_LEVELS = 7
CLIENT_POOL_PERCENT = int(os.getenv("CLIENT_POOL_PERCENT", "50"))
CONTRACTOR_POOL_PERCENT = int(os.getenv("CONTRACTOR_POOL_PERCENT", "25"))
ADMIN_ACCOUNT_PERCENT = int(os.getenv("ADMIN_ACCOUNT_PERCENT", "25"))
ADMIN_MEMBER_ID = os.getenv("ADMIN_MEMBER_ID")
ADMIN_RECIPIENT_LABEL = "PLATFORM Account"
MANDATE_RECIPIENT_LABEL = "Mandate Account"
POP_RECIPIENT_LABEL = "Poorest of the Poor (POP)"
POP_CAP_FLUSH_LABEL = f"{POP_RECIPIENT_LABEL} (Earnings cap flush)"
POP_LIFETIME_LIMIT_FUND_LABEL = f"{POP_RECIPIENT_LABEL} Lifetime Limit Fund"
ADMIN_SHARING_LEVEL = -1

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
USER_ROLE_ADMIN = "Admin"
USER_ROLE_STAFF = "Staff"
USER_ROLE_MEMBER = "Member"
USER_ROLES = [USER_ROLE_PORTAL_ADMIN, USER_ROLE_ADMIN, USER_ROLE_STAFF, USER_ROLE_MEMBER]


def normalize_role(role):
    value = (role or USER_ROLE_STAFF).strip().lower()
    role_map = {item.lower(): item for item in USER_ROLES}
    return role_map.get(value, USER_ROLE_STAFF)


def is_portal_admin_role(role=None):
    return normalize_role(role) == USER_ROLE_PORTAL_ADMIN


def is_admin_role(role=None):
    return normalize_role(role) in (USER_ROLE_PORTAL_ADMIN, USER_ROLE_ADMIN)


def is_staff_role(role=None):
    return normalize_role(role) == USER_ROLE_STAFF


def is_member_role(role=None):
    return normalize_role(role) == USER_ROLE_MEMBER


def is_staff_or_admin(role=None):
    return normalize_role(role) in (USER_ROLE_PORTAL_ADMIN, USER_ROLE_ADMIN, USER_ROLE_STAFF)


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
        return [USER_ROLE_ADMIN, USER_ROLE_STAFF, USER_ROLE_MEMBER]
    return [USER_ROLE_STAFF, USER_ROLE_MEMBER]


def staff_may_manage_user(actor_role, target_user_role):
    if is_portal_admin_role(actor_role):
        return True
    if is_portal_admin_role(target_user_role):
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
    return MANDATE_RECIPIENT_LABEL


MANDATE_SUBACCOUNT_LABELS = {
    "client": "Ref-Client pool — Level 7 Mandate account",
    "contractor": "Ref-Contractor pool — Level 7 Mandate account",
    "platform_ref_client": "Platform Ref-Client pool — Level 7 Mandate account",
    "platform_ref_contractor": "Platform Ref-Contractor pool — Level 7 Mandate account",
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
