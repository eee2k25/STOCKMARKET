"""Embed the interactive dashboard (interactive_portfolio_app.html) inside
other front-ends — currently the Streamlit app — with the market snapshot
injected as data, so it needs no backend endpoints to render and hover."""

import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FILE = os.path.join(BASE_DIR, "interactive_portfolio_app.html")


def build_embed_html(data):
    """data: dict with the same shape as GET /api/data
    (see market_data.collect_market_data)."""
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        html = f.read()
    payload = json.dumps(data)
    # Guard against </script> breaking out of the injection tag.
    payload = payload.replace("</", "<\\/")
    inject = f"<script>window.__EMBED_DATA__ = {payload};</script>"
    return html.replace("<body>", "<body>\n" + inject, 1)
