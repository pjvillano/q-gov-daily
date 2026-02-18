#!/usr/bin/env python3
"""
Q-GOV Daily Brief — Fetches quantum government intelligence via Anthropic API
and sends a formatted HTML email via Gmail SMTP.
"""

import os
import json
import smtplib
import anthropic
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── Configuration ─────────────────────────────────────────────────────────────
RECIPIENT_EMAIL = "villano@ionq.co"
SENDER_EMAIL    = os.environ["GMAIL_USER"]          # set in GitHub secrets
GMAIL_APP_PASS  = os.environ["GMAIL_APP_PASSWORD"]  # set in GitHub secrets
ANTHROPIC_KEY   = os.environ["ANTHROPIC_API_KEY"]   # set in GitHub secrets

SYSTEM_PROMPT = """You are a senior intelligence analyst specializing in quantum technologies
and national security. Your job is to produce a daily open-source intelligence (OSINT) brief
on how quantum technologies are being used, funded, or developed by governments and for
national security purposes worldwide.

Use your web search tool to find the most recent, relevant, publicly available news and reports
(prioritize last 7 days, then last 30 days, then up to 90 days if needed).

MANDATORY COVERAGE — include at least one dedicated section for each:

CHINA: PLA quantum programs, Chinese Academy of Sciences, Micius satellite, Beijing-Shanghai
QKD backbone, CETC and state-owned defense contractor quantum investments, export control or
espionage incidents related to quantum IP. China is the primary strategic competitor.

EUROPE: EU Quantum Flagship milestones, EuroQCI deployments, NATO quantum working groups,
UK National Quantum Strategy, German/French/Dutch national quantum programs, EU defense
quantum initiatives.

US: At least one US government or DoD quantum item (DARPA, NSA, NIST, DoE national labs,
or major defense contractor programs).

Also cover: Quantum computing programs, Quantum communications & QKD, Quantum sensing &
navigation, Post-quantum cryptography adoption, and any other relevant global developments.

Return ONLY a valid JSON object — no markdown, no backticks, no preamble — with this schema:
{
  "date": "ISO date string",
  "classification": "UNCLASSIFIED // FOR OFFICIAL USE ONLY",
  "summary": "2-3 sentence executive summary with an analogy to make it accessible",
  "threatLevel": "LOW | MODERATE | ELEVATED | HIGH",
  "threatRationale": "One sentence explaining the threat level",
  "sections": [
    {
      "id": "unique-id",
      "domain": "Domain name",
      "headline": "Short punchy headline",
      "body": "3-5 sentence explanation with a simple analogy",
      "significance": "LOW | MEDIUM | HIGH | CRITICAL",
      "actors": ["list", "of", "nations", "or", "agencies"],
      "sourceHint": "Publication or agency name"
    }
  ],
  "watchItems": ["3-5 things to watch in the coming days"],
  "analystNote": "Single paragraph big-picture observation with an analogy"
}"""

USER_PROMPT = f"""Today is {datetime.now().strftime('%A, %B %d, %Y')}.

Generate the Q-GOV quantum national security daily brief. Search explicitly for:
1. China quantum military/government programs — PLA, CAS, Micius satellite, QKD, national strategy
2. Europe quantum programs — EU Quantum Flagship, EuroQCI, NATO quantum, UK National Quantum Strategy
3. US DoD/DARPA/NIST/NSA quantum developments
4. Any other significant global quantum security or government quantum news

Return the JSON brief only."""

# ── Significance and Threat colors ────────────────────────────────────────────
SIG_COLORS = {
    "LOW":      "#4a9eff",
    "MEDIUM":   "#ffd700",
    "HIGH":     "#ff8c00",
    "CRITICAL": "#ff4444",
}
THREAT_COLORS = {
    "LOW":      {"bg": "#e8f5e9", "border": "#2e7d32", "text": "#2e7d32"},
    "MODERATE": {"bg": "#fff8e1", "border": "#f9a825", "text": "#f57f17"},
    "ELEVATED": {"bg": "#fff3e0", "border": "#e65100", "text": "#bf360c"},
    "HIGH":     {"bg": "#ffebee", "border": "#c62828", "text": "#b71c1c"},
}

# ── Fetch brief from Anthropic ─────────────────────────────────────────────────
def fetch_brief() -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    print("Fetching brief from Anthropic API with web search...")
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": USER_PROMPT}],
    )

    # Concatenate all text blocks
    full_text = "".join(
        block.text for block in response.content if block.type == "text"
    )
    # Strip any accidental markdown fences
    clean = full_text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean)


# ── Build HTML email ───────────────────────────────────────────────────────────
def build_html(brief: dict) -> str:
    threat    = brief.get("threatLevel", "MODERATE")
    tc        = THREAT_COLORS.get(threat, THREAT_COLORS["MODERATE"])
    date_str  = datetime.now().strftime("%A, %B %d, %Y")

    # Threat meter HTML
    levels = ["LOW", "MODERATE", "ELEVATED", "HIGH"]
    idx    = levels.index(threat) if threat in levels else 1
    meter_cells = "".join(
        f'<td style="width:28px;height:10px;background:{tc["border"] if i <= idx else "#e0e0e0"};'
        f'border:1px solid {tc["border"] if i <= idx else "#ccc"};border-radius:2px;"></td>'
        for i, _ in enumerate(levels)
    )
    meter_html = f'<table cellspacing="4" style="display:inline-table;vertical-align:middle;"><tr>{meter_cells}</tr></table>'

    # Section cards
    sections_html = ""
    for s in brief.get("sections", []):
        sig   = s.get("significance", "MEDIUM")
        color = SIG_COLORS.get(sig, "#4a9eff")
        actors_html = " ".join(
            f'<span style="background:#f5f5f5;border:1px solid #ddd;border-radius:3px;'
            f'padding:2px 8px;font-size:11px;color:#1565c0;font-family:monospace;">{a}</span>'
            for a in s.get("actors", [])
        )
        sections_html += f"""
        <div style="border-left:4px solid {color};background:#fafafa;padding:16px 18px;
                    margin-bottom:14px;border-radius:0 4px 4px 0;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
            <div>
              <div style="font-size:10px;color:#888;letter-spacing:2px;text-transform:uppercase;
                          font-family:monospace;margin-bottom:4px;">{s.get('domain','')}</div>
              <div style="font-size:15px;font-weight:700;color:#1a1a1a;line-height:1.3;">{s.get('headline','')}</div>
            </div>
            <span style="background:{color}22;border:1px solid {color};color:{color};
                         font-family:monospace;font-size:10px;padding:3px 8px;
                         letter-spacing:2px;white-space:nowrap;margin-left:12px;border-radius:3px;">{sig}</span>
          </div>
          <p style="color:#444;font-size:13px;line-height:1.75;margin:0 0 10px 0;">{s.get('body','')}</p>
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
            <div style="display:flex;gap:6px;flex-wrap:wrap;">{actors_html}</div>
            <span style="color:#aaa;font-size:11px;font-family:monospace;">SRC: {s.get('sourceHint','')}</span>
          </div>
        </div>"""

    # Watch items
    watch_items_html = "".join(
        f'<div style="display:flex;gap:10px;margin-bottom:8px;">'
        f'<span style="color:#f57f17;font-weight:700;flex-shrink:0;">→</span>'
        f'<span style="color:#555;font-size:13px;line-height:1.6;">{item}</span></div>'
        for item in brief.get("watchItems", [])
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Q-GOV Daily Brief — {date_str}</title>
</head>
<body style="margin:0;padding:0;background:#f0f2f0;font-family:Georgia,'Times New Roman',serif;">
<div style="max-width:720px;margin:24px auto;background:#fff;border:1px solid #ddd;border-radius:4px;overflow:hidden;">

  <!-- Header -->
  <div style="background:#0a1a0a;padding:24px 32px;border-bottom:3px solid #2e7d32;">
    <div style="font-family:monospace;font-size:10px;color:#4a7a4a;letter-spacing:4px;
                text-transform:uppercase;margin-bottom:6px;">◆ Quantum Intelligence Monitor ◆</div>
    <div style="font-family:monospace;font-size:24px;font-weight:700;color:#00c853;
                letter-spacing:3px;">Q-GOV DAILY BRIEF</div>
    <div style="font-family:monospace;font-size:11px;color:#4a7a4a;margin-top:6px;
                letter-spacing:2px;">{date_str} &nbsp;|&nbsp; {brief.get('classification','UNCLASSIFIED')}</div>
  </div>

  <div style="padding:28px 32px;">

    <!-- Threat Posture -->
    <div style="background:{tc['bg']};border:1px solid {tc['border']};border-radius:4px;
                padding:16px 20px;margin-bottom:24px;display:flex;
                justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
      <div>
        <div style="font-family:monospace;font-size:10px;color:{tc['text']};
                    letter-spacing:3px;margin-bottom:8px;">QUANTUM THREAT POSTURE</div>
        {meter_html}
        &nbsp;&nbsp;
        <span style="font-family:monospace;font-size:13px;font-weight:700;
                     color:{tc['text']};letter-spacing:2px;">{threat}</span>
      </div>
      <div style="max-width:340px;">
        <div style="font-family:monospace;font-size:10px;color:#888;letter-spacing:2px;margin-bottom:4px;">RATIONALE</div>
        <div style="font-size:12px;color:#555;line-height:1.6;">{brief.get('threatRationale','')}</div>
      </div>
    </div>

    <!-- Executive Summary -->
    <div style="background:#f8faf8;border-top:3px solid #2e7d32;border:1px solid #e0e8e0;
                border-radius:4px;padding:18px 20px;margin-bottom:28px;">
      <div style="font-family:monospace;font-size:10px;color:#4a7a4a;letter-spacing:4px;margin-bottom:10px;">
        EXECUTIVE SUMMARY
      </div>
      <p style="color:#333;font-size:14px;line-height:1.85;margin:0;font-style:italic;">
        {brief.get('summary','')}
      </p>
    </div>

    <!-- Section label -->
    <div style="font-family:monospace;font-size:10px;color:#aaa;letter-spacing:4px;margin-bottom:12px;">
      DOMAIN INTELLIGENCE // {len(brief.get('sections',[]))} ITEMS
    </div>

    <!-- Sections -->
    {sections_html}

    <!-- Watch Items -->
    <div style="background:#fffde7;border-left:4px solid #f9a825;border-radius:0 4px 4px 0;
                padding:16px 20px;margin-top:24px;margin-bottom:20px;">
      <div style="font-family:monospace;font-size:10px;color:#f57f17;letter-spacing:4px;margin-bottom:12px;">
        ◈ WATCH ITEMS // NEXT 72 HOURS
      </div>
      {watch_items_html}
    </div>

    <!-- Analyst Note -->
    <div style="background:#e8eaf6;border-left:4px solid #3949ab;border-radius:0 4px 4px 0;
                padding:16px 20px;margin-bottom:24px;">
      <div style="font-family:monospace;font-size:10px;color:#3949ab;letter-spacing:4px;margin-bottom:10px;">
        ANALYST NOTE
      </div>
      <p style="color:#333;font-size:13px;line-height:1.8;margin:0;">{brief.get('analystNote','')}</p>
    </div>

  </div>

  <!-- Footer -->
  <div style="background:#0a1a0a;padding:14px 32px;text-align:center;">
    <div style="font-family:monospace;font-size:10px;color:#2a4a2a;letter-spacing:2px;">
      GENERATED {datetime.now().strftime('%Y-%m-%d %H:%M UTC')} &nbsp;|&nbsp;
      OPEN SOURCE INTELLIGENCE ONLY &nbsp;|&nbsp; NOT FOR REDISTRIBUTION
    </div>
  </div>

</div>
</body>
</html>"""


# ── Send via Gmail SMTP ────────────────────────────────────────────────────────
def send_email(html: str, subject: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText(html, "html"))

    print(f"Sending email to {RECIPIENT_EMAIL}...")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, GMAIL_APP_PASS)
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
    print("Email sent successfully.")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    brief   = fetch_brief()
    html    = build_html(brief)
    threat  = brief.get("threatLevel", "MODERATE")
    date_s  = datetime.now().strftime("%B %d, %Y")
    subject = f"Q-GOV Quantum Brief [{threat}] — {date_s}"
    send_email(html, subject)


if __name__ == "__main__":
    main()
