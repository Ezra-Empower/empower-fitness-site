#!/usr/bin/env python3
"""
Change 7a — Add <main> landmark element.
Wraps page content between </nav> and <footer> in a <main> tag for
screen reader accessibility.

Skip rules:
  - Pages already containing <main> (23 pages)
  - Redirect stubs (is_redirect_stub())
  - 404.html
  - Pages without the expected </nav> ... <footer> structure

Usage:
  python3 tools/fix_main_landmark.py           # dry-run
  python3 tools/fix_main_landmark.py --apply   # write changes
"""
import argparse, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from site_utils import SITE, is_redirect_stub


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    dry = not args.apply

    added = 0
    skip_has_main = 0
    skip_stub = 0
    skip_404 = 0
    skip_no_structure = 0
    errors = []

    all_files = sorted(SITE.rglob('index.html')) + sorted(SITE.glob('*.html'))

    for path in sorted(set(all_files)):
        rel = str(path.relative_to(SITE))

        if path.name == '404.html':
            skip_404 += 1
            continue

        try:
            html = path.read_text(encoding='utf-8')
        except Exception as e:
            errors.append((rel, str(e)))
            continue

        if is_redirect_stub(html):
            skip_stub += 1
            continue

        # Skip if already has <main>
        if re.search(r'<main[\s>]', html, re.IGNORECASE):
            skip_has_main += 1
            continue

        # Find </nav> and <footer (must have both for safe wrapping)
        nav_close  = re.search(r'</nav>', html, re.IGNORECASE)
        footer_open = re.search(r'<footer[\s>]', html, re.IGNORECASE)

        if not nav_close or not footer_open:
            skip_no_structure += 1
            continue

        # Sanity: </nav> must come before <footer>
        if nav_close.end() >= footer_open.start():
            skip_no_structure += 1
            continue

        # Insert <main> after </nav> and </main> before <footer>
        insert_main_open  = nav_close.end()
        insert_main_close = footer_open.start()

        new_html = (
            html[:insert_main_open]
            + '\n<main>'
            + html[insert_main_open:insert_main_close]
            + '</main>\n'
            + html[insert_main_close:]
        )

        added += 1
        if not dry:
            path.write_text(new_html, encoding='utf-8')

    print(f"\n=== fix_main_landmark.py {'DRY RUN' if dry else 'APPLIED'} ===\n")
    print(f"  <main> {'would be added' if dry else 'added'}:         {added}")
    print(f"  Skipped (already has <main>):  {skip_has_main}")
    print(f"  Skipped (redirect stub):       {skip_stub}")
    print(f"  Skipped (404.html):            {skip_404}")
    print(f"  Skipped (no nav+footer):       {skip_no_structure}")
    print(f"  Errors:                        {len(errors)}")
    if errors:
        print("\n  Errors:")
        for p, e in errors:
            print(f"    {p}: {e}")
    if dry:
        print("\n  → Re-run with --apply to write changes.")
    print()


if __name__ == '__main__':
    main()
