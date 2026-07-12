"""Role-based user manual and help content for the portal and site admin."""

from app.config import (
    MEMBER_LIFETIME_PROJECT_CAP_AFTER_LIMIT,
    USER_ROLE_ADMIN,
    USER_ROLE_MEMBER,
    USER_ROLE_PORTAL_ADMIN,
    USER_ROLE_SITE_ADMIN,
    USER_ROLE_STAFF,
    normalize_role,
)

USER_MANUALS = {
    USER_ROLE_PORTAL_ADMIN: {
        "title": "PortalAdmin User Manual",
        "summary": "Highest-privilege account for protected portal maintenance and database purge actions.",
        "sections": [
            {
                "heading": "Main Responsibilities",
                "items": [
                    "Maintain the protected PortalAdmin account.",
                    "Use Delete All Members only when resetting demo or test data.",
                    "Review the portal as an Admin-level user when needed.",
                    "Delegate routine public website updates to SiteAdmin accounts.",
                ],
            },
            {
                "heading": "Delete All Members",
                "items": [
                    "Open Administration → Admin Options → Delete All Members.",
                    "Read the confirmation prompt carefully before continuing.",
                    "Type DELETE ALL MEMBERS exactly when the system asks for confirmation.",
                    "This clears member-related records, including ledgers, payouts, sharing data, projects, and contractors, then resets member and contractor ID sequences.",
                ],
            },
            {
                "heading": "Safety Notes",
                "items": [
                    "Do not use PortalAdmin for daily encoding work.",
                    "Do not share the PortalAdmin password with regular staff users.",
                    "Use a normal Admin account for routine portal management and a SiteAdmin account for website content.",
                ],
            },
        ],
    },
    USER_ROLE_SITE_ADMIN: {
        "title": "SiteAdmin User Manual",
        "summary": "Manage the public TBGP landing site, ecosystem pages, partner registry, and services contact card.",
        "sections": [
            {
                "heading": "Getting Started",
                "items": [
                    "Sign in with your SiteAdmin account to open the Site Content workspace at /site-admin.",
                    "Use the sidebar to move between overview, page editors, and registry tools.",
                    "On mobile, tap the hamburger menu in the top bar to open navigation.",
                    "Use View Site in the sidebar to preview the public website in a new tab.",
                ],
            },
            {
                "heading": "Landing and Ecosystem Pages",
                "items": [
                    "Landing Section edits the ecosystem header on the home page above the three pillar cards.",
                    "Products, Services, and Partners pages control each ecosystem pillar page copy, highlights, and portal call-to-action blocks.",
                    "Use Preview on the overview cards to check changes on the live public site after saving.",
                ],
            },
            {
                "heading": "Services Contact Card",
                "items": [
                    "Edit the title, displayed phone number, and click-to-call number for the services contact card.",
                    "This card appears on the Services page, Partners page, and every partner profile page.",
                ],
            },
            {
                "heading": "Partner Registry",
                "items": [
                    "Use Contractor Registry and Supplier Registry to add, edit, sort, or remove public partner profiles.",
                    "Set registry code, URL slug, specialty, images, profile copy, and capability gallery photos.",
                    "When Supabase Storage is configured, use Upload on thumbnail, logo, and gallery rows; the public URL is saved automatically.",
                    "You can still paste an external image URL instead of uploading.",
                    "Supplier entries support portal supplier ID linking; company name and location sync from the portal Suppliers module when linked.",
                ],
            },
            {
                "heading": "Portal Partner Linking",
                "items": [
                    "For contractors, enter Portal contractor ID to link a registry profile to a portal contractor record.",
                    "For suppliers, enter Portal supplier ID to link a registry profile to a portal supplier record.",
                    "When linked, company name and location are read-only here and sync from the portal database.",
                    "Codes ending in con-### or sup-### can auto-link without an explicit ID.",
                    "The public profile shows the member referrer when the linked portal record is found.",
                    "Update company name or address in the portal Contractors or Suppliers module, then reload or re-save the registry entry.",
                ],
            },
            {
                "heading": "Help and Account",
                "items": [
                    "Open User Manual in the sidebar for this guide.",
                    "Use Logout when finished. SiteAdmin accounts are for public site work, not daily portal encoding.",
                ],
            },
        ],
    },
    USER_ROLE_ADMIN: {
        "title": "Admin User Manual",
        "summary": "Admin users manage accounts, members, contractors, income workflows, payout approvals, and reports.",
        "sections": [
            {
                "heading": "Portal Navigation",
                "items": [
                    "Use the sidebar for Members, Member Ledger, Contractors, Suppliers, and Hierarchy Tree.",
                    "Open Payouts for payout scheme reference, payout queue actions, and fund release reports.",
                    "Open Income Management for project commissions, commission levels, generate sharing, and commission reports.",
                    "Open Administration → Admin Options for user management.",
                    "Open Help for this manual, Features & Process Flow, and About the Platform.",
                    "Use Home at the bottom of the sidebar to return to the public landing page.",
                ],
            },
            {
                "heading": "User Management",
                "items": [
                    "Open Administration → Admin Options → Manage Users to add, edit, or delete user accounts.",
                    "Assign only the role a user needs: Admin, Staff, or Member.",
                    "Link Member users to their correct Member ID so they can access their own portal.",
                    "PortalAdmin and SiteAdmin accounts are protected from normal user management.",
                ],
            },
            {
                "heading": "Member and Contractor Records",
                "items": [
                    "Use Members to add, edit, import, or review member profiles.",
                    "Use Contractors to add, edit, import, or review contractor records.",
                    "Use the generated Excel templates when importing new records.",
                    "Set a member lifetime limit threshold from the Add/Edit Member form when needed.",
                    f"After the threshold, that member is limited to {MEMBER_LIFETIME_PROJECT_CAP_AFTER_LIMIT:,.2f} per project and excess goes to the POP Lifetime Limit Fund.",
                    "Keep contractor company name and address accurate; linked public contractor profiles sync from these records.",
                ],
            },
            {
                "heading": "Income Management",
                "items": [
                    "Use Income Management → Project Commission to record projects, contractors, client referrals, addresses, and billings.",
                    "Use Commission Management to adjust commission levels.",
                    "Use Generate Sharing to preview and generate profit sharing for billing dates.",
                    "Generated sharing protects linked project and billing records from unsafe deletion.",
                    "Use Reports under Commission for project list and commission summary review.",
                ],
            },
            {
                "heading": "Payouts and Reports",
                "items": [
                    "Review Payout Scheme for OMPD and release rules.",
                    "Approve member payout requests from Payout Queue.",
                    "Review Staff release submissions and approve final releases.",
                    "Use Fund Release Reports for reconciliation and PDF export where available.",
                ],
            },
        ],
    },
    USER_ROLE_STAFF: {
        "title": "Staff User Manual",
        "summary": "Staff users encode operational records, generate sharing, and submit payout release details.",
        "sections": [
            {
                "heading": "Portal Navigation",
                "items": [
                    "Use the sidebar for Members, Member Ledger, Contractors, Suppliers, and Hierarchy Tree.",
                    "Open Payouts for payout scheme reference, payout queue work, and fund release reports.",
                    "Open Income Management for project commissions and generate sharing.",
                    "Open Help for this manual, Features & Process Flow, and About the Platform.",
                ],
            },
            {
                "heading": "Daily Data Entry",
                "items": [
                    "Use Members to add, edit, and import member records.",
                    "Use Contractors to add, edit, and import contractor records.",
                    "Check required fields before saving or importing records.",
                    "Staff cannot change Admin-only member lifetime limit controls.",
                ],
            },
            {
                "heading": "Project Commissions",
                "items": [
                    "Use Income Management → Project Commission to add projects, select contractors, set client referrals, and encode billings.",
                    "Once sharing has been generated, Staff cannot edit project title, address, client referral, contractor, or generated billing amounts.",
                    "Ask an Admin if generated project or billing details must be corrected.",
                ],
            },
            {
                "heading": "Generate Sharing",
                "items": [
                    "Use Income Management → Generate Sharing to preview available billings.",
                    "Review the billing date and records before generating sharing.",
                    "Generated sharing creates ledger entries and may lock related project billing details.",
                ],
            },
            {
                "heading": "Payout Release",
                "items": [
                    "Use Payout Queue to record release details for approved payout requests.",
                    "Select the correct release method and fill required reference details.",
                    "For Bank Deposit, enter bank name and branch; for Other, enter the custom method.",
                    "Staff cannot approve payout requests or final releases; escalate those to an Admin.",
                ],
            },
        ],
    },
    USER_ROLE_MEMBER: {
        "title": "Member User Manual",
        "summary": "Member users review their own profile, hierarchy, ledger, payout activity, and help resources.",
        "sections": [
            {
                "heading": "Portal Navigation",
                "items": [
                    "Use Dashboard for your member summary and earnings overview.",
                    "Use My Information, My Ledger, and My Hierarchy for your own records only.",
                    "Open Help for this manual, Features & Process Flow, and About the Platform.",
                    "Use Home at the bottom of the sidebar to return to the public landing page.",
                ],
            },
            {
                "heading": "Dashboard",
                "items": [
                    "Use Dashboard for your member summary, batch, member/contractor/supplier referrals, downline count, and ledger earnings.",
                    "Use the Member Support box on the dashboard to send a WhatsApp message for membership concerns or other matters.",
                    "Open Reading in the top bar to choose Standard, Large, or Extra large text and turn High contrast on or off.",
                    "When logged in, reading settings are saved to your account and follow you across devices.",
                    "On Dashboard, click any summary card to open member referrals, downline, contractor/supplier referrals, profile, or ledger details.",
                    "If your account is not linked to a member record, contact the Admin or Staff.",
                ],
            },
            {
                "heading": "My Information",
                "items": [
                    "Use My Information to review and update your member profile.",
                    "You can edit gender, civil status, phone, email, address, highest education, occupation or income source, monthly income, number of dependents, and beneficiary details.",
                    "Ask Staff or Admin to change your name, batch, referrer, status, or other membership records.",
                ],
            },
            {
                "heading": "My Ledger and Hierarchy",
                "items": [
                    "Use My Ledger to review earning transactions, payout deductions, and your payout request history.",
                    "Submit a payout request from My Ledger when you have available balance.",
                    "Use My Hierarchy to view your referral line and downline structure.",
                ],
            },
            {
                "heading": "Payout Guidance",
                "items": [
                    "Payout requests are submitted from My Ledger, not from a separate payout menu.",
                    "OMPD and other deductions are applied before net release; Staff and Admin process approved requests.",
                    "Coordinate with Staff or Admin for payout request and release concerns.",
                ],
            },
        ],
    },
}

APP_FEATURES = [
    {
        "icon": "bi-people",
        "title": "Member Management",
        "description": "Maintain member profiles, referral links, batch details, status, beneficiaries, and lifetime limit rules.",
    },
    {
        "icon": "bi-building",
        "title": "Contractor Management",
        "description": "Record contractors, company contacts, member referrers, and contractor batches used by project commissions.",
    },
    {
        "icon": "bi-diagram-3",
        "title": "Hierarchy and Ledger Tracking",
        "description": "View referral hierarchy, member downlines, and earning ledger transactions from generated sharing and payouts.",
    },
    {
        "icon": "bi-cash-stack",
        "title": "Project Commission and Sharing",
        "description": "Encode project billings, configure commission levels, preview sharing, and generate member ledger earnings.",
    },
    {
        "icon": "bi-wallet2",
        "title": "Payout Processing",
        "description": "Manage payout requests, Staff release submissions, Admin release approvals, and OMPD deductions.",
    },
    {
        "icon": "bi-file-earmark-text",
        "title": "Reports and PDF Export",
        "description": "Review project detail reports, commission summaries, fund release reports, and export key reports to PDF.",
    },
    {
        "icon": "bi-globe2",
        "title": "Public Site and Partner Registry",
        "description": "Publish ecosystem pages, partner profiles, and services contact content managed through Site Content.",
    },
    {
        "icon": "bi-shield-lock",
        "title": "Role-Based Access",
        "description": "Separate PortalAdmin, SiteAdmin, Admin, Staff, and Member permissions so users only see tools appropriate to their role.",
    },
    {
        "icon": "bi-file-earmark-spreadsheet",
        "title": "Excel Import Templates",
        "description": "Download generated blank templates for members and contractors, then import structured data with validation.",
    },
]

APP_PROCESS_FLOW = [
    {
        "title": "Set Up Users and Master Data",
        "description": "Admin creates users, Staff/Admin add members and contractors, and member accounts are linked to member records.",
    },
    {
        "title": "Publish Public Site Content",
        "description": "SiteAdmin or PortalAdmin updates landing copy, ecosystem pages, partner registry entries, and the services contact card.",
    },
    {
        "title": "Build the Referral Network",
        "description": "Member referrers and contractor referrers are recorded so hierarchy, commission paths, and ledger ownership are clear.",
    },
    {
        "title": "Encode Project Commissions",
        "description": "Staff/Admin adds the project, contractor, client referral, address, billing dates, and billing amounts.",
    },
    {
        "title": "Preview and Generate Sharing",
        "description": "Staff/Admin previews billings, then generates sharing. The system applies commission levels, per-project caps, and lifetime limit rules.",
    },
    {
        "title": "Record Ledger and POP Allocations",
        "description": "Generated sharing creates member ledger credits and redirects cap overflow to POP or the POP Lifetime Limit Fund.",
    },
    {
        "title": "Process Payouts",
        "description": "Members request payouts from My Ledger; Staff record releases; Admin approves requests and final releases.",
    },
    {
        "title": "Review Reports",
        "description": "Admin and authorized users review project reports, commission summaries, payout reports, and PDF exports for reconciliation.",
    },
]


MANUAL_ROLE_ORDER = [
    USER_ROLE_PORTAL_ADMIN,
    USER_ROLE_SITE_ADMIN,
    USER_ROLE_ADMIN,
    USER_ROLE_STAFF,
    USER_ROLE_MEMBER,
]


def list_manual_roles_for_viewer(viewer_role):
    normalized = normalize_role(viewer_role)
    if normalized == USER_ROLE_PORTAL_ADMIN:
        return list(MANUAL_ROLE_ORDER)
    if normalized == USER_ROLE_SITE_ADMIN:
        return [USER_ROLE_SITE_ADMIN]
    if normalized == USER_ROLE_ADMIN:
        return [USER_ROLE_ADMIN]
    if normalized == USER_ROLE_MEMBER:
        return [USER_ROLE_MEMBER]
    return [USER_ROLE_STAFF]


def resolve_user_manual(viewer_role, manual_role=None):
    allowed = list_manual_roles_for_viewer(viewer_role)
    target = normalize_role(manual_role) if manual_role else allowed[0]
    if target not in allowed:
        target = allowed[0]
    choices = [
        {"role": role_key, "title": USER_MANUALS[role_key]["title"]}
        for role_key in allowed
    ]
    return USER_MANUALS[target], target, choices


def get_portal_user_manual(role):
    """Return the portal help manual for the signed-in portal role only."""
    manual, _, _ = resolve_user_manual(role)
    return manual


def get_site_admin_user_manual():
    """Return the SiteAdmin manual. Intended only for SiteAdmin viewers."""
    return USER_MANUALS[USER_ROLE_SITE_ADMIN]
