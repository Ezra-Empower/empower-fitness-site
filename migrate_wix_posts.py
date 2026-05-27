#!/usr/bin/env python3
"""
Wix → Empower Fitness static site blog migration.
Regenerates dark-background (#0d0d0d) posts with white-background osteoporosis template.
Uses data/blog_images.json for unique hero images per post.
"""

import urllib.request, json, os, html, re
from datetime import datetime

KEY = "IST.eyJraWQiOiJQb3pIX2FDMiIsImFsZyI6IlJTMjU2In0.eyJkYXRhIjoie1wiaWRcIjpcImE3YmY0ZGQzLTA5Y2YtNGNkYi1hZjViLTIxMDZlZDJmNTRkNVwiLFwiaWRlbnRpdHlcIjp7XCJ0eXBlXCI6XCJhcHBsaWNhdGlvblwiLFwiaWRcIjpcImVlYTRiNGU0LTQ1OTYtNDk5MC05ZDNiLTI1Y2IzMGFmYmU4YVwifSxcInRlbmFudFwiOntcInR5cGVcIjpcImFjY291bnRcIixcImlkXCI6XCIxNzBkZTgxZC1jMTkyLTQ3ZTAtODY2MC00YTQyNjlmN2IwM2JcIn19IiwiaWF0IjoxNzc5ODI4ODIxfQ.T4qzxm8ZAerJ2b87M1ny-Mnz6rf-Nyyq2hx6YnwtUNAflUBoyuHJiHlNy8F3r1ZLrvlTyrd7qKQDh-K3eHwSQtlflgOADNRwQpOMZahNTIveZTvCZRnS6T-Z1aZKnTw2ng822I0PySPnDZ45kk0h09RmvPTFYJh41_2sTG4fD_OlHu_LMDkqtsIDhN_eg0O6NZq-xwI2OnqP3-h6bWs1vaz4JzEa2HGjLbY7gJjK2yWVbZCzIF7JHxoeG63F6-XM7j4ZsbCVu47aJLJJP5WVvC9gpg36__aXUCVSAe9OLKHQ-vb0dI5S3Z8_h0SusNklaxd88SwH1JUdrrQl6jgLEA"
SITE = "0f8f2566-ec74-42b9-8ff1-42cd4d7bb78d"
HEADERS = {"Authorization": KEY, "wix-site-id": SITE}
BLOG_DIR = "/Users/ezra/Documents/Claude/empower-site/blog"
REDIRECTS_FILE = "/Users/ezra/Documents/Claude/empower-site/_redirects"
IMAGES_JSON = "/Users/ezra/Documents/Claude/empower-site/data/blog_images.json"

# ── Load hero image data ───────────────────────────────────────────────────────
def load_blog_images():
    if os.path.isfile(IMAGES_JSON):
        with open(IMAGES_JSON, encoding="utf-8") as f:
            return json.load(f)
    return {}

BLOG_IMAGES = load_blog_images()

def get_hero_info(slug, title):
    """Return (photo_id, alt) for a slug, with topic-keyword fallback."""
    if slug in BLOG_IMAGES:
        entry = BLOG_IMAGES[slug]
        return entry["photo_id"], entry["alt"]
    # Fallback: pick from topic pool by keyword (for hubs/unknown slugs)
    s = slug.lower()
    fallback_map = [
        (["back", "spine", "lumbar", "spasm"], "photo-1559757148-5c350d0d3c56"),
        (["neck", "shoulder", "cervical"],     "photo-1566241440091-ec10de8db2e1"),
        (["knee", "acl", "mcl", "meniscus"],   "photo-1527689368864-3a821dbccc34"),
        (["ankle", "achilles", "plantar"],      "photo-1476480862126-209bfaa8edc8"),
        (["hip", "piriformis"],                 "photo-1616439369330-fb5f24e09e9c"),
        (["senior", "elder", "aging"],          "photo-1576765608535-5f04d1e3f289"),
        (["sport", "athlet", "soccer", "tennis", "golf", "run"], "photo-1517838277536-f5f99be501cd"),
        (["fitness", "strength", "gym"],        "photo-1517836357463-d25dfeac3438"),
        (["vertigo", "neuro", "balance", "concussion"], "photo-1576091160399-112ba8d25d1d"),
        (["pregnan", "prenatal"],               "photo-1519823551278-64ac92734fb1"),
        (["weight", "supplement", "nutrition"], "photo-1490645935967-10de6ba17061"),
    ]
    for keywords, photo_id in fallback_map:
        if any(k in s for k in keywords):
            return photo_id, title
    return "photo-1571019613454-1cb2f99b2d8b", title  # generic PT default

def hero_figure_html(slug, title):
    photo_id, alt = get_hero_info(slug, title)
    src = f"https://images.unsplash.com/{photo_id}?w=800&h=450&fit=crop&auto=format&q=80"
    safe_alt = html.escape(alt)
    return (
        f'<figure style="margin:2rem 0;text-align:center;">\n'
        f'  <img src="{src}" alt="{safe_alt}"\n'
        f'       style="width:100%;max-width:750px;height:auto;border-radius:8px;'
        f'box-shadow:0 4px 20px rgba(0,0,0,0.15);" loading="lazy">\n'
        f'</figure>\n'
    )

def hero_og_image(slug, title):
    photo_id, _ = get_hero_info(slug, title)
    return f"https://images.unsplash.com/{photo_id}?w=1200&h=630&fit=crop&auto=format&q=80"

# ── API helpers ────────────────────────────────────────────────────────────────
def api(url, data=None):
    headers = dict(HEADERS)
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, headers=headers, data=data)
    with urllib.request.urlopen(req) as r:
        return json.load(r)

def api_post(url, body):
    return api(url, data=json.dumps(body).encode("utf-8"))

def fetch_all_wix_posts():
    """Fetch all published Wix posts via paginated POST query."""
    by_id = {}
    page_size = 100
    offset = 0
    while True:
        resp = api_post(
            "https://www.wixapis.com/blog/v3/posts/query",
            {"query": {"paging": {"limit": page_size, "offset": offset}}},
        )
        batch = resp.get("posts", [])
        for post in batch:
            by_id[post["id"]] = post
        meta = resp.get("pagingMetadata", {})
        total = meta.get("total")
        print(f"  Fetched {len(batch)} posts at offset {offset}", end="")
        if total is not None:
            print(f" (Wix total: {total})")
        else:
            print()
        if not batch or len(batch) < page_size:
            break
        offset += len(batch)
    return list(by_id.values())

# ── String helpers ─────────────────────────────────────────────────────────────
def safe_str(v):
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, (int, float, bool)):
        return str(v)
    if isinstance(v, dict):
        for key in ("plainText", "text", "url", "path", "name", "value", "html"):
            if key in v and v[key] not in (None, ""):
                return safe_str(v[key])
        base = safe_str(v.get("base", ""))
        path = safe_str(v.get("path", ""))
        if base or path:
            return base + path
        return ""
    if isinstance(v, list):
        return " ".join(safe_str(x) for x in v if x is not None)
    return str(v)

def esc(v):
    return html.escape(safe_str(v))

# ── Rich-content renderer ──────────────────────────────────────────────────────
# Spam/promo image patterns to filter out
SPAM_ALT_PHRASES = [
    "convierge", "concierge physical therapist", "looking for the best",
    "learn about empower fitness", "learn about empower",
    "best convierge", "physical therapist in your area",
]
SPAM_URL_FRAGMENTS = ["wix-banner", "promotional"]

def is_spam_image(src, alt):
    alt_l = alt.lower()
    url_l = src.lower()
    if any(p in alt_l for p in SPAM_ALT_PHRASES):
        return True
    if any(f in url_l for f in SPAM_URL_FRAGMENTS):
        return True
    if src in ("/contact",) or src.endswith("/contact"):
        return True
    return False

def render_text(text_node):
    t = esc(text_node.get("textData", {}).get("text", ""))
    decorations = text_node.get("textData", {}).get("decorations", [])
    link_url = None
    is_bold = is_italic = is_underline = False
    for d in decorations:
        dtype = d.get("type", "")
        if dtype == "BOLD":
            is_bold = True
        elif dtype == "ITALIC":
            is_italic = True
        elif dtype == "UNDERLINE":
            is_underline = True
        elif dtype == "LINK":
            link_data = d.get("linkData", {}).get("link", {})
            link_url = safe_str(link_data.get("url", ""))
            if link_url and "empowerfitnesspt.com" in link_url:
                link_url = re.sub(r'https?://(?:www\.)?empowerfitnesspt\.com', '', link_url)
    if is_bold:
        t = f"<strong>{t}</strong>"
    if is_italic:
        t = f"<em>{t}</em>"
    if is_underline and not link_url:
        t = f"<u>{t}</u>"
    if link_url:
        t = f'<a href="{esc(link_url)}">{t}</a>'
    return t

def render_inline(node):
    parts = []
    for child in node.get("nodes", []):
        if child.get("type") == "TEXT":
            parts.append(render_text(child))
        else:
            parts.append(render_node(child))
    return "".join(parts)

def render_node(node):
    ntype = node.get("type", "")

    if ntype == "PARAGRAPH":
        inner = render_inline(node)
        if not inner.strip():
            return ""
        return f"<p>{inner}</p>\n"

    elif ntype == "HEADING":
        level = node.get("headingData", {}).get("level", 2)
        level = max(2, min(4, level))
        inner = render_inline(node)
        return f"<h{level}>{inner}</h{level}>\n"

    elif ntype == "BULLETED_LIST":
        items = "".join(render_node(c) for c in node.get("nodes", []))
        return f"<ul>\n{items}</ul>\n"

    elif ntype == "ORDERED_LIST":
        items = "".join(render_node(c) for c in node.get("nodes", []))
        return f"<ol>\n{items}</ol>\n"

    elif ntype == "LIST_ITEM":
        inner = render_inline(node)
        if not inner.strip():
            parts = []
            for child in node.get("nodes", []):
                parts.append(render_inline(child))
            inner = "".join(parts)
        return f"<li>{inner}</li>\n"

    elif ntype == "BLOCKQUOTE":
        inner = render_inline(node)
        if not inner.strip():
            parts = []
            for child in node.get("nodes", []):
                parts.append(render_inline(child))
            inner = "".join(parts)
        # White-theme: use #555 (dark) instead of #aaa (light)
        return (f'<blockquote style="border-left:4px solid #C8922A;padding:1rem 1.5rem;'
                f'margin:1.5rem 0;color:#555;font-style:italic;">{inner}</blockquote>\n')

    elif ntype == "DIVIDER":
        # White-theme: use #ddd instead of #2a2a2a
        return '<hr style="border:none;border-top:1px solid #ddd;margin:2rem 0;">\n'

    elif ntype == "IMAGE":
        img_data = node.get("imageData", {})
        alt = safe_str(img_data.get("altText", ""))
        media = img_data.get("image", {})
        src = ""
        if media:
            raw_src = media.get("src", "")
            src = safe_str(raw_src.get("url", "") if isinstance(raw_src, dict) else raw_src)
        if not src:
            src = safe_str(img_data.get("link", {}).get("url", ""))
        # Filter spam / promotional images
        if src and is_spam_image(src, alt):
            return ""
        if src:
            return (f'<figure style="margin:1.5rem 0;text-align:center;">'
                    f'<img src="{esc(src)}" alt="{esc(alt)}" '
                    f'style="max-width:100%;border-radius:6px;"></figure>\n')
        return ""

    elif ntype == "HTML":
        return safe_str(node.get("htmlData", {}).get("html", "")) + "\n"

    elif ntype == "CODE_BLOCK":
        code = esc(node.get("codeBlockData", {}).get("text", ""))
        return f"<pre><code>{code}</code></pre>\n"

    elif ntype == "VIDEO":
        video_data = node.get("videoData", {})
        raw_src = video_data.get("video", {}).get("src", "")
        src = safe_str(raw_src.get("url", "") if isinstance(raw_src, dict) else raw_src)
        if src and "youtube" in src:
            vid_id = re.search(r'(?:v=|youtu\.be/)([^&?]+)', src)
            if vid_id:
                return (f'<div style="position:relative;padding-bottom:56.25%;margin:1.5rem 0;">'
                        f'<iframe style="position:absolute;top:0;left:0;width:100%;height:100%;" '
                        f'src="https://www.youtube.com/embed/{vid_id.group(1)}" '
                        f'frameborder="0" allowfullscreen></iframe></div>\n')
        return ""

    elif ntype == "TABLE":
        rows = "".join(render_node(c) for c in node.get("nodes", []))
        return f'<div style="overflow-x:auto;margin:1.5rem 0;"><table>\n{rows}</table></div>\n'

    elif ntype == "TABLE_ROW":
        cells = "".join(render_node(c) for c in node.get("nodes", []))
        return f"<tr>{cells}</tr>\n"

    elif ntype == "TABLE_CELL":
        inner = "".join(render_node(c) for c in node.get("nodes", []))
        cell_data = node.get("tableCellData", {})
        is_header = cell_data.get("cellType") == "HEADER"
        tag = "th" if is_header else "td"
        return f"<{tag}>{inner}</{tag}>"

    children = node.get("nodes", [])
    if children:
        return "".join(render_node(c) for c in children)
    return ""

def rich_content_to_html(nodes):
    parts = []
    for node in nodes:
        rendered = render_node(node)
        if rendered:
            parts.append(rendered)
    return "\n".join(parts)

# ── HTML template ──────────────────────────────────────────────────────────────
def make_html(post, body_html):
    slug     = post["slug"]
    title    = esc(post.get("title", ""))
    excerpt  = esc(safe_str(post.get("excerpt", ""))[:160])
    pub_date = safe_str(post.get("firstPublishedDate", ""))[:10]
    canonical = f"https://www.empowerfitnesspt.com/blog/{slug}"
    og_image  = hero_og_image(slug, safe_str(post.get("title", "")))
    fig_html  = hero_figure_html(slug, safe_str(post.get("title", "")))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':
new Date().getTime(),event:'gtm.js'}});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
}})(window,document,'script','dataLayer','GTM-W8K8GRZQ');</script>
<!-- End Google Tag Manager -->
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>{title} | Empower Fitness PT</title>
<meta content="{excerpt}" name="description"/>
<link href="{canonical}" rel="canonical"/>
<meta property="og:title" content="{title}"/>
<meta property="og:description" content="{excerpt}"/>
<meta property="og:image" content="{og_image}"/>
<meta property="og:image:width" content="1200"/>
<meta property="og:image:height" content="630"/>
<meta property="og:type" content="article"/>
<meta property="og:url" content="{canonical}"/>
<script type="application/ld+json">
{{
  "@context":"https://schema.org",
  "@type":"BlogPosting",
  "headline":"{title}",
  "description":"{excerpt}",
  "datePublished":"{pub_date}",
  "author":{{"@type":"Person","name":"Dr. Ezra Miller, PT, DPT","url":"https://www.empowerfitnesspt.com/about"}},
  "publisher":{{"@type":"Organization","name":"Empower Fitness"}},
  "mainEntityOfPage":{{"@type":"WebPage","@id":"{canonical}"}}
}}
</script>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Georgia', serif; background: #ffffff; color: #222; line-height: 1.7; }}
a {{ color: #C8922A; }}
a:hover {{ text-decoration: underline; }}
nav {{ background: #000; padding: 18px 40px; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; }}
nav .logo {{ color: #C8922A; font-weight: 900; font-size: 1.3rem; letter-spacing: 1px; text-decoration: none; }}
nav ul {{ list-style: none; display: flex; gap: 30px; }}
nav ul a {{ color: #fff; text-decoration: none; font-size: 0.9rem; }}
nav .cta-btn {{ background: #C8922A; color: #000; padding: 10px 22px; border-radius: 4px; font-weight: 800; text-decoration: none; font-size: 0.9rem; }}
.hero {{ background: linear-gradient(135deg, #141414 0%, #1c1c1c 100%); padding: 80px 40px 60px; text-align: center; border-bottom: 1px solid #242424; }}
.hero .tag {{ color: #C8922A; font-size: 0.8rem; font-weight: 700; letter-spacing: 3px; text-transform: uppercase; margin-bottom: 20px; }}
.hero h1 {{ color: #fff; font-size: 2.2rem; font-weight: 900; line-height: 1.2; max-width: 800px; margin: 0 auto 20px; }}
.hero .byline {{ color: #aaa; font-size: 0.9rem; }}
.hero .byline span {{ color: #C8922A; }}
.content-wrap {{ max-width: 780px; margin: 0 auto; padding: 60px 30px; }}
.content-wrap h2 {{ font-size: 1.5rem; font-weight: 800; color: #0a0a0a; border-bottom: 2px solid #C8922A; padding-bottom: 10px; display: inline-block; margin: 48px 0 18px; line-height: 1.3; }}
.content-wrap h3 {{ font-size: 1.1rem; font-weight: 700; color: #0a0a0a; margin: 32px 0 12px; }}
.content-wrap p {{ color: #333; margin-bottom: 18px; font-size: 1.0rem; }}
.content-wrap ul, .content-wrap ol {{ color: #333; padding-left: 22px; margin-bottom: 20px; }}
.content-wrap li {{ margin-bottom: 10px; font-size: 1.0rem; }}
.content-wrap figure {{ margin: 2rem 0; text-align: center; }}
.content-wrap figure img {{ width: 100%; max-width: 750px; height: auto; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); }}
table {{ width: 100%; border-collapse: collapse; margin: 1.5rem 0; }}
th {{ background: #C8922A; color: #000; padding: 0.7rem 1rem; text-align: left; font-weight: 700; }}
td {{ padding: 0.7rem 1rem; border-bottom: 1px solid #eee; color: #333; }}
tr:nth-child(even) td {{ background: #f9f9f9; }}
.callout {{ background: #1c1c1c; border-left: 4px solid #C8922A; padding: 24px 28px; margin: 40px 0; border-radius: 0 8px 8px 0; }}
.callout p {{ color: #ddd; margin-bottom: 0; font-style: italic; }}
.callout .callout-title {{ color: #C8922A; font-weight: 800; font-size: 0.8rem; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px; display: block; font-style: normal; }}
.cta-block {{ background: linear-gradient(135deg, #C8922A, #a07520); padding: 50px 40px; text-align: center; border-radius: 12px; margin: 60px 0 40px; }}
.cta-block h2 {{ color: #000; font-size: 1.7rem; font-weight: 900; margin-bottom: 12px; }}
.cta-block p {{ color: #1a1a1a; margin-bottom: 28px; }}
.cta-block a {{ background: #000; color: #C8922A; padding: 16px 36px; border-radius: 4px; font-weight: 800; text-decoration: none; font-size: 1rem; display: inline-block; margin: 6px; }}
.cta-block a.secondary {{ background: transparent; border: 2px solid #000; color: #000; }}
.author-box {{ background: #f4f4f4; border: 1px solid #e0e0e0; border-radius: 12px; padding: 30px; display: flex; gap: 24px; align-items: flex-start; margin: 50px 0; }}
.author-avatar {{ width: 64px; height: 64px; background: #C8922A; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 1.4rem; color: #000; flex-shrink: 0; }}
.author-info h4 {{ color: #0a0a0a; font-weight: 800; margin-bottom: 6px; }}
.author-info p {{ color: #555; font-size: 0.9rem; margin-bottom: 0; }}
/* ===== NAVIGATION ===== */
nav {{
  position: fixed; top: 0; left: 0; right: 0;
  z-index: 1000;
  background: #000000;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 40px; height: 68px;
  border-bottom: 1px solid #1a1a1a;
}}
.nav-logo {{ font-size: 22px; font-weight: 900; letter-spacing: 3px; color: #C8922A; }}
.nav-logo span {{ color: #ffffff; }}
.nav-links {{ display: flex; gap: 32px; list-style: none; }}
.nav-links a {{ color: #ffffff; font-size: 14px; font-weight: 500; letter-spacing: 0.5px; transition: color 0.2s; text-decoration: none; }}
.nav-links a:hover {{ color: #C8922A; }}
.nav-cta {{
  background: #C8922A; color: #000000 !important;
  font-weight: 800; font-size: 13px; letter-spacing: 1.5px; text-transform: uppercase;
  padding: 10px 22px; border-radius: 2px; transition: background 0.2s;
  text-decoration: none; white-space: nowrap;
}}
.nav-cta:hover {{ background: #e0a93a; }}
.hero {{ padding-top: 108px; }}
@media (max-width: 768px) {{ .hero h1 {{ font-size: 1.6rem; }} .nav-links {{ display: none; }} .content-wrap {{ padding: 40px 20px; }} .author-box {{ flex-direction: column; }} }}
</style>
<link rel="stylesheet" href="/css/mobile-base.css">
<link rel="stylesheet" href="/css/mobile-overrides.css">
<link rel="stylesheet" href="/css/mobile-sections.css">
<link rel="stylesheet" href="/css/site-footer.css">
</head>
<body>
<!-- Google Tag Manager (noscript) -->
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-W8K8GRZQ"
height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
<!-- End Google Tag Manager (noscript) -->
<nav>
<div class="nav-logo"><img src="/img/logo-gold.png" alt="Empower Fitness" style="height:32px;width:auto;display:inline-block;vertical-align:middle;margin-right:10px;" /><span style="font-size:14px;font-weight:700;letter-spacing:2px;vertical-align:middle;">EMPOWER FITNESS</span></div>
<button class="nav-hamburger" onclick="this.classList.toggle('open');var nl=document.querySelector('.nav-links');if(nl)nl.classList.toggle('open')" aria-label="Menu"><span></span><span></span><span></span></button>
<ul class="nav-links">
<li><a href="/">Home</a></li>
<li><a href="/services">Services</a></li>
<li><a href="/injury-finder">Injury Finder</a></li>
<li><a href="/blog">Blog</a></li>
<li><a href="/about">About Us</a></li>
</ul>
<a class="nav-cta" href="/contact">CONTACT US</a>
</nav>
<div class="hero">
<p class="tag">Empower Fitness</p>
<h1>{title}</h1>
<p class="byline">By <span>Dr. Ezra Miller, PT, DPT</span> &nbsp;&middot;&nbsp; {pub_date} &nbsp;&middot;&nbsp; Boca Raton, FL</p>
</div>
<div class="content-wrap">
{fig_html}
{body_html}
<div class="cta-block">
<h2>Ready to Get Started?</h2>
<p>Free 20-minute consultation for patients in Boca Raton, Delray Beach, and Pompano Beach. No waiting rooms. I come to you.</p>
<a href="tel:+19549017211">Call: 954-901-7211</a>
<a class="secondary" href="/contact">Contact for Availability &rarr;</a>
</div>
<div class="author-box">
<div class="author-avatar">EM</div>
<div class="author-info">
<h4>Dr. Ezra Miller, PT, DPT</h4>
<p>Doctor of Physical Therapy and NASM Certified Personal Trainer with over 10 years of clinical experience. Founder of Empower Fitness &mdash; concierge physical therapy and functional fitness serving Boca Raton, Delray Beach, and Pompano Beach, FL. 954-901-7211 &middot; admin@empowerfitnesspt.com</p>
</div>
</div>
</div>
<footer>
<div class="footer-grid">
<div class="footer-brand">
<div class="nav-logo"><img src="/img/logo-gold.png" alt="Empower Fitness" style="height:32px;width:auto;display:inline-block;vertical-align:middle;margin-right:10px;" /><span style="font-size:14px;font-weight:700;letter-spacing:2px;vertical-align:middle;">EMPOWER FITNESS</span></div>
<p>Concierge physical therapy and functional fitness delivered to your door. Serving Boca Raton, Delray Beach, Pompano Beach, and surrounding South Florida.</p>
</div>
<div class="footer-col">
<h4>Services</h4>
<ul>
<li><a href="/in-home-physical-therapy-boca-raton">In-Home Physical Therapy</a></li>
<li><a href="/return-to-sport-physical-therapy-boca-raton">Return-to-Sport</a></li>
<li><a href="/fitness-training-boca-raton">Fitness Training</a></li>
<li><a href="/longevity-training-boca-raton">Longevity Program</a></li>
<li><a href="/nutrition-coaching-boca-raton">Nutrition Guidance</a></li>
</ul>
</div>
<div class="footer-col">
<h4>Company</h4>
<ul>
<li><a href="/about">About Dr. Ezra</a></li>
<li><a href="/about">Our Team</a></li>
<li><a href="/blog">Blog</a></li>
<li><a href="/injury-finder">Injury Finder</a></li>
<li><a href="/contact">Contact for Availability</a></li>
<li><a href="/pricing">Pricing</a></li>
</ul>
</div>
<div class="footer-col">
<h4>Contact</h4>
<ul>
<li>Boca Raton, FL</li>
<li>Delray Beach, FL</li>
<li>Pompano Beach, FL</li>
<li><a href="tel:954-901-7211">954-901-7211</a></li>
<li><a href="mailto:admin@empowerfitnesspt.com">admin@empowerfitnesspt.com</a></li>
<li style="margin-top:8px;"><a href="https://g.page/r/empowerfitnesspt/review" style="color:var(--gold);" target="_blank">&#9733; Leave a Google Review</a></li>
<li style="margin-top:6px;"><a href="https://www.instagram.com/empowerfitnesspro/" target="_blank">Instagram</a></li>
<li><a href="https://www.facebook.com/empowerfitnesspt.ok/" target="_blank">Facebook</a></li>
</ul>
</div>
</div>
<div class="footer-bottom">
<p>&copy; 2026 Empower Fitness. All rights reserved.</p>
<p>Dr. Ezra Miller, PT, DPT &middot; Licensed in Florida &middot; NASM Certified</p>
</div>
</footer>
<script>
(function(){{
  var btn = document.querySelector('.nav-hamburger');
  var links = document.querySelector('.nav-links');
  if(btn && links){{
    btn.addEventListener('click', function(){{
      btn.classList.toggle('open');
      links.classList.toggle('open');
    }});
    document.addEventListener('click', function(e){{
      if(!btn.contains(e.target) && !links.contains(e.target)){{
        btn.classList.remove('open');
        links.classList.remove('open');
      }}
    }});
  }}
}})();
</script>
</body>
</html>"""

# ── Dark-post detection ────────────────────────────────────────────────────────
def is_dark_post(slug):
    """Return True if the post's index.html uses the old dark (#0d0d0d) background."""
    path = os.path.join(BLOG_DIR, slug, "index.html")
    if not os.path.isfile(path):
        return False
    with open(path, encoding="utf-8") as f:
        content = f.read()
    return "background:#0d0d0d" in content or "background: #0d0d0d" in content

# ── MAIN ───────────────────────────────────────────────────────────────────────
print("Fetching all Wix posts...")
all_posts = fetch_all_wix_posts()
print(f"Found {len(all_posts)} posts on Wix")

posts_to_regen = [p for p in all_posts if is_dark_post(p["slug"])]
print(f"To regenerate (dark background): {len(posts_to_regen)}")
print()

new_redirects = []
created = []
errors = []

for i, post in enumerate(posts_to_regen):
    slug = post["slug"]
    print(f"[{i+1}/{len(posts_to_regen)}] {slug}")

    try:
        full = api(
            f"https://www.wixapis.com/blog/v3/posts/{post['id']}"
            "?fieldsets=RICH_CONTENT&fieldsets=CONTENT_TEXT"
        )
        full_post = full.get("post", post)
        nodes = full_post.get("richContent", {}).get("nodes", [])
        body_html = rich_content_to_html(nodes)
        if not body_html.strip():
            plain = safe_str(full_post.get("contentText", post.get("contentText", "")))
            if plain:
                body_html = "\n".join(
                    f"<p>{esc(p.strip())}</p>"
                    for p in re.split(r"\n\s*\n", plain)
                    if p.strip()
                )

        post.update({k: v for k, v in full_post.items() if k != "richContent"})

        page_html = make_html(post, body_html)

        out_dir = os.path.join(BLOG_DIR, slug)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(page_html)

        new_redirects.append(f"/post/{slug} /blog/{slug} 301")
        created.append(slug)

    except Exception as e:
        print(f"  ERROR: {e}")
        errors.append(slug)

# ── Update _redirects ──────────────────────────────────────────────────────────
print("\nUpdating _redirects...")

def update_redirects(new_rules):
    with open(REDIRECTS_FILE, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    post_rules = set(new_rules)
    kept = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# Migrated Wix /post/"):
            continue
        if stripped == "# Fallback for any remaining /post/ URLs":
            continue
        if stripped == "/post/* /blog/ 301":
            continue
        if stripped.startswith("/post/") and not stripped.startswith("/post/*") and "301" in stripped:
            post_rules.add(stripped)
            continue
        if stripped == "" and kept and kept[-1] == "":
            continue
        kept.append(line)

    while kept and kept[-1].strip() == "":
        kept.pop()

    block = [
        "# Migrated Wix /post/ → /blog/ (specific 301s)",
        *sorted(post_rules),
        "",
        "# Fallback for any remaining /post/ URLs",
        "/post/* /blog/ 301",
        "",
    ]

    if kept and "Wix blog URL" in kept[0]:
        output = [kept[0], ""] + block + kept[1:]
    else:
        output = block + kept

    with open(REDIRECTS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(output).rstrip() + "\n")

    return len(post_rules)

redirect_count = update_redirects(new_redirects)

print(f"\n✅ Regenerated: {len(created)} blog posts")
print(f"❌ Errors:      {len(errors)}")
if errors:
    print("  Failed:", errors)
print(f"✅ _redirects updated with {redirect_count} specific /post/ rules")
