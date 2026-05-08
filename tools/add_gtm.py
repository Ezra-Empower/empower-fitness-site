#!/usr/bin/env python3
"""
Empower Fitness — GTM Snippet Injector
Injects Google Tag Manager snippets into all real HTML pages.

Usage:
  python3 tools/add_gtm.py           # dry-run (default)
  python3 tools/add_gtm.py --apply   # write changes
"""
import argparse, os, re, sys
from pathlib import Path

SITE = Path(__file__).parent.parent
GTM_ID = 'GTM-W8K8GRZQ'

GTM_HEAD = """\
<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
})(window,document,'script','dataLayer','GTM-W8K8GRZQ');</script>
<!-- End Google Tag Manager -->"""

GTM_BODY = """\
<!-- Google Tag Manager (noscript) -->
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-W8K8GRZQ"
height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
<!-- End Google Tag Manager (noscript) -->"""


def is_redirect_stub(html):
    """True only when page is clearly a blank redirect shell (both signals present)."""
    has_refresh = bool(re.search(r'http-equiv=["\']refresh["\']', html, re.IGNORECASE))
    has_js_redirect = bool(re.search(r'window\.location\.replace', html))
    # Negligible content: body is essentially empty
    body_m = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
    body_text = body_m.group(1).strip() if body_m else ''
    return has_refresh and has_js_redirect and len(body_text) < 50


def process(path, dry_run):
    try:
        html = path.read_text(encoding='utf-8')
    except Exception as e:
        return 'error', str(e)

    if GTM_ID in html:
        return 'skip_already', None

    if is_redirect_stub(html):
        return 'skip_stub', None

    # Insert snippet 1 after <head ...>
    new_html = re.sub(
        r'(<head(?:\s[^>]*)?>)',
        r'\1\n' + GTM_HEAD,
        html, count=1, flags=re.IGNORECASE
    )
    # Insert snippet 2 after <body ...>
    new_html = re.sub(
        r'(<body(?:\s[^>]*)?>)',
        r'\1\n' + GTM_BODY,
        new_html, count=1, flags=re.IGNORECASE
    )

    if new_html == html:
        return 'error', 'regex did not match <head> or <body>'

    if not dry_run:
        path.write_text(new_html, encoding='utf-8')

    return 'inject', None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    dry_run = not args.apply

    mode = 'DRY RUN' if dry_run else 'APPLY'
    sep = '-' * 60
    print(f'{sep}\n Empower Fitness - GTM Injector [{mode}]\n{sep}\n')

    counts = {'inject': 0, 'skip_already': 0, 'skip_stub': 0, 'errors': 0}
    error_files = []

    html_files = sorted(
        p for p in SITE.rglob('*.html')
        if '.git' not in p.parts and 'tools' not in p.parts
    )

    for path in html_files:
        rel = path.relative_to(SITE)
        result, detail = process(path, dry_run)
        counts[result] += 1
        if result == 'error':
            error_files.append((rel, detail))
            print(f'  ERROR  {rel}: {detail}')
        elif result == 'inject':
            print(f'  inject {rel}')

    print(f'\nTotal scanned: {len(html_files)}')
    print(f'inject={counts["inject"]}  skip_stub={counts["skip_stub"]}  '
          f'skip_already={counts["skip_already"]}  errors={counts["errors"]}')

    if dry_run and counts['inject']:
        print(f'\nRun with --apply to write {counts["inject"]} file(s).')
    elif not dry_run:
        print(f'\nApplied to {counts["inject"]} file(s).')

    return 1 if counts['errors'] else 0


if __name__ == '__main__':
    sys.exit(main())
