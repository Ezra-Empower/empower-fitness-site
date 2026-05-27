#!/usr/bin/env python3
"""
Change 4 — Optimize logo-gold.png.
  Step 1: Generate /img/logo-gold.webp and /img/logo-gold-small.png
          at 122×64 px (2× retina of 61×32 display size).
  Step 2: Replace all <img src="/img/logo-gold.png"> tags across all
          HTML files with a <picture> element using WebP + PNG fallback.
          Does NOT touch og:image meta tags or JSON-LD references.

Usage:
  python3 tools/fix_logo.py           # dry-run
  python3 tools/fix_logo.py --apply   # write changes
"""
import argparse, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from site_utils import SITE

IMG_DIR = SITE / 'img'
ORIG_PNG = IMG_DIR / 'logo-gold.png'
NEW_WEBP = IMG_DIR / 'logo-gold.webp'
NEW_PNG  = IMG_DIR / 'logo-gold-small.png'

TARGET_W, TARGET_H = 122, 64  # 2× retina of ~61×32 display px

# Match <img> tags whose src is /img/logo-gold.png (not in meta/JSON-LD)
IMG_TAG_PAT = re.compile(
    r'<img\b([^>]*)src=["\']\/img\/logo-gold\.png["\']([^>]*)\/?>',
    re.IGNORECASE | re.DOTALL
)


def generate_images(dry):
    """Generate WebP and small PNG using Pillow."""
    try:
        from PIL import Image
    except ImportError:
        print("  ERROR: Pillow not installed. Run: pip3 install Pillow")
        return False

    img = Image.open(ORIG_PNG).convert('RGBA')
    resized = img.resize((TARGET_W, TARGET_H), Image.LANCZOS)

    if dry:
        print(f"  [dry-run] Would generate {NEW_WEBP.name} at {TARGET_W}×{TARGET_H}")
        print(f"  [dry-run] Would generate {NEW_PNG.name} at {TARGET_W}×{TARGET_H}")
        return True

    resized.save(str(NEW_WEBP), 'WEBP', quality=90)
    resized.save(str(NEW_PNG), 'PNG', optimize=True)

    webp_kb = NEW_WEBP.stat().st_size / 1024
    png_kb  = NEW_PNG.stat().st_size / 1024
    orig_kb = ORIG_PNG.stat().st_size / 1024
    print(f"  Generated {NEW_WEBP.name}: {webp_kb:.1f} KB (was {orig_kb:.1f} KB)")
    print(f"  Generated {NEW_PNG.name}: {png_kb:.1f} KB")
    return True


def replacement_picture(before_attrs, after_attrs):
    """Build the <picture> replacement HTML preserving existing style/alt attrs."""
    # Combine attribute fragments
    all_attrs = (before_attrs + ' ' + after_attrs).strip()
    # Remove src (already handled in <img src=...)
    all_attrs = re.sub(r'\bsrc=["\'][^"\']*["\']', '', all_attrs).strip()
    # Ensure width and height are set
    if 'width=' not in all_attrs:
        all_attrs += f' width="{TARGET_W}"'
    if 'height=' not in all_attrs:
        all_attrs += f' height="{TARGET_H}"'
    # Clean up extra whitespace
    all_attrs = re.sub(r'\s+', ' ', all_attrs).strip()

    return (
        '<picture>\n'
        '      <source srcset="/img/logo-gold.webp" type="image/webp">\n'
        f'      <img src="/img/logo-gold-small.png" {all_attrs}>\n'
        '    </picture>'
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    dry = not args.apply

    print(f"\n=== fix_logo.py {'DRY RUN' if dry else 'APPLIED'} ===\n")

    # Step 1: Generate images
    print("  Step 1 — Generate optimized logo images:")
    ok = generate_images(dry)
    if not ok:
        sys.exit(1)

    # Step 2: Replace <img> tags in HTML
    print("\n  Step 2 — Replace <img> tags with <picture> elements:")

    pages_updated = 0
    instances_replaced = 0
    og_image_unchanged = 0
    errors = []

    all_files = sorted(SITE.rglob('index.html')) + sorted(SITE.glob('*.html'))

    for path in sorted(set(all_files)):
        rel = str(path.relative_to(SITE))
        try:
            html = path.read_text(encoding='utf-8')
        except Exception as e:
            errors.append((rel, str(e)))
            continue

        if '/img/logo-gold.png' not in html:
            continue

        # Count og:image and JSON-LD references (must remain untouched)
        og_count = html.count('og:image')
        jsonld_count = html.count('"logo"')
        og_image_unchanged += og_count + jsonld_count

        # Replace only <img> tags pointing to logo-gold.png
        def make_replacement(m):
            return replacement_picture(m.group(1), m.group(2))

        new_html, n = IMG_TAG_PAT.subn(make_replacement, html)
        if n == 0:
            continue

        instances_replaced += n
        pages_updated += 1

        if not dry:
            path.write_text(new_html, encoding='utf-8')

    print(f"\n  Pages {'would be' if dry else ''} updated:     {pages_updated}")
    print(f"  <img> instances replaced:  {instances_replaced}")
    print(f"  og:image/JSON-LD skipped:  {og_image_unchanged} (unchanged)")
    print(f"  Errors:                    {len(errors)}")
    if errors:
        print("\n  Errors:")
        for p, e in errors:
            print(f"    {p}: {e}")
    if dry:
        print("\n  → Re-run with --apply to write changes.")
    print()


if __name__ == '__main__':
    main()
