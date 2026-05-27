#!/usr/bin/env python3
"""
Change 3 — Fix heading hierarchy: replace footer <h4> elements with <p
class="footer-col-heading"> to eliminate h1→h4 level skip.

HTML changes (all occurrences — footer only):
  <h4>Services</h4>  → <p class="footer-col-heading">Services</p>
  <h4>Company</h4>   → <p class="footer-col-heading">Company</p>
  <h4>Contact</h4>   → <p class="footer-col-heading">Contact</p>

CSS changes (all occurrences — index.html has two duplicate blocks):
  .footer-col h4 {   → .footer-col-heading {

Also updates /css/site-footer.css source file.

Usage:
  python3 tools/fix_headings.py           # dry-run
  python3 tools/fix_headings.py --apply   # write changes
"""
import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from site_utils import SITE

CSS_SOURCE = SITE / 'css' / 'site-footer.css'

# HTML replacements (str.replace — replaces all occurrences per file)
HTML_PAIRS = [
    ('<h4>Services</h4>', '<p class="footer-col-heading">Services</p>'),
    ('<h4>Company</h4>',  '<p class="footer-col-heading">Company</p>'),
    ('<h4>Contact</h4>',  '<p class="footer-col-heading">Contact</p>'),
    ('.footer-col h4 {',  '.footer-col-heading {'),
]

# CSS source replacements
CSS_PAIRS = [
    ('.footer-col h4 {',  '.footer-col-heading {'),
]


def apply_pairs(text, pairs):
    for old, new in pairs:
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

        new_html = apply_pairs(html, HTML_PAIRS)

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
        new_css = apply_pairs(css, CSS_PAIRS)
        if new_css != css:
            css_changed = True
            if not dry:
                CSS_SOURCE.write_text(new_css, encoding='utf-8')
    except Exception as e:
        errors.append((str(CSS_SOURCE.relative_to(SITE)), str(e)))

    print(f"\n=== fix_headings.py {'DRY RUN' if dry else 'APPLIED'} ===\n")
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
