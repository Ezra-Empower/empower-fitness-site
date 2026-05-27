#!/usr/bin/env python3
"""
Part 3: Assign unique hero images to ALL real blog posts + sync blog index card thumbnails.

What this script does:
1. Scans all real blog posts (non-stub, non-hub)
2. For each post, ensures it has a hero <figure> matching data/blog_images.json
3. Replaces duplicate/missing/wrong hero images
4. Updates og:image meta to match hero image
5. Syncs blog/index.html card thumbnails to match post hero images
6. Prints summary: updated / already-ok / missing-from-json / duplicate-ids
"""

import os, re, json
from collections import Counter

BLOG_DIR    = "/Users/ezra/Documents/Claude/empower-site/blog"
IMAGES_JSON = "/Users/ezra/Documents/Claude/empower-site/data/blog_images.json"

HUB_SLUGS = {
    "physical-therapy", "fitness", "weight-loss", "sports-therapy",
    "comprehensive-physical-therapy", "physical-therapy-vertigo", "empower-fitness",
}

# ── Load blog_images.json ─────────────────────────────────────────────────────
with open(IMAGES_JSON, encoding="utf-8") as f:
    BLOG_IMAGES = json.load(f)

def get_entry(slug):
    return BLOG_IMAGES.get(slug)

# ── Helpers ───────────────────────────────────────────────────────────────────
def is_stub(html):
    return 'http-equiv="refresh"' in html or 'window.location.replace' in html

def extract_hero_photo_id(html):
    """Extract the first Unsplash photo_id from content area (not nav/logo)."""
    # Find all unsplash photo URLs in content (after <body>)
    body_start = html.find('<body')
    if body_start == -1:
        body_start = 0
    body_html = html[body_start:]
    ids = re.findall(r'unsplash\.com/(photo-[a-zA-Z0-9_-]+)', body_html)
    # Skip logo (logo-gold.png is not unsplash, so first unsplash hit = hero)
    return ids[0] if ids else None

def build_figure(slug):
    """Build the correct hero <figure> HTML for a slug."""
    entry = get_entry(slug)
    if not entry:
        return None, None
    photo_id = entry["photo_id"]
    alt_text = entry["alt"]
    src = f"https://images.unsplash.com/{photo_id}?w=800&h=450&fit=crop&auto=format&q=80"
    og_src = f"https://images.unsplash.com/{photo_id}?w=1200&h=630&fit=crop&auto=format&q=80"
    fig = (
        f'<figure style="margin:2rem 0;text-align:center;">\n'
        f'  <img src="{src}" alt="{alt_text}"\n'
        f'       style="width:100%;max-width:750px;height:auto;border-radius:8px;'
        f'box-shadow:0 4px 20px rgba(0,0,0,0.15);" loading="lazy">\n'
        f'</figure>'
    )
    return fig, og_src

def remove_all_hero_figures(html):
    """Remove all Unsplash <figure> blocks from content area (keeps logo)."""
    # Remove <figure>...<img src="https://images.unsplash.com/...">...</figure>
    html = re.sub(
        r'<figure[^>]*>\s*<img[^>]*unsplash\.com[^>]*>[^<]*</figure>',
        '', html, flags=re.DOTALL
    )
    # Also remove the style-attr only version (no closing tag)
    html = re.sub(
        r'<figure[^>]*style="[^"]*"[^>]*>\s*<img[^>]*unsplash\.com[^>]*/?\s*>\s*</figure>',
        '', html, flags=re.DOTALL
    )
    return html

def inject_hero_figure(html, slug):
    """
    Inject one hero <figure> at the correct location:
    - After <div class="content-wrap"> (osteoporosis / migrated template)
    - After <div class="article-container"> (back-pain-pt style)
    - After first <p> in main content for other layouts
    Returns (new_html, was_changed).
    """
    fig, og_src = build_figure(slug)
    if fig is None:
        return html, False

    # Remove all existing hero figures first (clean slate)
    html_clean = remove_all_hero_figures(html)

    # Strategy 1: inject after <div class="content-wrap">
    m = re.search(r'(<div\s+class="content-wrap"[^>]*>)', html_clean)
    if m:
        insert_pos = m.end()
        new_html = html_clean[:insert_pos] + '\n' + fig + '\n' + html_clean[insert_pos:]
        return update_og_image(new_html, og_src), True

    # Strategy 2: inject after <div class="article-container">
    m = re.search(r'(<div\s+class="article-container"[^>]*>)', html_clean)
    if m:
        insert_pos = m.end()
        new_html = html_clean[:insert_pos] + '\n' + fig + '\n' + html_clean[insert_pos:]
        return update_og_image(new_html, og_src), True

    # Strategy 3: inject after <main> or <article>
    m = re.search(r'(<main[^>]*>|<article[^>]*>)', html_clean)
    if m:
        insert_pos = m.end()
        new_html = html_clean[:insert_pos] + '\n' + fig + '\n' + html_clean[insert_pos:]
        return update_og_image(new_html, og_src), True

    # Strategy 4: inject before first <p> after <body>
    m = re.search(r'(<body[^>]*>.*?)(<p)', html_clean, re.DOTALL)
    if m:
        insert_pos = m.start(2)
        new_html = html_clean[:insert_pos] + fig + '\n' + html_clean[insert_pos:]
        return update_og_image(new_html, og_src), True

    # No insertion point found
    return html, False

def update_og_image(html, og_src):
    """Replace og:image meta content with post's hero image URL."""
    # Replace existing og:image
    html = re.sub(
        r'(<meta\s+property="og:image"\s+content=")[^"]*(")',
        lambda m: m.group(1) + og_src + m.group(2),
        html
    )
    return html

def post_has_correct_hero(html, slug):
    """Return True if the post already has the correct hero image and it's not duplicated."""
    entry = get_entry(slug)
    if not entry:
        return False
    photo_id = entry["photo_id"]
    matches = re.findall(r'unsplash\.com/(photo-[a-zA-Z0-9_-]+)', html)
    # Count how many times the correct ID appears
    correct_count = matches.count(photo_id)
    total_count   = len(matches)
    # Correct if: exactly one hero figure with the right ID, no duplicates
    return correct_count == 1 and total_count == 1

# ── Process all real blog posts ───────────────────────────────────────────────
print("=== Part 3: Assign unique hero images to all blog posts ===\n")

updated       = []
already_ok    = []
missing_json  = []
no_inject     = []

# First pass: determine what each post has
slug_to_photo = {}  # for duplicate detection

for name in sorted(os.listdir(BLOG_DIR)):
    if name == "index.html":
        continue
    post_dir = os.path.join(BLOG_DIR, name)
    idx = os.path.join(post_dir, "index.html")
    if not os.path.isfile(idx):
        continue
    with open(idx, encoding="utf-8") as f:
        html = f.read()
    if is_stub(html):
        continue
    if name in HUB_SLUGS:
        continue

    pid = extract_hero_photo_id(html)
    slug_to_photo[name] = pid

# Detect duplicates across posts
all_photo_ids = [v for v in slug_to_photo.values() if v]
dup_ids = {pid for pid, cnt in Counter(all_photo_ids).items() if cnt > 1}
if dup_ids:
    print(f"Found {len(dup_ids)} duplicate photo IDs across posts — will fix\n")

# Second pass: update files
for name in sorted(slug_to_photo.keys()):
    post_dir = os.path.join(BLOG_DIR, name)
    idx = os.path.join(post_dir, "index.html")
    with open(idx, encoding="utf-8") as f:
        html = f.read()

    entry = get_entry(name)
    if entry is None:
        missing_json.append(name)
        continue

    correct_id = entry["photo_id"]
    current_id = slug_to_photo[name]

    # Post is already correct if it has exactly the right ID and no duplicates
    if current_id == correct_id and current_id not in dup_ids:
        already_ok.append(name)
        continue

    # Need to update: inject correct figure (removes old one, adds new one)
    new_html, changed = inject_hero_figure(html, name)
    if changed:
        with open(idx, "w", encoding="utf-8") as f:
            f.write(new_html)
        updated.append(name)
        print(f"  ✓ Updated: {name}")
    else:
        no_inject.append(name)
        print(f"  ⚠ Could not inject: {name}")

print(f"\n{'='*60}")
print(f"  Updated:              {len(updated)}")
print(f"  Already correct:      {len(already_ok)}")
print(f"  Missing from JSON:    {len(missing_json)}")
print(f"  No injection point:   {len(no_inject)}")
if missing_json:
    print(f"\n  Missing from JSON: {missing_json}")
if no_inject:
    print(f"\n  Could not inject:  {no_inject}")

# ── Sync blog/index.html card thumbnails ──────────────────────────────────────
print(f"\n=== Syncing blog/index.html card thumbnails ===\n")

INDEX_FILE = os.path.join(BLOG_DIR, "index.html")
with open(INDEX_FILE, encoding="utf-8") as f:
    index_html = f.read()

cards_updated = 0
cards_ok      = 0
cards_missing = 0

# Find each card's slug from the href link, then update its image src
# Pattern: find card-img img src and the related card link href
# We'll process the HTML looking for blog-card divs

def update_card_image(html_content, slug, photo_id):
    """
    Find the blog card for a given slug and update its thumbnail image.
    Cards have pattern: href="/blog/{slug}" nearby a blog-card-img img.
    """
    # Find the card that links to this slug
    # Pattern: <div class="blog-card"> ... href="/blog/{slug}" ... <img src="...">
    card_pattern = re.compile(
        r'(href="/blog/' + re.escape(slug) + r'")',
        re.DOTALL
    )

    m = card_pattern.search(html_content)
    if not m:
        return html_content, False

    # Find the enclosing blog-card div
    card_start = html_content.rfind('<div class="blog-card"', 0, m.start())
    if card_start == -1:
        return html_content, False

    # Find the end of this card
    card_end = html_content.find('</div>', m.end())
    # Find nested div closes — walk forward to find the right closing </div>
    depth = 0
    pos = card_start
    while pos < len(html_content):
        if html_content[pos:pos+4] == '<div':
            depth += 1
        elif html_content[pos:pos+6] == '</div>':
            depth -= 1
            if depth == 0:
                card_end = pos + 6
                break
        pos += 1

    card_html = html_content[card_start:card_end]
    new_src = f"https://images.unsplash.com/{photo_id}?w=400&h=220&fit=crop&auto=format&q=80"

    # Replace img src in the card's blog-card-img div
    new_card = re.sub(
        r'(<img[^>]*class="[^"]*blog-card-img[^"]*"[^>]*src=")[^"]*(")',
        lambda m2: m2.group(1) + new_src + m2.group(2),
        card_html
    )
    # Also try: img inside a div with class blog-card-img
    if new_card == card_html:
        new_card = re.sub(
            r'(<div[^>]*class="[^"]*blog-card-img[^"]*"[^>]*>.*?<img[^>]*src=")[^"]*(")',
            lambda m2: m2.group(1) + new_src + m2.group(2),
            card_html, flags=re.DOTALL
        )
    # Generic: first img in the card
    if new_card == card_html:
        new_card = re.sub(
            r'(<img[^>]*src=")https://images\.unsplash\.com/photo-[^"]*(")',
            lambda m2: m2.group(1) + new_src + m2.group(2),
            card_html, count=1
        )

    if new_card != card_html:
        return html_content[:card_start] + new_card + html_content[card_end:], True
    return html_content, False

for slug, entry in BLOG_IMAGES.items():
    photo_id = entry["photo_id"]
    index_html, changed = update_card_image(index_html, slug, photo_id)
    if changed:
        cards_updated += 1
    else:
        # Check if already correct
        if f"{photo_id}?w=400" in index_html:
            cards_ok += 1
        else:
            cards_missing += 1

# Write updated index
with open(INDEX_FILE, "w", encoding="utf-8") as f:
    f.write(index_html)

print(f"  Cards updated:  {cards_updated}")
print(f"  Cards already OK: {cards_ok}")
print(f"  Cards not found: {cards_missing}")

# ── Final verification ────────────────────────────────────────────────────────
print(f"\n=== Final verification ===")

# Re-scan for duplicate photo IDs
print("\nChecking for duplicate photo IDs across all posts...")
final_ids = []
for name in sorted(os.listdir(BLOG_DIR)):
    if name == "index.html":
        continue
    post_dir = os.path.join(BLOG_DIR, name)
    idx = os.path.join(post_dir, "index.html")
    if not os.path.isfile(idx):
        continue
    with open(idx, encoding="utf-8") as f:
        html = f.read()
    if is_stub(html):
        continue
    if name in HUB_SLUGS:
        continue
    pid = extract_hero_photo_id(html)
    if pid:
        final_ids.append((name, pid))

dup_check = Counter(pid for _, pid in final_ids)
dups = [(pid, cnt) for pid, cnt in dup_check.items() if cnt > 1]
if dups:
    print(f"  ⚠ {len(dups)} duplicate photo IDs remaining:")
    for pid, cnt in sorted(dups):
        posts = [n for n, p in final_ids if p == pid]
        print(f"    {pid} (used {cnt}x): {posts}")
else:
    print(f"  ✓ All {len(final_ids)} posts have unique hero photo IDs")

# Check index card duplicates
index_ids = re.findall(r'unsplash\.com/(photo-[a-zA-Z0-9_-]+)\?w=400', index_html)
idx_dup = [(pid, cnt) for pid, cnt in Counter(index_ids).items() if cnt >= 3]
if idx_dup:
    print(f"\n  ⚠ Index cards with 3+ reuses:")
    for pid, cnt in sorted(idx_dup):
        print(f"    {pid}: used {cnt}x")
else:
    unique_count = len(set(index_ids))
    print(f"  ✓ Index card images: {len(index_ids)} total, {unique_count} unique (max reuse: {max(Counter(index_ids).values()) if index_ids else 0}x)")

print("\n✅ Done.")
