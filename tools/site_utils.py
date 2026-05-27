#!/usr/bin/env python3
"""
Shared utilities for Empower Fitness site scripts.
Import this module in any script that needs stub detection or site paths.
"""
import re
from pathlib import Path

SITE = Path(__file__).parent.parent


def is_redirect_stub(html: str) -> bool:
    """True only when page is clearly a blank redirect shell (both signals present).
    Matches the same logic used in tools/add_gtm.py."""
    has_refresh = bool(re.search(r'http-equiv=["\']refresh["\']', html, re.IGNORECASE))
    has_js_redirect = bool(re.search(r'window\.location\.replace', html))
    body_m = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
    body_text = body_m.group(1).strip() if body_m else ''
    return has_refresh and has_js_redirect and len(body_text) < 50


def iter_html_files(site: Path = SITE):
    """Yield all index.html files under the site root."""
    for path in sorted(site.rglob('index.html')):
        yield path
    # Also yield top-level non-index html files (404.html, etc.)
    for path in sorted(site.glob('*.html')):
        if path.name != 'index.html':
            yield path
