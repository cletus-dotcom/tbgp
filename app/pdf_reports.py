from io import BytesIO
import re

from fpdf import FPDF


def _pdf_text(value):
    text = str(value or "")
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u20b1": "PHP ",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return re.sub(r"[^\x00-\xFF]", "?", text)


def _fmt_amount(value):
    return f"{float(value or 0):,.2f}"


class ReportPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 8, "TBGP ProF Sharing Report", ln=1)
        self.set_font("Helvetica", size=9)
        self.set_text_color(90, 90, 90)
        self.cell(0, 5, "Generated from TBGP Portal", ln=1)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")


def _ensure_page_space(pdf, height=12):
    if pdf.get_y() + height > pdf.page_break_trigger:
        pdf.add_page()


def _pdf_table_row(pdf, values, widths, height=6, aligns=None, bold=False, font_size=8):
    style = "B" if bold else ""
    pdf.set_font("Helvetica", style, font_size)
    if aligns is None:
        aligns = ["L"] * len(values)
    for value, width, align in zip(values, widths, aligns):
        pdf.cell(width, height, str(value), border=1, align=align)
    pdf.ln()


def _pdf_total_row(pdf, label, amount, widths, height=6, font_size=8):
    label_width = sum(widths[:-1])
    amount_width = widths[-1]
    pdf.set_font("Helvetica", "B", font_size)
    pdf.cell(label_width, height, label, border=1, align="R")
    pdf.cell(amount_width, height, amount, border=1, align="R")
    pdf.ln()


def _append_recipient_summary_pdf(pdf, recipient_summary):
    if not recipient_summary or not recipient_summary.get("rows"):
        return

    _ensure_page_space(pdf, 20)
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Summary by Member / Account", ln=1)
    pdf.set_font("Helvetica", size=8)
    pdf.cell(
        0,
        5,
        _pdf_text(f"{recipient_summary.get('account_count', 0)} recipient(s)"),
        ln=1,
    )
    pdf.ln(1)

    headers = ["Account", "ID", "Type", "Ref-Client", "Ref-Contr.", "Total"]
    widths = [48, 12, 22, 24, 24, 24]
    amount_aligns = ["L", "C", "L", "R", "R", "R"]
    _pdf_table_row(pdf, headers, widths, aligns=amount_aligns, bold=True, font_size=7)

    for row in recipient_summary["rows"]:
        _ensure_page_space(pdf, 8)
        values = [
            _pdf_text(row["account_name"][:30]),
            str(row["member_id"] or "-"),
            _pdf_text(row["account_type"][:14]),
            _fmt_amount(row["client_share"]),
            _fmt_amount(row["contractor_share"]),
            _fmt_amount(row["total_share"]),
        ]
        _pdf_table_row(pdf, values, widths, aligns=amount_aligns, font_size=7)

    _pdf_total_row(
        pdf,
        "GRAND TOTAL",
        _fmt_amount(recipient_summary.get("grand_total", 0)),
        widths,
        font_size=7,
    )


def build_project_report_pdf(report):
    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()

    project = report["project"]
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, _pdf_text(project["project_title"]), ln=1)
    pdf.set_font("Helvetica", size=10)
    if project.get("address"):
        pdf.cell(0, 5, _pdf_text(project["address"]), ln=1)
    pdf.cell(0, 5, f"Contractor: {_pdf_text(project.get('contractor_name', '-'))}", ln=1)
    pdf.cell(
        0,
        5,
        _pdf_text(f"Client referrer: {project.get('client_referrer_label', '-')}"),
        ln=1,
    )
    pdf.cell(
        0,
        5,
        _pdf_text(f"Contractor referrer: {project.get('contractor_referrer_label', '-')}"),
        ln=1,
    )
    pdf.ln(3)

    for generation in report["generations"]:
        _ensure_page_space(pdf, 24)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(
            0,
            6,
            _pdf_text(
                f"Billing {generation['billing_date']} - PHP {_fmt_amount(generation['billing_amount'])}"
            ),
            ln=1,
        )
        pdf.set_font("Helvetica", size=9)
        pdf.cell(0, 5, f"Generated: {generation['generated_at']}", ln=1)
        pdf.ln(1)

        headers = ["Scheme", "Recipient", "Account", "Lvl", "%", "Amount"]
        widths = [24, 52, 24, 12, 14, 24]
        row_aligns = ["L", "L", "L", "C", "R", "R"]
        _pdf_table_row(pdf, headers, widths, aligns=row_aligns, bold=True, font_size=8)

        for row in generation["entries"]:
            _ensure_page_space(pdf, 8)
            values = [
                _pdf_text(row["scheme_label"][:14]),
                _pdf_text((row["member_name"] or "-")[:28]),
                _pdf_text((row.get("account_type") or "-")[:12]),
                _pdf_text(row["level_label"]),
                f"{row['percentage']:.2f}",
                _fmt_amount(row["share_amount"]),
            ]
            _pdf_table_row(pdf, values, widths, aligns=row_aligns, font_size=8)

        _pdf_total_row(
            pdf,
            "Totals",
            _fmt_amount(generation["total_shared"]),
            widths,
            font_size=8,
        )
        pdf.ln(2)

    _append_recipient_summary_pdf(pdf, report.get("recipient_summary"))

    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer


def build_fund_release_pdf(rows, summary, filters=None):
    filters = filters or {}
    pdf = ReportPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Fund Release Report", ln=1)
    pdf.set_font("Helvetica", size=9)
    filter_bits = []
    if filters.get("date_from") or filters.get("date_to"):
        filter_bits.append(
            f"Period: {filters.get('date_from') or 'start'} to {filters.get('date_to') or 'present'}"
        )
    if filters.get("method"):
        filter_bits.append(f"Method: {filters['method']}")
    if filters.get("member_id"):
        filter_bits.append(f"Member ID: {filters['member_id']}")
    if filter_bits:
        pdf.cell(0, 5, _pdf_text(" | ".join(filter_bits)), ln=1)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Summary", ln=1)
    pdf.set_font("Helvetica", size=8)
    pdf.cell(0, 5, _pdf_text(
        f"Releases: {summary.get('release_count', 0)} | "
        f"Gross: {_fmt_amount(summary.get('total_gross', 0))} | "
        f"OMPD: {_fmt_amount(summary.get('total_ompd', 0))} | "
        f"Net: {_fmt_amount(summary.get('total_net_released', summary.get('total_released', 0)))}"
    ), ln=1)
    pdf.ln(2)

    widths = [16, 36, 18, 16, 18, 24, 30, 38, 24, 24]
    headers = [
        "Date/Time",
        "Member",
        "Gross",
        "OMPD",
        "Net",
        "Method",
        "Reference",
        "Account",
        "Submitted By",
        "Approved By",
    ]
    aligns = ["L", "L", "R", "R", "R", "L", "L", "L", "L", "L"]
    _pdf_table_row(pdf, headers, widths, aligns=aligns, bold=True, font_size=7)

    for row in rows:
        released = (row.get("released_at") or "")[:19].replace("T", " ")
        member_label = _pdf_text(f"#{row.get('member_id')} {row.get('member_name') or ''}")
        _pdf_table_row(
            pdf,
            [
                released,
                member_label,
                _fmt_amount(row.get("requested_amount")),
                _fmt_amount(row.get("ompd_deduction")),
                _fmt_amount(row.get("net_release_amount")),
                _pdf_text(row.get("release_method") or "—"),
                _pdf_text(row.get("release_reference") or "—"),
                _pdf_text(row.get("release_account_info") or "—"),
                _pdf_text(row.get("release_submitted_by") or "—"),
                _pdf_text(row.get("release_approved_by") or "—"),
            ],
            widths,
            aligns=aligns,
            font_size=7,
        )

    _pdf_total_row(
        pdf,
        "NET TOTAL",
        _fmt_amount(summary.get("total_net_released", summary.get("total_released", 0))),
        widths,
        font_size=7,
    )

    if summary.get("by_method"):
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "Summary by Method", ln=1)
        method_widths = [50, 25, 35]
        _pdf_table_row(pdf, ["Method", "Count", "Total"], method_widths, bold=True, aligns=["L", "R", "R"])
        for item in summary["by_method"]:
            _pdf_table_row(
                pdf,
                [
                    _pdf_text(item["method"]),
                    str(item["count"]),
                    _fmt_amount(item["total"]),
                ],
                method_widths,
                aligns=["L", "R", "R"],
            )

    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer


def _pdf_section_title(pdf, title, subtitle=None):
    _ensure_page_space(pdf, 16)
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, _pdf_text(title), ln=1)
    if subtitle:
        pdf.set_font("Helvetica", size=8)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(0, 4, _pdf_text(subtitle))
        pdf.set_text_color(0, 0, 0)
    pdf.ln(1)


def build_commission_summary_pdf(report):
    pdf = ReportPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "Commission Summary Report", ln=1)
    pdf.set_font("Helvetica", size=9)
    split = report["pool_split"]
    pdf.cell(
        0,
        5,
        _pdf_text(
            f"Pools: {split['client_percent']}% Ref-Client / "
            f"{split['contractor_percent']}% Ref-Contractor / "
            f"{split['admin_percent']}% PLATFORM"
        ),
        ln=1,
    )
    platform_breakdown = report.get("platform_breakdown") or {}
    if platform_breakdown:
        pdf.cell(
            0,
            5,
            _pdf_text(
                "PLATFORM split: "
                f"{platform_breakdown.get('founders_prerogative', 5)}% Founders / "
                f"{platform_breakdown.get('platform_ref_client', 12)}% Plat. Ref-Client / "
                f"{platform_breakdown.get('platform_ref_contractor', 8)}% Plat. Ref-Contractor / "
                f"{platform_breakdown.get('platform_pop', 10)}% Platform POP / "
                f"{platform_breakdown.get('platform_main', 65)}% PLATFORM"
            ),
            ln=1,
        )
    pdf.ln(2)

    # Project details
    project_details = report.get("project_details") or {}
    _pdf_section_title(
        pdf,
        "Project Details",
        "Generated commission projects with contractor and referrer assignments.",
    )
    proj_headers = ["Project", "Contractor", "Client Ref.", "Contr. Ref.", "Billings", "Commission"]
    proj_widths = [48, 32, 38, 38, 14, 24]
    proj_aligns = ["L", "L", "L", "L", "C", "R"]
    _pdf_table_row(pdf, proj_headers, proj_widths, aligns=proj_aligns, bold=True, font_size=7)
    for row in project_details.get("rows", []):
        _ensure_page_space(pdf, 8)
        _pdf_table_row(
            pdf,
            [
                _pdf_text(row["project_title"][:30]),
                _pdf_text((row.get("contractor_name") or "-")[:22]),
                _pdf_text((row.get("client_referrer_label") or "-")[:24]),
                _pdf_text((row.get("contractor_referrer_label") or "-")[:24]),
                str(row.get("billing_count", 0)),
                _fmt_amount(row.get("total_commission", 0)),
            ],
            proj_widths,
            aligns=proj_aligns,
            font_size=7,
        )

    # Ref-Client hierarchy
    client_hierarchy = report.get("client_hierarchy") or {}
    _pdf_section_title(
        pdf,
        "Ref-Client Hierarchy Details",
        "7-level upline chain from the project client referrer.",
    )
    hier_headers = ["Project", "Lvl", "Role", "%", "Member", "ID", "Account"]
    hier_widths = [36, 10, 34, 10, 40, 12, 18]
    hier_aligns = ["L", "C", "L", "R", "L", "C", "L"]
    _pdf_table_row(pdf, hier_headers, hier_widths, aligns=hier_aligns, bold=True, font_size=6)
    for row in client_hierarchy.get("rows", []):
        _ensure_page_space(pdf, 7)
        _pdf_table_row(
            pdf,
            [
                _pdf_text(row["project_title"][:22]),
                row["level_label"],
                _pdf_text((row.get("role_description") or "-")[:20]),
                f"{row['percentage']:.2f}",
                _pdf_text((row.get("member_name") or "-")[:24]),
                str(row.get("member_id") or "-"),
                _pdf_text((row.get("account_type") or "-")[:12]),
            ],
            hier_widths,
            aligns=hier_aligns,
            font_size=6,
        )

    # Ref-Contractor hierarchy
    contractor_hierarchy = report.get("contractor_hierarchy") or {}
    _pdf_section_title(
        pdf,
        "Ref-Contractor Hierarchy Details",
        "7-level upline chain from the contractor member referrer.",
    )
    _pdf_table_row(pdf, hier_headers, hier_widths, aligns=hier_aligns, bold=True, font_size=6)
    for row in contractor_hierarchy.get("rows", []):
        _ensure_page_space(pdf, 7)
        _pdf_table_row(
            pdf,
            [
                _pdf_text(row["project_title"][:22]),
                row["level_label"],
                _pdf_text((row.get("role_description") or "-")[:20]),
                f"{row['percentage']:.2f}",
                _pdf_text((row.get("member_name") or "-")[:24]),
                str(row.get("member_id") or "-"),
                _pdf_text((row.get("account_type") or "-")[:12]),
            ],
            hier_widths,
            aligns=hier_aligns,
            font_size=6,
        )

    # Table 1 — Main pools
    main = report["main_pools"]
    _pdf_section_title(
        pdf,
        "1. Main Commission Pools",
        "Total commission per project split into Ref-Client, Ref-Contractor, and PLATFORM pools.",
    )
    headers = ["Project", "Billings", "Commission", "Ref-Client", "Ref-Contr.", "PLATFORM"]
    widths = [58, 16, 28, 28, 28, 28]
    aligns = ["L", "C", "R", "R", "R", "R"]
    _pdf_table_row(pdf, headers, widths, aligns=aligns, bold=True, font_size=7)
    for row in main["rows"]:
        _ensure_page_space(pdf, 8)
        _pdf_table_row(
            pdf,
            [
                _pdf_text(row["project_title"][:32]),
                str(row["billing_count"]),
                _fmt_amount(row["total_commission"]),
                _fmt_amount(row["client_pool"]),
                _fmt_amount(row["contractor_pool"]),
                _fmt_amount(row["platform_pool"]),
            ],
            widths,
            aligns=aligns,
            font_size=7,
        )
    totals = main["totals"]
    _pdf_table_row(
        pdf,
        [
            f"TOTAL ({totals['project_count']} projects)",
            "",
            _fmt_amount(totals["total_commission"]),
            _fmt_amount(totals["client_pool"]),
            _fmt_amount(totals["contractor_pool"]),
            _fmt_amount(totals["platform_total"]),
        ],
        widths,
        aligns=aligns,
        bold=True,
        font_size=7,
    )

    # Table 2 — Ref-Client details
    client = report["client_details"]
    _pdf_section_title(
        pdf,
        "2. Ref-Client Sharing Details",
        _pdf_text(
            f"Member, Mandate account, and POP from the Ref-Client pool ({client.get('pool_percent', 50)}%). "
            f"Pool total: {_fmt_amount(client['total'])}."
        ),
    )
    headers = ["Project", "Billing", "Member", "ID", "Account", "Lvl", "%", "Amount"]
    widths = [40, 22, 38, 12, 18, 10, 12, 22]
    aligns = ["L", "C", "L", "C", "L", "C", "R", "R"]
    _pdf_table_row(pdf, headers, widths, aligns=aligns, bold=True, font_size=6)
    for row in client["rows"]:
        _ensure_page_space(pdf, 7)
        pct = "-" if row.get("is_pop_row") or row.get("percentage") is None else f"{row['percentage']:.2f}"
        member_label = row["member_name"]
        if row.get("is_pop_row"):
            member_label = f"POP: {member_label}"
        elif row.get("is_mandate_row"):
            member_label = f"Mandate: {member_label}"
        _pdf_table_row(
            pdf,
            [
                _pdf_text(row["project_title"][:24]),
                _pdf_text(str(row["billing_date"])[:10]),
                _pdf_text(member_label[:22]),
                str(row["member_id"] or "-"),
                _pdf_text(row["account_type"][:12]),
                row["level_label"],
                pct,
                _fmt_amount(row["share_amount"]),
            ],
            widths,
            aligns=aligns,
            font_size=6,
        )
    if client.get("member_total") is not None:
        _pdf_table_row(
            pdf,
            ["", "", "", "", "", "", "Members", _fmt_amount(client["member_total"])],
            widths,
            aligns=aligns,
            font_size=6,
        )
        _pdf_table_row(
            pdf,
            ["", "", "", "", "", "", "Mandate", _fmt_amount(client.get("mandate_total", 0))],
            widths,
            aligns=aligns,
            font_size=6,
        )
        _pdf_table_row(
            pdf,
            ["", "", "", "", "", "", "POP", _fmt_amount(client["pop_total"])],
            widths,
            aligns=aligns,
            font_size=6,
        )
        _pdf_table_row(
            pdf,
            ["", "", "", "", "", "", f"Pool ({client.get('pool_percent', 50)}%)", _fmt_amount(client["total"])],
            widths,
            aligns=aligns,
            bold=True,
            font_size=6,
        )

    # Table 3 — Ref-Contractor details
    contractor = report["contractor_details"]
    _pdf_section_title(
        pdf,
        "3. Ref-Contractor Sharing Details",
        _pdf_text(
            f"Member, Mandate account, and POP from the Ref-Contractor pool ({contractor.get('pool_percent', 25)}%). "
            f"Pool total: {_fmt_amount(contractor['total'])}."
        ),
    )
    _pdf_table_row(pdf, headers, widths, aligns=aligns, bold=True, font_size=6)
    for row in contractor["rows"]:
        _ensure_page_space(pdf, 7)
        pct = "-" if row.get("is_pop_row") or row.get("percentage") is None else f"{row['percentage']:.2f}"
        member_label = row["member_name"]
        if row.get("is_pop_row"):
            member_label = f"POP: {member_label}"
        elif row.get("is_mandate_row"):
            member_label = f"Mandate: {member_label}"
        _pdf_table_row(
            pdf,
            [
                _pdf_text(row["project_title"][:24]),
                _pdf_text(str(row["billing_date"])[:10]),
                _pdf_text(member_label[:22]),
                str(row["member_id"] or "-"),
                _pdf_text(row["account_type"][:12]),
                row["level_label"],
                pct,
                _fmt_amount(row["share_amount"]),
            ],
            widths,
            aligns=aligns,
            font_size=6,
        )
    if contractor.get("member_total") is not None:
        _pdf_table_row(
            pdf,
            ["", "", "", "", "", "", "Members", _fmt_amount(contractor["member_total"])],
            widths,
            aligns=aligns,
            font_size=6,
        )
        _pdf_table_row(
            pdf,
            ["", "", "", "", "", "", "Mandate", _fmt_amount(contractor.get("mandate_total", 0))],
            widths,
            aligns=aligns,
            font_size=6,
        )
        _pdf_table_row(
            pdf,
            ["", "", "", "", "", "", "POP", _fmt_amount(contractor["pop_total"])],
            widths,
            aligns=aligns,
            font_size=6,
        )
        _pdf_table_row(
            pdf,
            ["", "", "", "", "", "", f"Pool ({contractor.get('pool_percent', 25)}%)", _fmt_amount(contractor["total"])],
            widths,
            aligns=aligns,
            bold=True,
            font_size=6,
        )

    # Table 4 — PLATFORM breakdown
    platform = report["platform_details"]
    _pdf_section_title(
        pdf,
        "4. PLATFORM Pool Breakdown",
        "How each project's PLATFORM pool is split across sub-accounts.",
    )
    headers = [
        "Project",
        "Commission",
        "PLATFORM",
        "Founders",
        "Plat RC",
        "Plat RCon",
        "Plat POP",
        "PLATFORM",
    ]
    widths = [44, 22, 22, 22, 22, 22, 22, 22]
    aligns = ["L", "R", "R", "R", "R", "R", "R", "R"]
    _pdf_table_row(pdf, headers, widths, aligns=aligns, bold=True, font_size=7)
    for row in platform["rows"]:
        _ensure_page_space(pdf, 8)
        _pdf_table_row(
            pdf,
            [
                _pdf_text(row["project_title"][:28]),
                _fmt_amount(row["total_commission"]),
                _fmt_amount(row["platform_pool"]),
                _fmt_amount(row["platform_founders"]),
                _fmt_amount(row["platform_ref_client"]),
                _fmt_amount(row["platform_ref_contractor"]),
                _fmt_amount(row["platform_pop"]),
                _fmt_amount(row["platform_main"]),
            ],
            widths,
            aligns=aligns,
            font_size=7,
        )
    pt = platform["totals"]
    _pdf_table_row(
        pdf,
        [
            "TOTAL",
            "",
            _fmt_amount(pt["platform_pool"]),
            _fmt_amount(pt["platform_founders"]),
            _fmt_amount(pt["platform_ref_client"]),
            _fmt_amount(pt["platform_ref_contractor"]),
            _fmt_amount(pt["platform_pop"]),
            _fmt_amount(pt["platform_main"]),
        ],
        widths,
        aligns=aligns,
        bold=True,
        font_size=7,
    )

    # Table 5 — Member summary
    members = report["member_summary"]
    _pdf_section_title(
        pdf,
        "5. Member Earnings Summary",
        "Combined totals per member across all four MLM sharing streams.",
    )
    headers = ["Member", "ID", "Ref-Client", "Ref-Contr.", "Plat RC", "Plat RCon", "Total"]
    widths = [52, 12, 24, 24, 24, 24, 24]
    aligns = ["L", "C", "R", "R", "R", "R", "R"]
    _pdf_table_row(pdf, headers, widths, aligns=aligns, bold=True, font_size=7)
    for row in members["rows"]:
        _ensure_page_space(pdf, 8)
        _pdf_table_row(
            pdf,
            [
                _pdf_text(row["member_name"][:28]),
                str(row["member_id"] or "-"),
                _fmt_amount(row["ref_client"]),
                _fmt_amount(row["ref_contractor"]),
                _fmt_amount(row["platform_ref_client"]),
                _fmt_amount(row["platform_ref_contractor"]),
                _fmt_amount(row["total"]),
            ],
            widths,
            aligns=aligns,
            font_size=7,
        )
    ct = members["column_totals"]
    _pdf_table_row(
        pdf,
        [
            f"TOTAL ({members['member_count']} members)",
            "",
            _fmt_amount(ct["ref_client"]),
            _fmt_amount(ct["ref_contractor"]),
            _fmt_amount(ct["platform_ref_client"]),
            _fmt_amount(ct["platform_ref_contractor"]),
            _fmt_amount(ct["total"]),
        ],
        widths,
        aligns=aligns,
        bold=True,
        font_size=7,
    )

    # Table 6 — Mandate account
    mandate = report["mandate_account"]
    _pdf_section_title(
        pdf,
        "6. Mandate Account Summary",
        _pdf_text(
            f"Level 7 (6%) allocations credited to the {mandate.get('mandate_label', 'Mandate Account')}."
        ),
    )

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 6, "Mandate by sub-account", ln=1)
    mandate_src_headers = ["Sub-account", "Entries", "Amount"]
    mandate_src_widths = [140, 20, 30]
    mandate_src_aligns = ["L", "C", "R"]
    _pdf_table_row(pdf, mandate_src_headers, mandate_src_widths, aligns=mandate_src_aligns, bold=True, font_size=7)
    for row in mandate.get("by_source", []):
        _ensure_page_space(pdf, 8)
        _pdf_table_row(
            pdf,
            [
                _pdf_text(row["source_label"][:72]),
                str(row["entry_count"]),
                _fmt_amount(row["amount"]),
            ],
            mandate_src_widths,
            aligns=mandate_src_aligns,
            font_size=7,
        )
    _pdf_table_row(
        pdf,
        ["Total Mandate Account", "", _fmt_amount(mandate.get("source_total", 0))],
        mandate_src_widths,
        aligns=mandate_src_aligns,
        bold=True,
        font_size=7,
    )

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 6, "Mandate by project", ln=1)
    mandate_proj_headers = ["Project", "Ref-Client", "Ref-Contr.", "Plat RC", "Plat RCon", "Total"]
    mandate_proj_widths = [52, 24, 24, 24, 24, 24]
    mandate_proj_aligns = ["L", "R", "R", "R", "R", "R"]
    _pdf_table_row(pdf, mandate_proj_headers, mandate_proj_widths, aligns=mandate_proj_aligns, bold=True, font_size=7)
    for row in mandate.get("by_project", []):
        _ensure_page_space(pdf, 8)
        _pdf_table_row(
            pdf,
            [
                _pdf_text(row["project_title"][:32]),
                _fmt_amount(row["ref_client"]),
                _fmt_amount(row["ref_contractor"]),
                _fmt_amount(row["platform_ref_client"]),
                _fmt_amount(row["platform_ref_contractor"]),
                _fmt_amount(row["total"]),
            ],
            mandate_proj_widths,
            aligns=mandate_proj_aligns,
            font_size=7,
        )
    _pdf_table_row(
        pdf,
        ["Grand Total", "", "", "", "", _fmt_amount(mandate.get("project_total", 0))],
        mandate_proj_widths,
        aligns=mandate_proj_aligns,
        bold=True,
        font_size=7,
    )

    # Table 7 — POP & PLATFORM
    pop_platform = report["pop_and_platform"]
    pop_summary = pop_platform["pop_summary"]
    _pdf_section_title(
        pdf,
        "7. POP and PLATFORM Account Summary",
        "POP receipts by source; PLATFORM account credits (Founders + main share).",
    )

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 6, "POP by source", ln=1)
    pop_headers = ["Source", "Entries", "Amount"]
    pop_widths = [140, 20, 30]
    pop_aligns = ["L", "C", "R"]
    _pdf_table_row(pdf, pop_headers, pop_widths, aligns=pop_aligns, bold=True, font_size=7)
    for row in pop_summary["by_source"]:
        _ensure_page_space(pdf, 8)
        _pdf_table_row(
            pdf,
            [
                _pdf_text(row["source_label"][:72]),
                str(row["entry_count"]),
                _fmt_amount(row["amount"]),
            ],
            pop_widths,
            aligns=pop_aligns,
            font_size=7,
        )
    _pdf_table_row(
        pdf,
        ["Total POP", "", _fmt_amount(pop_summary["source_total"])],
        pop_widths,
        aligns=pop_aligns,
        bold=True,
        font_size=7,
    )

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 6, "PLATFORM account by project", ln=1)
    plat_headers = ["Project", "Founders (5%)", "PLATFORM (65%)", "Total"]
    plat_widths = [80, 40, 40, 30]
    plat_aligns = ["L", "R", "R", "R"]
    _pdf_table_row(pdf, plat_headers, plat_widths, aligns=plat_aligns, bold=True, font_size=7)
    for row in pop_platform["platform"]["by_project"]:
        _ensure_page_space(pdf, 8)
        _pdf_table_row(
            pdf,
            [
                _pdf_text(row["project_title"][:40]),
                _fmt_amount(row["founders"]),
                _fmt_amount(row["platform_main"]),
                _fmt_amount(row["total"]),
            ],
            plat_widths,
            aligns=plat_aligns,
            font_size=7,
        )
    _pdf_table_row(
        pdf,
        [
            "TOTAL",
            _fmt_amount(pop_platform["platform"]["founders_total"]),
            _fmt_amount(pop_platform["platform"]["platform_main_total"]),
            _fmt_amount(pop_platform["platform"]["grand_total"]),
        ],
        plat_widths,
        aligns=plat_aligns,
        bold=True,
        font_size=7,
    )

    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer
