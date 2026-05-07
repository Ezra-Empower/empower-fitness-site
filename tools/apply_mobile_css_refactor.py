#!/usr/bin/env python3
"""
Empower Fitness — Mobile CSS Refactor Script
Externalises the inline "MOBILE RESPONSIVE OVERRIDE v2" blob to /css/*.css
and performs related targeted fixes.

Usage:
  python3 tools/apply_mobile_css_refactor.py           # dry-run (default)
  python3 tools/apply_mobile_css_refactor.py --apply   # write changes
"""
import argparse, os, re, sys
from pathlib import Path

SITE = Path(__file__).parent.parent

# ── Link tags to inject ──────────────────────────────────────────────────────
BASE_LINKS = [
    '<link rel="stylesheet" href="/css/mobile-base.css">',
    '<link rel="stylesheet" href="/css/mobile-overrides.css">',
    '<link rel="stylesheet" href="/css/mobile-sections.css">',
]
TABLE_LINK = '<link rel="stylesheet" href="/css/mobile-tables.css">'

# ── Files with dead .footer-content CSS ─────────────────────────────────────
FOOTER_CONTENT_FILES = {
    'about/index.html',
    'contact/index.html',
    'fitness-training-boca-raton/index.html',
    'in-home-physical-therapy-boca-raton/index.html',
    'longevity-training-boca-raton/index.html',
    'nutrition-coaching-boca-raton/index.html',
    'return-to-sport-physical-therapy-boca-raton/index.html',
}

# ── Regex patterns ───────────────────────────────────────────────────────────

# Variant A: blob is inline inside a <style> block (═ box banner) — remove blob content only
BLOB_RE = re.compile(
    r'/\*\s*═+\s*EMPOWER FITNESS[^*]+OVERRIDE v2[^*]+═+\s*\*/.*?'
    r'(?=\s*</style>)',
    re.DOTALL
)

# Variant B: blob IS a complete standalone <style> block (simple banner) — remove whole block
BLOB_BLOCK_RE = re.compile(
    r'<style>\s*/\*\s*EMPOWER FITNESS[^*]*OVERRIDE v2[^*]*\*/.*?</style>[ \t]*\n?',
    re.DOTALL
)

# Dead .footer-content CSS block
FOOTER_CONTENT_RE = re.compile(
    r'[ \t]*\.footer-content\s*\{[^}]+\}\n?',
    re.DOTALL
)

# Stale LEGEND PANEL comment (index.html only)
LEGEND_COMMENT_RE = re.compile(
    r'\s*/\*\s*={3,}[^*]*LEGEND PANEL \(FLOATING\)[^*]*={3,}\s*\*/',
    re.DOTALL
)

# Legacy nav flex-wrap pair in contact (very specific to avoid hitting other nav a rules)
CONTACT_NAV_FLEXWRAP_RE = re.compile(
    r'\n[ \t]+nav\s*\{\s*\n[ \t]+flex-wrap:\s*wrap;\s*\n[ \t]+\}\s*\n+'
    r'[ \t]+nav\s+a\s*\{[^}]+\}',
    re.DOTALL
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def find_last_style_end_in_head(html):
    """Return position just after the last </style> in <head>. None if not found."""
    head_m = re.search(r'</head>', html, re.IGNORECASE)
    if not head_m:
        return None
    head_section = html[:head_m.start()]
    ends = [m.end() for m in re.finditer(r'</style>', head_section, re.IGNORECASE)]
    return ends[-1] if ends else None


def inject_links(html, links):
    """Insert link tags after the last </style> in <head>. Returns (new_html, added_count)."""
    pos = find_last_style_end_in_head(html)
    if pos is None:
        return html, 0
    insertion = '\n' + '\n'.join(links)
    return html[:pos] + insertion + html[pos:], len(links)


def has_href(html, css_filename):
    return css_filename in html


def wrap_tables(html):
    """Wrap bare <table>...</table> blocks with <div class="table-responsive">."""
    def replacer(m):
        table_html = m.group(0)
        return '<div class="table-responsive">\n' + table_html + '\n</div>'

    # Only replace tables that are NOT already inside table-responsive.
    # Strategy: if file already has 'table-responsive', check counts.
    if 'table-responsive' not in html:
        new_html = re.sub(
            r'<table[\s\S]*?</table>',
            replacer,
            html,
            flags=re.IGNORECASE
        )
        return new_html, (new_html != html)
    else:
        # File already has some table-responsive wrappers; skip for safety.
        return html, False


# ── Per-file processor ───────────────────────────────────────────────────────

def process_file(path, rel, dry_run):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            original = f.read()
    except Exception as e:
        return {'rel': rel, 'error': str(e), 'modified': False, 'changes': [], 'manual_review': []}

    html = original
    changes = []
    manual_review = []

    # 1. Remove inline blob
    if 'MOBILE RESPONSIVE OVERRIDE v2' in html:
        # Variant B: blob is an entire standalone <style> block (simple banner)
        new_html = BLOB_BLOCK_RE.sub('', html)
        if new_html != html:
            html = new_html
            changes.append('removed inline blob (standalone style block)')
        else:
            # Variant A: blob is inline inside existing <style> block (box banner)
            new_html = BLOB_RE.sub('', html)
            if new_html != html:
                html = new_html
                changes.append('removed inline blob')
            else:
                manual_review.append('blob present but regex failed to remove -- check manually')

    # 2. Remove stale LEGEND comment (index.html only) ─────────────────────
    if rel == 'index.html' and 'LEGEND PANEL (FLOATING)' in html:
        new_html = LEGEND_COMMENT_RE.sub('', html)
        if new_html != html:
            html = new_html
            changes.append('removed stale LEGEND comment')

    # 3. Remove dead .footer-content CSS ───────────────────────────────────
    if rel in FOOTER_CONTENT_FILES and '.footer-content' in html:
        new_html = FOOTER_CONTENT_RE.sub('', html)
        if new_html != html:
            html = new_html
            changes.append('removed dead .footer-content CSS block')

    # 4. contact: remove legacy nav flex-wrap rules ────────────────────────
    if rel == 'contact/index.html' and 'flex-wrap: wrap' in html:
        new_html = CONTACT_NAV_FLEXWRAP_RE.sub('', html)
        if new_html != html:
            html = new_html
            changes.append('removed legacy nav flex-wrap rules from @media block')
        else:
            manual_review.append('flex-wrap:wrap found but contact regex did not match — check manually')

    # 5. careers: add form-row mobile stack rule ───────────────────────────
    if rel == 'careers/index.html' and '.form-row' in html:
        stack_rule = '@media(max-width:768px){\n  .form-row{grid-template-columns:1fr !important;}\n}'
        if 'form-row{grid-template-columns:1fr' not in html and stack_rule not in html:
            # Insert just before the last </style> in head
            head_m = re.search(r'</head>', html, re.IGNORECASE)
            if head_m:
                head_section = html[:head_m.start()]
                style_ends = [(m.start(), m.end()) for m in re.finditer(r'</style>', head_section, re.IGNORECASE)]
                if style_ends:
                    last_style_open = style_ends[-1][0]  # position of last </style>
                    html = html[:last_style_open] + stack_rule + '\n' + html[last_style_open:]
                    changes.append('added form-row mobile stack rule before </style>')


    # Skip link injection for redirect stubs (pages that immediately redirect)
    is_redirect_stub = bool(re.search(r'http-equiv=["\']refresh["\']|window\.location\.replace', html, re.IGNORECASE))

    # 6. Inject link tags
    has_table = bool(re.search(r'<table[\s>]', html, re.IGNORECASE))
    if is_redirect_stub:
        pass  # redirect stubs don't need CSS links
    else:
        links_to_add = []
        for link in BASE_LINKS:
            css_file = '/' + link.split('href="')[1].split('"')[0].lstrip('/')
            if css_file not in html:
                links_to_add.append(link)
        if has_table and '/css/mobile-tables.css' not in html:
            links_to_add.append(TABLE_LINK)

        if links_to_add:
            new_html, added = inject_links(html, links_to_add)
            if added:
                html = new_html
                names = ', '.join(l.split('/css/')[1].split('"')[0] for l in links_to_add)
                changes.append(f'injected link(s): {names}')
            else:
                manual_review.append('no </style> in <head> -- links not injected')


    # 7. Table wrapping ────────────────────────────────────────────────────
    if has_table:
        new_html, wrapped = wrap_tables(html)
        if wrapped:
            html = new_html
            changes.append('wrapped <table> with .table-responsive')
        elif 'table-responsive' in html:
            # Already wrapped somewhere — check counts
            tbl_count = len(re.findall(r'<table[\s>]', html, re.IGNORECASE))
            resp_count = len(re.findall(r'class="table-responsive"', html))
            if tbl_count > resp_count:
                manual_review.append(
                    f'{tbl_count} table(s) but only {resp_count} table-responsive wrapper(s) — verify manually'
                )

    # Done ─────────────────────────────────────────────────────────────────
    modified = (html != original)
    if modified and not dry_run:
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)
        except Exception as e:
            return {'rel': rel, 'error': str(e), 'modified': False, 'changes': changes, 'manual_review': manual_review}

    return {
        'rel': rel,
        'modified': modified,
        'changes': changes,
        'manual_review': manual_review,
        'error': None,
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Write changes (default: dry-run)')
    args = parser.parse_args()
    dry_run = not args.apply

    mode = 'DRY RUN' if dry_run else 'APPLY'
    sep = '-' * 60
    print(sep)
    print(f' Empower Fitness - Mobile CSS Refactor [{mode}]')
    print(sep + '\n')

    # Collect all HTML files
    html_files = []
    for root, dirs, files in os.walk(SITE):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d not in ('node_modules', 'tools'))
        for fname in sorted(files):
            if fname.endswith('.html'):
                html_files.append(Path(root) / fname)

    results = []
    for path in html_files:
        rel = str(path.relative_to(SITE))
        result = process_file(path, rel, dry_run)
        results.append(result)

    # Print results
    modified = [r for r in results if r['modified']]
    unmodified = [r for r in results if not r['modified'] and not r.get('error')]
    errors = [r for r in results if r.get('error')]
    manual = [r for r in results if r['manual_review']]

    for r in modified:
        print(f'  CHANGE  {r["rel"]}')
        for c in r['changes']:
            print(f'          • {c}')

    print()
    print(f'Files scanned:    {len(results)}')
    print(f'Files to change:  {len(modified)}')
    print(f'Unchanged:        {len(unmodified)}')
    print(f'Errors:           {len(errors)}')
    print(f'Manual review:    {len(manual)}')

    if errors:
        print('\nERRORS:')
        for r in errors:
            print(f'  {r["rel"]}: {r["error"]}')

    if manual:
        print('\nMANUAL REVIEW NEEDED:')
        for r in manual:
            print(f'  {r["rel"]}')
            for note in r['manual_review']:
                print(f'    ⚠  {note}')

    if dry_run and modified:
        print(f'\nRun with --apply to write {len(modified)} file(s).')
    elif not dry_run:
        print(f'\nApplied changes to {len(modified)} file(s).')

    return 1 if errors or manual else 0


if __name__ == '__main__':
    sys.exit(main())
