"""
PDF Service — Young IG Auto Inspection System  (Design v1)

Generates branded, professional Vehicle Inspection Reports as PDFs using
WeasyPrint. Brand colors: Red (#D32F2F) and Yellow (#FFD600).

Flow:
    1. InspectionService.build_pdf_report() -> InspectionPDFReport (Pydantic DTO)
    2. PDFService.generate(report) -> renders HTML -> WeasyPrint -> PDF bytes
    3. The bytes can be saved to disk, uploaded to Cloudinary, or returned directly.
"""

import os
import base64
from pathlib import Path
from typing import Optional
from datetime import datetime

from loguru import logger

from ..schemas.inspection_pdf_report import InspectionPDFReport, PDFCategoryFindings
from ..enums import OverallCondition, ImageCategory


# ---------------------------------------------------------------------------
# Resolve the company logo path once at module load
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # Young_IG_WEBSITE_ 2/
_LOGO_PATH = _PROJECT_ROOT / "media" / "Logo.png"


def _logo_base64() -> str:
    """Encode the logo as a base64 data URI so it embeds directly in the HTML."""
    if not _LOGO_PATH.exists():
        logger.warning(f"Logo not found at {_LOGO_PATH}")
        return ""
    with open(_LOGO_PATH, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def _condition_label(condition: Optional[OverallCondition]) -> str:
    """Human-friendly label for the overall condition enum."""
    labels = {
        OverallCondition.NO_MAJOR_ISSUES: "No Major Issues",
        OverallCondition.MINOR_ISSUES_FOUND: "Minor Issues Found",
        OverallCondition.MAJOR_ISSUES_FOUND: "Major Issues Found",
        OverallCondition.CRITICAL_SAFETY_ISSUES: "Critical Safety Issues",
    }
    return labels.get(condition, "Not Assessed")


def _condition_color(condition: Optional[OverallCondition]) -> str:
    """Badge color for the overall condition."""
    colors = {
        OverallCondition.NO_MAJOR_ISSUES: "#2e7d32",
        OverallCondition.MINOR_ISSUES_FOUND: "#f9a825",
        OverallCondition.MAJOR_ISSUES_FOUND: "#e65100",
        OverallCondition.CRITICAL_SAFETY_ISSUES: "#c62828",
    }
    return colors.get(condition, "#757575")


def _mileage_badge(authentic: Optional[bool]) -> str:
    """Returns the HTML badge for mileage authenticity."""
    if authentic is True:
        return '<span class="badge badge-green">AUTHENTIC ✓</span>'
    elif authentic is False:
        return '<span class="badge badge-red">TAMPERED ✗</span>'
    return '<span class="badge badge-grey">NOT VERIFIED</span>'


# ---------------------------------------------------------------------------
# HTML Template Builder
# ---------------------------------------------------------------------------

def _build_findings_html(categories: list[PDFCategoryFindings]) -> str:
    """Build the inspection findings sections from category data."""
    if not categories:
        return '<p class="no-data">No inspection findings recorded.</p>'

    sections = []
    for idx, cat in enumerate(categories, start=1):
        rows = ""
        for finding in cat.findings:
            value_display = finding.value or "—"
            notes_html = f'<div class="field-notes">{finding.notes}</div>' if finding.notes else ""
            rows += f"""
                <tr>
                    <td class="field-name">{finding.field_name}</td>
                    <td class="field-value">{value_display}{notes_html}</td>
                </tr>
            """

        sections.append(f"""
            <div class="section">
                <div class="section-header">
                    <div class="section-number">{idx}</div>
                    <h2>{cat.category_name}</h2>
                </div>
                <table class="findings-table">
                    <thead>
                        <tr>
                            <th>Inspection Item</th>
                            <th>Condition / Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            </div>
        """)

    return "\n".join(sections)


def _build_images_html(images_by_category: dict) -> str:
    """Build the visual evidence section from images grouped by category."""
    if not images_by_category:
        return ""

    image_sections = []
    for cat_key, images in images_by_category.items():
        cat_label = cat_key.replace("_", " ").title()
        image_grid = ""
        for img in images:
            image_grid += f"""
                <div class="image-card">
                    <img src="{img.image_url}" alt="{cat_label}" />
                    <p class="image-label">{cat_label}</p>
                </div>
            """
        image_sections.append(f"""
            <div class="image-category-group">
                <h3 class="image-category-title">{cat_label}</h3>
                <div class="image-grid">
                    {image_grid}
                </div>
            </div>
        """)

    return f"""
        <div class="section">
            <div class="section-header">
                <div class="section-number">📷</div>
                <h2>Visual Evidence</h2>
            </div>
            {"".join(image_sections)}
        </div>
    """


def _render_html(report: InspectionPDFReport) -> str:
    """Build the complete HTML document for the PDF."""
    logo_b64 = _logo_base64()
    condition_label = _condition_label(report.overall_condition)
    condition_color = _condition_color(report.overall_condition)
    mileage_badge = _mileage_badge(report.mileage_authentic)
    findings_html = _build_findings_html(report.findings_by_category)
    images_html = _build_images_html(report.images_by_category)

    # Vehicle info
    v = report.vehicle_info
    mileage_display = f"{report.mileage:,}" if report.mileage else "—"
    odo_unit = report.odo_measure.value if report.odo_measure else "KMS"

    # Customer info
    customer_section = ""
    if report.customer_info:
        c = report.customer_info
        customer_section = f"""
            <div class="info-card">
                <h3>Customer Information</h3>
                <div class="info-grid">
                    <div class="info-item"><span class="label">Name</span><span class="value">{c.full_name}</span></div>
                    <div class="info-item"><span class="label">Email</span><span class="value">{c.email or '—'}</span></div>
                    <div class="info-item"><span class="label">Phone</span><span class="value">{c.phone or '—'}</span></div>
                    <div class="info-item"><span class="label">KRA PIN</span><span class="value">{c.kra_pin or '—'}</span></div>
                </div>
            </div>
        """

    seller_section = ""
    if report.seller_name:
        seller_section = f"""
            <div class="info-card">
                <h3>Seller Information</h3>
                <div class="info-grid">
                    <div class="info-item"><span class="label">Seller Name</span><span class="value">{report.seller_name}</span></div>
                </div>
            </div>
        """

    # Final notes
    final_notes_html = ""
    if report.final_notes:
        final_notes_html = f"""
            <div class="section">
                <div class="section-header">
                    <div class="section-number">📝</div>
                    <h2>Inspector's Notes</h2>
                </div>
                <div class="notes-box">
                    {report.final_notes}
                </div>
            </div>
        """

    generated_at = datetime.now().strftime("%d %B %Y, %H:%M")

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <title>Inspection Report — {v.registration_number}</title>
        <style>
            /* ─── Reset & Base ────────────────────────────────────────── */
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
                font-size: 10pt;
                color: #2d2d2d;
                line-height: 1.5;
                background: #ffffff;
            }}

            /* ─── Page Setup ──────────────────────────────────────────── */
            @page {{
                size: A4;
                margin: 15mm 15mm 20mm 15mm;
                @bottom-center {{
                    content: "Page " counter(page) " of " counter(pages);
                    font-size: 8pt;
                    color: #999;
                }}
            }}

            /* ─── Header ──────────────────────────────────────────────── */
            .header {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                border-bottom: 4px solid #D32F2F;
                padding-bottom: 12px;
                margin-bottom: 20px;
            }}
            .header-logo {{
                width: 90px;
                height: 90px;
                border-radius: 50%;
                object-fit: cover;
            }}
            .header-text {{
                text-align: right;
                flex: 1;
                padding-left: 15px;
            }}
            .header-text h1 {{
                font-size: 22pt;
                font-weight: 800;
                color: #D32F2F;
                letter-spacing: 0.5px;
                margin-bottom: 2px;
            }}
            .header-text .subtitle {{
                font-size: 10pt;
                color: #555;
                font-weight: 400;
            }}
            .header-text .doc-id {{
                font-size: 8.5pt;
                color: #888;
                margin-top: 4px;
            }}

            /* ─── Overall Condition Banner ────────────────────────────── */
            .condition-banner {{
                background: {condition_color};
                color: #fff;
                padding: 12px 20px;
                border-radius: 6px;
                margin-bottom: 22px;
                text-align: center;
            }}
            .condition-banner .condition-label {{
                font-size: 9pt;
                text-transform: uppercase;
                letter-spacing: 1px;
                opacity: 0.9;
            }}
            .condition-banner .condition-value {{
                font-size: 16pt;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}

            /* ─── Info Cards ──────────────────────────────────────────── */
            .info-card {{
                background: #fafafa;
                border: 1px solid #eee;
                border-left: 4px solid #FFD600;
                border-radius: 4px;
                padding: 14px 18px;
                margin-bottom: 14px;
            }}
            .info-card h3 {{
                font-size: 10pt;
                color: #D32F2F;
                text-transform: uppercase;
                letter-spacing: 0.8px;
                margin-bottom: 10px;
                padding-bottom: 5px;
                border-bottom: 1px solid #eee;
            }}
            .info-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 6px 20px;
            }}
            .info-item {{
                display: flex;
                flex-direction: column;
            }}
            .info-item .label {{
                font-size: 7.5pt;
                color: #888;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .info-item .value {{
                font-size: 10pt;
                font-weight: 600;
                color: #333;
            }}

            /* ─── Badges ──────────────────────────────────────────────── */
            .badge {{
                display: inline-block;
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 8pt;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
            .badge-green {{ background: #e8f5e9; color: #2e7d32; border: 1px solid #a5d6a7; }}
            .badge-red {{ background: #ffebee; color: #c62828; border: 1px solid #ef9a9a; }}
            .badge-grey {{ background: #f5f5f5; color: #757575; border: 1px solid #e0e0e0; }}

            /* ─── Sections ────────────────────────────────────────────── */
            .section {{
                margin-bottom: 22px;
                page-break-inside: avoid;
            }}
            .section-header {{
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 10px;
                padding-bottom: 6px;
                border-bottom: 2px solid #D32F2F;
            }}
            .section-number {{
                background: #D32F2F;
                color: #fff;
                width: 28px;
                height: 28px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 11pt;
                font-weight: 700;
                flex-shrink: 0;
            }}
            .section-header h2 {{
                font-size: 13pt;
                color: #333;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}

            /* ─── Findings Table ──────────────────────────────────────── */
            .findings-table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 9.5pt;
            }}
            .findings-table thead th {{
                background: #333;
                color: #fff;
                padding: 8px 12px;
                text-align: left;
                font-size: 8.5pt;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .findings-table tbody tr {{
                border-bottom: 1px solid #eee;
            }}
            .findings-table tbody tr:nth-child(even) {{
                background: #fafafa;
            }}
            .findings-table td {{
                padding: 7px 12px;
                vertical-align: top;
            }}
            .field-name {{
                font-weight: 600;
                width: 40%;
                color: #444;
            }}
            .field-value {{
                color: #333;
            }}
            .field-notes {{
                font-size: 8pt;
                color: #888;
                font-style: italic;
                margin-top: 3px;
            }}

            /* ─── Images ──────────────────────────────────────────────── */
            .image-category-title {{
                font-size: 10pt;
                color: #D32F2F;
                margin: 10px 0 8px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .image-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                margin-bottom: 10px;
            }}
            .image-card {{
                text-align: center;
            }}
            .image-card img {{
                width: 100%;
                max-height: 200px;
                object-fit: cover;
                border-radius: 4px;
                border: 1px solid #ddd;
            }}
            .image-label {{
                font-size: 8pt;
                color: #777;
                margin-top: 4px;
            }}

            /* ─── Notes Box ───────────────────────────────────────────── */
            .notes-box {{
                background: #fffde7;
                border: 1px solid #FFD600;
                border-left: 4px solid #FFD600;
                padding: 14px 18px;
                border-radius: 4px;
                font-size: 10pt;
                line-height: 1.6;
                color: #444;
            }}

            /* ─── Footer ──────────────────────────────────────────────── */
            .footer {{
                margin-top: 30px;
                padding-top: 14px;
                border-top: 2px solid #D32F2F;
                text-align: center;
            }}
            .footer .company-name {{
                font-size: 11pt;
                font-weight: 700;
                color: #D32F2F;
            }}
            .footer .company-desc {{
                font-size: 8pt;
                color: #888;
                margin-top: 2px;
            }}
            .footer .generated-at {{
                font-size: 7.5pt;
                color: #aaa;
                margin-top: 8px;
            }}

            .no-data {{
                color: #999;
                font-style: italic;
                padding: 10px;
            }}

            .signature-line {{
                margin-top: 30px;
                padding-top: 10px;
                border-top: 1px solid #ccc;
                font-size: 9pt;
                color: #666;
            }}
        </style>
    </head>
    <body>

        <!-- ═══════ HEADER ═══════ -->
        <div class="header">
            {'<img class="header-logo" src="' + logo_b64 + '" alt="Young IG Logo" />' if logo_b64 else ''}
            <div class="header-text">
                <h1>VEHICLE INSPECTION REPORT</h1>
                <div class="subtitle">Young I.G Auto-Solution</div>
                <div class="doc-id">
                    Document ID: {report.inspection_number} &nbsp;|&nbsp;
                    Reg: {v.registration_number} &nbsp;|&nbsp;
                    Date: {report.inspection_date.strftime('%d %B %Y')}
                </div>
            </div>
        </div>

        <!-- ═══════ OVERALL CONDITION BANNER ═══════ -->
        <div class="condition-banner">
            <div class="condition-label">Overall Condition</div>
            <div class="condition-value">{condition_label.upper()}</div>
        </div>

        <!-- ═══════ VEHICLE SUMMARY ═══════ -->
        <div class="info-card">
            <h3>Vehicle Summary</h3>
            <div class="info-grid">
                <div class="info-item"><span class="label">Registration</span><span class="value">{v.registration_number}</span></div>
                <div class="info-item"><span class="label">Make</span><span class="value">{v.make or '—'}</span></div>
                <div class="info-item"><span class="label">Model</span><span class="value">{v.model or '—'}</span></div>
                <div class="info-item"><span class="label">Year</span><span class="value">{v.manufacture_year or '—'}</span></div>
                <div class="info-item"><span class="label">Fuel Type</span><span class="value">{v.fuel_type or '—'}</span></div>
                <div class="info-item"><span class="label">Transmission</span><span class="value">{v.transmission or '—'}</span></div>
                <div class="info-item"><span class="label">VIN / Chassis No</span><span class="value">{v.chassis_number or '—'}</span></div>
                <div class="info-item"><span class="label">Engine No</span><span class="value">{v.engine_number or '—'}</span></div>
                <div class="info-item">
                    <span class="label">Mileage</span>
                    <span class="value">{mileage_display} {odo_unit} &nbsp; {mileage_badge}</span>
                </div>
            </div>
        </div>

        <!-- ═══════ INSPECTOR INFO ═══════ -->
        <div class="info-card">
            <h3>Inspector Details</h3>
            <div class="info-grid">
                <div class="info-item"><span class="label">Inspector</span><span class="value">{report.inspector_info.full_name}</span></div>
                <div class="info-item"><span class="label">Email</span><span class="value">{report.inspector_info.email}</span></div>
                <div class="info-item"><span class="label">Phone</span><span class="value">{report.inspector_info.phone or '—'}</span></div>
                <div class="info-item"><span class="label">Inspection Date</span><span class="value">{report.inspection_date.strftime('%d %B %Y')}</span></div>
            </div>
        </div>

        <!-- ═══════ CUSTOMER INFO (if present) ═══════ -->
        {customer_section}

        <!-- ═══════ SELLER INFO (if present) ═══════ -->
        {seller_section}

        <!-- ═══════ INSPECTION FINDINGS ═══════ -->
        {findings_html}

        <!-- ═══════ VISUAL EVIDENCE ═══════ -->
        {images_html}

        <!-- ═══════ INSPECTOR NOTES ═══════ -->
        {final_notes_html}

        <!-- ═══════ SIGNATURE ═══════ -->
        <div class="signature-line">
            <strong>Authorized Inspector Signature:</strong> ____________________________
        </div>

        <!-- ═══════ FOOTER ═══════ -->
        <div class="footer">
            <div class="company-name">Young I.G Auto-Solution</div>
            <div class="company-desc">Professional Vehicle Inspection & Valuation</div>
            <div class="generated-at">
                Report generated on {generated_at} &nbsp;|&nbsp; Document ID: {report.inspection_number}
            </div>
        </div>

    </body>
    </html>
    """


# ---------------------------------------------------------------------------
# PDF Service Class
# ---------------------------------------------------------------------------

class PDFService:
    """
    Generates Vehicle Inspection Report PDFs using WeasyPrint.
    Consumes an InspectionPDFReport DTO and outputs PDF bytes.
    WeasyPrint is imported lazily to allow loading on Windows dev machines
    that don't have GTK+ installed.
    """

    def generate(self, report: InspectionPDFReport) -> bytes:
        """
        Render the inspection report as a PDF and return the raw bytes.
        """
        from weasyprint import HTML
        html_content = _render_html(report)
        pdf_bytes = HTML(string=html_content).write_pdf()
        logger.info(
            f"PDF generated for inspection {report.inspection_number} "
            f"({len(pdf_bytes):,} bytes)"
        )
        return pdf_bytes

    def generate_to_file(
        self,
        report: InspectionPDFReport,
        output_dir: str = "generated_reports",
    ) -> str:
        """
        Generate the PDF and save it to disk, named by the vehicle's
        registration number.

        Returns the full file path.
        """
        pdf_bytes = self.generate(report)

        # Sanitize the reg number for a safe filename
        safe_name = report.vehicle_info.registration_number.replace(" ", "_").replace("/", "-")
        filename = f"{safe_name}.pdf"

        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "wb") as f:
            f.write(pdf_bytes)

        logger.info(f"PDF saved to: {filepath}")
        return filepath
