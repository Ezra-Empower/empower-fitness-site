#!/usr/bin/env python3
"""
Wix → Empower Fitness static site blog migration.
Fetches all missing Wix posts and generates HTML files in the site's theme.
"""

import urllib.request, json, os, html, re
from datetime import datetime

KEY = "IST.eyJraWQiOiJQb3pIX2FDMiIsImFsZyI6IlJTMjU2In0.eyJkYXRhIjoie1wiaWRcIjpcImE3YmY0ZGQzLTA5Y2YtNGNkYi1hZjViLTIxMDZlZDJmNTRkNVwiLFwiaWRlbnRpdHlcIjp7XCJ0eXBlXCI6XCJhcHBsaWNhdGlvblwiLFwiaWRcIjpcImVlYTRiNGU0LTQ1OTYtNDk5MC05ZDNiLTI1Y2IzMGFmYmU4YVwifSxcInRlbmFudFwiOntcInR5cGVcIjpcImFjY291bnRcIixcImlkXCI6XCIxNzBkZTgxZC1jMTkyLTQ3ZTAtODY2MC00YTQyNjlmN2IwM2JcIn19IiwiaWF0IjoxNzc5ODI4ODIxfQ.T4qzxm8ZAerJ2b87M1ny-Mnz6rf-Nyyq2hx6YnwtUNAflUBoyuHJiHlNy8F3r1ZLrvlTyrd7qKQDh-K3eHwSQtlflgOADNRwQpOMZahNTIveZTvCZRnS6T-Z1aZKnTw2ng822I0PySPnDZ45kk0h09RmvPTFYJh41_2sTG4fD_OlHu_LMDkqtsIDhN_eg0O6NZq-xwI2OnqP3-h6bWs1vaz4JzEa2HGjLbY7gJjK2yWVbZCzIF7JHxoeG63F6-XM7j4ZsbCVu47aJLJJP5WVvC9gpg36__aXUCVSAe9OLKHQ-vb0dI5S3Z8_h0SusNklaxd88SwH1JUdrrQl6jgLEA"
SITE = "0f8f2566-ec74-42b9-8ff1-42cd4d7bb78d"
HEADERS = {"Authorization": KEY, "wix-site-id": SITE}
BLOG_DIR = "/Users/ezra/Documents/Claude/empower-site/blog"
REDIRECTS_FILE = "/Users/ezra/Documents/Claude/empower-site/_redirects"

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
    """Fetch all published Wix posts. API defaults to 50/page — paginate to get all."""
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

    if not by_id:
        # Fallback: GET list with nested paging.* query params (not plain ?limit=)
        offset = 0
        while True:
            url = (
                "https://www.wixapis.com/blog/v3/posts"
                f"?paging.limit={page_size}&paging.offset={offset}"
            )
            resp = api(url)
            batch = resp.get("posts", [])
            for post in batch:
                by_id[post["id"]] = post
            meta = resp.get("metaData", resp.get("pagingMetadata", {}))
            total = meta.get("total")
            print(f"  [GET fallback] {len(batch)} posts at offset {offset}", end="")
            if total is not None:
                print(f" (total: {total})")
            else:
                print()
            if not batch or len(batch) < page_size:
                break
            offset += len(batch)

    return list(by_id.values())

def safe_str(v):
    """Coerce Wix API values (sometimes dicts) to plain strings."""
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
    """html.escape() calls .replace() internally — always coerce to str first."""
    return html.escape(safe_str(v))

def render_text(text_node):
    """Convert a TEXT node with decorations to HTML."""
    t = esc(text_node.get("textData", {}).get("text", ""))
    decorations = text_node.get("textData", {}).get("decorations", [])
    # Apply decorations inside-out
    link_url = None
    is_bold = False
    is_italic = False
    is_underline = False
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
            # Make internal Wix links relative
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
    """Render a node's inline children as HTML string."""
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
            return ""  # skip empty paragraphs
        return f"<p>{inner}</p>\n"

    elif ntype == "HEADING":
        level = node.get("headingData", {}).get("level", 2)
        level = max(2, min(4, level))  # clamp to h2-h4
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
            # list item may have paragraph children
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
        return f'<blockquote style="border-left:4px solid #C8922A;padding:1rem 1.5rem;margin:1.5rem 0;color:#aaa;font-style:italic;">{inner}</blockquote>\n'

    elif ntype == "DIVIDER":
        return '<hr style="border:none;border-top:1px solid #2a2a2a;margin:2rem 0;">\n'

    elif ntype == "IMAGE":
        img_data = node.get("imageData", {})
        alt = safe_str(img_data.get("altText", ""))
        media = img_data.get("image", {})
        src = ""
        if media:
            raw_src = media.get("src", "")
            if isinstance(raw_src, dict):
                src = safe_str(raw_src.get("url", ""))
            else:
                src = safe_str(raw_src)
        if not src:
            src = safe_str(img_data.get("link", {}).get("url", ""))
        if src:
            return f'<figure style="margin:1.5rem 0;text-align:center;"><img src="{esc(src)}" alt="{esc(alt)}" style="max-width:100%;border-radius:6px;"></figure>\n'
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
                return f'<div style="position:relative;padding-bottom:56.25%;margin:1.5rem 0;"><iframe style="position:absolute;top:0;left:0;width:100%;height:100%;" src="https://www.youtube.com/embed/{vid_id.group(1)}" frameborder="0" allowfullscreen></iframe></div>\n'
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

    # Unknown block types: try rendering nested nodes
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

def make_html(post, body_html):
    slug = post["slug"]
    title = esc(post.get("title", ""))
    excerpt = esc(safe_str(post.get("excerpt", ""))[:160])
    pub_date = safe_str(post.get("firstPublishedDate", ""))[:10]
    canonical = f"https://www.empowerfitnesspt.com/blog/{slug}"

    # Featured image
    media = post.get("media", {})
    hero_img_html = ""
    og_image = "https://empowerfitnesspt.com/img/og-default.jpg"

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
<meta charset="utf-8"/><meta content="width=device-width,initial-scale=1" name="viewport"/>
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
  "author":{{"@type":"Person","name":"Dr. Ezra Miller, PT, DPT"}},
  "publisher":{{"@type":"Organization","name":"Empower Fitness","logo":{{"@type":"ImageObject","url":"https://www.empowerfitnesspt.com/logo.png"}}}},
  "datePublished":"{pub_date}",
  "mainEntityOfPage":{{"@type":"WebPage","@id":"{canonical}"}}
}}
</script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:"Helvetica Neue",Arial,sans-serif;background:#0d0d0d;color:#ccc;line-height:1.7}}
a{{color:#C8922A}}a:hover{{text-decoration:underline}}
nav{{position:fixed;top:0;left:0;right:0;z-index:1000;background:#000000;display:flex;align-items:center;justify-content:space-between;padding:0 40px;height:68px;border-bottom:1px solid #1a1a1a;}}
.nav-logo{{font-size:22px;font-weight:900;letter-spacing:3px;color:#C8922A;}}
.nav-logo span{{color:#ffffff;}}
.nav-links{{display:flex;gap:32px;list-style:none;}}
.nav-links a{{color:#ffffff;font-size:14px;font-weight:500;letter-spacing:0.5px;transition:color 0.2s;text-decoration:none;}}
.nav-links a:hover{{color:#C8922A;}}
.nav-cta{{background:#C8922A;color:#000000 !important;font-weight:800;font-size:13px;letter-spacing:1.5px;text-transform:uppercase;padding:10px 22px;border-radius:2px;text-decoration:none;white-space:nowrap;}}
.hero{{background:linear-gradient(135deg,#0d0d0d,#1c1c1c);border-bottom:3px solid #C8922A;padding:5rem 2rem 2.5rem}}
.hero-inner{{max-width:800px;margin:0 auto}}
.tag{{display:inline-block;background:#C8922A;color:#000;font-size:.75rem;font-weight:700;padding:.3rem .8rem;border-radius:3px;letter-spacing:.5px;text-transform:uppercase;margin-bottom:1rem}}
h1{{font-size:2.1rem;font-weight:900;color:#fff;line-height:1.2;margin-bottom:1rem}}
.meta{{font-size:.85rem;color:#888;margin-bottom:1.5rem}}
.meta span{{color:#C8922A;font-weight:600}}
.intro-box{{background:#1c1c1c;border-left:4px solid #C8922A;padding:1.2rem 1.5rem;border-radius:4px;color:#ddd;font-size:1.05rem}}
.body{{max-width:800px;margin:2.5rem auto;padding:0 1.5rem 3rem}}
.body p{{margin-bottom:1.2rem;color:#ccc}}
.body ul,.body ol{{padding-left:1.4rem;margin-bottom:1.2rem;color:#ccc}}
.body li{{margin-bottom:.5rem}}
.body h2{{color:#C8922A;margin:2rem 0 .7rem;font-size:1.4rem}}
.body h3{{color:#C8922A;margin:1.5rem 0 .5rem;font-size:1.15rem}}
.body h4{{color:#e0e0e0;margin:1.2rem 0 .4rem;font-size:1rem}}
table{{width:100%;border-collapse:collapse;margin:1.5rem 0}}
th{{background:#C8922A;color:#000;padding:.7rem 1rem;text-align:left;font-weight:700}}
td{{padding:.7rem 1rem;border-bottom:1px solid #2a2a2a;color:#ccc}}
tr:nth-child(even) td{{background:#1a1a1a}}
.cta-box{{background:linear-gradient(135deg,#C8922A,#a07520);border-radius:8px;padding:2.5rem;text-align:center;margin:2.5rem 0}}
.cta-box h3{{color:#000;font-size:1.5rem;font-weight:900;margin-bottom:.8rem}}
.cta-box p{{color:#1a0f00;margin-bottom:1.5rem}}
.cta-box a{{background:#000;color:#C8922A;padding:.9rem 2rem;border-radius:4px;font-weight:700;font-size:1rem;display:inline-block;text-decoration:none}}
footer{{background:#000;color:#666;text-align:center;padding:2rem;margin-top:3rem;font-size:.85rem}}
footer a{{color:#C8922A}}
@media(max-width:768px){{nav{{padding:0 20px;}}h1{{font-size:1.5rem}}.hero{{padding:5rem 1.2rem 2rem}}.body{{padding:0 1rem 2rem}}}}
</style>
<link rel="stylesheet" href="/css/mobile-base.css">
<link rel="stylesheet" href="/css/mobile-overrides.css">
</head>
<body>
<!-- Google Tag Manager (noscript) -->
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-W8K8GRZQ" height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
<nav>
<div class="nav-logo"><img src="/img/logo-gold.png" alt="Empower Fitness" style="height:32px;width:auto;display:inline-block;vertical-align:middle;margin-right:10px;" /><span style="font-size:14px;font-weight:700;letter-spacing:2px;vertical-align:middle;">EMPOWER FITNESS</span></div>
<button class="nav-hamburger" onclick="this.classList.toggle('open');var nl=document.querySelector('.nav-links');if(nl)nl.classList.toggle('open')" aria-label="Menu"><span></span><span></span><span></span></button>
<ul class="nav-links">
<li><a href="/">Home</a></li>
<li><a href="/services">Services</a></li>
<li><a href="/injury-finder">Injury Finder</a></li>
<li><a href="/blog">Blog</a></li>
<li><a href="/about">About Us</a></li>
<li><a class="nav-cta" href="/contact">CONTACT US</a></li>
</ul>
</nav>
<div class="hero">
<div class="hero-inner">
<span class="tag">Empower Fitness</span>
<h1>{title}</h1>
<div class="meta">By <span>Dr. Ezra Miller, PT, DPT</span> &nbsp;|&nbsp; {pub_date} &nbsp;|&nbsp; Boca Raton, FL</div>
<div class="intro-box">{excerpt}</div>
</div>
</div>
<div class="body">
{body_html}
<div class="cta-box">
<h3>Ready to Feel Better?</h3>
<p>Dr. Ezra Miller brings expert physical therapy directly to your home in Boca Raton and surrounding South Florida communities.</p>
<a href="/contact">Contact for Availability &rarr;</a>
</div>
</div>
<footer>
<p>&copy; 2026 Empower Fitness PT &mdash; Boca Raton, FL &nbsp;|&nbsp; <a href="/contact">Contact</a> &nbsp;|&nbsp; <a href="/blog">Blog</a> &nbsp;|&nbsp; <a href="/privacy">Privacy Policy</a></p>
</footer>
<script>
var h=document.querySelector('.nav-hamburger');
if(h)h.addEventListener('click',function(){{this.classList.toggle('open');var nl=document.querySelector('.nav-links');if(nl)nl.classList.toggle('open');}});
</script>
</body>
</html>"""

# ── MAIN ──────────────────────────────────────────────────────────────────────

print("Fetching all Wix posts...")
all_posts = fetch_all_wix_posts()
print(f"Found {len(all_posts)} posts on Wix")

existing_slugs = set()
for name in os.listdir(BLOG_DIR):
    post_dir = os.path.join(BLOG_DIR, name)
    if os.path.isdir(post_dir) and os.path.isfile(os.path.join(post_dir, "index.html")):
        existing_slugs.add(name)

missing = [p for p in all_posts if p["slug"] not in existing_slugs]
print(f"Already on new site: {len(all_posts) - len(missing)}")
print(f"To migrate: {len(missing)}")
print()

new_redirects = []
created = []
errors = []

for i, post in enumerate(missing):
    slug = post["slug"]
    print(f"[{i+1}/{len(missing)}] {slug}")

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

        # Merge metadata
        post.update({k: v for k, v in full_post.items() if k != "richContent"})

        page_html = make_html(post, body_html)

        # Write file
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
    """Merge /post/ → /blog/ rules without duplicating migration blocks."""
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

print(f"\n✅ Created: {len(created)} blog posts")
print(f"❌ Errors:  {len(errors)}")
if errors:
    print("  Failed:", errors)
print(f"✅ _redirects updated with {redirect_count} specific /post/ rules")
