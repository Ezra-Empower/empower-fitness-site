#!/usr/bin/env python3
"""
Change 3 — Inline render-blocking external CSS files.

Removes <link rel="stylesheet"> tags for the 4 blocking CSS files and
inlines their contents directly in each page's <head>:
  - /css/mobile-base.css      → 152 pages  (Step 2a)
  - /css/mobile-overrides.css → 152 pages  (Step 2a)
  - /css/mobile-sections.css  → 152 pages  (Step 2a)
  - /css/site-footer.css      → 208 pages  (Step 2b, :root deduped)

mobile-tables.css is left external (13 pages, non-critical).

Usage:
  python3 tools/fix_inline_css.py           # dry-run
  python3 tools/fix_inline_css.py --apply   # write changes
"""
import argparse, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from site_utils import SITE

CSS_DIR = SITE / 'css'

# ── Load CSS file contents ────────────────────────────────────────────────────

def load_css(filename):
    return (CSS_DIR / filename).read_text(encoding='utf-8')

MOBILE_BASE      = load_css('mobile-base.css')
MOBILE_OVERRIDES = load_css('mobile-overrides.css')
MOBILE_SECTIONS  = load_css('mobile-sections.css')
SITE_FOOTER_RAW  = load_css('site-footer.css')

# Strip the :root{} block from site-footer.css (already present in every page)
SITE_FOOTER_CSS = re.sub(
    r':root\s*\{[^}]*\}',
    '',
    SITE_FOOTER_RAW,
    flags=re.DOTALL
).strip()

# Combine the mobile trio into one block
MOBILE_COMBINED = '\n'.join([MOBILE_BASE, MOBILE_OVERRIDES, MOBILE_SECTIONS])

# Link tag patterns to detect and remove
LINK_PATTERNS = {
    'mobile-base':      re.compile(r'\s*<link\s[^>]*href=["\']\/css\/mobile-base\.css["\'][^>]*>\n?', re.IGNORECASE),
    'mobile-overrides': re.compile(r'\s*<link\s[^>]*href=["\']\/css\/mobile-overrides\.css["\'][^>]*>\n?', re.IGNORECASE),
    'mobile-sections':  re.compile(r'\s*<link\s[^>]*href=["\']\/css\/mobile-sections\.css["\'][^>]*>\n?', re.IGNORECASE),
    'site-footer':      re.compile(r'\s*<link\s[^>]*href=["\']\/css\/site-footer\.css["\'][^>]*>\n?', re.IGNORECASE),
}


def process_file(html):
    """
    Returns (new_html, had_mobile, had_footer, changed).
    """
    had_mobile = bool(LINK_PATTERNS['mobile-base'].search(html))
    had_footer = bool(LINK_PATTERNS['site-footer'].search(html))

    if not had_mobile and not had_footer:
        return html, False, False, False

    new_html = html

    # ── Step 1: Remove all matching <link> tags ───────────────────────────────
    for key in ('mobile-base', 'mobile-overrides', 'mobile-sections', 'site-footer'):
        new_html = LINK_PATTERNS[key].sub('', new_html)

    # ── Step 2a: Inline mobile trio as a new <style> before </head> ──────────
    if had_mobile:
        mobile_style = f'\n<style>\n{MOBILE_COMBINED}\n</style>'
        new_html = re.sub(
            r'(</head>)',
            mobile_style + '\n\\1',
            new_html, count=1, flags=re.IGNORECASE
        )

    # ── Step 2b: Append footer CSS to the FIRST existing <style> block ───────
    if had_footer:
        # Find the first <style>...</style> block
        style_pat = re.compile(r'(<style[^>]*>)(.*?)(</style>)', re.DOTALL | re.IGNORECASE)
        m = style_pat.search(new_html)
        if m:
            # Append footer CSS inside the existing block
            new_content = m.group(2).rstrip() + '\n/* site-footer */\n' + SITE_FOOTER_CSS + '\n'
            new_html = (
                new_html[:m.start()]
                + m.group(1) + new_content + m.group(3)
                + new_html[m.end():]
            )
        else:
            # No existing <style> — create one before </head>
            footer_style = f'\n<style>\n{SITE_FOOTER_CSS}\n</style>'
            new_html = re.sub(
                r'(</head>)',
                footer_style + '\n\\1',
                new_html, count=1, flags=re.IGNORECASE
            )

    changed = new_html != html
    return new_html, had_mobile, had_footer, changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    dry = not args.apply

    both_done = 0
    mobile_only = 0
    footer_only = 0
    skipped = 0
    errors = []

    all_files = sorted(SITE.rglob('index.html')) + sorted(SITE.glob('*.html'))

    for path in sorted(set(all_files)):
        rel = str(path.relative_to(SITE))
        try:
            html = path.read_text(encoding='utf-8')
        except Exception as e:
            errors.append((rel, str(e)))
            continue

        new_html, had_mobile, had_footer, changed = process_file(html)

        if not changed:
            skipped += 1
            continue

        if had_mobile and had_footer:
            both_done += 1
        elif had_mobile:
            mobile_only += 1
        elif had_footer:
            footer_only += 1

        if not dry:
            path.write_text(new_html, encoding='utf-8')

    total = both_done + mobile_only + footer_only
    print(f"\n=== fix_inline_css.py {'DRY RUN' if dry else 'APPLIED'} ===\n")
    print(f"  Total pages {'would be' if dry else ''} updated:  {total}")
    print(f"    Both mobile + footer inlined:  {both_done}")
    print(f"    Mobile trio only:              {mobile_only}")
    print(f"    Footer only (57-page group):   {footer_only}")
    print(f"  Skipped (no matching links):     {skipped}")
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
