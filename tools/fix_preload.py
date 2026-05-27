#!/usr/bin/env python3
"""
Change 2 — Add preconnect + preload hints.
  Part A: Homepage gets preconnect + preload for CSS background hero image.
  Part B: All 209 pages get preconnect to GTM and Unsplash origins.
  Part C: ~132 real blog posts get fetchpriority="high" on first hero img
          and have loading="lazy" removed from that same img.

Usage:
  python3 tools/fix_preload.py           # dry-run
  python3 tools/fix_preload.py --apply   # write changes
"""
import argparse, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from site_utils import SITE, is_redirect_stub

HOMEPAGE = SITE / 'index.html'
BLOG_DIR = SITE / 'blog'

# Hub blog slugs (not real posts)
HUB_SLUGS = {
    'physical-therapy', 'fitness', 'weight-loss', 'sports-therapy',
    'comprehensive-physical-therapy', 'physical-therapy-vertigo',
    'empower-fitness',
}

NO_GTM_PAGES = {
    'blog/low-back-pain/index.html',
    'locations/boca-raton/index.html',
    'locations/delray-beach/index.html',
    'locations/pompano-beach/index.html',
    'schedule/index.html',
    'services/fitness-training/index.html',
    'services/in-home-physical-therapy/index.html',
    'services/in-home-pt/index.html',
    'services/longevity/index.html',
    'services/return-to-sport/index.html',
}

HOMEPAGE_HERO_URL = (
    'https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=1400&q=80'
)

PRELOAD_BLOCK = (
    '<link rel="preconnect" href="https://images.unsplash.com" crossorigin>\n'
    f'<link rel="preload" as="image" href="{HOMEPAGE_HERO_URL}" fetchpriority="high">'
)

GTM_PRECONNECT = '<link rel="preconnect" href="https://www.googletagmanager.com">'
UNSPLASH_PRECONNECT = '<link rel="preconnect" href="https://images.unsplash.com" crossorigin>'


def already_has(html, fragment):
    return fragment in html


def add_preload_to_homepage(html):
    """Insert preconnect + preload immediately after <meta charset=.../>."""
    charset_pat = re.compile(r'(<meta\s+charset=[^>]+>)', re.IGNORECASE)
    m = charset_pat.search(html)
    if not m:
        return html, False
    insert_pos = m.end()
    new_html = html[:insert_pos] + '\n' + PRELOAD_BLOCK + html[insert_pos:]
    return new_html, True


def add_preconnects_before_head_end(html, include_gtm):
    """Insert preconnect tags before </head>."""
    # Build what's needed
    to_add = []
    if include_gtm and not already_has(html, 'preconnect" href="https://www.googletagmanager.com"'):
        to_add.append(GTM_PRECONNECT)
    if not already_has(html, 'preconnect" href="https://images.unsplash.com"'):
        to_add.append(UNSPLASH_PRECONNECT)
    if not to_add:
        return html, False
    block = '\n'.join(to_add)
    new_html = re.sub(r'(</head>)', '\n' + block + '\n\\1', html, count=1, flags=re.IGNORECASE)
    changed = new_html != html
    return new_html, changed


def fix_blog_hero_img(html):
    """
    Find the first Unsplash <img> in the page (the hero figure).
    Add fetchpriority="high" and remove loading="lazy" from it only.
    Returns (new_html, changed).
    """
    # Find first unsplash img tag
    img_pat = re.compile(
        r'(<img\b[^>]*https://images\.unsplash\.com[^>]*>)',
        re.DOTALL | re.IGNORECASE
    )
    m = img_pat.search(html)
    if not m:
        return html, False

    original_tag = m.group(1)
    tag = original_tag

    # Remove loading="lazy" or loading='lazy'
    tag = re.sub(r'\s+loading=["\']lazy["\']', '', tag, flags=re.IGNORECASE)

    # Add fetchpriority="high" if not already present
    if 'fetchpriority' not in tag.lower():
        # Insert before the closing > or />
        tag = re.sub(r'(\s*/?>\s*)$', ' fetchpriority="high"\\1', tag)

    if tag == original_tag:
        return html, False

    new_html = html[:m.start()] + tag + html[m.end():]
    return new_html, True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    dry = not args.apply

    preload_done = 0
    preconnect_done = 0
    hero_done = 0
    hero_skipped_stub = 0
    hero_skipped_no_unsplash = 0
    errors = []

    all_html_files = sorted(SITE.rglob('index.html')) + sorted(SITE.glob('*.html'))
    all_html_files = [p for p in all_html_files if p.name != 'index.html' or p == p]  # keep all

    for path in sorted(set(all_html_files)):
        rel = str(path.relative_to(SITE))
        try:
            html = path.read_text(encoding='utf-8')
        except Exception as e:
            errors.append((rel, str(e)))
            continue

        changed = False
        new_html = html

        # ── Part A: Homepage preload ──────────────────────────────────────────
        if path == HOMEPAGE:
            if HOMEPAGE_HERO_URL not in new_html or 'preload' not in new_html:
                new_html, ok = add_preload_to_homepage(new_html)
                if ok:
                    preload_done += 1
                    changed = True

        # ── Part B: Preconnect on all pages ───────────────────────────────────
        include_gtm = rel not in NO_GTM_PAGES
        # Skip Unsplash preconnect on homepage if already added via Part A
        if path == HOMEPAGE:
            # Only add GTM preconnect (Unsplash already in preload block)
            if include_gtm and not already_has(new_html, GTM_PRECONNECT):
                new_html = re.sub(
                    r'(</head>)',
                    '\n' + GTM_PRECONNECT + '\n\\1',
                    new_html, count=1, flags=re.IGNORECASE
                )
                preconnect_done += 1
                changed = True
        else:
            new_html, ok = add_preconnects_before_head_end(new_html, include_gtm)
            if ok:
                preconnect_done += 1
                changed = True

        # ── Part C: Blog hero img fetchpriority ───────────────────────────────
        # Only real blog posts (not homepage, not stubs, not hubs)
        if (path.parent.parent == BLOG_DIR and
                path.parent.name not in HUB_SLUGS and
                path.parent.name != 'blog'):
            if is_redirect_stub(html):
                hero_skipped_stub += 1
            elif 'images.unsplash.com' not in html:
                hero_skipped_no_unsplash += 1
            else:
                new_html, ok = fix_blog_hero_img(new_html)
                if ok:
                    hero_done += 1
                    changed = True

        if changed and not dry:
            path.write_text(new_html, encoding='utf-8')

    print(f"\n=== fix_preload.py {'DRY RUN' if dry else 'APPLIED'} ===\n")
    print(f"  Homepage preload added:          {preload_done}")
    print(f"  Pages with preconnect added:     {preconnect_done}")
    print(f"  Blog hero fetchpriority added:   {hero_done}")
    print(f"  Blog stubs skipped (Part C):     {hero_skipped_stub}")
    print(f"  Blog posts skipped (no img):     {hero_skipped_no_unsplash}")
    print(f"  Errors:                          {len(errors)}")
    if errors:
        print("\n  Errors:")
        for p, e in errors:
            print(f"    {p}: {e}")
    if dry:
        print("\n  → Re-run with --apply to write changes.")
    print()


if __name__ == '__main__':
    main()
