"""
PDF Service — Young IG Auto Inspection System  (Design v2)

Generates branded, professional Vehicle Inspection Reports as PDFs using
WeasyPrint.

Design v2 — fully revised per client feedback:
  - Side-by-side category layout: findings left (65%), photos right (35%)
  - Deep Navy primary palette; red reserved only for failed/critical items
  - Semantic pill badges (green/amber/red) per finding value
  - Row-level tinting for non-passing items
  - Hero vehicle card (image + specs grid + verification badge)
  - Inspector summary panel replaces bare banner
  - Customer/Inspector/Seller metadata moved to compact footer
  - CSS page-break rules enforced; clean zebra-striped tables

Flow:
    1. InspectionService.build_pdf_report() -> InspectionPDFReport (Pydantic DTO)
    2. PDFService.generate(report)          -> renders HTML -> WeasyPrint -> PDF bytes
    3. Bytes are saved, uploaded, or streamed back to the client.
"""

import os
import base64
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

from loguru import logger

from ..schemas.inspection_pdf_report import (
    InspectionPDFReport, PDFCategoryFindings, PDFImage
)
from ..enums import OverallCondition


# ---------------------------------------------------------------------------
# Asset helpers
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_LOGO_PATH = _PROJECT_ROOT / "media" / "Logo.png"


def _logo_base64() -> str:
    """Encode the YIA logo as an embedded base64 data URI."""
    if not _LOGO_PATH.exists():
        logger.warning(f"Logo not found at {_LOGO_PATH}")
        return ""
    with open(_LOGO_PATH, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


# ---------------------------------------------------------------------------
# Condition helpers
# ---------------------------------------------------------------------------

_CONDITION_META = {
    OverallCondition.NO_MAJOR_ISSUES:        ("PASS — NO MAJOR ISSUES",     "#166534", "#dcfce7", "✓"),
    OverallCondition.MINOR_ISSUES_FOUND:     ("MINOR ISSUES FOUND",          "#92400e", "#fef3c7", "⚠"),
    OverallCondition.MAJOR_ISSUES_FOUND:     ("MAJOR ISSUES FOUND",          "#7f1d1d", "#fee2e2", "✗"),
    OverallCondition.CRITICAL_SAFETY_ISSUES: ("CRITICAL SAFETY ISSUES",      "#ffffff", "#991b1b", "✗"),
}


def _condition_meta(condition: Optional[OverallCondition]):
    return _CONDITION_META.get(
        condition,
        ("NOT ASSESSED", "#374151", "#f3f4f6", "?")
    )


# ---------------------------------------------------------------------------
# Badge / row-tint classification
# ---------------------------------------------------------------------------

_PASS_WORDS = {
    "good", "pass", "ok", "excellent", "clean", "normal", "authentic",
    "working", "intact", "present", "full", "clear", "no issues", "fine",
    "functional", "healthy", "secure", "tight", "smooth"
}
_WARN_WORDS = {
    "attention", "monitor", "worn", "low", "minor", "slight",
    "note", "check", "aged", "faded", "fair", "average", "marginal"
}
_FAIL_WORDS = {
    "fail", "defect", "poor", "bad", "missing", "broken", "damaged",
    "tampered", "critical", "unsafe", "leak", "rust", "cracked",
    "absent", "no", "none", "not working", "faulty", "repair"
}


def _value_tier(value: Optional[str]) -> str:
    """Return 'pass', 'warn', or 'fail' based on the raw finding value."""
    if not value:
        return "neutral"
    v = value.strip().lower()
    for word in _FAIL_WORDS:
        if word in v:
            return "fail"
    for word in _WARN_WORDS:
        if word in v:
            return "warn"
    for word in _PASS_WORDS:
        if word in v:
            return "pass"
    return "neutral"


def _badge(value: Optional[str]) -> str:
    """Return a semantic pill badge HTML span for a finding value."""
    if not value:
        return '<span class="badge badge-neutral">—</span>'
    tier = _value_tier(value)
    css = {
        "pass":    "badge-success",
        "warn":    "badge-warning",
        "fail":    "badge-danger",
        "neutral": "badge-neutral",
    }[tier]
    return f'<span class="badge {css}">{value}</span>'


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _build_category_sections(
    categories: List[PDFCategoryFindings],
    images_by_category: Dict[str, List[PDFImage]]
) -> str:
    """Side-by-side: findings (65%) + category photos (35%) per category."""
    if not categories:
        return '<p class="no-data">No inspection findings recorded.</p>'

    sections = []
    for idx, cat in enumerate(categories, start=1):
        rows_html = ""
        for finding in cat.findings:
            tier = _value_tier(finding.value)
            row_class = {"fail": "row-fail", "warn": "row-warn", "pass": "", "neutral": ""}[tier]
            notes_html = (
                f'<div class="field-notes">{finding.notes}</div>'
                if finding.notes else ""
            )
            rows_html += f"""
                <tr class="{row_class}">
                    <td class="field-name">{finding.field_name}</td>
                    <td class="field-value">{_badge(finding.value)}{notes_html}</td>
                </tr>
            """

        table_html = f"""
            <table class="findings-table">
                <thead>
                    <tr><th>Inspection Item</th><th>Condition / Value</th></tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        """

        cat_key = cat.category_name.upper()
        cat_images = images_by_category.get(cat_key, [])

        if cat_images:
            thumbs = "".join(
                f'<div class="thumb-card"><img src="{img.image_url}" alt="{cat.category_name}" /></div>'
                for img in cat_images[:4]
            )
            photos_col = f'<div class="photo-grid">{thumbs}</div>'
        else:
            photos_col = '<div class="photo-placeholder">No photos for this section</div>'

        sections.append(f"""
            <div class="category-block">
                <div class="category-header">
                    <div class="cat-num">{idx}</div>
                    <h2>{cat.category_name}</h2>
                </div>
                <div class="category-body">
                    <div class="findings-col">{table_html}</div>
                    <div class="photos-col">{photos_col}</div>
                </div>
            </div>
        """)

    return "\n".join(sections)


def _build_hero_image(images_by_category: Dict[str, List[PDFImage]]) -> str:
    hero_url = ""
    for key in ("EXTERIOR", "INTERIOR", "ENGINE", "OTHER"):
        imgs = images_by_category.get(key, [])
        if imgs:
            hero_url = imgs[0].image_url
            break
    if not hero_url:
        return ""
    return f'<img class="hero-img" src="{hero_url}" alt="Vehicle front view" />'


def _build_summary_panel(report: InspectionPDFReport) -> str:
    label, text_color, bg_color, icon = _condition_meta(report.overall_condition)

    notes_block = ""
    if report.final_notes:
        notes_block = f"""
            <div class="summary-notes">
                <div class="notes-label">Inspector's Assessment</div>
                <div class="notes-text">{report.final_notes}</div>
            </div>
        """

    mileage_display = f"{report.mileage:,}" if report.mileage else "N/A"
    odo_unit = report.odo_measure.value if report.odo_measure else "KMS"

    if report.mileage_authentic is True:
        odo_badge = '<span class="seal seal-pass">✓ AUTHENTIC</span>'
    elif report.mileage_authentic is False:
        odo_badge = '<span class="seal seal-fail">✗ TAMPERED</span>'
    else:
        odo_badge = '<span class="seal seal-neutral">UNVERIFIED</span>'

    return f"""
        <div class="summary-panel" style="background:{bg_color}; border-color:{text_color}">
            <div class="summary-top">
                <div class="condition-block">
                    <div class="condition-icon" style="color:{text_color}">{icon}</div>
                    <div>
                        <div class="condition-verdict" style="color:{text_color}">{label}</div>
                        <div class="condition-sub" style="color:{text_color}">Overall Condition Assessment</div>
                    </div>
                </div>
                <div class="mileage-block">
                    <div class="mileage-val">{mileage_display} {odo_unit}</div>
                    <div class="mileage-label">Recorded Mileage &nbsp; {odo_badge}</div>
                </div>
            </div>
            {notes_block}
        </div>
    """


# ---------------------------------------------------------------------------
# Main HTML renderer
# ---------------------------------------------------------------------------

def _render_html(report: InspectionPDFReport) -> str:
    logo_b64 = _logo_base64()
    logo_tag = (
        f'<img class="header-logo" src="{logo_b64}" alt="YIA Logo" />'
        if logo_b64 else ""
    )

    v = report.vehicle_info
    generated_at = datetime.now().strftime("%d %B %Y, %H:%M")
    hero_img = _build_hero_image(report.images_by_category)
    summary_panel = _build_summary_panel(report)
    category_sections = _build_category_sections(
        report.findings_by_category, report.images_by_category
    )

    inspector = report.inspector_info
    customer  = report.customer_info
    seller    = report.seller_name or "—"
    cust_name  = customer.full_name if customer else "—"
    cust_phone = customer.phone     if customer else "—"
    cust_email = customer.email     if customer else "—"

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <title>Inspection Report — {v.registration_number}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
                font-size: 9.5pt;
                color: #0f172a;
                line-height: 1.55;
                background: #ffffff;
            }}
            @page {{
                size: A4;
                margin: 14mm 14mm 20mm 14mm;
                @bottom-right {{
                    content: "Page " counter(page) " of " counter(pages);
                    font-size: 7.5pt;
                    color: #94a3b8;
                }}
            }}
            .header {{
                display: flex;
                align-items: center;
                gap: 16px;
                padding-bottom: 12px;
                border-bottom: 3px solid #1e293b;
                margin-bottom: 16px;
            }}
            .header-logo {{
                width: 72px;
                height: 72px;
                border-radius: 50%;
                object-fit: cover;
                flex-shrink: 0;
            }}
            .header-text {{ flex: 1; }}
            .header-text h1 {{
                font-size: 18pt;
                font-weight: 800;
                color: #1e293b;
                letter-spacing: 0.3px;
            }}
            .header-text .company {{ font-size: 9.5pt; color: #64748b; }}
            .header-right {{ text-align: right; flex-shrink: 0; }}
            .header-right .report-label {{
                font-size: 7pt;
                text-transform: uppercase;
                letter-spacing: 1.5px;
                color: #94a3b8;
            }}
            .header-right .report-number {{ font-size: 12pt; font-weight: 700; color: #1e293b; }}
            .header-right .doc-meta {{ font-size: 7.5pt; color: #94a3b8; margin-top: 3px; }}

            .hero-card {{
                display: flex;
                gap: 14px;
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-left: 4px solid #1e293b;
                border-radius: 6px;
                padding: 14px;
                margin-bottom: 14px;
            }}
            .hero-img-wrap {{ flex-shrink: 0; width: 210px; }}
            .hero-img {{
                width: 100%;
                height: 140px;
                object-fit: cover;
                border-radius: 5px;
                border: 1px solid #e2e8f0;
            }}
            .hero-specs {{ flex: 1; }}
            .hero-specs h3 {{ font-size: 11pt; font-weight: 700; color: #1e293b; margin-bottom: 8px; }}
            .specs-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 5px 16px; }}
            .spec-item {{ display: flex; flex-direction: column; }}
            .spec-label {{ font-size: 6.5pt; text-transform: uppercase; letter-spacing: 0.8px; color: #64748b; }}
            .spec-value {{ font-size: 9.5pt; font-weight: 700; color: #0f172a; }}

            .summary-panel {{
                border: 1.5px solid;
                border-radius: 6px;
                padding: 14px 18px;
                margin-bottom: 18px;
            }}
            .summary-top {{ display: flex; justify-content: space-between; align-items: center; }}
            .condition-block {{ display: flex; align-items: center; gap: 10px; }}
            .condition-icon {{ font-size: 24pt; font-weight: 900; line-height: 1; }}
            .condition-verdict {{ font-size: 13pt; font-weight: 800; letter-spacing: 0.3px; }}
            .condition-sub {{ font-size: 7.5pt; opacity: 0.7; }}
            .mileage-block {{ text-align: right; }}
            .mileage-val {{ font-size: 14pt; font-weight: 800; color: #1e293b; }}
            .mileage-label {{ font-size: 7.5pt; color: #64748b; margin-top: 2px; }}
            .summary-notes {{ margin-top: 12px; padding-top: 10px; border-top: 1px solid rgba(0,0,0,0.12); }}
            .notes-label {{ font-size: 7pt; text-transform: uppercase; letter-spacing: 1px; color: #64748b; margin-bottom: 4px; }}
            .notes-text {{ font-size: 9.5pt; color: #374151; line-height: 1.55; font-style: italic; }}

            .seal {{ display: inline-block; padding: 2px 8px; border-radius: 9px; font-size: 7pt; font-weight: 700; letter-spacing: 0.5px; }}
            .seal-pass    {{ background: #dcfce7; color: #166534; }}
            .seal-fail    {{ background: #fee2e2; color: #991b1b; }}
            .seal-neutral {{ background: #f1f5f9; color: #475569; }}

            .badge {{ display: inline-block; padding: 2px 9px; border-radius: 9px; font-size: 7.5pt; font-weight: 700; letter-spacing: 0.3px; }}
            .badge-success {{ background: #dcfce7; color: #166534; }}
            .badge-warning {{ background: #fef3c7; color: #92400e; }}
            .badge-danger  {{ background: #fee2e2; color: #991b1b; }}
            .badge-neutral {{ background: #f1f5f9; color: #475569; }}

            .category-block {{ margin-bottom: 20px; page-break-inside: avoid; break-inside: avoid; }}
            .category-header {{
                display: flex; align-items: center; gap: 8px;
                margin-bottom: 8px; padding-bottom: 6px; border-bottom: 2px solid #1e293b;
            }}
            .cat-num {{
                background: #1e293b; color: #ffffff; width: 24px; height: 24px;
                border-radius: 50%; display: flex; align-items: center; justify-content: center;
                font-size: 10pt; font-weight: 700; flex-shrink: 0;
            }}
            .category-header h2 {{ font-size: 11pt; font-weight: 700; color: #1e293b; text-transform: uppercase; letter-spacing: 0.5px; }}
            .category-body {{ display: flex; gap: 12px; }}
            .findings-col {{ flex: 0 0 65%; max-width: 65%; }}
            .photos-col   {{ flex: 0 0 33%; max-width: 33%; }}

            .findings-table {{ width: 100%; border-collapse: collapse; font-size: 8.5pt; }}
            .findings-table thead th {{
                background: #f1f5f9; color: #64748b; font-size: 7pt;
                text-transform: uppercase; letter-spacing: 0.8px;
                padding: 6px 10px; border-bottom: 1px solid #e2e8f0; text-align: left;
            }}
            .findings-table tbody tr {{ border-bottom: 1px solid #f1f5f9; }}
            .findings-table tbody tr:nth-child(even) {{ background: #f8fafc; }}
            .findings-table tbody tr.row-fail {{ background: #fff1f2 !important; }}
            .findings-table tbody tr.row-warn {{ background: #fffbeb !important; }}
            .findings-table td {{ padding: 6px 10px; vertical-align: top; }}
            .field-name {{ font-weight: 600; color: #334155; width: 50%; }}
            .field-value {{ color: #0f172a; }}
            .field-notes {{ font-size: 7.5pt; color: #94a3b8; font-style: italic; margin-top: 3px; }}

            .photo-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }}
            .thumb-card img {{
                width: 100%; height: 68px; object-fit: cover;
                border-radius: 4px; border: 1px solid #e2e8f0; display: block;
            }}
            .photo-placeholder {{
                color: #94a3b8; font-size: 7.5pt; font-style: italic;
                padding: 8px 4px; text-align: center;
                border: 1px dashed #e2e8f0; border-radius: 4px;
            }}

            .signature-section {{
                margin-top: 24px; padding-top: 12px; border-top: 1px solid #e2e8f0;
                display: flex; justify-content: space-between;
            }}
            .sig-block {{ text-align: center; width: 44%; }}
            .sig-line {{ border-top: 1px solid #94a3b8; margin-bottom: 4px; }}
            .sig-label {{ font-size: 7.5pt; color: #64748b; }}

            .meta-footer {{
                margin-top: 20px; padding: 10px 14px;
                background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 5px;
            }}
            .meta-footer-title {{ font-size: 7pt; text-transform: uppercase; letter-spacing: 1px; color: #94a3b8; margin-bottom: 8px; }}
            .meta-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px 20px; }}
            .meta-col h4 {{
                font-size: 7pt; text-transform: uppercase; letter-spacing: 0.8px;
                color: #64748b; margin-bottom: 4px; border-bottom: 1px solid #e2e8f0; padding-bottom: 3px;
            }}
            .meta-item {{ display: flex; flex-direction: column; margin-bottom: 4px; }}
            .meta-label {{ font-size: 6.5pt; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }}
            .meta-value {{ font-size: 8.5pt; font-weight: 600; color: #1e293b; }}

            .page-footer {{
                margin-top: 14px; padding-top: 8px; border-top: 2px solid #1e293b;
                display: flex; justify-content: space-between; align-items: center;
            }}
            .page-footer .co-name {{ font-weight: 700; color: #1e293b; font-size: 9pt; }}
            .page-footer .co-tag {{ font-size: 7.5pt; color: #64748b; }}
            .page-footer .gen-ts {{ font-size: 7pt; color: #94a3b8; text-align: right; }}

            .no-data {{ color: #94a3b8; font-style: italic; padding: 10px; }}
        </style>
    </head>
    <body>

        <div class="header">
            {logo_tag}
            <div class="header-text">
                <h1>VEHICLE INSPECTION REPORT</h1>
                <div class="company">Young I.G Auto-Solution &nbsp;|&nbsp; Professional Vehicle Inspection &amp; Valuation</div>
            </div>
            <div class="header-right">
                <div class="report-label">Document ID</div>
                <div class="report-number">{report.inspection_number}</div>
                <div class="doc-meta">{report.inspection_date.strftime('%d %B %Y')}</div>
            </div>
        </div>

        <div class="hero-card">
            {"<div class='hero-img-wrap'>" + hero_img + "</div>" if hero_img else ""}
            <div class="hero-specs">
                <h3>{v.make or ""} {v.model or ""} — {v.registration_number}</h3>
                <div class="specs-grid">
                    <div class="spec-item"><span class="spec-label">Registration</span><span class="spec-value">{v.registration_number}</span></div>
                    <div class="spec-item"><span class="spec-label">Make</span><span class="spec-value">{v.make or "—"}</span></div>
                    <div class="spec-item"><span class="spec-label">Model</span><span class="spec-value">{v.model or "—"}</span></div>
                    <div class="spec-item"><span class="spec-label">Year</span><span class="spec-value">{v.manufacture_year or "—"}</span></div>
                    <div class="spec-item"><span class="spec-label">Fuel Type</span><span class="spec-value">{v.fuel_type or "—"}</span></div>
                    <div class="spec-item"><span class="spec-label">Transmission</span><span class="spec-value">{v.transmission or "—"}</span></div>
                    <div class="spec-item"><span class="spec-label">VIN / Chassis</span><span class="spec-value">{v.chassis_number or "—"}</span></div>
                    <div class="spec-item"><span class="spec-label">Engine No.</span><span class="spec-value">{v.engine_number or "—"}</span></div>
                </div>
            </div>
        </div>

        {summary_panel}

        {category_sections}

        <div class="signature-section">
            <div class="sig-block">
                <div class="sig-line"></div>
                <div class="sig-label">Authorized Inspector Signature</div>
            </div>
            <div class="sig-block">
                <div class="sig-line"></div>
                <div class="sig-label">Stamp / Date</div>
            </div>
        </div>

        <div class="meta-footer">
            <div class="meta-footer-title">Report Parties</div>
            <div class="meta-grid">
                <div class="meta-col">
                    <h4>Inspector</h4>
                    <div class="meta-item"><span class="meta-label">Name</span><span class="meta-value">{inspector.full_name}</span></div>
                    <div class="meta-item"><span class="meta-label">Email</span><span class="meta-value">{inspector.email}</span></div>
                    <div class="meta-item"><span class="meta-label">Phone</span><span class="meta-value">{inspector.phone or "—"}</span></div>
                </div>
                <div class="meta-col">
                    <h4>Customer</h4>
                    <div class="meta-item"><span class="meta-label">Name</span><span class="meta-value">{cust_name}</span></div>
                    <div class="meta-item"><span class="meta-label">Phone</span><span class="meta-value">{cust_phone}</span></div>
                    <div class="meta-item"><span class="meta-label">Email</span><span class="meta-value">{cust_email}</span></div>
                </div>
                <div class="meta-col">
                    <h4>Seller / Dealer</h4>
                    <div class="meta-item"><span class="meta-label">Seller Name</span><span class="meta-value">{seller}</span></div>
                    <div class="meta-item"><span class="meta-label">Inspection No.</span><span class="meta-value">{report.inspection_number}</span></div>
                    <div class="meta-item"><span class="meta-label">Inspection Date</span><span class="meta-value">{report.inspection_date.strftime('%d %B %Y')}</span></div>
                </div>
            </div>
        </div>

        <div class="page-footer">
            <div>
                <div class="co-name">Young I.G Auto-Solution</div>
                <div class="co-tag">Professional Vehicle Inspection &amp; Valuation</div>
            </div>
            <div class="gen-ts">
                Generated: {generated_at}<br />
                Doc ID: {report.inspection_number}
            </div>
        </div>

    </body>
    </html>
    """


# ---------------------------------------------------------------------------
# PDFService class
# ---------------------------------------------------------------------------

class PDFService:
    """
    Generates Vehicle Inspection Report PDFs using WeasyPrint.
    WeasyPrint is imported lazily so this module can be loaded on
    Windows dev machines without GTK+ installed.
    """

    def generate(self, report: InspectionPDFReport) -> bytes:
        """Render the inspection report as PDF and return raw bytes."""
        from weasyprint import HTML
        html_content = _render_html(report)
        pdf_bytes = HTML(string=html_content).write_pdf()
        logger.info(
            f"PDF generated for {report.inspection_number} ({len(pdf_bytes):,} bytes)"
        )
        return pdf_bytes

    def generate_to_file(
        self,
        report: InspectionPDFReport,
        output_dir: str = "generated_reports",
    ) -> str:
        """Generate the PDF and save to disk named by vehicle registration."""
        pdf_bytes = self.generate(report)
        safe_name = (
            report.vehicle_info.registration_number
            .replace(" ", "_").replace("/", "-")
        )
        filename = f"{safe_name}.pdf"
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)
        logger.info(f"PDF saved: {filepath}")
        return filepath
