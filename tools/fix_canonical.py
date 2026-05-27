#!/usr/bin/env python3
"""
Change 6 — Fix rel=canonical tags.
  Bucket 1 (73 pages): relative canonical → convert to absolute
  Bucket 2 (76 pages): already absolute → skip
  Bucket 3 (2 pages):  no canonical → add (privacy, terms only)
  Remaining (58):       stubs + 404.html → skip

Trailing-slash policy: preserve existing path exactly (no add/remove).
Site uses NO trailing slashes for top-level pages (confirmed via sitemap).

Usage:
  python3 tools/fix_canonical.py           # dry-run
  python3 tools/fix_canonical.py --apply   # write changes
"""
import argparse, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from site_utils import SITE, is_redirect_stub

BASE_URL = 'https://www.empowerfitnesspt.com'

# Pages that need a canonical ADDED (Bucket 3 — only these 2)
ADD_CANONICAL = {
    'privacy/index.html': f'{BASE_URL}/privacy',
    'terms/index.html':   f'{BASE_URL}/terms',
}

# Match <link rel="canonical"> regardless of attribute order
CANONICAL_PAT = re.compile(
    r'<link\s[^>]*rel=["\']canonical["\'][^>]*>',
    re.IGNORECASE
)

# Extract href value from a canonical tag
HREF_PAT = re.compile(r'\bhref=["\']([^"\']*)["\']', re.IGNORECASE)


def get_canonical_href(tag):
    m = HREF_PAT.search(tag)
    return m.group(1) if m else None


def make_absolute_canonical(path_str):
    """Prepend BASE_URL to a relative path, preserving trailing slash."""
    return f'{BASE_URL}{path_str}'


def build_canonical_tag(url):
    return f'<link rel="canonical" href="{url}">'


def insert_canonical_after_last_meta(html, tag):
    """Insert canonical tag after the last <meta> tag in <head>."""
    head_end = re.search(r'</head>', html, re.IGNORECASE)
    if not head_end:
        return html, False
    head_chunk = html[:head_end.start()]
    # Find last <meta ...> in head
    last_meta = None
    for m in re.finditer(r'<meta\b[^>]*/?>|<meta\b[^>]*>', head_chunk, re.IGNORECASE):
        last_meta = m
    if last_meta:
        insert_pos = last_meta.end()
    else:
        # Fall back: just before </head>
        insert_pos = head_end.start()
    new_html = html[:insert_pos] + '\n' + tag + html[insert_pos:]
    return new_html, True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    dry = not args.apply

    converted = []
    added = []
    skipped_absolute = 0
    skipped_stub = 0
    skipped_404 = 0
    errors = []

    all_files = sorted(SITE.rglob('index.html')) + sorted(SITE.glob('*.html'))

    for path in sorted(set(all_files)):
        rel = str(path.relative_to(SITE))

        # Skip 404
        if path.name == '404.html':
            skipped_404 += 1
            continue

        try:
            html = path.read_text(encoding='utf-8')
        except Exception as e:
            errors.append((rel, str(e)))
            continue

        # Skip stubs
        if is_redirect_stub(html):
            skipped_stub += 1
            continue

        canonical_match = CANONICAL_PAT.search(html)

        if canonical_match:
            href = get_canonical_href(canonical_match.group(0))
            if href is None:
                errors.append((rel, 'canonical tag found but no href'))
                continue

            if href.startswith('https://') or href.startswith('http://'):
                # Bucket 2: already absolute — skip
                skipped_absolute += 1
                continue

            # Bucket 1: relative → convert
            new_url = make_absolute_canonical(href)
            new_tag = build_canonical_tag(new_url)
            new_html = html[:canonical_match.start()] + new_tag + html[canonical_match.end():]
            converted.append((rel, href, new_url))
            if not dry:
                path.write_text(new_html, encoding='utf-8')

        else:
            # No canonical tag
            if rel in ADD_CANONICAL:
                # Bucket 3: add for privacy + terms
                new_url = ADD_CANONICAL[rel]
                new_tag = build_canonical_tag(new_url)
                new_html, ok = insert_canonical_after_last_meta(html, new_tag)
                if ok:
                    added.append((rel, new_url))
                    if not dry:
                        path.write_text(new_html, encoding='utf-8')
                else:
                    errors.append((rel, 'could not find insertion point'))
            # else: stub caught above, or other no-canonical page → implicitly skipped

    print(f"\n=== fix_canonical.py {'DRY RUN' if dry else 'APPLIED'} ===\n")
    print(f"  Canonical converted (relative→absolute): {len(converted)}")
    print(f"  Canonical added (missing):               {len(added)}")
    print(f"  Canonical skipped (already absolute):    {skipped_absolute}")
    print(f"  Stubs skipped:                           {skipped_stub}")
    print(f"  404.html skipped:                        {skipped_404}")
    print(f"  Errors:                                  {len(errors)}")
    if added:
        print(f"\n  Added canonicals:")
        for p, url in added:
            print(f"    {p} → {url}")
    if errors:
        print(f"\n  Errors:")
        for p, e in errors:
            print(f"    {p}: {e}")
    if dry:
        print("\n  → Re-run with --apply to write changes.")
    print()


if __name__ == '__main__':
    main()
