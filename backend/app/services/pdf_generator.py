"""Pay slip PDF generator using ReportLab.

Generates A4 pay slip PDFs with Slovak payroll layout including:
- Company (tenant) header
- Employee details
- Gross wage breakdown
- Social insurance (SP) contributions — employee + employer
- Health insurance (ZP) contributions — employee + employer
- Tax computation details
- Net wage summary

All functions are synchronous (def, not async def) per DESIGN.md.
"""

import logging
import os
from decimal import Decimal
from io import BytesIO
from pathlib import Path

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
except ImportError:
    # reportlab is optional at import time — functions that need it will fail
    # at call time with a clear error.
    colors = None  # type: ignore[assignment]
    A4 = None  # type: ignore[assignment]
    ParagraphStyle = None  # type: ignore[assignment,misc]
    getSampleStyleSheet = None  # type: ignore[assignment]
    cm = None  # type: ignore[assignment]
    mm = None  # type: ignore[assignment]
    Paragraph = None  # type: ignore[assignment,misc]
    SimpleDocTemplate = None  # type: ignore[assignment,misc]
    Spacer = None  # type: ignore[assignment,misc]
    Table = None  # type: ignore[assignment,misc]
    TableStyle = None  # type: ignore[assignment,misc]

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Slovak month names
# ---------------------------------------------------------------------------
MONTH_NAMES_SK = {
    1: "Január",
    2: "Február",
    3: "Marec",
    4: "Apríl",
    5: "Máj",
    6: "Jún",
    7: "Júl",
    8: "August",
    9: "September",
    10: "Október",
    11: "November",
    12: "December",
}

# ---------------------------------------------------------------------------
# PDF base path
# ---------------------------------------------------------------------------
PDF_BASE_PATH = settings.pdf_base_path


def _fmt(value: Decimal | None) -> str:
    """Format a Decimal as a string with 2 decimal places and € suffix."""
    if value is None:
        return "0.00 €"
    return f"{value:,.2f} €".replace(",", " ")


def _fmt_no_eur(value: Decimal | None) -> str:
    """Format a Decimal as a string with 2 decimal places, no currency."""
    if value is None:
        return "0.00"
    return f"{value:,.2f}".replace(",", " ")


# ---------------------------------------------------------------------------
# Dataclass-like container for PDF input data
# ---------------------------------------------------------------------------


class PaySlipData:
    """Container for all data needed to render a pay slip PDF.

    Populated from Payroll + Employee + Tenant ORM instances.
    """

    def __init__(
        self,
        *,
        # Tenant (company) info
        company_name: str,
        company_ico: str,
        company_dic: str | None = None,
        company_address: str,
        # Employee info
        employee_name: str,
        employee_number: str,
        employee_birth_date: str,
        employee_address: str,
        # Period
        period_year: int,
        period_month: int,
        # Gross components
        base_wage: Decimal,
        overtime_hours: Decimal,
        overtime_amount: Decimal,
        bonus_amount: Decimal,
        supplement_amount: Decimal,
        gross_wage: Decimal,
        # SP employee
        sp_assessment_base: Decimal,
        sp_nemocenske: Decimal,
        sp_starobne: Decimal,
        sp_invalidne: Decimal,
        sp_nezamestnanost: Decimal,
        sp_employee_total: Decimal,
        # ZP employee
        zp_assessment_base: Decimal,
        zp_employee: Decimal,
        # Tax
        partial_tax_base: Decimal,
        nczd_applied: Decimal,
        tax_base: Decimal,
        tax_advance: Decimal,
        child_bonus: Decimal,
        tax_after_bonus: Decimal,
        # Net
        net_wage: Decimal,
        # SP employer
        sp_employer_total: Decimal,
        # ZP employer
        zp_employer: Decimal,
        # Total employer cost
        total_employer_cost: Decimal,
        # Pillar 2
        pillar2_amount: Decimal,
    ):
        self.company_name = company_name
        self.company_ico = company_ico
        self.company_dic = company_dic
        self.company_address = company_address
        self.employee_name = employee_name
        self.employee_number = employee_number
        self.employee_birth_date = employee_birth_date
        self.employee_address = employee_address
        self.period_year = period_year
        self.period_month = period_month
        self.base_wage = base_wage
        self.overtime_hours = overtime_hours
        self.overtime_amount = overtime_amount
        self.bonus_amount = bonus_amount
        self.supplement_amount = supplement_amount
        self.gross_wage = gross_wage
        self.sp_assessment_base = sp_assessment_base
        self.sp_nemocenske = sp_nemocenske
        self.sp_starobne = sp_starobne
        self.sp_invalidne = sp_invalidne
        self.sp_nezamestnanost = sp_nezamestnanost
        self.sp_employee_total = sp_employee_total
        self.zp_assessment_base = zp_assessment_base
        self.zp_employee = zp_employee
        self.partial_tax_base = partial_tax_base
        self.nczd_applied = nczd_applied
        self.tax_base = tax_base
        self.tax_advance = tax_advance
        self.child_bonus = child_bonus
        self.tax_after_bonus = tax_after_bonus
        self.net_wage = net_wage
        self.sp_employer_total = sp_employer_total
        self.zp_employer = zp_employer
        self.total_employer_cost = total_employer_cost
        self.pillar2_amount = pillar2_amount


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

_HEADER_BG = colors.HexColor("#2563EB")
_SECTION_BG = colors.HexColor("#EFF6FF")
_NET_BG = colors.HexColor("#DCFCE7")
_BORDER_COLOR = colors.HexColor("#D1D5DB")


def _get_styles():
    """Return custom paragraph styles for the pay slip."""
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "SlipTitle",
            parent=styles["Heading1"],
            fontSize=16,
            spaceAfter=6,
            textColor=colors.HexColor("#1E3A5F"),
        )
    )
    styles.add(
        ParagraphStyle(
            "SectionHeader",
            parent=styles["Heading2"],
            fontSize=11,
            spaceBefore=8,
            spaceAfter=4,
            textColor=colors.HexColor("#1E40AF"),
        )
    )
    styles.add(
        ParagraphStyle(
            "SmallText",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#6B7280"),
        )
    )
    return styles


# ---------------------------------------------------------------------------
# Table style helpers
# ---------------------------------------------------------------------------


def _data_table_style(row_count: int) -> TableStyle:
    """Standard data table style with alternating rows."""
    style_commands = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    # Alternating row background
    for i in range(1, row_count):
        if i % 2 == 0:
            style_commands.append(("BACKGROUND", (0, i), (-1, i), _SECTION_BG))

    return TableStyle(style_commands)


def _summary_table_style() -> TableStyle:
    """Style for the net wage summary table."""
    return TableStyle(
        [
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 12),
            ("BACKGROUND", (0, 0), (-1, -1), _NET_BG),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#16A34A")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]
    )


# ---------------------------------------------------------------------------
# PDF builder
# ---------------------------------------------------------------------------


def build_pay_slip_pdf(data: PaySlipData) -> bytes:
    """Generate a pay slip PDF and return the raw bytes.

    Uses ReportLab platypus for layout. The result is a complete PDF
    ready to be written to disk or streamed as an HTTP response.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
    )

    styles = _get_styles()
    elements: list = []

    period_label = f"{MONTH_NAMES_SK.get(data.period_month, str(data.period_month))} {data.period_year}"

    # -- Title --
    elements.append(Paragraph(f"Výplatná páska — {period_label}", styles["SlipTitle"]))
    elements.append(Spacer(1, 4 * mm))

    # -- Company & Employee info side by side --
    company_info = (
        f"<b>{data.company_name}</b><br/>"
        f"IČO: {data.company_ico}"
        f"{f'  |  DIČ: {data.company_dic}' if data.company_dic else ''}<br/>"
        f"{data.company_address}"
    )
    employee_info = (
        f"<b>{data.employee_name}</b><br/>"
        f"Osobné číslo: {data.employee_number}<br/>"
        f"Dátum narodenia: {data.employee_birth_date}<br/>"
        f"{data.employee_address}"
    )

    info_table = Table(
        [
            [
                Paragraph(company_info, styles["Normal"]),
                Paragraph(employee_info, styles["Normal"]),
            ]
        ],
        colWidths=[9 * cm, 9 * cm],
    )
    info_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("BOX", (0, 0), (-1, -1), 0.5, _BORDER_COLOR),
                ("LINEBEFORE", (1, 0), (1, -1), 0.5, _BORDER_COLOR),
            ]
        )
    )
    elements.append(info_table)
    elements.append(Spacer(1, 6 * mm))

    # -- Gross wage breakdown --
    elements.append(Paragraph("Hrubá mzda", styles["SectionHeader"]))
    gross_data = [
        ["Zložka", "Suma"],
        ["Základná mzda", _fmt(data.base_wage)],
        ["Nadčasy (hodiny)", _fmt_no_eur(data.overtime_hours)],
        ["Nadčasy (suma)", _fmt(data.overtime_amount)],
        ["Odmeny", _fmt(data.bonus_amount)],
        ["Príplatky", _fmt(data.supplement_amount)],
        ["Hrubá mzda spolu", _fmt(data.gross_wage)],
    ]
    gross_table = Table(gross_data, colWidths=[12 * cm, 6 * cm])
    gross_table.setStyle(_data_table_style(len(gross_data)))
    # Bold the total row
    gross_table.setStyle(TableStyle([("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")]))
    elements.append(gross_table)
    elements.append(Spacer(1, 4 * mm))

    # -- Social insurance (employee) --
    elements.append(Paragraph("Sociálne poistenie — zamestnanec", styles["SectionHeader"]))
    sp_data = [
        ["Položka", "Suma"],
        ["Vymeriavací základ", _fmt(data.sp_assessment_base)],
        ["Nemocenské (1,4 %)", _fmt(data.sp_nemocenske)],
        ["Starobné (4,0 %)", _fmt(data.sp_starobne)],
        ["Invalidné (3,0 %)", _fmt(data.sp_invalidne)],
        ["Nezamestnanosť (1,0 %)", _fmt(data.sp_nezamestnanost)],
        ["SP zamestnanec spolu", _fmt(data.sp_employee_total)],
    ]
    sp_table = Table(sp_data, colWidths=[12 * cm, 6 * cm])
    sp_table.setStyle(_data_table_style(len(sp_data)))
    sp_table.setStyle(TableStyle([("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")]))
    elements.append(sp_table)
    elements.append(Spacer(1, 4 * mm))

    # -- Health insurance (employee) --
    elements.append(Paragraph("Zdravotné poistenie — zamestnanec", styles["SectionHeader"]))
    zp_data = [
        ["Položka", "Suma"],
        ["Vymeriavací základ", _fmt(data.zp_assessment_base)],
        ["ZP zamestnanec (5,0 / 2,5 %)", _fmt(data.zp_employee)],
    ]
    zp_table = Table(zp_data, colWidths=[12 * cm, 6 * cm])
    zp_table.setStyle(_data_table_style(len(zp_data)))
    elements.append(zp_table)
    elements.append(Spacer(1, 4 * mm))

    # -- Tax calculation --
    elements.append(Paragraph("Výpočet dane", styles["SectionHeader"]))
    tax_data = [
        ["Položka", "Suma"],
        ["Čiastkový základ dane", _fmt(data.partial_tax_base)],
        ["NČZD (nezdaniteľná časť)", _fmt(data.nczd_applied)],
        ["Základ dane", _fmt(data.tax_base)],
        ["Preddavok na daň", _fmt(data.tax_advance)],
        ["Daňový bonus (deti)", _fmt(data.child_bonus)],
        ["Daň po bonuse", _fmt(data.tax_after_bonus)],
    ]
    tax_table = Table(tax_data, colWidths=[12 * cm, 6 * cm])
    tax_table.setStyle(_data_table_style(len(tax_data)))
    tax_table.setStyle(TableStyle([("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")]))
    elements.append(tax_table)
    elements.append(Spacer(1, 6 * mm))

    # -- NET WAGE (highlighted) --
    net_data = [["ČISTÁ MZDA", _fmt(data.net_wage)]]
    net_table = Table(net_data, colWidths=[12 * cm, 6 * cm])
    net_table.setStyle(_summary_table_style())
    elements.append(net_table)
    elements.append(Spacer(1, 6 * mm))

    # -- Employer costs (informational) --
    elements.append(Paragraph("Náklady zamestnávateľa", styles["SectionHeader"]))
    employer_data = [
        ["Položka", "Suma"],
        ["SP zamestnávateľ", _fmt(data.sp_employer_total)],
        ["ZP zamestnávateľ", _fmt(data.zp_employer)],
        ["II. pilier", _fmt(data.pillar2_amount)],
        ["Celkové náklady zamestnávateľa", _fmt(data.total_employer_cost)],
    ]
    employer_table = Table(employer_data, colWidths=[12 * cm, 6 * cm])
    employer_table.setStyle(_data_table_style(len(employer_data)))
    employer_table.setStyle(TableStyle([("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")]))
    elements.append(employer_table)
    elements.append(Spacer(1, 8 * mm))

    # -- Footer --
    elements.append(
        Paragraph(
            f"Vygenerované systémom NEX Payroll | {period_label}",
            styles["SmallText"],
        )
    )

    doc.build(elements)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# File persistence
# ---------------------------------------------------------------------------


def get_pdf_path(
    tenant_schema: str,
    period_year: int,
    period_month: int,
    employee_number: str,
) -> str:
    """Compute the canonical PDF file path per DESIGN.md convention.

    Pattern: {PDF_BASE_PATH}/{tenant_schema}/{year}/{month:02d}/{employee_number}.pdf
    """
    return os.path.join(
        PDF_BASE_PATH,
        tenant_schema,
        str(period_year),
        f"{period_month:02d}",
        f"{employee_number}.pdf",
    )


def write_pdf_to_disk(pdf_bytes: bytes, file_path: str) -> int:
    """Write PDF bytes to disk, creating directories as needed.

    Returns the file size in bytes.
    """
    directory = os.path.dirname(file_path)
    Path(directory).mkdir(parents=True, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(pdf_bytes)
    return len(pdf_bytes)


def build_pay_slip_data_from_models(
    *,
    tenant,
    employee,
    payroll,
) -> PaySlipData:
    """Create a PaySlipData instance from ORM model instances.

    Extracts the relevant fields from Tenant, Employee, and Payroll
    ORM objects to feed the PDF generator.
    """
    company_address = f"{tenant.address_street}, {tenant.address_zip} {tenant.address_city}"
    employee_address = f"{employee.address_street}, {employee.address_zip} {employee.address_city}"

    return PaySlipData(
        # Company
        company_name=tenant.name,
        company_ico=tenant.ico,
        company_dic=tenant.dic,
        company_address=company_address,
        # Employee
        employee_name=f"{employee.first_name} {employee.last_name}",
        employee_number=employee.employee_number,
        employee_birth_date=employee.birth_date.strftime("%d.%m.%Y"),
        employee_address=employee_address,
        # Period
        period_year=payroll.period_year,
        period_month=payroll.period_month,
        # Gross
        base_wage=payroll.base_wage,
        overtime_hours=payroll.overtime_hours,
        overtime_amount=payroll.overtime_amount,
        bonus_amount=payroll.bonus_amount,
        supplement_amount=payroll.supplement_amount,
        gross_wage=payroll.gross_wage,
        # SP employee
        sp_assessment_base=payroll.sp_assessment_base,
        sp_nemocenske=payroll.sp_nemocenske,
        sp_starobne=payroll.sp_starobne,
        sp_invalidne=payroll.sp_invalidne,
        sp_nezamestnanost=payroll.sp_nezamestnanost,
        sp_employee_total=payroll.sp_employee_total,
        # ZP employee
        zp_assessment_base=payroll.zp_assessment_base,
        zp_employee=payroll.zp_employee,
        # Tax
        partial_tax_base=payroll.partial_tax_base,
        nczd_applied=payroll.nczd_applied,
        tax_base=payroll.tax_base,
        tax_advance=payroll.tax_advance,
        child_bonus=payroll.child_bonus,
        tax_after_bonus=payroll.tax_after_bonus,
        # Net
        net_wage=payroll.net_wage,
        # Employer
        sp_employer_total=payroll.sp_employer_total,
        zp_employer=payroll.zp_employer,
        total_employer_cost=payroll.total_employer_cost,
        pillar2_amount=payroll.pillar2_amount,
    )
