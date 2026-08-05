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
        "summary": "Highest-privilege account for protected portal maintenance, manual review, and database purge actions.",
        "sections": [
            {
                "heading": "Main Responsibilities",
                "items": [
                    "Maintain the protected PortalAdmin account.",
                    "Use Delete All Members only when resetting demo or test data.",
                    "Review the portal as an Admin-level user when needed, including Products Commission under Income Management → Commission.",
                    "Delegate routine public website updates to SiteAdmin accounts.",
                    "Delegate daily portal encoding and payout work to Admin and Staff accounts.",
                ],
            },
            {
                "heading": "Help and Role Manuals",
                "items": [
                    "Open Help → User Manual to browse manuals for PortalAdmin, SiteAdmin, Admin, Staff, and Member.",
                    "Use the role tabs at the top of the manual page to switch between role guides.",
                    "Share the appropriate manual link or guidance with users when onboarding new accounts.",
                ],
            },
            {
                "heading": "Delete All Members",
                "items": [
                    "Open Administration → Admin Options → Delete All Members.",
                    "Read the confirmation prompt carefully before continuing.",
                    "Type DELETE ALL MEMBERS exactly when the system asks for confirmation.",
                    "This clears member-related records, including ledgers, payouts, sharing data, projects, contractors, and suppliers, then resets member, contractor, and supplier ID sequences.",
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
        "summary": "Manage the public TBGP landing site, ecosystem pages, partner registry, marketplace listings, and services contact card.",
        "sections": [
            {
                "heading": "Getting Started",
                "items": [
                    "Sign in with your SiteAdmin account to open the Site Content workspace at /site-admin.",
                    "Use the sidebar to move between overview, page editors, and registry tools.",
                    "On mobile, tap the hamburger menu in the top bar to open navigation.",
                    "Use View Site in the sidebar to preview the public website in a new tab.",
                    "Open Reading in the top bar to choose Standard, Large, or Extra large text and turn High contrast on or off.",
                    "When logged in, reading settings are saved to your account and follow you across devices.",
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
                "heading": "Marketplace Listings",
                "items": [
                    "Use Marketplace in the sidebar to add, edit, publish, or delete real property and products listings.",
                    "Set title, summary, details, price label, location, thumbnail, gallery images, and inquiry contact defaults.",
                    "Only Published listings appear on the public marketplace and landing carousel.",
                    "Edit Executive summaries on the Marketplace page to set the intro copy shown on each public category page.",
                    "When Supabase Storage is configured, upload thumbnail and gallery images; otherwise paste public image URLs.",
                    "Guest inquiries are interest-only (no online payment). Members share referral links and review attributed leads in My Marketplace.",
                    "Admin and PortalAdmin accounts can also open Marketplace Listings from the portal Administration menu.",
                    "Use Marketplace CRM to trace inquiries: filter by category, listing, date, and referrer; see who inquired and who referred them; open per-listing statistics; export CSV.",
                ],
            },
            {
                "heading": "Help and Account",
                "items": [
                    "Open User Manual in the sidebar for this guide.",
                    "Use Logout when finished. SiteAdmin accounts are for public site work, not daily portal encoding.",
                    "Coordinate with Admin or Staff when portal supplier or contractor records must be corrected before public profiles can sync.",
                ],
            },
        ],
    },
    USER_ROLE_ADMIN: {
        "title": "Admin User Manual",
        "summary": "Admin users manage accounts, members, contractors, suppliers, income workflows, payout approvals, and reports.",
        "sections": [
            {
                "heading": "Portal Navigation",
                "items": [
                    "Use the sidebar for Members, Member Ledger, Contractors, Suppliers, and Hierarchy Tree.",
                    "Open Payouts for payout scheme reference, payout queue actions, and fund release reports.",
                    "Open Income Management for project commissions, products commission, commission levels, generate project commission, and commission reports.",
                    "Open Administration → Admin Options for user management.",
                    "Open Administration → Site Content or Marketplace Listings to publish marketplace items and edit category executive summaries.",
                    "Open Help for this manual, Features & Process Flow, and About the Platform.",
                    "Use Home at the bottom of the sidebar to return to the public landing page.",
                    "Open Reading in the top bar to choose Standard, Large, or Extra large text and turn High contrast on or off.",
                ],
            },
            {
                "heading": "Dashboard",
                "items": [
                    "Use Dashboard for network-wide statistics on members, contractors, and suppliers.",
                    "Click any summary card to open the related Members, Contractors, or Suppliers list.",
                    "Review batch distribution, top referrers, and latest batch counts from the dashboard sections.",
                ],
            },
            {
                "heading": "Marketplace Listings",
                "items": [
                    "Use Administration → Marketplace Listings to create, edit, publish, or delete real property and products listings.",
                    "Published listings appear on the public marketplace pages and landing carousel.",
                    "Edit Executive summaries on the same page to control the intro copy on each marketplace category page.",
                    "Use Administration → Marketplace CRM to view inquiry statistics, search/filter leads, and see who inquired and which member referred them.",
                    "Open a listing from Marketplace CRM for per-item inquiry counts, referrer breakdown, and guest contact details. Export filtered results to CSV when needed.",
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
                "heading": "Member, Contractor, and Supplier Records",
                "items": [
                    "Use Members to add, edit, import, or review member profiles.",
                    "Use Contractors to add, edit, import, or review contractor records.",
                    "Use Suppliers to add, edit, import, or review supplier records.",
                    "Use the generated Excel templates when importing new records.",
                    "Set a member lifetime limit threshold from the Add/Edit Member form when needed.",
                    f"After the threshold, that member is limited to {MEMBER_LIFETIME_PROJECT_CAP_AFTER_LIMIT:,.2f} per project and excess goes to the POP Lifetime Limit Fund.",
                    "Members can update their own contact, employment, and beneficiary fields in My Information; Admin and Staff handle name, batch, referrer, status, and other membership fields.",
                    "Keep contractor and supplier company name and address accurate; linked public partner profiles sync from these records.",
                ],
            },
            {
                "heading": "Income Management",
                "items": [
                    "Use Income Management → Project Commission to record projects, contractors, client referrals, addresses, and billings.",
                    "Use Income Management → Products Commission to enter product commission amount, Ref-Seller, Ref-Buyer, and Ref-Buyer bonus carved from the PLATFORM share (65% gross). Auto-Bonus is 10% of commission (PLATFORM net 55%); AD-Bonus NN% is set by Admin (e.g. 34% bonus → PLATFORM net 31%).",
                    "Products Commission splits each amount into Ref-Seller 8%, Ref-Buyer 12%, POP 10%, AD-Fund 5%, and PLATFORM 65%; each Ref pool uses a 7-level upline table, with unallocated shares going to AD-Fund.",
                    "On Products Commission, optionally enter AD-Members Split Sharing amounts (members from Commission Management) charged against PLATFORM or AD-Fund; Update Computation refreshes the summary before save.",
                    "Use the Products Commission computation card to preview sharing before saving; saving posts member and PLATFORM ledger credits.",
                    "Use Commission Management to adjust project commission levels and maintain AD-Members Split Sharing (members eligible for Admin Discretion bonus).",
                    "Use Generate Project Commission to preview and generate profit sharing for billing dates.",
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
                    "Open Income Management for project commissions and generate project commission.",
                    "Open Help for this manual, Features & Process Flow, and About the Platform.",
                    "Open Reading in the top bar to choose Standard, Large, or Extra large text and turn High contrast on or off.",
                ],
            },
            {
                "heading": "Dashboard",
                "items": [
                    "Use Dashboard for network-wide statistics on members, contractors, and suppliers.",
                    "Click any summary card to open the related Members, Contractors, or Suppliers list.",
                ],
            },
            {
                "heading": "Daily Data Entry",
                "items": [
                    "Use Members to add, edit, and import member records.",
                    "Use Contractors to add, edit, and import contractor records.",
                    "Use Suppliers to add, edit, and import supplier records.",
                    "Check required fields before saving or importing records.",
                    "Staff cannot change Admin-only member lifetime limit controls.",
                    "Members update their own contact, employment, and beneficiary fields in My Information; Staff handles name, batch, referrer, status, and other membership fields.",
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
                "heading": "Generate Project Commission",
                "items": [
                    "Use Income Management → Generate Project Commission to preview available billings.",
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
        "summary": "Member users review their own profile, referrals, hierarchy, ledger, payout activity, and help resources.",
        "sections": [
            {
                "heading": "Portal Navigation",
                "items": [
                    "Use Dashboard for your member summary and earnings overview.",
                    "Use My Information, My Ledger, and My Hierarchy for your own records only.",
                    "Use My Member Referrals, My Contractors, and My Suppliers to review partners you referred.",
                    "Use My Marketplace to copy your share links and review guest inquiries attributed to you.",
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
                    "Click any summary card to open member referrals, downline, contractor/supplier referrals, profile, or ledger details.",
                    "If your account is not linked to a member record, contact the Admin or Staff.",
                ],
            },
            {
                "heading": "My Marketplace CRM",
                "items": [
                    "Open My Marketplace to copy your personal marketplace hub link and category links.",
                    "When a guest opens your /m/<code>/marketplace link, TBGP remembers you for about 30 days and credits inquiries to your CRM log.",
                    "Guests can browse listings and submit interest inquiries only; there is no online checkout in this version.",
                    "Review attributed guest name, contact details, listing, and message in the Inquiry CRM log.",
                ],
            },
            {
                "heading": "My Information",
                "items": [
                    "Use My Information to review and update your member profile.",
                    "Click Edit My Information to open the profile editor.",
                    "You can edit gender, civil status, phone, email, address, highest education, occupation or income source, monthly income, number of dependents, and beneficiary details.",
                    "Ask Staff or Admin to change your name, batch, referrer, status, or other membership records.",
                ],
            },
            {
                "heading": "My Referrals",
                "items": [
                    "Use My Member Referrals to view members you directly referred.",
                    "Use My Contractors to view contractor records linked to you as member referrer.",
                    "Use My Suppliers to view supplier records linked to you as member referrer.",
                    "You can also open these lists from the matching Dashboard summary cards.",
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
        "description": "Maintain member profiles, referral links, batch details, status, beneficiaries, lifetime limit rules, and member self-service profile updates.",
    },
    {
        "icon": "bi-building",
        "title": "Contractor Management",
        "description": "Record contractors, company contacts, member referrers, and contractor batches used by project commissions.",
    },
    {
        "icon": "bi-box-seam",
        "title": "Supplier Management",
        "description": "Record suppliers, company contacts, member referrers, and supplier batches linked to the public partner registry.",
    },
    {
        "icon": "bi-diagram-3",
        "title": "Hierarchy and Ledger Tracking",
        "description": "View referral hierarchy, member downlines, referral lists, and earning ledger transactions from generated sharing and payouts.",
    },
    {
        "icon": "bi-cash-stack",
        "title": "Project Commission and Sharing",
        "description": "Encode project billings, configure commission levels, preview sharing, and generate member ledger earnings.",
    },
    {
        "icon": "bi-box-seam",
        "title": "Products Commission",
        "description": "Admin entry for product commission with Ref-Seller/Ref-Buyer pools, Ref-Buyer PLATFORM bonuses, optional AD-Members split (from PLATFORM or AD-Fund), POP, AD-Fund, and 7-level Mandate sharing.",
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
        "description": "Publish ecosystem pages, partner profiles with image uploads, marketplace listings, and services contact content managed through Site Content.",
    },
    {
        "icon": "bi-shield-lock",
        "title": "Role-Based Access",
        "description": "Separate PortalAdmin, SiteAdmin, Admin, Staff, and Member permissions so users only see tools appropriate to their role.",
    },
    {
        "icon": "bi-shop",
        "title": "Marketplace and Member CRM",
        "description": "Public marketplace for property and products; members share referral links and review attributed guest inquiries.",
    },
    {
        "icon": "bi-file-earmark-spreadsheet",
        "title": "Excel Import Templates",
        "description": "Download generated blank templates for members, contractors, and suppliers, then import structured data with validation.",
    },
    {
        "icon": "bi-universal-access",
        "title": "Reading and Contrast Settings",
        "description": "Adjust text size and high-contrast mode from the Reading control; preferences sync to your account when logged in.",
    },
]

APP_PROCESS_FLOW = [
    {
        "title": "Set Up Users and Master Data",
        "description": "Admin creates users, Staff/Admin add members, contractors, and suppliers, and member accounts are linked to member records.",
    },
    {
        "title": "Publish Public Site Content",
        "description": "SiteAdmin, Admin, or PortalAdmin updates landing copy, ecosystem pages, partner registry, marketplace listings and executive summaries, and the services contact card.",
    },
    {
        "title": "Build the Referral Network",
        "description": "Member referrers and contractor or supplier referrers are recorded so hierarchy, commission paths, referral lists, and ledger ownership are clear.",
    },
    {
        "title": "Share Marketplace Links",
        "description": "Members copy personal marketplace links; guests browse listings and submit inquiries that are attributed to the referring member’s CRM log.",
    },
    {
        "title": "Encode Project Commissions",
        "description": "Staff/Admin adds the project, contractor, client referral, address, billing dates, and billing amounts.",
    },
    {
        "title": "Encode Products Commissions",
        "description": "Admin or PortalAdmin enters product commission amount, Ref-Seller, Ref-Buyer, Ref-Buyer bonus, and optional AD-Members split amounts; the system splits pools and posts 7-level sharing.",
    },
    {
        "title": "Preview and Generate Project Commission",
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


MARKETPLACE_CRM_GUIDE = {
    "title": "Marketplace & CRM Guide",
    "summary": (
        "Public inquiry marketplace for Real Property and Products, member share-link attribution, "
        "and Admin Marketplace CRM for tracing inquiries and referrers. No online checkout in this version."
    ),
    "overview": [
        "TBGP Marketplace is a public inquiry marketplace (interest only—no payment or cart).",
        "Categories: Real Property and Products.",
        "Site Admin / Admin / PortalAdmin publish listings and category executive summaries.",
        "Members share personal marketplace links; guests who inquire via those links are attributed to the member.",
        "Marketplace CRM lets Admin and Site Content editors search, filter, and review inquiry statistics.",
    ],
    "roles": [
        {"role": "Guest", "access": "Browse marketplace, open listings, submit inquiries."},
        {"role": "Member", "access": "Copy share links and review attributed inquiries in My Marketplace."},
        {
            "role": "Admin / PortalAdmin / SiteAdmin",
            "access": "Create and publish listings, edit executive summaries, use Marketplace CRM.",
        },
        {
            "role": "Staff",
            "access": "Read this guide for operational awareness; listing publish and CRM tools remain with Admin / Site Content editors.",
        },
    ],
    "modules": [
        {
            "title": "Public Marketplace",
            "items": [
                "Landing page carousel links to Real Property and Products.",
                "Each category page shows an executive summary plus a thumbnail grid of published listings.",
                "Listing detail shows basic information, gallery, and an inquiry form (name plus phone or email, and optional message).",
            ],
        },
        {
            "title": "Member Share & Attribution",
            "items": [
                "Each member receives a marketplace share code (created on first visit to My Marketplace).",
                "Share URLs use the form /m/<code>/marketplace/…",
                "Opening a share link sets a ~30-day attribution cookie (last share link visited wins).",
                "An inquiry is stored against the listing and credited to the attributed member when the cookie is present.",
            ],
        },
        {
            "title": "Listing Management",
            "items": [
                "Path: Site Content → Marketplace, or Administration → Marketplace Listings.",
                "Create, edit, publish, or delete listings (draft/published, price label, location, summary, body, images, contacts).",
                "Edit the Products page hero image (URL or upload) shown on /marketplace/products.",
                "Edit executive summaries (title and body) shown on each public category page.",
            ],
        },
        {
            "title": "Marketplace CRM (Admin)",
            "items": [
                "Path: Administration → Marketplace CRM (/admin/marketplace-crm).",
                "Overview: total inquiries, attributed vs direct, listings with leads, counts by category, top listings, top referrers.",
                "Inquiry log columns: who inquired, contact, listing, referred by, message.",
                "Filters: search, category, listing, has/no referrer, referrer member ID, date range.",
                "Per-listing page: item stats, referrer breakdown, and full guest list.",
                "Export CSV for the current filter set.",
            ],
        },
        {
            "title": "Member CRM (My Marketplace)",
            "items": [
                "Members copy hub and per-category share links.",
                "Inquiry log shows only leads attributed to that member.",
            ],
        },
    ],
    "process_flow": [
        {
            "title": "Publish listings",
            "description": "Admin or SiteAdmin creates and publishes Real Property or Products listings and optional executive summaries.",
        },
        {
            "title": "Listings go public",
            "description": "Published items appear on the landing marketplace carousel and category grids.",
        },
        {
            "title": "Guest browses or member shares",
            "description": "Guests open the public marketplace, or a member shares /m/<code>/marketplace/… so attribution is stored.",
        },
        {
            "title": "Guest submits inquiry",
            "description": "Inquiry is saved with guest details, listing, and optional attributed member.",
        },
        {
            "title": "CRM follow-up",
            "description": "Member sees the lead in My Marketplace; Admin reviews it in Marketplace CRM (stats, filters, export).",
        },
        {
            "title": "Offline sale (optional)",
            "description": "If a deal closes offline, staff may encode Products Commission manually using the CRM record as evidence. Inquiries do not auto-post commission.",
        },
    ],
    "urls": [
        {"label": "Landing marketplace", "path": "/#marketplace"},
        {"label": "Real Property", "path": "/marketplace/real_property"},
        {"label": "Products", "path": "/marketplace/products"},
        {"label": "Member share pattern", "path": "/m/<code>/marketplace/..."},
        {"label": "My Marketplace (members)", "path": "/my-marketplace"},
        {"label": "Manage listings", "path": "/site-admin/marketplace"},
        {"label": "Marketplace CRM", "path": "/admin/marketplace-crm"},
    ],
    "out_of_scope": [
        "Online payment or checkout",
        "Member-created listings",
        "Construction Sites category (retired)",
        "Automatic commission posting from an inquiry",
    ],
}


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
