#!/usr/bin/env python3
"""
Change 1 — Delay GTM + Facebook Pixel initialization.
Replaces the synchronous GTM head snippet with a deferred version that
fires after 3.5s idle OR first user interaction, whichever comes first.

Usage:
  python3 tools/fix_gtm_delay.py           # dry-run
  python3 tools/fix_gtm_delay.py --apply   # write changes
"""
import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from site_utils import SITE, iter_html_files

# ── Exact string to find (must match every page precisely) ────────────────────
OLD_GTM = """\
<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
})(window,document,'script','dataLayer','GTM-W8K8GRZQ');</script>
<!-- End Google Tag Manager -->"""

NEW_GTM = """\
<!-- Google Tag Manager — deferred for performance -->
<script>
(function(){
  var gtmLoaded=false;
  function loadGTM(){
    if(gtmLoaded)return;
    gtmLoaded=true;
    (function(w,d,s,l,i){
      w[l]=w[l]||[];
      w[l].push({'gtm.start':new Date().getTime(),event:'gtm.js'});
      var f=d.getElementsByTagName(s)[0],
          j=d.createElement(s),
          dl=l!='dataLayer'?'&l='+l:'';
      j.async=true;
      j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;
      f.parentNode.insertBefore(j,f);
    })(window,document,'script','dataLayer','GTM-W8K8GRZQ');
  }
  setTimeout(loadGTM,3500);
  ['mousedown','touchstart','keydown','scroll','mousemove'].forEach(function(e){
    document.addEventListener(e,loadGTM,{once:true,passive:true});
  });
})();
</script>
<!-- End Google Tag Manager -->"""

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    dry = not args.apply

    updated, skipped_no_gtm, skipped_already_new, errors = [], [], [], []

    for path in iter_html_files():
        rel = str(path.relative_to(SITE))
        try:
            html = path.read_text(encoding='utf-8')
        except Exception as e:
            errors.append((rel, str(e)))
            continue

        # Check if this is a known no-GTM page
        if rel in NO_GTM_PAGES:
            skipped_no_gtm.append(rel)
            continue

        # Already updated
        if 'gtmLoaded' in html:
            skipped_already_new.append(rel)
            continue

        # Has old GTM snippet — replace it
        if OLD_GTM in html:
            new_html = html.replace(OLD_GTM, NEW_GTM, 1)
            if not dry:
                path.write_text(new_html, encoding='utf-8')
            updated.append(rel)
        # Has GTM ID but in some other format — skip with warning
        elif 'GTM-W8K8GRZQ' in html:
            errors.append((rel, 'GTM present but snippet format unexpected — skipped'))

    print(f"\n=== fix_gtm_delay.py {'DRY RUN' if dry else 'APPLIED'} ===\n")
    print(f"  GTM delay {'would be applied' if dry else 'applied'}: {len(updated)}")
    print(f"  Skipped (no GTM — known list):  {len(skipped_no_gtm)}")
    print(f"  Skipped (already deferred):     {len(skipped_already_new)}")
    print(f"  Errors:                         {len(errors)}")
    if skipped_no_gtm:
        print(f"\n  No-GTM pages (not touched):")
        for p in sorted(skipped_no_gtm):
            print(f"    {p}")
    if errors:
        print(f"\n  Errors:")
        for p, e in errors:
            print(f"    {p}: {e}")
    if dry:
        print("\n  → Re-run with --apply to write changes.")
    print()


if __name__ == '__main__':
    main()
