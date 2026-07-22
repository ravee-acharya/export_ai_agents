"""
ExportAI visual dashboard — visuals-first redesign.

Design principles:
- Token usage: compact badge in sidebar (top-right feel), not a banner
- Every section leads with a chart, not text
- Text exists only to interpret a visual, never to replace it
- Naive user can scan the page in 30 seconds and know what to do
"""

import streamlit as st

from ui.trade_globe import render_trade_globe
from ui.theme import render_score_ring

# Lazy import — plotly may not be installed on first deploy before
# requirements.txt is processed. Import inside functions so a missing
# package gives a graceful degradation, not a blank page.
def _go():
    import plotly.graph_objects as go
    return go

# Design tokens from Export Trading Terminal (light theme)
_TEAL  = "#0e7a6b"   # brand teal
_BRASS = "#d68a2b"   # amber / warn
_CORAL = "#d15b4a"   # red / weak
_GO    = "#2f9e6e"   # green / positive
_INK   = "#221f1a"   # near-black text
_SUB   = "#6d675c"   # secondary text
_MIST  = "#a29b8c"   # tertiary / faint
_LINE  = "#e7e0d3"   # borders
_BG    = "rgba(0,0,0,0)"
_CARD  = "#ffffff"
_GRID  = "#e7e0d3"
_TEXT  = "#221f1a"
_SOFT  = "#e3f1ee"   # brand soft tint


def _score_tier(score):
    if score >= 60: return "Strong",  _TEAL,  "🟢"
    if score >= 30: return "Moderate", _BRASS, "🟡"
    return               "Weak",    _CORAL, "🔴"


def _best_per_country(scores):
    best = {}
    for s in scores or []:
        c = s.get("destination_country", "")
        if c not in best or s.get("score", 0) > best[c].get("score", 0):
            best[c] = s
    return best


# ─────────────────────────────────────────────────────────────────
# Token badge — lives in the sidebar so it feels top-right
# ─────────────────────────────────────────────────────────────────

def render_token_badge(result):
    """Call this from app.py inside `with st.sidebar:` AFTER render_sidebar()."""
    usage = result.get("token_usage") if result else None
    if not usage or not usage.get("total_tokens"):
        return

    total  = usage.get("total_tokens", 0)
    cost   = usage.get("total_cost_usd", 0.0)
    model  = usage.get("model", "")
    input_ = usage.get("total_input_tokens", 0)
    out_   = usage.get("total_output_tokens", 0)

    cost_str = "Free" if cost == 0.0 else f"${cost:.4f}"
    model_short = model.split("/")[-1][:22]

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"""
<div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);
border-radius:10px;padding:10px 12px;font-family:Arial,sans-serif;">
  <div style="font-size:10px;color:{_MIST};text-transform:uppercase;letter-spacing:.6px;
  margin-bottom:6px;">Last Query</div>
  <div style="font-size:13px;color:{_TEXT};font-weight:600;">🤖 {model_short}</div>
  <div style="display:flex;gap:10px;margin-top:6px;">
    <div style="flex:1;text-align:center;">
      <div style="font-size:18px;font-weight:700;color:{_BRASS};font-family:Georgia,serif;">
        {total:,}</div>
      <div style="font-size:10px;color:{_MIST};">tokens</div>
    </div>
    <div style="flex:1;text-align:center;">
      <div style="font-size:18px;font-weight:700;color:{_TEAL};font-family:Georgia,serif;">
        {cost_str}</div>
      <div style="font-size:10px;color:{_MIST};">cost</div>
    </div>
  </div>
  <div style="font-size:10px;color:{_MIST};margin-top:6px;text-align:center;">
    {input_:,} in · {out_:,} out
  </div>
</div>""",
        unsafe_allow_html=True,
    )

    with st.sidebar.expander("Per-agent breakdown"):
        for a in usage.get("per_agent", []):
            st.caption(
                f"**{a['agent']}** — {a['total_tokens']:,} tokens"
                + ("" if a.get("cost_usd", 0) == 0 else f" (${a['cost_usd']:.5f})")
            )


# ─────────────────────────────────────────────────────────────────
# Main dashboard entry point
# ─────────────────────────────────────────────────────────────────

def render_dashboard(result):
    if not result:
        return

    scores = result.get("opportunity_scores", [])
    best   = _best_per_country(scores)

    _render_hero(result, best)
    _render_radar_chart(best)

    tabs = st.tabs(["🏆 Markets", "💰 Money", "⚠️ Risk", "🚢 Logistics", "🎯 Buyers"])

    with tabs[0]:
        _render_score_cards(best)
        _render_forecast_chart(result)
        _render_trade_globe_section(result)

    with tabs[1]:
        _render_pricing_visual(result)
        _render_fta_visual(result)
        _render_schemes_visual(result)

    with tabs[2]:
        _render_risk_gauges(result)
        _render_readiness_visual(result)

    with tabs[3]:
        _render_logistics_visual(result)
        _render_documents_visual(result)

    with tabs[4]:
        _render_buyers_visual(result)
        _render_competitors_visual(result)

    summary = result.get("summary")
    if summary:
        with st.expander("📝 Full AI Analysis"):
            st.markdown(summary)

    errors = result.get("errors")
    if errors:
        with st.expander("⚠️ Agent issues", expanded=False):
            for e in errors:
                st.caption(f"- {e}")



# ─────────────────────────────────────────────────────────────────
# Export buttons — PDF and PNG download
# ─────────────────────────────────────────────────────────────────

def render_export_buttons(result):
    """
    Renders compact Export PDF / Export Image buttons. Called from
    app.py's title row (top-right of the app), not from inside the
    dashboard, so it's visible immediately without needing to scroll.
    """
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📄 PDF", key="export_pdf_btn", use_container_width=True,
                     help="Download full intelligence report as PDF"):
            with st.spinner("Building PDF..."):
                try:
                    from services.report_exporter import build_pdf
                    pdf_bytes = build_pdf(result)
                    sector = result.get("sector", "export")
                    fname = f"ExportAI_{sector}_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.pdf"
                    st.download_button(
                        label="⬇️ Download",
                        data=pdf_bytes,
                        file_name=fname,
                        mime="application/pdf",
                        key="pdf_download_btn",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"PDF export failed: {e}")

    with col2:
        if st.button("🖼️ Image", key="export_png_btn", use_container_width=True,
                     help="Download high-quality summary image (PNG)"):
            with st.spinner("Rendering..."):
                try:
                    from services.report_exporter import build_png
                    png_bytes = build_png(result)
                    sector = result.get("sector", "export")
                    fname = f"ExportAI_{sector}_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.png"
                    st.download_button(
                        label="⬇️ Download",
                        data=png_bytes,
                        file_name=fname,
                        mime="image/png",
                        key="png_download_btn",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"Image export failed: {e}")


# ─────────────────────────────────────────────────────────────────
# Hero — recommendation + key numbers in one glance
# ─────────────────────────────────────────────────────────────────

def _render_hero(result, best):
    if not best:
        return

    top_c, top_row = max(best.items(), key=lambda kv: kv[1].get("score", 0))
    top_score = top_row.get("score", 0)
    label, color, emoji = _score_tier(top_score)

    # Pull supporting numbers
    breakdown = top_row.get("score_breakdown", {})
    growth = breakdown.get("demand_growth_pct", "—")
    try:    growth_str = f"{float(growth):.1f}%"
    except: growth_str = str(growth)

    risk_lvl = "—"
    risk_output = result.get("risk_output")
    if risk_output and getattr(risk_output, "signals", None):
        for r in risk_output.signals:
            if r.destination_country == top_c:
                risk_lvl = r.risk_level; break

    transit = "—"
    log_output = result.get("logistics_output")
    if log_output and getattr(log_output, "signals", None):
        for l in log_output.signals:
            if l.destination_country == top_c:
                transit = f"{l.sea_transit_days}d"; break

    fob = "—"
    pricing_output = result.get("pricing_output")
    if pricing_output and getattr(pricing_output, "pricing", None):
        for p in pricing_output.pricing:
            if p.destination_country == top_c:
                fob = f"${p.recommended_fob_price}"; break

    others = sorted(
        [(c, s.get("score", 0)) for c, s in best.items() if c != top_c],
        key=lambda x: x[1], reverse=True,
    )
    others_html = " · ".join(
        f'<span style="opacity:.8">{c} {s:.0f}</span>'
        for c, s in others[:4]
    )

    st.markdown(
        f"""<div style="background:linear-gradient(100deg,#123f38,#0e7a6b);
            border-radius:16px;padding:20px 24px;color:#fff;margin-bottom:4px;">
  <div style="font-size:11px;opacity:.7;font-weight:600;letter-spacing:.04em;
    text-transform:uppercase;margin-bottom:8px;">⭐ Top Pick For You · Ranked from demand, price, shipping &amp; safety</div>
  <div style="display:flex;gap:28px;flex-wrap:wrap;align-items:center;">
    <div>
      <div style="font-size:28px;font-weight:800;letter-spacing:-.01em;">{emoji} {top_c}</div>
      <div style="font-size:13px;opacity:.75;margin-top:3px;">Score {top_score:.0f} / 100</div>
    </div>
    <div style="display:flex;gap:24px;flex-wrap:wrap;">
      <div>
        <div style="font-size:11px;opacity:.7;">Demand growth</div>
        <div style="font-size:21px;font-weight:800;color:#6ee7c7;margin-top:2px;">{growth_str}<span style="font-size:11px;opacity:.7;">/yr</span></div>
      </div>
      <div>
        <div style="font-size:11px;opacity:.7;">Selling price</div>
        <div style="font-size:21px;font-weight:800;margin-top:2px;">{fob}</div>
        <div style="font-size:10px;opacity:.6;">per unit (FOB)</div>
      </div>
      <div>
        <div style="font-size:11px;opacity:.7;">Ships in</div>
        <div style="font-size:21px;font-weight:800;margin-top:2px;">{transit}</div>
        <div style="font-size:10px;opacity:.6;">by sea</div>
      </div>
      <div>
        <div style="font-size:11px;opacity:.7;">Risk</div>
        <div style="font-size:21px;font-weight:800;margin-top:2px;">{risk_lvl}</div>
        <div style="font-size:10px;opacity:.6;">country safety</div>
      </div>
    </div>
  </div>
  <div style="font-size:11px;opacity:.55;margin-top:10px;border-top:1px solid rgba(255,255,255,.15);padding-top:10px;">
    Other markets: {others_html if others_html else "—"}
  </div>
</div>""",
        unsafe_allow_html=True,
    )
    st.markdown("")


# ─────────────────────────────────────────────────────────────────
# Radar chart — all markets on one multi-axis visual
# ─────────────────────────────────────────────────────────────────

def _render_radar_chart(best):
    if len(best) < 2:
        return

    # Axes and scoring factors — extract from score_breakdown
    axes = ["Demand", "Price", "Logistics", "Safety", "Overall"]

    def _row_values(country, row):
        bd = row.get("score_breakdown", {})
        overall = float(row.get("score", 50)) / 100

        try:    demand = min(1, float(bd.get("demand_growth_pct", 5)) / 20)
        except: demand = 0.4

        try:    price = float(bd.get("competitiveness_score", 5)) / 10
        except: price = 0.5

        try:    logistics = 1 - (float(bd.get("logistics_cost", 0.5)))
        except: logistics = 0.5

        cap_dist = bd.get("capability_distance", 0.5)
        try:    safety = 1 - float(cap_dist) / 5
        except: safety = 0.5

        return [demand, price, logistics, safety, overall]

    colors = [_TEAL, _BRASS, _CORAL, "#9CA3BF", "#C084FC"]
    _fill_colors = [
        "rgba(63,184,175,0.07)",   # teal
        "rgba(227,168,87,0.07)",   # brass
        "rgba(226,114,91,0.07)",   # coral
        "rgba(156,163,191,0.07)",  # mist
        "rgba(192,132,252,0.07)",  # purple
    ]
    fig = _go().Figure()

    for i, (country, row) in enumerate(list(best.items())[:5]):
        vals = _row_values(country, row)
        vals_pct = [v * 100 for v in vals]
        fig.add_trace(_go().Scatterpolar(
            r=vals_pct + [vals_pct[0]],
            theta=axes + [axes[0]],
            fill="toself",
            name=country,
            line=dict(color=colors[i % len(colors)], width=2),
            fillcolor=_fill_colors[i % len(_fill_colors)],
        ))

    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 100],
                            gridcolor=_GRID, color=_MIST,
                            tickfont=dict(size=9, color=_MIST)),
            angularaxis=dict(gridcolor=_GRID, color=_INK,
                             tickfont=dict(size=12, color=_TEXT)),
        ),
        paper_bgcolor=_BG,
        legend=dict(font=dict(color=_INK, size=12), bgcolor="rgba(0,0,0,0)"),
        height=340,
        margin=dict(t=20, b=20, l=40, r=40),
        title=dict(text="Market Comparison Radar",
                   font=dict(color=_INK, size=14, family="Georgia,serif")),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption("Outer edge = stronger on that dimension")
    st.divider()



# ─────────────────────────────────────────────────────────────────
# Forecast chart — 12-month demand projection with confidence band
# ─────────────────────────────────────────────────────────────────

def _render_forecast_chart(result):
    forecast_output = result.get("forecast_output")
    if not forecast_output or not getattr(forecast_output, "signals", None):
        return

    signals = [s for s in forecast_output.signals if s.monthly_projections]
    if not signals:
        return

    st.divider()
    st.subheader("📈 12-Month Demand Forecast")
    st.caption(
        "Linear trend projection from 3 years of UN Comtrade data. "
        "Shaded band = 80% confidence interval (wider = less certain)."
    )

    # One chart per market (up to 4), laid out in 2-column grid
    cols_per_row = 2
    rows = [signals[i:i+cols_per_row] for i in range(0, min(len(signals), 4), cols_per_row)]

    for row_signals in rows:
        cols = st.columns(len(row_signals))
        for col, signal in zip(cols, row_signals):
            with col:
                _render_single_forecast(signal)


def _render_single_forecast(signal):
    """Render one forecast line chart with confidence band."""
    go = _go()
    projs = signal.monthly_projections
    months = [p.month for p in projs]
    projected = [p.projected_value_usd / 1_000_000 for p in projs]  # in $M
    lower = [p.lower_bound_usd / 1_000_000 for p in projs]
    upper = [p.upper_bound_usd / 1_000_000 for p in projs]

    conf_colors = {"High": _TEAL, "Moderate": _BRASS, "Low": _CORAL}
    _fill_rgba = {
        "High":     "rgba(63,184,175,0.12)",
        "Moderate": "rgba(227,168,87,0.12)",
        "Low":      "rgba(226,114,91,0.12)",
    }
    line_color = conf_colors.get(signal.confidence, _BRASS)
    fill_color = _fill_rgba.get(signal.confidence, "rgba(227,168,87,0.12)")

    fig = go.Figure()

    # Confidence band (upper then lower reversed for fill)
    fig.add_trace(go.Scatter(
        x=months + months[::-1],
        y=upper + lower[::-1],
        fill="toself",
        fillcolor=fill_color,
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=False,
        hoverinfo="skip",
    ))

    # Projection line
    fig.add_trace(go.Scatter(
        x=months,
        y=projected,
        mode="lines+markers",
        line=dict(color=line_color, width=2.5),
        marker=dict(size=5, color=line_color),
        name=f"{signal.destination_country}",
        hovertemplate="%{x}: $%{y:.2f}M<extra></extra>",
    ))

    growth_sign = "+" if signal.projected_annual_growth_pct >= 0 else ""
    title_text = (
        f"{signal.destination_country} · HS {signal.hs_code}<br>"
        f"<span style='font-size:11px;color:{_MIST}'>"
        f"{growth_sign}{signal.projected_annual_growth_pct:.1f}%/yr · "
        f"{signal.confidence} confidence (R²={signal.r_squared:.2f})</span>"
    )

    fig.update_layout(
        title=dict(text=title_text, font=dict(color=_INK, size=13)),
        paper_bgcolor=_BG, plot_bgcolor=_BG,
        height=220,
        margin=dict(t=55, b=30, l=10, r=10),
        xaxis=dict(
            color=_MIST, gridcolor=_GRID,
            tickangle=45, tickfont=dict(size=9),
        ),
        yaxis=dict(
            color=_MIST, gridcolor=_GRID,
            title=dict(text="$M USD / month", font=dict(size=10, color=_MIST)),
        ),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption(signal.outlook_label)


# ─────────────────────────────────────────────────────────────────
# Score cards — one visual card per market, no tables
# ─────────────────────────────────────────────────────────────────

def _render_score_cards(best):
    if not best:
        return

    sorted_markets = sorted(best.items(), key=lambda x: x[1].get("score", 0), reverse=True)
    cols = st.columns(min(len(sorted_markets), 4))

    for i, (country, row) in enumerate(sorted_markets[:4]):
        score = row.get("score", 0)
        label, color, emoji = _score_tier(score)
        bd = row.get("score_breakdown", {})

        try:    growth = f"{float(bd.get('demand_growth_pct', 0)):.1f}%"
        except: growth = "—"

        with cols[i]:
            tier_colors = {"Strong": "#2f9e6e", "Moderate": "#d68a2b", "Weak": "#d15b4a"}
            tier_soft   = {"Strong": "#e8f5ee", "Moderate": "#fdf0dc", "Weak": "#fce8e4"}
            tc = tier_colors.get(label, _TEAL)
            ts = tier_soft.get(label, _SOFT)
            st.markdown(
                f"""<div style="background:#fff;border:1px solid #e7e0d3;
                border-radius:14px;padding:18px;box-shadow:0 1px 3px rgba(40,30,10,.04);">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
    <div style="font-size:18px;font-weight:800;color:#221f1a;">{country}</div>
    <span style="font-size:10px;font-weight:700;color:{tc};background:{ts};
      padding:4px 9px;border-radius:20px;">{emoji} {label}</span>
  </div>
  <div style="font-size:32px;font-weight:800;color:{tc};letter-spacing:-.01em;">{score:.0f}</div>
  <div style="font-size:11px;color:#a29b8c;margin-top:2px;">/ 100 opportunity score</div>
  <div style="height:6px;background:#f1ebde;border-radius:4px;overflow:hidden;margin-top:10px;">
    <div style="width:{score}%;height:100%;background:{tc};border-radius:4px;"></div>
  </div>
  <div style="font-size:12px;color:#2f9e6e;font-weight:600;margin-top:8px;">↑ {growth} demand growth</div>
</div>""",
                unsafe_allow_html=True,
            )

    st.markdown("")


# ─────────────────────────────────────────────────────────────────
# Globe
# ─────────────────────────────────────────────────────────────────

def _render_trade_globe_section(result):
    scores = result.get("opportunity_scores", [])
    if not scores:
        return
    st.divider()
    st.caption("🌍 Trade routes from India — drag to rotate, scroll to zoom")
    render_trade_globe(scores)


# ─────────────────────────────────────────────────────────────────
# Pricing visual — horizontal bar chart
# ─────────────────────────────────────────────────────────────────

def _render_pricing_visual(result):
    pricing_output = result.get("pricing_output")
    if not pricing_output or not getattr(pricing_output, "pricing", None):
        st.info("No pricing data for this query.")
        return

    st.subheader("💰 Pricing Signals")

    countries, margins, fob_prices = [], [], []
    for p in pricing_output.pricing:
        countries.append(p.destination_country)
        margins.append(float(p.expected_margin_pct or 0))
        fob_prices.append(float(p.recommended_fob_price or 0))

    col1, col2 = st.columns(2)

    with col1:
        fig = _go().Figure(_go().Bar(
            y=countries, x=margins,
            orientation="h",
            marker_color=[_TEAL if m >= 20 else _BRASS if m >= 10 else _CORAL for m in margins],
            text=[f"{m:.0f}%" for m in margins],
            textposition="outside",
            textfont=dict(color=_INK),
            hovertemplate="%{y}: %{x:.0f}% margin<extra></extra>",
        ))
        fig.update_layout(
            title=dict(text="Expected Margin %", font=dict(color=_INK, size=13)),
            paper_bgcolor=_BG, plot_bgcolor=_BG, height=220,
            margin=dict(t=40, b=10, l=10, r=60),
            xaxis=dict(color=_MIST, gridcolor=_GRID),
            yaxis=dict(color=_TEXT),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col2:
        fig2 = _go().Figure(_go().Bar(
            y=countries, x=fob_prices,
            orientation="h",
            marker_color=_BRASS,
            text=[f"${v:.0f}" for v in fob_prices],
            textposition="outside",
            textfont=dict(color=_INK),
            hovertemplate="%{y}: $%{x:.0f} FOB<extra></extra>",
        ))
        fig2.update_layout(
            title=dict(text="Recommended FOB Price ($)", font=dict(color=_INK, size=13)),
            paper_bgcolor=_BG, plot_bgcolor=_BG, height=220,
            margin=dict(t=40, b=10, l=10, r=60),
            xaxis=dict(color=_MIST, gridcolor=_GRID),
            yaxis=dict(color=_TEXT),
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────
# FTA visual — duty savings as a clean table of badges
# ─────────────────────────────────────────────────────────────────

def _render_fta_visual(result):
    fta_output = result.get("fta_output")
    if not fta_output or not getattr(fta_output, "signals", None):
        return

    st.subheader("📜 Duty & Trade Deals")

    data = []
    for s in fta_output.signals:
        data.append({
            "Market": s.destination_country,
            "Standard Duty": f"{s.mfn_tariff_pct}%",
            "Your Duty": f"{s.preferential_tariff_pct}%",
            "You Save": f"{s.tariff_savings_pct}pp",
            "Deal": s.fta_name if getattr(s, "eligible", False) else "None",
        })

    if not data:
        return

    # Duty savings waterfall
    countries = [d["Market"] for d in data]
    def _safe_pct(val):
        try: return float(str(val or 0).replace("%", "").strip() or 0)
        except: return 0.0

    standard  = [_safe_pct(d["Standard Duty"]) for d in data]
    preferred = [_safe_pct(d["Your Duty"]) for d in data]

    fig = _go().Figure()
    fig.add_trace(_go().Bar(name="Standard duty", x=countries, y=standard,
                         marker_color=_CORAL, opacity=0.6))
    fig.add_trace(_go().Bar(name="Your actual duty", x=countries, y=preferred,
                         marker_color=_TEAL))
    fig.update_layout(
        barmode="overlay",
        title=dict(text="Duty Rate Comparison (%)", font=dict(color=_INK, size=13)),
        paper_bgcolor=_BG, plot_bgcolor=_BG, height=240,
        margin=dict(t=40, b=20, l=10, r=10),
        xaxis=dict(color=_TEXT),
        yaxis=dict(color=_MIST, gridcolor=_GRID, title="Duty %"),
        legend=dict(font=dict(color=_INK), bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption("Teal = what you actually pay with trade agreement · Red = standard rate")


# ─────────────────────────────────────────────────────────────────
# Schemes — icon cards, no walls of text
# ─────────────────────────────────────────────────────────────────

def _render_schemes_visual(result):
    scheme_output = result.get("scheme_compliance_output")
    if not scheme_output:
        return
    schemes = scheme_output.eligible_schemes()
    if not schemes:
        return

    st.subheader("🏛 Government Support")
    cols = st.columns(min(len(schemes), 3))
    for i, s in enumerate(schemes[:3]):
        with cols[i]:
            st.markdown(
                f"""<div style="background:#fff;border:1px solid #e7e0d3;
                border-radius:12px;padding:14px;">
  <div style="font-size:13px;font-weight:700;color:#0e7a6b;margin-bottom:6px;">{s.name}</div>
  <div style="font-size:11px;color:{_MIST};margin-bottom:4px;">{s.issuing_body}</div>
  <div style="font-size:12px;color:{_TEXT};">{s.benefit_summary[:100]}{'…' if len(s.benefit_summary)>100 else ''}</div>
</div>""",
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────
# Risk — gauge charts, one per market
# ─────────────────────────────────────────────────────────────────

def _render_risk_gauges(result):
    risk_output = result.get("risk_output")
    if not risk_output or not getattr(risk_output, "signals", None):
        st.info("No risk data for this query.")
        return

    st.subheader("⚠️ Country Risk")

    signals = risk_output.signals[:4]
    cols = st.columns(len(signals))

    _risk_to_score = {"Low": 15, "Moderate": 45, "High": 72, "Severe": 92}
    _risk_color    = {"Low": _TEAL, "Moderate": _BRASS, "High": "#E2725B", "Severe": "#EF4444"}

    for i, signal in enumerate(signals):
        score = _risk_to_score.get(signal.risk_level, 50)
        color = _risk_color.get(signal.risk_level, _BRASS)

        fig = _go().Figure(_go().Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "", "font": {"size": 1, "color": "rgba(0,0,0,0)"}},  # hidden
            title={"text": signal.destination_country,
                   "font": {"size": 14, "color": _TEXT}},
            gauge={
                "axis": {"range": [0, 100], "visible": False},
                "bar": {"color": color, "thickness": 0.6},
                "bgcolor": "rgba(255,255,255,0.05)",
                "bordercolor": "rgba(0,0,0,0)",
                "steps": [
                    {"range": [0, 30],  "color": "rgba(63,184,175,0.12)"},
                    {"range": [30, 60], "color": "rgba(227,168,87,0.12)"},
                    {"range": [60, 100],"color": "rgba(226,114,91,0.12)"},
                ],
            },
        ))
        fig.update_layout(
            paper_bgcolor=_BG, height=160,
            margin=dict(t=30, b=0, l=10, r=10),
        )
        with cols[i]:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            risk_icons = {"Low":"🟢","Moderate":"🟡","High":"🟠","Severe":"🔴"}
            st.markdown(
                f"<div style='text-align:center;font-size:12px;color:{color};margin-top:-10px;'>"
                f"{risk_icons.get(signal.risk_level,'⚪')} {signal.risk_level}</div>",
                unsafe_allow_html=True,
            )
            if signal.sanctions_flag:
                st.error("⛔ Sanctions apply")


# ─────────────────────────────────────────────────────────────────
# Readiness — visual gap meter
# ─────────────────────────────────────────────────────────────────

def _render_readiness_visual(result):
    cap = result.get("capability_gap_output")
    if not cap:
        return

    st.subheader("🎓 Export Readiness")
    gap = cap.gap_score  # 1-5, lower = better

    readiness_pct = max(0, (5 - gap) / 4 * 100)
    color = _TEAL if readiness_pct >= 60 else _BRASS if readiness_pct >= 30 else _CORAL
    label = "Well prepared" if readiness_pct >= 60 else "Some gaps" if readiness_pct >= 30 else "Major gaps"

    fig = _go().Figure(_go().Indicator(
        mode="gauge+number",
        value=readiness_pct,
        number={"suffix": "%", "font": {"size": 28, "color": color}},
        title={"text": label, "font": {"size": 14, "color": _TEXT}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": _MIST,
                     "tickfont": {"color": _MIST}},
            "bar": {"color": color, "thickness": 0.5},
            "bgcolor": "rgba(255,255,255,0.04)",
            "bordercolor": "rgba(0,0,0,0)",
            "steps": [
                {"range": [0, 40],  "color": "rgba(226,114,91,0.12)"},
                {"range": [40, 70], "color": "rgba(227,168,87,0.12)"},
                {"range": [70, 100],"color": "rgba(63,184,175,0.12)"},
            ],
        },
    ))
    fig.update_layout(paper_bgcolor=_BG, height=200,
                      margin=dict(t=20, b=0, l=20, r=20))

    col1, col2 = st.columns([1, 1])
    with col1:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col2:
        if cap.missing_requirements:
            st.markdown("**Gaps to close:**")
            for r in cap.missing_requirements:
                st.markdown(f"- {r}")
        if cap.upgrade_path:
            st.markdown("**Next steps:**")
            for step in cap.upgrade_path[:3]:
                st.markdown(f"- {step}")


# ─────────────────────────────────────────────────────────────────
# Logistics — transit time + cost scatter
# ─────────────────────────────────────────────────────────────────

def _render_logistics_visual(result):
    log_output = result.get("logistics_output")
    if not log_output or not getattr(log_output, "signals", None):
        st.info("No logistics data for this query.")
        return

    st.subheader("🚢 Shipping Overview")

    countries, days, costs, sizes = [], [], [], []
    for s in log_output.signals:
        countries.append(s.destination_country)
        days.append(float(s.sea_transit_days or 0))
        costs.append(float(s.freight_cost_usd_per_kg or 0))
        sizes.append(20)

    fig = _go().Figure(_go().Scatter(
        x=days, y=costs,
        mode="markers+text",
        text=countries,
        textposition="top center",
        textfont=dict(color=_INK, size=12),
        marker=dict(
            size=22, color=_TEAL,
            line=dict(color=_BRASS, width=1.5),
        ),
        hovertemplate="%{text}<br>%{x} days · $%{y}/kg<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor=_BG, plot_bgcolor=_BG, height=280,
        margin=dict(t=20, b=30, l=10, r=10),
        xaxis=dict(title="Sea transit (days)", color=_MIST, gridcolor=_GRID),
        yaxis=dict(title="Freight cost ($/kg)", color=_MIST, gridcolor=_GRID),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption("Bottom-left = faster & cheaper to ship there")

    # Document checklist as compact chips
    doc_output = result.get("document_intelligence_output")
    if doc_output and getattr(doc_output, "checklists", None):
        st.markdown("**📋 Documents needed:**")
        for cl in doc_output.checklists[:2]:
            st.markdown(f"**{cl.destination_country}:** " +
                       " · ".join(cl.mandatory_documents[:5]))


# ─────────────────────────────────────────────────────────────────
# Documents visual (if standalone)
# ─────────────────────────────────────────────────────────────────

def _render_documents_visual(result):
    cert_output = result.get("certification_output")
    if not cert_output or not getattr(cert_output, "certifications", None):
        return

    st.subheader("📝 Certification Costs & Timelines")

    names, cost_los, cost_his, time_los, time_his = [], [], [], [], []
    for c in cert_output.certifications[:5]:
        names.append(c.name[:25])
        lo, hi = c.cost_usd_range
        tlo, thi = c.timeline_weeks_range
        cost_los.append(float(lo or 0))
        cost_his.append(float(hi or 0))
        time_los.append(float(tlo or 0))
        time_his.append(float(thi or 0))

    if not names:
        return

    fig = _go().Figure()
    fig.add_trace(_go().Bar(
        name="Min cost", y=names, x=cost_los, orientation="h",
        marker_color=_BRASS, opacity=0.6,
    ))
    fig.add_trace(_go().Bar(
        name="Max cost", y=names, x=cost_his, orientation="h",
        marker_color=_BRASS, opacity=0.9,
    ))
    fig.update_layout(
        barmode="overlay",
        title=dict(text="Certification Cost Range (USD)",
                   font=dict(color=_INK, size=13)),
        paper_bgcolor=_BG, plot_bgcolor=_BG, height=220,
        margin=dict(t=40, b=20, l=10, r=10),
        xaxis=dict(color=_MIST, gridcolor=_GRID, title="USD"),
        yaxis=dict(color=_TEXT),
        legend=dict(font=dict(color=_INK), bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────
# Buyers — persona cards + channel pills
# ─────────────────────────────────────────────────────────────────

def _render_buyers_visual(result):
    buyer_output = result.get("buyer_discovery_output")
    if not buyer_output or not getattr(buyer_output, "buyer_personas", None):
        st.info("No buyer data for this query.")
        return

    st.subheader("🎯 Who Will Buy From You")
    st.caption("Buyer types, not specific companies — use to shape your outreach")

    cols = st.columns(min(len(buyer_output.buyer_personas), 3))
    for i, persona in enumerate(buyer_output.buyer_personas[:3]):
        with cols[i]:
            st.markdown(
                f"""<div style="background:#faf7f0;border:1px solid #e7e0d3;
                border-radius:12px;padding:14px;height:180px;overflow:hidden;">
  <div style="font-size:13px;font-weight:700;color:#0e7a6b;margin-bottom:6px;">
    {persona.persona_name}</div>
  <div style="font-size:11px;color:{_TEXT};margin-bottom:8px;line-height:1.5;">
    {persona.description[:120]}{'…' if len(persona.description)>120 else ''}</div>
  <div style="font-size:10px;color:#d68a2b;">📦 {persona.typical_order_size}</div>
</div>""",
                unsafe_allow_html=True,
            )

    if getattr(buyer_output, "recommended_channels", None):
        st.markdown("**Where to find them:**")
        channel_html = " ".join(
            f'<span style="background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.12);'
            f'border-radius:20px;padding:3px 10px;font-size:11px;color:#0e7a6b;margin:2px;'
            f'display:inline-block;">{c}</span>'
            for c in buyer_output.recommended_channels[:6]
        )
        st.markdown(channel_html, unsafe_allow_html=True)

    if getattr(buyer_output, "outreach_tips", None):
        st.markdown("**Quick tips:**")
        for tip in buyer_output.outreach_tips[:3]:
            st.markdown(f"- {tip}")


# ─────────────────────────────────────────────────────────────────
# Competitors — market share donut
# ─────────────────────────────────────────────────────────────────

def _render_competitors_visual(result):
    comp_output = result.get("competitor_output")
    if not comp_output or not getattr(comp_output, "signals", None):
        return

    st.subheader("🌐 Competition Landscape")

    for signal in comp_output.signals[:2]:
        if not getattr(signal, "top_competitors", None):
            continue

        competitors = signal.top_competitors[:5]
        labels = [c.country for c in competitors] + ["India", "Others"]
        india_share = float(signal.india_market_share_pct or 5)
        comp_shares = [float(c.market_share_pct or 0) for c in competitors]
        other_share = max(0, 100 - sum(comp_shares) - india_share)
        values = comp_shares + [india_share, other_share]
        colors_pie = [_CORAL] * len(competitors) + [_TEAL, _MIST]

        fig = _go().Figure(_go().Pie(
            labels=labels, values=values,
            marker=dict(colors=colors_pie,
                        line=dict(color="#0D1220", width=2)),
            textfont=dict(color=_INK, size=11),
            hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
            hole=0.45,
        ))
        fig.update_layout(
            title=dict(
                text=f"{signal.destination_country} market share",
                font=dict(color=_INK, size=13),
            ),
            paper_bgcolor=_BG, height=260,
            margin=dict(t=40, b=10, l=10, r=10),
            legend=dict(font=dict(color=_INK, size=10),
                        bgcolor="rgba(0,0,0,0)"),
            annotations=[dict(
                text=f"India<br>{india_share:.0f}%",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=12, color=_TEAL),
            )],
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
