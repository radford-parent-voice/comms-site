#!/usr/bin/env python3
import os
import re
import html
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

FEED_URL = os.environ.get("RSS_FEED", "").strip()
OUT_DIR = os.path.join("docs", "news")
MAX_ITEMS = int(os.environ.get("MAX_ITEMS", "20"))

GISCUS_SNIPPET = os.environ.get("GISCUS_SNIPPET", "").strip()

def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-") or "item"

def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")

def parse_rss(xml_text: str):
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    if channel is None:
        return []

    items = []
    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()

        # Try to parse pubDate; fall back to now
        try:
            dt = parsedate_to_datetime(pub)
        except Exception:
            dt = datetime.now()

        items.append({
            "title": title or "Untitled",
            "link": link,
            "description": desc,
            "pubDate": dt,
        })

    # newest first
    items.sort(key=lambda x: x["pubDate"], reverse=True)
    return items[:MAX_ITEMS]

def page_template(title, published, body_html, nav_prefix="../"):
    # If you haven’t set giscus yet, we still generate pages
    giscus_block = f"""
<h2>Comments</h2>
<div class="giscus"></div>
{GISCUS_SNIPPET}
""".strip() if GISCUS_SNIPPET else "<p><em>(Comments not configured yet)</em></p>"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; line-height: 1.5; margin: 0; }}
    header, main, footer {{ max-width: 900px; margin: 0 auto; padding: 18px; }}
    nav a {{ margin-right: 12px; }}
    article {{ border: 1px solid #ddd; border-radius: 10px; padding: 14px; }}
    .muted {{ color: #555; }}
    hr {{ border: 0; border-top: 1px solid #eee; margin: 18px 0; }}
  </style>
</head>
<body>
  <header>
    <nav>
      <a href="{nav_prefix}">Home</a>
      <a href="{nav_prefix}news/">News</a>
      <a href="{nav_prefix}policies/">Policies</a>
    </nav>
  </header>

  <main>
    <article>
      <h1>{html.escape(title)}</h1>
      <p class="muted"><em>Published: {html.escape(published)}</em></p>
      <hr />
      {body_html}
    </article>

    <hr />
    {giscus_block}
  </main>

  <footer class="muted">
    <hr />
    <p>Not affiliated with the school. Parent/community initiative focused on improving communication.</p>
  </footer>
</body>
</html>
"""

def write_file(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

def main():
    if not FEED_URL:
        raise SystemExit("RSS_FEED env var is required")

    xml_text = fetch(FEED_URL)
    items = parse_rss(xml_text)

    os.makedirs(OUT_DIR, exist_ok=True)

    index_items = []
    for it in items:
        dt = it["pubDate"]
        date_str = dt.strftime("%Y-%m-%d")
        slug = slugify(it["title"])
        filename = f"{date_str}-{slug}.html"
        out_path = os.path.join(OUT_DIR, filename)

        # RSS description is often HTML inside CDATA — include as-is
        body_html = it["description"] or "<p>(No description provided)</p>"
        page = page_template(it["title"], dt.strftime("%d %b %Y"), body_html, nav_prefix="../")
        write_file(out_path, page)

        index_items.append((dt, it["title"], filename))

    # Build docs/news/index.html
    index_items.sort(key=lambda x: x[0], reverse=True)
    lis = "\n".join(
        f'<li><a href="./{html.escape(fname)}">{html.escape(title)}</a> <span class="muted">({dt.strftime("%d %b %Y")})</span></li>'
        for dt, title, fname in index_items
    )

    news_index = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>News</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; line-height: 1.5; margin: 0; }}
    header, main {{ max-width: 900px; margin: 0 auto; padding: 18px; }}
    nav a {{ margin-right: 12px; }}
    .muted {{ color: #555; }}
  </style>
</head>
<body>
  <header>
    <nav>
      <a href="../">Home</a>
      <a href="./">News</a>
      <a href="../policies/">Policies</a>
    </nav>
    <h1>News</h1>
    <p class="muted">Auto-generated from the configured RSS feed.</p>
  </header>
  <main>
    <ul>
      {lis}
    </ul>
  </main>
</body>
</html>
"""
    write_file(os.path.join(OUT_DIR, "index.html"), news_index)

if __name__ == "__main__":
    main()
