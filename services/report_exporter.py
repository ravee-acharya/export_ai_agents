"""
ExportAI Report Exporter.

Generates a structured PDF report and a high-quality PNG summary image
from the orchestrator result dict. Both use pure Python rendering —
no Chrome, no Selenium, no browser dependency — so they work reliably
on Streamlit Cloud.

Libraries used:
  reportlab — PDF layout engine (pure Python)
  matplotlib — chart rendering to PNG/PDF (Agg backend, no display needed)

PDF structure:
  Page 1 — Header, recommendation hero, opportunity scores table
  Page 2 — Market comparison bar chart + radar dimensions table
  Page 3 — Pricing signals chart
  Page 4 — Risk summary + logistics scatter
  Page 5 — Buyer personas + government schemes
  Page 6 — Forecast charts

PNG structure:
  Single high-resolution image (2400×3200px @ 150dpi)
  showing the 6 most important data points on one page,
  suitable for WhatsApp/email sharing.
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any

import matplotlib
matplotlib.use("Agg")   # non-interactive backend, works on servers
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ------------------------------------------------------------------
# Colour palette (dark theme → mapped to print-safe equivalents)
# ------------------------------------------------------------------
_TEAL   = "#3FB8AF"
_BRASS  = "#E3A857"
_CORAL  = "#E2725B"
_NAVY   = "#0D1220"
_MIST   = "#9CA3BF"

_TEAL_RGB  = (0.247, 0.722, 0.686)
_BRASS_RGB = (0.890, 0.659, 0.341)
_CORAL_RGB = (0.886, 0.447, 0.357)
_NAVY_RGB  = (0.051, 0.071, 0.125)
_MIST_RGB  = (0.612, 0.639, 0.749)

PAGE_W, PAGE_H = A4   # 595 × 842 pt


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _score_tier(score: float) -> tuple[str, tuple]:
    if score >= 60: return "Strong",   _TEAL_RGB
    if score >= 30: return "Moderate", _BRASS_RGB
    return               "Weak",     _CORAL_RGB


def _fig_to_rl_image(fig, width_cm: float = 16, height_cm: float = 8) -> RLImage:
    """Save a matplotlib figure to an in-memory PNG and wrap as ReportLab Image."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)
    return RLImage(buf, width=width_cm * cm, height=height_cm * cm)


def _mpl_style(fig, ax_list=None):
    """Apply dark-navy style to a matplotlib figure."""
    fig.patch.set_facecolor(_NAVY_RGB)
    if ax_list is None:
        ax_list = fig.get_axes()
    for ax in ax_list:
        ax.set_facecolor(_NAVY_RGB)
        ax.tick_params(colors="white", labelsize=8)
        ax.spines["bottom"].set_color(_MIST_RGB)
        ax.spines["left"].set_color(_MIST_RGB)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.yaxis.label.set_color("white")
        ax.xaxis.label.set_color("white")
        ax.title.set_color("white")


# ------------------------------------------------------------------
# Chart builders (matplotlib, no Plotly dependency)
# ------------------------------------------------------------------

def _chart_opportunity_scores(scores: list[dict]) -> RLImage | None:
    if not scores:
        return None

    # Aggregate best score per country
    best: dict[str, float] = {}
    for s in scores:
        c = s.get("destination_country", "")
        best[c] = max(best.get(c, 0), float(s.get("score", 0)))

    countries = sorted(best, key=best.get, reverse=True)[:6]
    values = [best[c] for c in countries]
    bar_colors = [_score_tier(v)[1] for v in values]

    fig, ax = plt.subplots(figsize=(10, 4))
    _mpl_style(fig, [ax])
    bars = ax.bar(countries, values, color=bar_colors, width=0.6, zorder=2)
    ax.set_ylim(0, 110)
    ax.set_ylabel("Score / 100", color="white")
    ax.set_title("Market Opportunity Scores", color="white", fontsize=13,
                 fontweight="bold", pad=10)
    ax.axhline(60, color=_TEAL_RGB, lw=1, ls="--", alpha=0.5, label="Strong threshold")
    ax.axhline(30, color=_BRASS_RGB, lw=1, ls="--", alpha=0.5, label="Moderate threshold")
    ax.grid(axis="y", color=_MIST_RGB, alpha=0.2, zorder=1)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                f"{val:.0f}", ha="center", va="bottom", color="white", fontsize=9)
    legend = ax.legend(fontsize=8, framealpha=0.2, labelcolor="white")
    legend.get_frame().set_facecolor(_NAVY_RGB)
    fig.tight_layout(pad=0.5)
    return _fig_to_rl_image(fig, 16, 7)


def _chart_pricing(pricing_output) -> RLImage | None:
    if not pricing_output or not getattr(pricing_output, "pricing", None):
        return None
    pricing = pricing_output.pricing[:6]
    countries = [p.destination_country for p in pricing]
    margins   = [float(p.expected_margin_pct or 0) for p in pricing]
    fob       = [float(p.recommended_fob_price or 0) for p in pricing]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    _mpl_style(fig, [ax1, ax2])

    bar_colors1 = [_TEAL_RGB if m >= 20 else _BRASS_RGB if m >= 10 else _CORAL_RGB
                   for m in margins]
    ax1.barh(countries, margins, color=bar_colors1)
    ax1.set_xlabel("Margin %", color="white")
    ax1.set_title("Expected Margin %", color="white", fontsize=11)
    for i, v in enumerate(margins):
        ax1.text(v + 0.3, i, f"{v:.0f}%", va="center", color="white", fontsize=8)

    ax2.barh(countries, fob, color=_BRASS_RGB)
    ax2.set_xlabel("USD", color="white")
    ax2.set_title("Recommended FOB Price ($)", color="white", fontsize=11)
    for i, v in enumerate(fob):
        ax2.text(v + 0.3, i, f"${v:.0f}", va="center", color="white", fontsize=8)

    fig.tight_layout(pad=1.5)
    return _fig_to_rl_image(fig, 16, 6)


def _chart_risk(risk_output) -> RLImage | None:
    if not risk_output or not getattr(risk_output, "signals", None):
        return None
    signals = risk_output.signals[:5]
    _risk_score = {"Low": 15, "Moderate": 45, "High": 72, "Severe": 95}
    _risk_color = {"Low": _TEAL_RGB, "Moderate": _BRASS_RGB,
                   "High": _CORAL_RGB, "Severe": (0.93, 0.27, 0.27)}

    fig, axes = plt.subplots(1, len(signals), figsize=(3 * len(signals), 3))
    if len(signals) == 1:
        axes = [axes]
    _mpl_style(fig, axes)

    for ax, sig in zip(axes, signals):
        score = _risk_score.get(sig.risk_level, 50)
        color = _risk_color.get(sig.risk_level, _BRASS_RGB)
        theta = np.linspace(0, 2 * np.pi, 100)
        ax.plot(np.cos(theta), np.sin(theta), color=_MIST_RGB, lw=1, alpha=0.3)
        end_angle = (score / 100) * 2 * np.pi - np.pi / 2
        t = np.linspace(-np.pi / 2, end_angle, 100)
        ax.plot(np.cos(t), np.sin(t), color=color, lw=4)
        ax.text(0, 0, sig.risk_level, ha="center", va="center",
                color=color, fontsize=8, fontweight="bold")
        ax.set_xlim(-1.4, 1.4)
        ax.set_ylim(-1.4, 1.4)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(sig.destination_country, color="white", fontsize=10, pad=3)
        if sig.sanctions_flag:
            ax.text(0, -1.2, "⛔ Sanctions", ha="center",
                    color=_CORAL_RGB, fontsize=7)

    fig.suptitle("Country Risk", color="white", fontsize=12, fontweight="bold")
    fig.tight_layout(pad=0.5)
    return _fig_to_rl_image(fig, 16, 5)


def _chart_logistics(logistics_output) -> RLImage | None:
    if not logistics_output or not getattr(logistics_output, "signals", None):
        return None
    signals = logistics_output.signals
    countries = [s.destination_country for s in signals]
    days  = [float(s.sea_transit_days or 0) for s in signals]
    costs = [float(s.freight_cost_usd_per_kg or 0) for s in signals]

    fig, ax = plt.subplots(figsize=(8, 5))
    _mpl_style(fig, [ax])
    ax.scatter(days, costs, color=_TEAL_RGB, s=120, zorder=3,
               edgecolors=_BRASS_RGB, linewidths=1.5)
    for c, d, cost in zip(countries, days, costs):
        ax.annotate(c, (d, cost), textcoords="offset points",
                    xytext=(5, 5), color="white", fontsize=9)
    ax.set_xlabel("Sea transit (days)", color="white")
    ax.set_ylabel("Freight cost ($/kg)", color="white")
    ax.set_title("Logistics: Cost vs Transit Time\n(Bottom-left = better)",
                 color="white", fontsize=11)
    ax.grid(color=_MIST_RGB, alpha=0.2)
    fig.tight_layout(pad=0.5)
    return _fig_to_rl_image(fig, 12, 7)


def _chart_forecast(forecast_output) -> RLImage | None:
    if not forecast_output or not getattr(forecast_output, "signals", None):
        return None
    signals = [s for s in forecast_output.signals if s.monthly_projections][:4]
    if not signals:
        return None

    cols = min(len(signals), 2)
    rows = (len(signals) + 1) // 2
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 8, rows * 4))
    if len(signals) == 1:
        axes = [[axes]]
    elif rows == 1:
        axes = [axes]
    _mpl_style(fig)

    _conf_color = {"High": _TEAL_RGB, "Moderate": _BRASS_RGB, "Low": _CORAL_RGB}
    _fill_alpha  = {"High": 0.15, "Moderate": 0.12, "Low": 0.10}

    for idx, signal in enumerate(signals):
        r, c = divmod(idx, cols)
        ax = axes[r][c] if rows > 1 else axes[0][c]
        _mpl_style(fig, [ax])

        months = [p.month for p in signal.monthly_projections]
        proj   = [p.projected_value_usd / 1e6 for p in signal.monthly_projections]
        lower  = [p.lower_bound_usd / 1e6 for p in signal.monthly_projections]
        upper  = [p.upper_bound_usd / 1e6 for p in signal.monthly_projections]
        x = range(len(months))
        color = _conf_color.get(signal.confidence, _BRASS_RGB)
        alpha = _fill_alpha.get(signal.confidence, 0.12)

        ax.fill_between(x, lower, upper, color=color, alpha=alpha)
        ax.plot(x, proj, color=color, lw=2.5, marker="o", markersize=4)
        ax.set_xticks(x[::2])
        ax.set_xticklabels([months[i] for i in range(0, len(months), 2)],
                           rotation=45, ha="right", fontsize=7)
        growth_sign = "+" if signal.projected_annual_growth_pct >= 0 else ""
        ax.set_title(
            f"{signal.destination_country} · HS {signal.hs_code}\n"
            f"{growth_sign}{signal.projected_annual_growth_pct:.1f}%/yr "
            f"· {signal.confidence} confidence (R²={signal.r_squared:.2f})",
            color="white", fontsize=9, pad=4,
        )
        ax.set_ylabel("$M / month", color="white", fontsize=8)
        ax.grid(color=_MIST_RGB, alpha=0.15)

    # Hide any unused axes
    for idx in range(len(signals), rows * cols):
        r, c = divmod(idx, cols)
        ax = axes[r][c] if rows > 1 else axes[0][c]
        ax.set_visible(False)

    fig.suptitle("12-Month Demand Forecast", color="white",
                 fontsize=13, fontweight="bold", y=1.01)
    fig.tight_layout(pad=1.0)
    return _fig_to_rl_image(fig, 16, rows * 5)


# ------------------------------------------------------------------
# ReportLab styles
# ------------------------------------------------------------------

def _build_styles():
    base = getSampleStyleSheet()
    title = ParagraphStyle("ExportTitle", parent=base["Title"],
                           textColor=colors.HexColor(_TEAL),
                           fontSize=22, spaceAfter=4)
    h2 = ParagraphStyle("ExportH2", parent=base["Heading2"],
                        textColor=colors.HexColor(_BRASS),
                        fontSize=14, spaceBefore=12, spaceAfter=4)
    body = ParagraphStyle("ExportBody", parent=base["Normal"],
                          textColor=colors.black, fontSize=10,
                          leading=14, spaceAfter=6)
    caption = ParagraphStyle("ExportCaption", parent=base["Normal"],
                              textColor=colors.HexColor(_MIST),
                              fontSize=8, italic=True)
    return title, h2, body, caption


# ------------------------------------------------------------------
# PDF builder
# ------------------------------------------------------------------

def build_pdf(result: dict) -> bytes:
    """Build a structured PDF report from an orchestrator result dict.
    Returns the PDF as bytes."""

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    title_style, h2_style, body_style, caption_style = _build_styles()
    story = []
    SEP = HRFlowable(width="100%", thickness=0.5,
                     color=colors.HexColor(_TEAL), spaceAfter=6)

    # ── Cover / header ──────────────────────────────────────────
    story.append(Paragraph("ExportAI Intelligence Report", title_style))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}",
        caption_style,
    ))
    story.append(SEP)

    # Sector + markets
    sector = result.get("sector", "—")
    countries = ", ".join(result.get("target_countries", [])) or "—"
    story.append(Paragraph(f"<b>Sector:</b> {sector.title()}", body_style))
    story.append(Paragraph(f"<b>Target Markets:</b> {countries}", body_style))
    story.append(Spacer(1, 0.4*cm))

    # Summary
    summary = result.get("summary", "")
    if summary:
        story.append(Paragraph("Executive Summary", h2_style))
        story.append(Paragraph(summary, body_style))

    # ── Opportunity scores ───────────────────────────────────────
    scores = result.get("opportunity_scores", [])
    if scores:
        story.append(Paragraph("Market Opportunity Scores", h2_style))
        img = _chart_opportunity_scores(scores)
        if img:
            story.append(img)
            story.append(Paragraph(
                "🟢 Strong (60+) · 🟡 Moderate (30–60) · 🔴 Weak (<30)",
                caption_style,
            ))
        # Scores table
        best: dict[str, dict] = {}
        for s in scores:
            c = s.get("destination_country", "")
            if c not in best or s.get("score", 0) > best[c].get("score", 0):
                best[c] = s
        table_data = [["Market", "Score", "Tier", "HS Code"]]
        for c, row in sorted(best.items(), key=lambda x: x[1].get("score", 0), reverse=True):
            tier, _ = _score_tier(row.get("score", 0))
            table_data.append([c, f"{row.get('score', 0):.0f}/100",
                                tier, row.get("hs_code", "—")])
        tbl = Table(table_data, colWidths=[4*cm, 3*cm, 3*cm, 3*cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_NAVY)),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.HexColor(_TEAL)),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#F5F5F5")]),
            ("GRID",       (0, 0), (-1, -1), 0.25, colors.HexColor(_MIST)),
            ("ALIGN",      (1, 1), (-1, -1), "CENTER"),
        ]))
        story.append(Spacer(1, 0.3*cm))
        story.append(tbl)

    story.append(PageBreak())

    # ── Pricing ─────────────────────────────────────────────────
    pricing_output = result.get("pricing_output")
    if pricing_output and getattr(pricing_output, "pricing", None):
        story.append(Paragraph("Pricing Intelligence", h2_style))
        img = _chart_pricing(pricing_output)
        if img:
            story.append(img)
        # Pricing table
        tdata = [["Market", "FOB Price", "Margin %", "Competitiveness"]]
        for p in pricing_output.pricing:
            tdata.append([
                p.destination_country,
                f"${p.recommended_fob_price}",
                f"{p.expected_margin_pct}%",
                f"{p.competitiveness_score}/10",
            ])
        tbl2 = Table(tdata, colWidths=[4*cm, 3.5*cm, 3.5*cm, 3.5*cm])
        tbl2.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_NAVY)),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.HexColor(_BRASS)),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#F5F5F5")]),
            ("GRID",       (0, 0), (-1, -1), 0.25, colors.HexColor(_MIST)),
            ("ALIGN",      (1, 1), (-1, -1), "CENTER"),
        ]))
        story.append(Spacer(1, 0.3*cm))
        story.append(tbl2)
        story.append(PageBreak())

    # ── Risk ────────────────────────────────────────────────────
    risk_output = result.get("risk_output")
    if risk_output and getattr(risk_output, "signals", None):
        story.append(Paragraph("Country Risk Assessment", h2_style))
        img = _chart_risk(risk_output)
        if img:
            story.append(img)
        rdata = [["Market", "Risk Level", "Sanctions", "ECGC Cover", "Notes"]]
        for sig in risk_output.signals:
            rdata.append([
                sig.destination_country,
                sig.risk_level,
                "⛔ YES" if sig.sanctions_flag else "✅ No",
                "✅ Yes" if sig.ecgc_cover_available else "❌ No",
                sig.notes[:60] + "…" if len(sig.notes) > 60 else sig.notes,
            ])
        rbl = Table(rdata, colWidths=[2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 5*cm])
        rbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_NAVY)),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.HexColor(_CORAL)),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#F5F5F5")]),
            ("GRID",       (0, 0), (-1, -1), 0.25, colors.HexColor(_MIST)),
            ("ALIGN",      (1, 1), (3, -1), "CENTER"),
        ]))
        story.append(Spacer(1, 0.3*cm))
        story.append(rbl)
        story.append(PageBreak())

    # ── Logistics ───────────────────────────────────────────────
    log_output = result.get("logistics_output")
    if log_output and getattr(log_output, "signals", None):
        story.append(Paragraph("Logistics Overview", h2_style))
        img = _chart_logistics(log_output)
        if img:
            story.append(img)
        ldata = [["Market", "Sea Transit", "Freight $/kg", "Customs Complexity"]]
        for sig in log_output.signals:
            ldata.append([
                sig.destination_country,
                f"{sig.sea_transit_days} days",
                f"${sig.freight_cost_usd_per_kg:.2f}",
                f"{sig.customs_complexity:.0%}",
            ])
        ltbl = Table(ldata, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
        ltbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_NAVY)),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#F5F5F5")]),
            ("GRID",       (0, 0), (-1, -1), 0.25, colors.HexColor(_MIST)),
            ("ALIGN",      (1, 1), (-1, -1), "CENTER"),
        ]))
        story.append(Spacer(1, 0.3*cm))
        story.append(ltbl)
        story.append(PageBreak())

    # ── Forecast ────────────────────────────────────────────────
    forecast_output = result.get("forecast_output")
    if forecast_output and getattr(forecast_output, "signals", None):
        story.append(Paragraph("12-Month Demand Forecast", h2_style))
        story.append(Paragraph(
            "Linear trend projection from 3 years of UN Comtrade data. "
            "Shaded band = 80% confidence interval.",
            caption_style,
        ))
        img = _chart_forecast(forecast_output)
        if img:
            story.append(img)
        fdata = [["Market", "HS Code", "Growth %/yr", "Confidence", "R²"]]
        for sig in forecast_output.signals:
            fdata.append([
                sig.destination_country,
                sig.hs_code,
                f"{sig.projected_annual_growth_pct:+.1f}%",
                sig.confidence,
                f"{sig.r_squared:.2f}",
            ])
        ftbl = Table(fdata, colWidths=[3*cm, 3*cm, 3.5*cm, 3.5*cm, 2.5*cm])
        ftbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_NAVY)),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.HexColor(_TEAL)),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#F5F5F5")]),
            ("GRID",       (0, 0), (-1, -1), 0.25, colors.HexColor(_MIST)),
            ("ALIGN",      (1, 1), (-1, -1), "CENTER"),
        ]))
        story.append(Spacer(1, 0.3*cm))
        story.append(ftbl)

    # ── Government schemes ──────────────────────────────────────
    scheme_output = result.get("scheme_compliance_output")
    if scheme_output:
        schemes = scheme_output.eligible_schemes()
        if schemes:
            story.append(PageBreak())
            story.append(Paragraph("Government Schemes Available", h2_style))
            for s in schemes:
                story.append(Paragraph(f"<b>{s.name}</b> — {s.issuing_body}",
                                       body_style))
                story.append(Paragraph(s.benefit_summary, body_style))
                story.append(Spacer(1, 0.2*cm))

    # ── Footer disclaimer ───────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Disclaimer", h2_style))
    story.append(Paragraph(
        "This report was generated by ExportAI, an AI-powered export intelligence "
        "platform. Trade data is sourced from UN Comtrade and other public sources. "
        "All projections are statistical estimates and should not be relied upon as "
        "financial or legal advice. Consult a licensed export consultant or trade "
        "attorney before making export decisions.",
        body_style,
    ))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        f"ExportAI · {datetime.now().strftime('%Y')} · export-ai-agents.streamlit.app",
        caption_style,
    ))

    doc.build(story)
    return buf.getvalue()


# ------------------------------------------------------------------
# PNG summary builder
# ------------------------------------------------------------------

def build_png(result: dict) -> bytes:
    """Build a high-quality single-page PNG summary image.
    Returns PNG bytes. 2400×3200 @ 150dpi ≈ 16×21 inches — suitable for
    WhatsApp sharing or email attachment."""

    fig = plt.figure(figsize=(16, 21), dpi=150)
    fig.patch.set_facecolor(_NAVY_RGB)

    # Layout: title row + 3 rows × 2 cols of charts
    gs = fig.add_gridspec(
        4, 2,
        height_ratios=[0.8, 3, 3, 3],
        hspace=0.45, wspace=0.35,
        left=0.07, right=0.97, top=0.97, bottom=0.03,
    )

    # ── Title ───────────────────────────────────────────────────
    ax_title = fig.add_subplot(gs[0, :])
    ax_title.set_facecolor(_NAVY_RGB)
    ax_title.axis("off")
    sector = result.get("sector", "").title()
    countries = ", ".join(result.get("target_countries", []))
    ax_title.text(0.5, 0.75, "ExportAI Intelligence Report",
                  ha="center", va="center", color=_TEAL_RGB,
                  fontsize=22, fontweight="bold", transform=ax_title.transAxes)
    ax_title.text(0.5, 0.35,
                  f"Sector: {sector}  ·  Markets: {countries}  ·  "
                  f"{datetime.now().strftime('%d %b %Y')}",
                  ha="center", va="center", color=tuple(_MIST_RGB),
                  fontsize=11, transform=ax_title.transAxes)

    # ── Row 1: Opportunity scores + Pricing ────────────────────
    ax1 = fig.add_subplot(gs[1, 0])
    ax2 = fig.add_subplot(gs[1, 1])

    scores = result.get("opportunity_scores", [])
    best: dict[str, float] = {}
    for s in scores:
        c = s.get("destination_country", "")
        best[c] = max(best.get(c, 0), float(s.get("score", 0)))
    if best:
        ctries = sorted(best, key=best.get, reverse=True)[:5]
        vals   = [best[c] for c in ctries]
        cols   = [_score_tier(v)[1] for v in vals]
        ax1.bar(ctries, vals, color=cols, width=0.6, zorder=2)
        ax1.set_ylim(0, 110)
        ax1.set_title("Opportunity Scores", color="white", fontsize=12,
                      fontweight="bold")
        for c, v, col in zip(ctries, vals, cols):
            ax1.text(ctries.index(c), v + 2, f"{v:.0f}",
                     ha="center", color="white", fontsize=9)
        ax1.grid(axis="y", color=_MIST_RGB, alpha=0.2, zorder=1)
    else:
        ax1.text(0.5, 0.5, "No score data", ha="center", va="center",
                 color=tuple(_MIST_RGB), transform=ax1.transAxes)
    _mpl_style(fig, [ax1])

    pricing_output = result.get("pricing_output")
    if pricing_output and getattr(pricing_output, "pricing", None):
        pricing = pricing_output.pricing[:5]
        p_ctries = [p.destination_country for p in pricing]
        margins  = [float(p.expected_margin_pct or 0) for p in pricing]
        bar_cols = [_TEAL_RGB if m >= 20 else _BRASS_RGB if m >= 10
                    else _CORAL_RGB for m in margins]
        ax2.barh(p_ctries, margins, color=bar_cols)
        ax2.set_xlabel("Margin %", color="white", fontsize=9)
        ax2.set_title("Expected Margin %", color="white", fontsize=12,
                      fontweight="bold")
        for i, v in enumerate(margins):
            ax2.text(v + 0.3, i, f"{v:.0f}%", va="center",
                     color="white", fontsize=9)
    else:
        ax2.text(0.5, 0.5, "No pricing data", ha="center", va="center",
                 color=tuple(_MIST_RGB), transform=ax2.transAxes)
    _mpl_style(fig, [ax2])

    # ── Row 2: Risk + Logistics ─────────────────────────────────
    ax3 = fig.add_subplot(gs[2, 0])
    ax4 = fig.add_subplot(gs[2, 1])

    risk_output = result.get("risk_output")
    if risk_output and getattr(risk_output, "signals", None):
        _rc = {"Low": _TEAL_RGB, "Moderate": _BRASS_RGB,
               "High": _CORAL_RGB, "Severe": (0.93, 0.27, 0.27)}
        _rs = {"Low": 1, "Moderate": 2, "High": 3, "Severe": 4}
        rsigs = risk_output.signals[:5]
        rx = [s.destination_country for s in rsigs]
        ry = [_rs.get(s.risk_level, 2) for s in rsigs]
        rc = [_rc.get(s.risk_level, _BRASS_RGB) for s in rsigs]
        ax3.bar(rx, ry, color=rc, width=0.6)
        ax3.set_yticks([1, 2, 3, 4])
        ax3.set_yticklabels(["Low", "Moderate", "High", "Severe"],
                            color="white", fontsize=8)
        ax3.set_title("Country Risk Levels", color="white", fontsize=12,
                      fontweight="bold")
        for i, sig in enumerate(rsigs):
            if sig.sanctions_flag:
                ax3.text(i, ry[i] + 0.1, "⛔", ha="center", fontsize=10)
    else:
        ax3.text(0.5, 0.5, "No risk data", ha="center", va="center",
                 color=tuple(_MIST_RGB), transform=ax3.transAxes)
    _mpl_style(fig, [ax3])

    log_output = result.get("logistics_output")
    if log_output and getattr(log_output, "signals", None):
        lsigs = log_output.signals
        lx = [s.destination_country for s in lsigs]
        ldays = [float(s.sea_transit_days or 0) for s in lsigs]
        lcost = [float(s.freight_cost_usd_per_kg or 0) for s in lsigs]
        ax4.scatter(ldays, lcost, color=_TEAL_RGB, s=100, zorder=3,
                    edgecolors=_BRASS_RGB, lw=1.5)
        for c, d, cost in zip(lx, ldays, lcost):
            ax4.annotate(c, (d, cost), textcoords="offset points",
                         xytext=(4, 4), color="white", fontsize=9)
        ax4.set_xlabel("Transit days", color="white", fontsize=9)
        ax4.set_ylabel("$/kg", color="white", fontsize=9)
        ax4.set_title("Logistics: Cost vs Time", color="white",
                      fontsize=12, fontweight="bold")
        ax4.grid(color=_MIST_RGB, alpha=0.2)
    else:
        ax4.text(0.5, 0.5, "No logistics data", ha="center", va="center",
                 color=tuple(_MIST_RGB), transform=ax4.transAxes)
    _mpl_style(fig, [ax4])

    # ── Row 3: Forecast ─────────────────────────────────────────
    forecast_output = result.get("forecast_output")
    fsignals = []
    if forecast_output and getattr(forecast_output, "signals", None):
        fsignals = [s for s in forecast_output.signals
                    if s.monthly_projections][:2]

    for fi, (ax_f, sig) in enumerate(zip(
        [fig.add_subplot(gs[3, 0]), fig.add_subplot(gs[3, 1])],
        fsignals + [None] * (2 - len(fsignals)),
    )):
        if sig is None:
            ax_f.text(0.5, 0.5, "No forecast data", ha="center", va="center",
                      color=tuple(_MIST_RGB), transform=ax_f.transAxes)
            _mpl_style(fig, [ax_f])
            continue
        color = ({"High": _TEAL_RGB, "Moderate": _BRASS_RGB,
                  "Low": _CORAL_RGB}).get(sig.confidence, _BRASS_RGB)
        months = [p.month for p in sig.monthly_projections]
        proj   = [p.projected_value_usd / 1e6 for p in sig.monthly_projections]
        lower  = [p.lower_bound_usd / 1e6 for p in sig.monthly_projections]
        upper  = [p.upper_bound_usd / 1e6 for p in sig.monthly_projections]
        x = range(len(months))
        ax_f.fill_between(x, lower, upper, color=color, alpha=0.12)
        ax_f.plot(x, proj, color=color, lw=2.5, marker="o", markersize=4)
        ax_f.set_xticks(list(x)[::2])
        ax_f.set_xticklabels([months[i] for i in range(0, len(months), 2)],
                             rotation=45, ha="right", fontsize=7)
        sign = "+" if sig.projected_annual_growth_pct >= 0 else ""
        ax_f.set_title(
            f"{sig.destination_country} · {sign}{sig.projected_annual_growth_pct:.1f}%/yr",
            color="white", fontsize=11, fontweight="bold",
        )
        ax_f.set_ylabel("$M / month", color="white", fontsize=8)
        ax_f.grid(color=_MIST_RGB, alpha=0.15)
        _mpl_style(fig, [ax_f])

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=_NAVY_RGB)
    plt.close(fig)
    buf.seek(0)
    return buf.read()
