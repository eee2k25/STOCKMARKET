#!/usr/bin/env python3
"""
HTML email report builder for the Market Advisory Engine.

Renders the dict produced by indian_market_monitor.generate_advisory_report()
into a professional, email-client-safe HTML digest (table layout + inline
styles, since Gmail/Outlook strip <style> blocks and class selectors).

Usage:
    from generate_preview import build_html_report
    html = build_html_report(report_dict)
"""

import html

# Brand palette (kept in sync with the dashboard design system)
INK = "#0f172a"        # headings
BODY = "#334155"       # body text
MUTED = "#64748b"      # secondary text
UP = "#059669"         # gains / positive
DOWN = "#dc2626"       # losses / negative
WARN = "#b45309"       # caution
LINE = "#e2e8f0"       # hairlines
BG = "#f1f5f9"         # page background
CARD = "#ffffff"       # card surface
GREEN_TINT = "#ecfdf5"
RED_TINT = "#fef2f2"
AMBER_TINT = "#fffbeb"

TRANCHE_LABELS = {
    "conservative": ("Tranche 1 (20%) now", "Tranche 2 (30%) if dips deepen", "Tranche 3 (50%) at capitulation"),
    "moderate": ("Tranche 1 (30%) now", "Tranche 2 (30%) if dips deepen", "Tranche 3 (40%) at capitulation"),
    "aggressive": ("Tranche 1 (40%) now", "Tranche 2 (35%) if dips deepen", "Tranche 3 (25%) at capitulation"),
}


def _esc(s):
    return html.escape(str(s if s is not None else ""))


def _inr(n):
    try:
        return f"{float(n):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _chg_cell(value, suffix="%"):
    """Colored change cell: value is a signed percentage."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return f'<span style="color:{MUTED}">—</span>'
    color = UP if v >= 0 else DOWN
    sign = "+" if v > 0 else ""
    return f'<span style="color:{color};font-weight:700">{sign}{v:.2f}{suffix}</span>'


def _status_pill(drawdown, fund=False):
    t1, t2 = (-10.0, -4.0) if fund else (-20.0, -8.0)
    if drawdown <= t1:
        label, bg, fg = ("HIGH CONVICTION DIP" if fund else "DEEP VALUE DIP"), RED_TINT, DOWN
    elif drawdown <= t2:
        label, bg, fg = "VALUE PULLBACK" if fund else "CORRECTION ZONE", AMBER_TINT, WARN
    else:
        label, bg, fg = "HOLDING SUPPORT" if fund else "CONSOLIDATION", GREEN_TINT, UP
    return (f'<span style="display:inline-block;padding:3px 9px;border-radius:99px;'
            f'background:{bg};color:{fg};font-size:11px;font-weight:700;'
            f'letter-spacing:.04em;white-space:nowrap">{label}</span>')


def _index_banner(index):
    idx = index or {}
    price = _inr(idx.get("price"))
    chg = idx.get("pct_change", 0) or 0
    color = UP if chg >= 0 else DOWN
    arrow = "▲" if chg >= 0 else "▼"
    off_peak = 0.0
    try:
        if idx.get("high_52w"):
            off_peak = (float(idx["price"]) - float(idx["high_52w"])) / float(idx["high_52w"]) * 100
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    peak_color = DOWN if off_peak <= -10 else (WARN if off_peak <= -4 else UP)
    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:{CARD};border:1px solid {LINE};border-radius:14px;margin:0 0 22px">
      <tr>
        <td style="padding:22px 26px">
          <p style="margin:0 0 6px;font-size:12px;font-weight:700;letter-spacing:.12em;color:{MUTED};text-transform:uppercase">
            NIFTY 50 &nbsp;·&nbsp; NSE
          </p>
          <p style="margin:0 0 10px;font-size:34px;font-weight:800;color:{INK};line-height:1.1">
            {price}
            <span style="font-size:15px;font-weight:700;color:{color};margin-left:8px">
              {arrow} {abs(float(chg or 0)):.2f}%
            </span>
          </p>
          <p style="margin:0;font-size:13px;color:{BODY}">
            52-week high <b style="color:{INK}">{_inr(idx.get('high_52w'))}</b>
            &nbsp;·&nbsp; distance from peak
            <b style="color:{peak_color}">{off_peak:+.2f}%</b>
          </p>
        </td>
      </tr>
    </table>"""


def _instrument_table(rows, kind):
    """rows: list of dicts; kind: 'stocks' | 'funds'."""
    if not rows:
        return f"""
        <div style="background:{BG};border:1px dashed {LINE};border-radius:12px;padding:18px;
                    text-align:center;color:{MUTED};font-size:13px">
          No data available for this section in this run.
        </div>"""

    is_fund = kind == "funds"
    body = []
    for r in rows:
        dd = float(r.get("drawdown_52w", 0) or 0)
        if is_fund:
            ident = r.get("name", "")
            sub = f"{r.get('category', '')} · Code {r.get('code', '—')}"
            price = _inr(r.get("nav"))
        else:
            ident = f"{r.get('ticker', '')} — {r.get('name', '')}"
            sub = r.get("sector", "")
            price = _inr(r.get("price"))
        upside = f"+{float(r.get('recovery_upside_pct', 0) or 0):.2f}%"
        body.append(f"""
        <tr>
          <td style="padding:12px 14px;border-bottom:1px solid {LINE};vertical-align:top">
            <span style="display:block;font-size:13.5px;font-weight:700;color:{INK}">{_esc(ident)}</span>
            <span style="display:block;font-size:11.5px;color:{MUTED};margin-top:2px">{_esc(sub)}</span>
          </td>
          <td style="padding:12px 14px;border-bottom:1px solid {LINE};text-align:right;white-space:nowrap">
            <span style="font-size:13.5px;font-weight:700;color:{INK}">₹{price}</span><br>
            <span style="font-size:12px">{_chg_cell(r.get('pct_change'))}</span>
          </td>
          <td style="padding:12px 14px;border-bottom:1px solid {LINE};text-align:right;white-space:nowrap">
            <span style="font-size:12px;color:{MUTED}">52w high ₹{_inr(r.get('high_52w'))}</span><br>
            <span style="font-size:13px;font-weight:700;color:{DOWN if dd <= (-10 if is_fund else -20) else WARN if dd <= (-4 if is_fund else -8) else UP}">
              {dd:+.2f}%
            </span>
          </td>
          <td style="padding:12px 14px;border-bottom:1px solid {LINE};text-align:right;white-space:nowrap">
            <span style="font-size:13px;font-weight:700;color:{UP}">{upside}</span>
          </td>
          <td style="padding:12px 14px;border-bottom:1px solid {LINE};text-align:center">
            {_status_pill(dd, fund=is_fund)}
          </td>
        </tr>""")
    head_cols = ("Instrument", "Price / NAV", "From 52w high", "Recovery", "Status")
    header = "".join(
        f'<th style="padding:10px 14px;text-align:{"left" if i == 0 else "right" if i < 4 else "center"};'
        f'font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:{MUTED};'
        f'border-bottom:2px solid {LINE};white-space:nowrap">{c}</th>'
        for i, c in enumerate(head_cols))
    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:{CARD};border:1px solid {LINE};border-radius:14px;overflow:hidden;border-collapse:collapse">
      <thead><tr>{header}</tr></thead>
      <tbody>{''.join(body)}</tbody>
    </table>"""


def _dip_rows(rows, kind):
    """Highlight the instruments currently flagged as dips."""
    is_fund = kind == "funds"
    dips = [r for r in rows if r.get("is_dip")]
    if not dips:
        return f"""
        <p style="margin:0;background:{GREEN_TINT};border:1px solid #a7f3d0;border-radius:10px;
                  padding:12px 16px;font-size:13px;color:{UP};font-weight:600">
          ✔ Clean tape — nothing on your watchlist is in a dip zone right now. Discipline beats FOMO.
        </p>"""
    dips.sort(key=lambda r: float(r.get("drawdown_52w", 0) or 0))
    items = []
    for r in dips[:5]:
        dd = float(r.get("drawdown_52w", 0) or 0)
        name = r.get("name") if is_fund else f"{r.get('ticker')} — {r.get('name')}"
        items.append(
            f'<li style="margin:0 0 8px;font-size:13.5px;color:{BODY}">'
            f'<b style="color:{INK}">{_esc(name)}</b> '
            f'<span style="color:{DOWN};font-weight:700">({dd:+.1f}% from peak)</span> '
            f'→ recovery upside <b style="color:{UP}">+{float(r.get("recovery_upside_pct", 0) or 0):.1f}%</b>'
            f'</li>')
    label = "Mutual funds" if is_fund else "Stocks"
    return f"""
    <p style="margin:0 0 8px;font-size:12px;font-weight:700;letter-spacing:.1em;
              text-transform:uppercase;color:{MUTED}">{label} in dip zone ({len(dips)})</p>
    <ul style="margin:0;padding-left:20px">{''.join(items)}</ul>"""


def _action_plan(risk):
    t1, t2, t3 = TRANCHE_LABELS.get((risk or "moderate").lower(), TRANCHE_LABELS["moderate"])
    cells = []
    for i, (title, tint) in enumerate(((t1, GREEN_TINT), (t2, AMBER_TINT), (t3, RED_TINT)), start=1):
        cells.append(f"""
        <td width="33.33%" style="padding:0 6px">
          <div style="background:{tint};border:1px solid {LINE};border-radius:12px;padding:16px;text-align:center">
            <div style="font-size:11px;font-weight:700;letter-spacing:.1em;color:{MUTED}">TRANCHE {i}</div>
            <div style="font-size:14px;font-weight:800;color:{INK};margin-top:6px">{title}</div>
          </div>
        </td>""")
    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:separate;margin:6px 0 0">
      <tr>{''.join(cells)}</tr>
    </table>"""


def build_html_report(rep):
    """rep: dict from indian_market_monitor.generate_advisory_report()."""
    risk = rep.get("risk_profile", "moderate")
    idx = rep.get("index", {})
    stocks = rep.get("stocks", [])
    funds = rep.get("funds", [])

    dip_funds = sum(1 for f in funds if f.get("is_dip"))
    dip_stocks = sum(1 for s in stocks if s.get("is_dip"))

    return f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Market Advisory Digest</title></head>
<body style="margin:0;padding:24px 12px;background:{BG};font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif">

<div style="max-width:680px;margin:0 auto">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#065f46,#047857);border-radius:16px 16px 0 0;padding:26px 28px">
    <p style="margin:0;font-size:11px;font-weight:700;letter-spacing:.16em;color:#a7f3d0;text-transform:uppercase">
      MEK Stock Alert Pro
    </p>
    <h1 style="margin:6px 0 0;font-size:22px;font-weight:800;color:#ffffff;letter-spacing:-.01em">
      Daily Downturn &amp; Dip Digest
    </h1>
    <p style="margin:8px 0 0;font-size:12.5px;color:#d1fae5">
      {_esc(rep.get('timestamp', ''))} &nbsp;·&nbsp; Moderate risk profile &nbsp;·&nbsp;
      {_esc(rep.get('recipient_email', ''))}
    </p>
  </div>

  <!-- Body -->
  <div style="background:{CARD};border:1px solid {LINE};border-top:none;border-radius:0 0 16px 16px;padding:24px 24px 8px">

    {_index_banner(idx)}

    <!-- Summary -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:separate;margin:0 0 22px">
      <tr>
        <td width="50%" style="padding:0 5px">
          <div style="background:{BG};border:1px solid {LINE};border-radius:12px;padding:14px 16px;text-align:center">
            <div style="font-size:26px;font-weight:800;color:{DOWN if dip_funds else UP}">{dip_funds}/{len(funds)}</div>
            <div style="font-size:11px;font-weight:700;letter-spacing:.08em;color:{MUTED};text-transform:uppercase">Funds in dip zone</div>
          </div>
        </td>
        <td width="50%" style="padding:0 5px">
          <div style="background:{BG};border:1px solid {LINE};border-radius:12px;padding:14px 16px;text-align:center">
            <div style="font-size:26px;font-weight:800;color:{DOWN if dip_stocks else UP}">{dip_stocks}/{len(stocks)}</div>
            <div style="font-size:11px;font-weight:700;letter-spacing:.08em;color:{MUTED};text-transform:uppercase">Stocks in dip zone</div>
          </div>
        </td>
      </tr>
    </table>

    <!-- Dip highlights -->
    <h2 style="margin:0 0 12px;font-size:15px;font-weight:800;color:{INK}">🎯 Today's dip radar</h2>
    {_dip_rows(funds, 'funds')}
    <div style="height:14px;line-height:14px">&nbsp;</div>
    {_dip_rows(stocks, 'stocks')}

    <!-- Action plan -->
    <h2 style="margin:26px 0 4px;font-size:15px;font-weight:800;color:{INK}">🛡️ Staggered action plan</h2>
    <p style="margin:0 0 10px;font-size:12.5px;color:{MUTED}">
      Calibrated for a <b>{_esc(risk)}</b> risk profile — never deploy the full tranche in one shot.
    </p>
    {_action_plan(risk)}

    <!-- Detail tables -->
    <h2 style="margin:28px 0 12px;font-size:15px;font-weight:800;color:{INK}">💎 Mutual fund watchlist</h2>
    {_instrument_table(funds, 'funds')}

    <h2 style="margin:26px 0 12px;font-size:15px;font-weight:800;color:{INK}">🏢 Equity watchlist</h2>
    {_instrument_table(stocks, 'stocks')}

    <p style="margin:22px 0 20px;font-size:11px;color:{MUTED};line-height:1.6">
      Data: AMFI NAV feed · Yahoo Finance (NSE), delayed by up to one session.
      This is a personal advisory tool, not investment advice. Mutual fund investments are subject
      to market risks — read all scheme-related documents carefully before investing.
    </p>
  </div>
</div>
</body>
</html>"""


if __name__ == "__main__":
    # Render a self-contained sample report to preview the template.
    import indian_market_monitor as imm
    report = imm.generate_advisory_report()
    out = build_html_report(report)
    with open("email_preview.html", "w", encoding="utf-8") as f:
        f.write(out)
    print(f"Preview written to email_preview.html ({len(out):,} bytes)")
