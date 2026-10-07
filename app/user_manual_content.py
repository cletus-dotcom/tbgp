"""Role-based user manual and help content for the portal and site admin."""

from app.config import (
    MEMBER_LIFETIME_PROJECT_CAP_AFTER_LIMIT,
    PROJECT_DEFAULT_COMMISSION_PERCENT,
    PROJECT_REMINDER_DAYS,
    PROJECT_STALE_DAYS,
    PROJECT_STUCK_DAYS,
    PRODUCT_QUOTE_FOLLOWUP_DAYS,
    PRODUCT_STALE_DAYS,
    PRODUCT_STUCK_DAYS,
    PRODUCT_UNASSIGNED_DAYS,
    SANCTION_DEFAULT_DAYS,
    USER_ROLE_ADMIN,
    USER_ROLE_CONTRACTOR,
    USER_ROLE_MEMBER,
    USER_ROLE_PORTAL_ADMIN,
    USER_ROLE_SITE_ADMIN,
    USER_ROLE_STAFF,
    USER_ROLE_SUPPLIER,
    normalize_role,
)

PROJECT_SECTIONS = [
    {
        "heading": "Project Team and Duties",
        "items": [
            "Duties sit on top of the login role. Admin or Staff tick them per user in Manage Users; one person may hold several.",
            "Projects Manager (Staff/Admin): sees the Projects team workload card (open projects per person and slot), projects without a coordinator, missing estimators or site engineers, and status suggestions from field agents.",
            "Project Coordinator: owns projects from inquiry to turnover. Estimator / Quantity Surveyor: prepares costing and quotations. Site Engineer / Inspector: does oculars, inspections, and progress checks.",
            "Members may hold the Project Coordinator, Estimator, or Site Engineer duty as field agents; Projects Manager is for Staff and Admin only.",
            "On each project, the Project team panel has three pickers: Project coordinator, Estimator, and Site engineer. Each lists the users holding that duty; until somebody holds a duty, all Staff and Admin users are listed.",
            "Choosing the project coordinator also fills the Coordinator name (sheet) field. Coordinate this on the project page makes you the coordinator.",
            "When a user first gets the Project Coordinator duty, unassigned projects whose sheet coordinator name matches that user (e.g. 'Engr. Bruno' for Bruno Santos) are linked to them automatically. Imports link new rows the same way.",
            "Everyone on the team gets the project as New in their Projects badge (members: My Assignments) when assigned, and when a contractor or field agent reports progress, uploads a file, or posts a note.",
            "The project list filter Team member shows projects where the person holds any of the three slots; On my team shows yours.",
            "Dashboard cards follow your duties: My projects (coordinator) with attention reasons, My quotation queue (estimator), and My sites with your visits and delivery progress (site engineer). Admin always sees the manager cards.",
            "Duties only drive the pickers, notifications, and dashboards; they do not restrict what Staff and Admin can open or edit.",
        ],
    },
    {
        "heading": "Project Monitoring",
        "items": [
            "Open Projects in the sidebar (or the Projects tab in Transactions); the badge counts new web project inquiries and projects assigned to you.",
            "Project inquiries come from the public Request a project form (/projects/inquire, linked from Marketplace → Services) and get a PRJ reference no. (e.g. PRJ-0031).",
            "Track project / scope, location, project details, ProF, client representative, project coordinator, assigned contractor(s), action needed, and date completed.",
            "Pre-award statuses follow the PROJECTS sheet color legend: gray = Dead / terminated, blue = Quotation in process, green = For assignment of contractor, orange = On hold, yellow = For costing / quotation, fuchsia = Quotation submitted.",
            "After the quotation the project moves through the delivery statuses: Awarded / contract signed → Mobilization → Ongoing implementation → For turnover → Completed.",
            "The project list shows a progress bar for projects in delivery and a red flag when a project needs attention. Use the Needs attention tile to list only those projects.",
            "Admin can upload the monitoring workbook with type Project; the PROJECTS tab is imported automatically. Export Excel on the Projects tab downloads the projects layout.",
            "Every action on the Project delivery panel (stages, files, schedules, payments) and every contractor change is written to the project history.",
        ],
    },
    {
        "heading": "Project Delivery Stages and Progress",
        "items": [
            "Open a project and use the Stages & progress tab of the Project delivery panel.",
            "Set a target date for each stage (for quotation, quotation submitted, for contractor, awarded, mobilization, ongoing, turnover, completed).",
            "The reached date is filled in automatically when the project status changes to that stage; you can correct it by hand.",
            "Stages are colored: green = reached, amber = current (with days in the stage), red = target date passed but not reached.",
            "Enter the percent complete and a short site update under Implementation progress. Completing the project sets progress to 100%.",
        ],
    },
    {
        "heading": "Assigning the Contractor",
        "items": [
            "Open the project, pick a registered contractor in the Contractor list under Project team, and click Save. The contractor name is filled in and the change is written to the project history.",
            "The contractor's linked portal account then sees the project under My Projects and can view shared files and schedules, report progress, and upload site files.",
            "For a contractor not on the portal (or several contractors), type the name(s) in Assigned contractor(s) instead; they get no portal access.",
            "Choose — Not assigned — to remove the contractor; the portal access ends at once.",
            "Assigning a contractor does not change the status. Set the status yourself (e.g. Awarded / contract signed) and enter the contract amount in Contract & payments.",
        ],
    },
    {
        "heading": "Project Documents",
        "items": [
            "Use the Documents tab to attach the client layout, BOQ, plans, quotation, contract, site photos, and progress photos.",
            "Upload a file (PDF, images, Word, Excel, CSV, PowerPoint, DWG/DXF, or ZIP; up to 10 MB) or paste a Google Drive / Dropbox link.",
            "Tick Share with the contractor to let the assigned contractor open the file. Unshared files stay internal to TBGP staff.",
            "Files uploaded by the assigned contractor appear here automatically and are marked in the history.",
        ],
    },
    {
        "heading": "Site Visits and Meetings",
        "items": [
            "Use the Site visits & meetings tab to schedule an ocular / site visit, client meeting, or Zoom call with start, end, location, meeting link, and the person assigned (Staff, Admin, or a member field agent; defaults to the project's site engineer).",
            "Mark a schedule Done (with the outcome or minutes), Cancel it, or Reopen it. Past schedules not marked done are flagged as overdue.",
            "Click the calendar icon to download an .ics file; it adds the schedule to Google, Outlook, or phone calendars with a reminder one hour before.",
            "Open Project Calendar in the sidebar for a month view of all schedules; use Only mine to show the schedules assigned to you.",
            f"The dashboard lists schedules in the next {PROJECT_REMINDER_DAYS} days plus any past schedules not yet marked done.",
        ],
    },
    {
        "heading": "Contract, Payments, and Commission",
        "items": [
            "Use the Contract & payments tab to enter the contract amount, contract signed date, and the TBGP commission rate.",
            f"The commission rate is a percentage of each client payment (default {PROJECT_DEFAULT_COMMISSION_PERCENT}% when left blank).",
            "Add payment milestones one by one, or click Generate to create a downpayment / progress billing / final payment schedule from percentages such as 30, 40, 30.",
            "When a payment arrives, click Received and enter the date and OR / reference. You may override the commission amount for that payment.",
            "Click Post commission to add the commission as a billing in Income Management → Project Commission (one record per project, using the assigned contractor and the ProF as client referrer; direct inquiries use the admin member).",
            "Then run Income Management → Generate Project Commission for that billing date to share it (client ProF 50%, contractor's member referrer 25%, admin pool 25%).",
            "Use Unpost to remove a billing before sharing is generated. After sharing is generated, the billing is locked.",
            "Posting requires a contractor assigned from the Project team list (registered on the portal) with a member referrer.",
        ],
    },
    {
        "heading": "Overdue Alerts",
        "items": [
            f"A project needs attention when it has no update in {PROJECT_STALE_DAYS} days, has been in the same status for more than {PROJECT_STUCK_DAYS} days (On hold is excluded), or has a passed stage target, an overdue payment, or a past site visit not marked done.",
            "The dashboard card Projects needing attention lists the most urgent projects with the reasons; View all opens the filtered project list.",
            "Updating the project, logging a follow-up, or reaching the next stage clears the alert.",
        ],
    },
    {
        "heading": "Project Analytics",
        "items": [
            "Open Trends & Analysis → Projects for the project dashboard. Filter by request date range.",
            "Review total, open, won, and lost projects, the win rate (won ÷ won + terminated), average open aging, and won contract value.",
            "Pipeline by status shows how many projects are in each status; click a status to open the list.",
            "Average days per stage is computed from status changes in the project history.",
            "Workload per project coordinator and per contractor, projects by scope (grouped from the project name), and projects by location help balance assignments.",
        ],
    },
]

PRODUCT_SECTIONS = [
    {
        "heading": "Product Team and Duties",
        "items": [
            "Product inquiries (PRD reference nos.) have their own team, set per user in Manage Users under the Products duty group.",
            "Products Manager (Staff/Admin): sees the Products team workload card, product inquiries without an account officer, inquiries missing a sourcing, pricing, or logistics person, needs-attention counts, and status suggestions from sales agents.",
            "Account Officer / Sales Coordinator: owns the inquiry from first contact to closing; follows up the client and the quotation and moves the status.",
            "Sourcing / Purchasing Officer: finds suppliers, checks specs and stock, and gets supplier prices (For research and For costing / quotation).",
            "Pricing / Quotation Officer: prepares costing, margin, and the client quotation (For costing / quotation and Quotation in process).",
            "Logistics / Delivery Coordinator: schedules the delivery and collects the delivery receipt and proof of delivery (PO / order confirmed and For delivery).",
            "Sales Agent: a member (or staff) who follows up the client in the field and works the inquiry from My Assignments. Members may only hold Sales Agent among the product duties.",
            "On each product transaction, the Product team panel has pickers for Account officer, Sourcing officer, Pricing officer, Logistics coordinator, and Sales agent, plus the Supplier. Each person list shows the duty holders (Staff and Admin until somebody holds the duty; the Sales agent list stays empty until someone holds that duty).",
            "Take as account officer on the transaction page (or Take on the list) makes you the account officer.",
            "Everyone on the team gets the transaction as New when assigned, when the status changes, and when the sales agent or supplier posts a note or uploads a file.",
            "Dashboard cards follow your duties: My accounts, My sourcing queue, My pricing queue, My deliveries, and My product leads (sales agent). Admin always sees the products manager cards.",
        ],
    },
    {
        "heading": "Product Monitoring and Order Statuses",
        "items": [
            "Open Transactions → Products. The Team member filter shows inquiries where the person holds any product team slot; On my team shows yours; No account officer lists unowned inquiries.",
            "Pre-order statuses: New inquiry → For research → For costing / quotation → Quotation in process → Quotation submitted → For follow-up.",
            "After the client accepts, move the order through PO / order confirmed → For delivery → Delivered → Completed. On hold and Dead / terminated stay available.",
            "Set Scheduled delivery (under Follow-up) once the order is confirmed; the Order to delivery panel on the transaction page shows the current step and flags an overdue delivery.",
            "The Team / supplier column on the list shows the sourcing, pricing, logistics, and sales agent names, the supplier (Portal badge when registered), and the delivery date.",
        ],
    },
    {
        "heading": "Assigning the Supplier",
        "items": [
            "Pick a registered supplier in the Supplier list under Product team and click Save. The supplier name fills Assigned contractor / supplier and the change is written to the history.",
            "The supplier's linked portal account then sees the order under My Orders, can open files you shared, send updates, and upload supplier quotations, spec sheets, invoices, delivery receipts, proof of delivery, and photos.",
            "For a supplier not on the portal, type the name in Assigned contractor / supplier instead; they get no portal access.",
            "Choose — Not assigned — to remove the supplier; portal access ends at once.",
        ],
    },
    {
        "heading": "Product Documents",
        "items": [
            "Use Documents on the Product order panel to attach supplier quotations, the client quotation, the purchase order, spec sheets, supplier invoices, the delivery receipt (DR), proof of delivery, and photos (file up to 10 MB or a link).",
            "Tick Share with the supplier to let the assigned supplier open a file. Unshared files stay internal.",
            "Sales agents never see supplier quotations or supplier invoices, so supplier costs stay with the office team.",
            "Files uploaded by the supplier or the sales agent appear here automatically and are marked in the history.",
        ],
    },
    {
        "heading": "Product Alerts",
        "items": [
            f"A product transaction needs attention when it has no account officer after {PRODUCT_UNASSIGNED_DAYS} day(s), no update in {PRODUCT_STALE_DAYS} days, the same status for more than {PRODUCT_STUCK_DAYS} days (On hold and Quotation submitted excluded), or a quotation submitted more than {PRODUCT_QUOTE_FOLLOWUP_DAYS} days ago without an answer.",
            "Orders also get alerts when the scheduled delivery date passes before Delivered, when a confirmed order has no logistics coordinator or delivery date, and when the client's target date (Estimated date of implementation, if entered as a date such as 2026-10-15) has passed.",
            "Use the Needs attention tile on the Products list to show only those transactions; the reasons appear under each status and on the transaction page.",
        ],
    },
]

CONFIDENTIALITY_ITEMS = [
    "Only the approved TBGP ads may be posted publicly: the published marketplace listings and the share links on My Marketplace.",
    "Client names and contact details, project locations and addresses, project lists, documents, and transaction details are confidential. Never post or share them on social media, chat groups, or anywhere public, even with the listing.",
    "TBGP does not issue a project list for posting. My Ledger shows only reference numbers, and My Referred Projects and My Assignments are for your own follow-up.",
    "Violations lead to suspension from posting ads and endorsing contractors (Memorandum Order TBGP-51026-1); repeat violations get a more severe penalty.",
]

SUSPENSION_SECTION = {
    "heading": "Member Suspensions",
    "items": [
        "Open Suspensions in the sidebar (under Member Ledger) to see who is suspended; the badge counts active suspensions.",
        f"Admin issues a suspension: choose the member, enter the memorandum no. and reason, the start date, and the number of days (default {SANCTION_DEFAULT_DAYS}), and tick Posting ads and/or Endorsing contractors.",
        "Posting ads: the member's share links stop crediting inquiries to them, including links shared before the suspension, and My Marketplace hides their links. Guests can still browse and inquire.",
        "Endorsing contractors: the member cannot be set as the member referrer of a new contractor (form or Excel import), and project commissions created during the period credit the contractor endorsement to the admin member instead. Commission records created before the suspension keep their referrer.",
        "The member sees a red banner in the portal for the whole period. The suspension ends automatically after the last day; Admin can lift it early with a reason.",
        "Served and lifted suspensions stay in the violation history, so repeat violations are visible when deciding a penalty. Staff can view suspensions but only Admin can issue or lift them.",
    ],
}

AUDIT_LOG_SECTION = {
    "heading": "Audit Log",
    "items": [
        "Open Administration → Audit Log to trace who did what in the portal and the site-content area.",
        "Every sign-in (including failed attempts), logout, save, delete, upload, approval, import, and export is recorded automatically with the date and time (Manila), user, role, and IP address.",
        "Outcome shows Success, Failed (for example a validation error), or Denied (a user tried a page or action their role does not allow).",
        "Click the button on a row to see the submitted values and the saved changes: each record created, deleted, or updated with the old → new value of every changed field. Changes that were not saved (errors, rolled back) are not listed.",
        "Filter by date range, user, area (Members, Income, Payouts, Transactions, Site Content, Exports, and so on), outcome, IP address, record type and id, or search text; Export CSV downloads the filtered list.",
        "Passwords, password hashes, and security tokens are never recorded. Guest inquiry forms are logged without the guest's message or contact values.",
        "Entries cannot be edited or deleted from the portal.",
    ],
}

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
                    "Open Help → User Manual to browse manuals for PortalAdmin, SiteAdmin, Admin, Staff, Member, Contractor, and Supplier.",
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
                    "The purge is recorded in the Audit Log; audit entries themselves are kept.",
                ],
            },
            AUDIT_LOG_SECTION,
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
                    "Use Marketplace in the sidebar to add, edit, publish, or delete products, services, and real property listings.",
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
                "heading": "Approved Ads and Confidentiality",
                "items": [
                    "Published listings and gallery folders are the approved TBGP ads that members are allowed to share. Keep them generic.",
                    "Never include client names or contacts, exact project locations or addresses, project lists, signage or plate numbers in photos, documents, or transaction details. Use TBGP contact details only.",
                    "Staff can only save gallery folders as drafts. Review the drafts, then publish them yourself.",
                    "Every public page shows the TBGP disclaimer (program of the founding company, independent facilitators, payments only to the founding company).",
                ],
            },
            {
                "heading": "Audit Log",
                "items": [
                    "Open Audit Log in the sidebar to see the same full audit trail as Admin: sign-ins, user management, members, suspensions, income, payouts, transactions, notices, site content, and exports.",
                    "Set Area to Site content to trace changes to the public site (landing and ecosystem pages, contact card, partner registry, marketplace listings, and gallery folders, including Staff gallery drafts).",
                    "Click the button on a row to see the submitted values and the saved field changes (old → new). Failed and denied attempts are marked.",
                    "Filter by date, user, area, outcome, IP address, record, or search text, and export the filtered list to CSV. The audit log is read-only; you still cannot change portal records yourself.",
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
                    "Use the sidebar for Members, Member Ledger, Suspensions, Contractors, Suppliers, and Hierarchy Tree.",
                    "Open Payouts for payout scheme reference, payout queue actions, and fund release reports.",
                    "Open Income Management for project commissions, products commission, commission levels, generate project commission, and commission reports.",
                    "Open Administration → Admin Options for user management, and Administration → Audit Log to trace who changed what.",
                    "Open Transactions and Projects to monitor inquiries, product orders, and projects; open Project Calendar for site visits and meetings.",
                    "Open Trends & Analysis → Projects for pipeline, win rate, days per stage, and workload analytics.",
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
                    "The Projects needing attention and Site visits & meetings cards show overdue projects and upcoming schedules.",
                    "Admin always sees the Projects and Products team workload cards; personal duty cards appear for the duties you hold.",
                ],
            },
            {
                "heading": "Marketplace Listings",
                "items": [
                    "Use Administration → Marketplace Listings to create, edit, publish, or delete products, services, and real property listings.",
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
                    "Assign only the role a user needs: Admin, Staff, Member, Supplier, or Contractor.",
                    "Link Member users to their correct Member ID so they can access their own portal.",
                    "For Contractor users, choose the Linked contractor record so the contractor sees the projects assigned to that company under My Projects.",
                    "For Supplier users, choose the Linked supplier record so the supplier sees the product orders assigned to that company under My Orders.",
                    "Tick duties for Staff, Admin, or Member users; the Duties column lists them. Projects group: Projects Manager, Project Coordinator, Estimator / Quantity Surveyor, Site Engineer / Inspector. Products group: Products Manager, Account Officer / Sales Coordinator, Sourcing / Purchasing Officer, Pricing / Quotation Officer, Logistics / Delivery Coordinator, Sales Agent.",
                    "Members may hold the project field duties (coordinator, estimator, site engineer) and Sales Agent; manager and office product duties are for Staff and Admin. See Project Team and Duties and Product Team and Duties.",
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
                    "Project commission billings can also be posted from a monitored project's Contract & payments tab when the client pays; they appear under Project Commission for the usual sharing run.",
                ],
            },
            *PROJECT_SECTIONS,
            *PRODUCT_SECTIONS,
            SUSPENSION_SECTION,
            AUDIT_LOG_SECTION,
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
                    "Use the sidebar for Members, Member Ledger, Suspensions, Contractors, Suppliers, Hierarchy Tree, and My Marketplace.",
                    "Open Administration → Marketplace CRM to review all guest inquiries and update follow-up status.",
                    "Open Transactions and Projects to monitor inquiries, product orders, and projects; open Project Calendar for site visits and meetings.",
                    "Open Trends & Analysis → Projects for project pipeline, win rate, and workload analytics.",
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
                    "The Projects needing attention card lists overdue projects with the reasons; the Site visits & meetings card lists upcoming schedules assigned to you or unassigned.",
                    "If you hold project duties, cards for them appear above: team workload (Projects Manager), My projects (coordinator), My quotation queue (estimator), and My sites (site engineer).",
                    "Product duties add their own cards: Products team workload (Products Manager), My accounts (account officer), My sourcing queue, My pricing queue, My deliveries (logistics), and My product leads (sales agent).",
                ],
            },
            {
                "heading": "Marketplace CRM",
                "items": [
                    "Open Administration → Marketplace CRM to review inquiries by category, listing, referrer, and date.",
                    "Open Transactions in the sidebar to monitor every inquiry: the badge counts new unassigned web inquiries and transactions assigned to you.",
                    "Each transaction has a reference no. (e.g. PRD-0077); take it with Take / Assign to me, then call or email the client and ProF from the transaction page.",
                    "Update the status (New inquiry, For research, For costing / quotation, Quotation in process, Quotation submitted, For follow-up, For assignment of contractor, On hold, Completed, Dead / terminated) plus action needed, coordinator, contractor, and remarks.",
                    "Product transactions also have the order statuses PO / order confirmed, For delivery, and Delivered, plus the product team and supplier; see Product Monitoring and Order Statuses.",
                    "Every change and every logged call, email, or note is kept in the transaction history; Aging counts days since the request date.",
                    "Export Excel downloads the monitoring-sheet layout; Admin can upload the color-coded monitoring sheet to import or update transactions.",
                    "Staff can update transactions but cannot publish marketplace listings; ask Admin or SiteAdmin for listing changes.",
                    "Staff can prepare Gallery Folders as drafts; a SiteAdmin or Admin reviews and publishes them. Never put client names, exact locations, signage, or documents in public photos or captions.",
                ],
            },
            *PROJECT_SECTIONS,
            *PRODUCT_SECTIONS,
            SUSPENSION_SECTION,
            {
                "heading": "My Marketplace",
                "items": [
                    "Open My Marketplace to copy your personal marketplace hub link and category links.",
                    "Your Staff account must be linked to a Member ID (set by Admin under Users) so share links attribute inquiries to you.",
                    "When a guest opens your /m/<code>/marketplace link, TBGP remembers you for about 30 days and credits inquiries to your CRM log.",
                    "Review attributed guest name, contact details, listing, follow-up status, and message in the Inquiry CRM log.",
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
                "heading": "Confidentiality and Approved Ads",
                "items": [
                    *CONFIDENTIALITY_ITEMS,
                    "If you are suspended, a red banner shows the period and what you may not do. During a suspension from posting ads your share links do not credit inquiries to you; during a suspension from endorsing contractors you cannot be named as a contractor's member referrer.",
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
                "heading": "My Referred Projects",
                "items": [
                    "Share your project inquiry link from My Marketplace; clients who request a project through it are credited to you as ProF.",
                    "Open My Referred Projects in the sidebar (or the Referred Projects card on the Dashboard) to see each project you referred.",
                    "Each row shows the PRJ reference no., project, client, request date, current status (from quotation to awarded, mobilization, ongoing, turnover, and completed), percent complete, and the assigned contractor.",
                    "Project commission from client payments is shared to your ledger after TBGP posts the billing and generates sharing; check My Ledger for the credits.",
                ],
            },
            {
                "heading": "My Assignments (project field agents)",
                "items": [
                    "TBGP may give your account a project duty (Project Coordinator, Estimator / Quantity Surveyor, or Site Engineer / Inspector). My Assignments then appears in the sidebar; its badge counts projects new or updated for you.",
                    "The list shows every project where you are on the team, your role, status, progress, and the coordinator, plus your upcoming site visits and meetings.",
                    "Open a project for the client contact, scope, project team, stage plan, schedules, files, and recent activity. Contract documents and payments stay with TBGP staff.",
                    "Post a site note, report percent complete, or upload site photos, plans, BOQ, or quotations; the project team is notified.",
                    "Mark your own site visits and meetings Done with the outcome; use the calendar icon to add them to your phone calendar.",
                    "Use Suggest a status change when the project should move on (e.g. quotation sent); the coordinator reviews it and updates the status.",
                    "Your Dashboard shows cards for your duties: projects you coordinate, your quotation queue, or your sites.",
                ],
            },
            {
                "heading": "My Assignments (sales agents)",
                "items": [
                    "TBGP may give your account the Sales Agent duty. My Assignments then lists Product inquiries assigned to you above any projects.",
                    "Each row shows the PRD reference no., product, client, status, scheduled delivery, and the TBGP account officer.",
                    "Open an inquiry for the client contact, quantity, specifications, the product team, client-facing files, and recent activity. Supplier quotations and supplier invoices stay with TBGP staff.",
                    "Post a client note after each visit or call, and upload photos, the client quotation, a PO, spec sheets, or delivery documents; the product team is notified.",
                    "Use Suggest a status change when the inquiry should move on (e.g. the client approved the quotation); the account officer reviews it and updates the status.",
                    "Your Dashboard shows My product leads (sales agent) with any alerts on your inquiries.",
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
                    "Use My Ledger to review earning transactions, payout deductions, and your payout request history. Project credits show the reference no. (e.g. PRJ-0012) or project no., not the project name.",
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
    USER_ROLE_CONTRACTOR: {
        "title": "Contractor User Manual",
        "summary": "Contractor users follow the projects TBGP assigns to their company, report progress, and upload site files.",
        "sections": [
            {
                "heading": "Getting Started",
                "items": [
                    "Sign in with the contractor account TBGP created for your company. The account must be linked to your contractor record; if My Projects says it is not linked, contact the TBGP administrator.",
                    "Use Dashboard for a summary: all projects, active projects to report on, completed projects, and upcoming site visits.",
                    "Use My Projects in the sidebar to open the full list.",
                    "Open Reading in the top bar to choose Standard, Large, or Extra large text and turn High contrast on or off.",
                ],
            },
            {
                "heading": "Assigned Projects",
                "items": [
                    "TBGP staff assign the contractor for each project. When your company is assigned, the project appears in My Projects with its status (for example Awarded, Mobilization, Ongoing implementation, For turnover, Completed).",
                    "Open the project to read the scope and download the files TBGP shared with you (layout, BOQ, plans, site photos).",
                    "Use Report progress to enter the percent complete and a site update; TBGP sees it in the project history.",
                    "Upload progress photos, site photos, plans, or BOQ revisions under Project files (up to 10 MB, or paste a link).",
                    "Review delivery stage target dates and the site visit / meeting schedule; download a schedule to your calendar with the calendar icon.",
                ],
            },
            {
                "heading": "Access Notes",
                "items": [
                    "You only see projects TBGP assigned to your company. Client contact details, internal files, and payment records stay with TBGP.",
                    "If TBGP removes your company from a project, it leaves your list.",
                ],
            },
        ],
    },
    USER_ROLE_SUPPLIER: {
        "title": "Supplier User Manual",
        "summary": "Supplier users follow the product orders TBGP assigns to their company, send updates, and upload quotations and delivery documents.",
        "sections": [
            {
                "heading": "Getting Started",
                "items": [
                    "Sign in with the supplier account TBGP created for your company. The account must be linked to your supplier record; if My Orders says it is not linked, contact the TBGP administrator.",
                    "Use Dashboard for a summary: all orders, active orders, orders for delivery, and deliveries past their scheduled date.",
                    "Use My Orders in the sidebar to open the full list.",
                    "Open Reading in the top bar to choose Standard, Large, or Extra large text and turn High contrast on or off.",
                ],
            },
            {
                "heading": "Assigned Orders",
                "items": [
                    "TBGP staff assign the supplier for each product order. When your company is assigned, the order appears in My Orders with its quantity, delivery location, status (for example For costing / quotation, PO / order confirmed, For delivery, Delivered), and scheduled delivery date.",
                    "Open the order to read the quantity and specifications and download the files TBGP shared with you (for example the purchase order).",
                    "Use Send an update for price and availability, lead time, dispatch, or delivery issues; the TBGP product team is notified.",
                    "Upload your quotation, spec sheets or catalog, invoice, delivery receipt (DR), proof of delivery, or photos under Order files (up to 10 MB, or paste a link).",
                ],
            },
            {
                "heading": "Access Notes",
                "items": [
                    "You only see orders TBGP assigned to your company. Client contact details, internal files, and TBGP pricing stay with TBGP.",
                    "If TBGP removes your company from an order, it leaves your list.",
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
        "description": "Separate PortalAdmin, SiteAdmin, Admin, Staff, Member, Contractor, and Supplier permissions so users only see tools appropriate to their role.",
    },
    {
        "icon": "bi-shop",
        "title": "Marketplace and Member CRM",
        "description": "Public marketplace for property and products; members share referral links and review attributed guest inquiries.",
    },
    {
        "icon": "bi-cone-striped",
        "title": "Project Delivery Tracking",
        "description": "Monitor projects from inquiry to turnover: stage targets and aging, staff-assigned contractors, documents, site visits and meetings calendar, contract payments with commission posting, overdue alerts, and project analytics.",
    },
    {
        "icon": "bi-building-gear",
        "title": "Contractor and ProF Project Portals",
        "description": "Contractors see the projects assigned to them, report progress, and upload site files; ProF members follow the status of projects they referred; member field agents work their assigned projects under My Assignments.",
    },
    {
        "icon": "bi-people",
        "title": "Project Team Duties",
        "description": "Projects Manager, Project Coordinator, Estimator, and Site Engineer duties on Staff and Member accounts drive the project team pickers, notifications, and duty dashboards.",
    },
    {
        "icon": "bi-truck",
        "title": "Product Order Tracking",
        "description": "Product inquiries get their own team (Products Manager, Account Officer, Sourcing, Pricing, Logistics, Sales Agent), order-to-delivery statuses with a scheduled delivery date, product documents, needs-attention alerts, and duty dashboards.",
    },
    {
        "icon": "bi-box-seam",
        "title": "Supplier Order Portal",
        "description": "Registered suppliers assigned to a product order see it under My Orders, send updates, and upload quotations, invoices, delivery receipts, and proof of delivery.",
    },
    {
        "icon": "bi-slash-circle",
        "title": "Confidentiality and Member Suspensions",
        "description": "Only approved TBGP ads are shareable: members' ledgers show reference numbers instead of project names, member pages carry a confidentiality reminder, and Admin can suspend a member from posting ads and endorsing contractors for a set period with a violation history.",
    },
    {
        "icon": "bi-journal-check",
        "title": "Audit Log",
        "description": "Every sign-in, save, delete, upload, and export is recorded with the user, IP address, outcome, and field-level old → new changes; Admin and SiteAdmin can trace the full trail with filters and CSV export.",
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
        "title": "Track Product Orders to Delivery",
        "description": "The products manager staffs each product inquiry with an account officer, sourcing and pricing officers, a logistics coordinator, and optionally a member sales agent; the team sources and quotes, assigns the supplier, confirms the order, schedules and confirms delivery, and closes it. Supplier and sales agent updates reach the team automatically.",
    },
    {
        "title": "Track Projects to Completion",
        "description": "The projects manager staffs each project with a coordinator, estimator, and site engineer; the team quotes the project, assigns the contractor, schedules site visits, and follows stages and progress. Client payments post commission billings to Project Commission.",
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
        "Public inquiry marketplace for Products, Services, and Real Property, member share-link attribution, "
        "and Admin Marketplace CRM for tracing inquiries and referrers. No online checkout in this version."
    ),
    "overview": [
        "TBGP Marketplace is a public inquiry marketplace (interest only—no payment or cart).",
        "Categories: Products, Services, and Real Property (in that order on the landing page).",
        "Site Admin / Admin / PortalAdmin publish listings and category executive summaries.",
        "Members share personal marketplace links; guests who inquire via those links are attributed to the member.",
        "Marketplace CRM lets Admin and Site Content editors search, filter, and review inquiry statistics.",
    ],
    "roles": [
        {"role": "Guest", "access": "Browse marketplace, open listings, submit inquiries."},
        {"role": "Member", "access": "Copy share links and review attributed inquiries in My Marketplace."},
        {
            "role": "Staff",
            "access": "Open Marketplace CRM to review inquiries and update follow-up status; use My Marketplace when linked to a Member ID. Listing publish remains with Admin / Site Content editors.",
        },
        {
            "role": "Admin / PortalAdmin / SiteAdmin",
            "access": "Create and publish listings, edit executive summaries, use Marketplace CRM (including status updates).",
        },
    ],
    "modules": [
        {
            "title": "Public Marketplace",
            "items": [
                "Landing page carousel links to Products, Services, then Real Property.",
                "Each category page shows an executive summary plus a thumbnail grid of published listings.",
                "Listing detail shows basic information, gallery, and an inquiry form (full name, email, and contact number required; company, qty, specifications, delivery location, needed-by date, and message optional).",
            ],
        },
        {
            "title": "Member Share & Attribution",
            "items": [
                "Each member (and Staff linked to a Member ID) receives a marketplace share code on first visit to My Marketplace.",
                "Share URLs use the form /m/<code>/marketplace/…; the project inquiry form link is /m/<code>/projects/inquire.",
                "Each inquiry becomes a transaction with a reference no. and starts as New inquiry; Admin and Staff are notified in the sidebar and dashboard.",
                "Staff and Admin follow up in Transactions (status, action needed, assignment, coordinator, contractor, remarks).",
                "Aging shows days since the request date; History is a ledger of status changes, calls, emails, and notes.",
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
        {"label": "My Marketplace (members / staff)", "path": "/my-marketplace"},
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
    USER_ROLE_CONTRACTOR,
    USER_ROLE_SUPPLIER,
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
    if normalized == USER_ROLE_CONTRACTOR:
        return [USER_ROLE_CONTRACTOR]
    if normalized == USER_ROLE_SUPPLIER:
        return [USER_ROLE_SUPPLIER]
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
