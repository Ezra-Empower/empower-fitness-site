#!/usr/bin/env python3
"""
Change 2c+2d — Fix low-contrast footer text colors across all HTML files.

Replacements (replace applied to every occurrence per file — index.html
has two duplicate footer CSS blocks from the inlining done in fix_inline_css.py):

  .footer-bottom p { font-size: 12px; color: #555; }
      → color: #888

  .footer-brand p block: color: var(--gray)  → color: #bbbbbb
  .footer-col li  block: color: var(--gray)  → color: #bbbbbb
  .footer-col li a: color: var(--gray)       → color: #bbbbbb

Also updates /css/site-footer.css source file.

Usage:
  python3 tools/fix_contrast.py           # dry-run
  python3 tools/fix_contrast.py --apply   # write changes
"""
import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from site_utils import SITE, is_redirect_stub

CSS_SOURCE = SITE / 'css' / 'site-footer.css'

# Each (old, new) pair — applied as str.replace() which replaces ALL occurrences
PAIRS = [
    # footer-bottom p
    (
        '.footer-bottom p { font-size: 12px; color: #555; }',
        '.footer-bottom p { font-size: 12px; color: #888; }'
    ),
    # footer-col li a (single-line rule)
    (
        '.footer-col li a { color: var(--gray); transition: color 0.2s; }',
        '.footer-col li a { color: #bbbbbb; transition: color 0.2s; }'
    ),
    # footer-brand p block — use the unique 3-line fingerprint
    (
        '.footer-brand p {\n      font-size: 14px;\n      color: var(--gray);',
        '.footer-brand p {\n      font-size: 14px;\n      color: #bbbbbb;'
    ),
    # footer-col li block — use the unique 3-line fingerprint
    (
        '.footer-col li {\n      font-size: 14px;\n      color: var(--gray);',
        '.footer-col li {\n      font-size: 14px;\n      color: #bbbbbb;'
    ),
]


def apply_pairs(text):
    for old, new in PAIRS:
        text = text.replace(old, new)
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    dry = not args.apply

    updated = 0
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

        new_html = apply_pairs(html)

        if new_html == html:
            skipped += 1
            continue

        updated += 1
        if not dry:
            path.write_text(new_html, encoding='utf-8')

    # Also fix site-footer.css source
    css_changed = False
    try:
        css = CSS_SOURCE.read_text(encoding='utf-8')
        new_css = apply_pairs(css)
        if new_css != css:
            css_changed = True
            if not dry:
                CSS_SOURCE.write_text(new_css, encoding='utf-8')
    except Exception as e:
        errors.append((str(CSS_SOURCE.relative_to(SITE)), str(e)))

    print(f"\n=== fix_contrast.py {'DRY RUN' if dry else 'APPLIED'} ===\n")
    print(f"  HTML files {'would be' if dry else ''} updated:  {updated}")
    print(f"  HTML files skipped (no match):     {skipped}")
    print(f"  site-footer.css {'would be' if dry else ''} updated:  {css_changed}")
    print(f"  Errors:                            {len(errors)}")
    if errors:
        print("\n  Errors:")
        for p, e in errors:
            print(f"    {p}: {e}")
    if dry:
        print("\n  → Re-run with --apply to write changes.")
    print()


if __name__ == '__main__':
    main()
