#!/usr/bin/env python3
"""
Fix 22 broken Unsplash photo IDs.
1. Verify candidates via HTTP HEAD
2. Update data/blog_images.json (17 entries)
3. Patch blog/{slug}/index.html hero figures + og:image (17 posts)
4. Patch blog/index.html card thumbnails (22 cards)
5. Final audit: confirm 0 broken IDs remain
"""
import os, re, json, urllib.request, urllib.error, time
from collections import Counter

BASE  = "/Users/ezra/Documents/Claude/empower-site"
JSON  = os.path.join(BASE, "data/blog_images.json")
BLOG  = os.path.join(BASE, "blog")
INDEX = os.path.join(BLOG, "index.html")

# ── Load current JSON ─────────────────────────────────────────────────────────
with open(JSON, encoding="utf-8") as f:
    BLOG_IMAGES = json.load(f)

used_ids = {v["photo_id"] for v in BLOG_IMAGES.values()}

# ── Broken IDs to fix ─────────────────────────────────────────────────────────
BROKEN_IN_JSON = {
    "adjustable-beds-for-seniors":                   {"alt": "Adjustable Beds For Seniors",                  "topic": "senior"},
    "benefits-of-a-sauna":                           {"alt": "Benefits Of A Sauna",                          "topic": "sauna"},
    "exercise-bikes-for-seniors":                    {"alt": "Exercise Bikes For Seniors",                   "topic": "senior_exercise"},
    "foldable-mobility-scooter":                     {"alt": "Foldable Mobility Scooter",                    "topic": "mobility"},
    "hip-flexor-exercises":                          {"alt": "Hip Flexor Exercises",                         "topic": "hip"},
    "hip-replacement-recovery-timeline":             {"alt": "Hip Replacement Recovery Timeline",            "topic": "hip"},
    "how-long-do-back-spasms-last":                  {"alt": "How Long Do Back Spasms Last",                 "topic": "back"},
    "how-to-strengthen-knee-ligaments":              {"alt": "How To Strengthen Knee Ligaments",             "topic": "knee"},
    "in-home-physical-therapy-services-near-me":     {"alt": "In Home Physical Therapy Services Near Me",   "topic": "pt_clinic"},
    "knee-support-meniscus-injury":                  {"alt": "Knee Support Meniscus Injury",                 "topic": "knee"},
    "lower-back-and-hip-pain":                       {"alt": "Lower Back And Hip Pain",                      "topic": "back"},
    "physical-therapy-for-sports-hernia-rehabilitation": {"alt": "Physical Therapy For Sports Hernia Rehab", "topic": "sports"},
    "seated-core-exercises":                         {"alt": "Seated Core Exercises",                        "topic": "senior_exercise"},
    "sports-medicine-physician":                     {"alt": "Sports Medicine Physician",                    "topic": "sports"},
    "sports-physical-therapist-near-me":             {"alt": "Sports Physical Therapist Near Me",            "topic": "pt_clinic"},
    "ucl-injury":                                    {"alt": "UCL Injury",                                   "topic": "sports"},
    "what-neurological-disorders-cause-balance-problems": {"alt": "Neurological Disorders Balance Problems", "topic": "neuro"},
}

# Stub cards only in index.html (not in JSON)
BROKEN_INDEX_ONLY = {
    "pickleball-injuries-pt-south-florida": {"alt": "Pickleball Injuries PT South Florida", "topic": "sports"},
    "deep-tissue-injury":                   {"alt": "Deep Tissue Injury",                    "topic": "back"},
    "sacroiliac-joint-dysfunction":         {"alt": "Sacroiliac Joint Dysfunction",          "topic": "back"},
    "cold-plunge-chiller":                  {"alt": "Cold Plunge Chiller",                   "topic": "sauna"},
    "balance-board-exercises":              {"alt": "Balance Board Exercises",               "topic": "fitness"},
}

# ── Candidate pools by topic (multiple per topic for fallback) ────────────────
# All IDs below have been selected from well-known Unsplash photo collections
CANDIDATES = {
    "senior": [
        "photo-1506126613408-eca07ce68773",  # elderly person outdoors
        "photo-1571019613454-1cb2f99b2d8b",  # senior walking
        "photo-1584464367415-ba38e0b67d5c",  # older adult exercise
        "photo-1540555700478-4be289fbecef",  # senior fitness
        "photo-1607746882042-944635dfe10e",  # older adult active
        "photo-1544005313-94ddf0286df2",     # senior portrait
        "photo-1531746020798-e6953c6e8e04",  # senior stretching
        "photo-1588776814546-1ffbb3bf6e68",  # elderly couple active
        "photo-1616781677772-2e05b4cab47e",  # senior wellness
        "photo-1598300042247-d088f8ab3a91",  # older adult healthy
    ],
    "senior_exercise": [
        "photo-1520334363787-e34f23c69b33",  # placeholder
        "photo-1571019613454-1cb2f99b2d8b",
        "photo-1517838277536-f5f99be501cd",  # gym/fitness
        "photo-1576678927484-cc907957088c",  # fitness workout
        "photo-1599058945522-28d584b6f0ff",  # exercise class
        "photo-1544991875-5dc1b05f2571",     # senior fitness
        "photo-1585384341408-cc8f70dbfa86",  # yoga/stretching
        "photo-1593810450967-f9c42742e326",  # fitness equipment
        "photo-1549576490-b0b4831ef60a",     # gym workout
        "photo-1540541338287-41700207dee6",  # yoga class
    ],
    "sauna": [
        "photo-1544551763-46a013bb70d5",     # sauna rocks/steam
        "photo-1583500178690-23b0a2516eec",  # wellness spa
        "photo-1571752726703-5e7d1f6a986d",  # sauna interior
        "photo-1576678927484-cc907957088c",
        "photo-1528360983277-13d401cdc186",  # steam/heat
        "photo-1561731216-c3a4d99437d5",     # spa/wellness
        "photo-1554244933-d876deb6b2ff",     # relaxation
        "photo-1540555700478-4be289fbecef",
        "photo-1611073615830-9e0f38b46785",  # cold/hot therapy
        "photo-1515377905703-c4788e51af15",  # wellness spa
    ],
    "mobility": [
        "photo-1559757148-5c350d0d3c56",     # elderly mobility
        "photo-1506126613408-eca07ce68773",
        "photo-1488521787991-ed7bbaae773c",  # accessibility
        "photo-1545205597-3d9d02c29597",     # physical care
        "photo-1582719471384-894fbb16e074",  # healthcare
        "photo-1584464367415-ba38e0b67d5c",
        "photo-1631217868264-e5b90bb7e133",  # PT care
        "photo-1623874514711-0f321325f318",  # mobility aid
        "photo-1607746882042-944635dfe10e",
        "photo-1516574187841-cb9cc2ca948b",  # healthcare
    ],
    "hip": [
        "photo-1518611012118-696072aa579a",  # yoga hip stretch
        "photo-1552196563-55cd4e45efb3",     # stretching
        "photo-1571019613454-1cb2f99b2d8b",
        "photo-1490645935967-10de6ba17061",  # stretching pose
        "photo-1517838277536-f5f99be501cd",
        "photo-1536922246289-88c42f957773",  # hip stretch
        "photo-1519311726-c73a863dccea",     # exercise stretch
        "photo-1470468969717-61d5d54fd036",  # yoga stretch
        "photo-1549576490-b0b4831ef60a",
        "photo-1605296867424-35fc25c9212a",  # exercise
    ],
    "back": [
        "photo-1559757175-0eb30cd8c063",     # back pain/massage
        "photo-1544967082-d9d25d867d66",     # back treatment
        "photo-1530893609608-32a9af3aa95c",  # massage therapy
        "photo-1612897237985-c72c17e4e56e",  # back pain
        "photo-1587721804584-9d6e0be8fc6a",  # spine/back
        "photo-1567532939604-b6b5b0db2604",  # physical therapy
        "photo-1620818977390-e3b5c1c0b43e",  # back care
        "photo-1506905925346-21bda4d32df4",  # wellness
        "photo-1565299585323-38d6b0865b47",  # therapy
        "photo-1497366216548-37526070297c",  # health
    ],
    "knee": [
        "photo-1597452485669-2c7bb5fef90d",  # knee/running
        "photo-1605296867424-35fc25c9212a",
        "photo-1518459031867-a89b944bffe4",  # knee brace
        "photo-1552196563-55cd4e45efb3",
        "photo-1571019613454-1cb2f99b2d8b",
        "photo-1611590027211-b954fd540b32",  # knee therapy
        "photo-1535914254981-b5012eebbd15",  # running/sport
        "photo-1587614382346-4ec70e388b28",  # PT knee
        "photo-1558618666-fcd25c85cd64",     # fitness/exercise
        "photo-1616279969096-54b228935b58",  # physical therapy
    ],
    "pt_clinic": [
        "photo-1576091160399-112ba8d25d1d",  # PT clinic
        "photo-1576091160550-2173dba999ef",  # fitness/PT
        "photo-1574088491987-eb2e2d1f4a5d",  # PT session
        "photo-1545205597-3d9d02c29597",     # healthcare
        "photo-1619870989039-5e2f9a9b8ba1",  # medical care
        "photo-1582719471384-894fbb16e074",
        "photo-1631217868264-e5b90bb7e133",
        "photo-1623874514711-0f321325f318",
        "photo-1516574187841-cb9cc2ca948b",
        "photo-1519494026892-80bbd2d6fd0d",  # healthcare
    ],
    "sports": [
        "photo-1461896836934-ffe607ba8211",  # sports action
        "photo-1543741031-56cd3e55bb0c",     # sports medicine
        "photo-1571731956672-f2b94d7dd0cb",  # athlete
        "photo-1489899012116-1d61b3d68b3e",  # sports training
        "photo-1534438327276-14e5300c3a48",  # gym workout
        "photo-1517836357463-d25dfeac3438",  # sports fitness
        "photo-1581009137042-c552e485697a",  # gym/sports
        "photo-1546483875-ad9014c88eba",     # sports therapy
        "photo-1517838277536-f5f99be501cd",
        "photo-1599058945522-28d584b6f0ff",
    ],
    "neuro": [
        "photo-1559757148-5c350d0d3c56",
        "photo-1576678927484-cc907957088c",
        "photo-1559757175-0eb30cd8c063",
        "photo-1516574187841-cb9cc2ca948b",
        "photo-1581594693702-fbdc51b2763b",  # balance/neuro
        "photo-1565299585323-38d6b0865b47",
        "photo-1545389336-cf090694435e",     # brain/neurology
        "photo-1628348068343-c6a848d2b6dd",  # healthcare
        "photo-1504439468489-c8920d796a29",  # medical
        "photo-1588776814546-1ffbb3bf6e68",
    ],
    "fitness": [
        "photo-1534438327276-14e5300c3a48",  # gym
        "photo-1517836357463-d25dfeac3438",  # fitness
        "photo-1518611012118-696072aa579a",
        "photo-1549060279-7e168fcee0c2",     # fitness workout
        "photo-1476480862126-209bfaa8edc8",  # outdoor fitness
        "photo-1540541338287-41700207dee6",
        "photo-1599058945522-28d584b6f0ff",
        "photo-1581009137042-c552e485697a",
        "photo-1571731956672-f2b94d7dd0cb",
        "photo-1490645935967-10de6ba17061",
    ],
}

# ── HTTP verification ─────────────────────────────────────────────────────────
def check_id(photo_id):
    url = f"https://images.unsplash.com/{photo_id}?w=100&q=10&auto=format"
    try:
        req = urllib.request.Request(url, method="HEAD",
              headers={"User-Agent": "Mozilla/5.0"})
        r = urllib.request.urlopen(req, timeout=8)
        return r.status == 200
    except Exception:
        return False

def find_working_id(topic, exclude):
    candidates = CANDIDATES.get(topic, CANDIDATES["fitness"])
    for pid in candidates:
        if pid in exclude:
            continue
        if check_id(pid):
            return pid
        time.sleep(0.2)
    return None

# ── Assign replacement IDs ─────────────────────────────────────────────────────
print("=== Step 1: Finding verified replacement IDs ===\n")

replacements = {}   # slug → new photo_id
all_assigned = set(used_ids)

# First remove the broken IDs from the "used" set so we can replace them
broken_json_ids = {BLOG_IMAGES[s]["photo_id"] for s in BROKEN_IN_JSON}
broken_all_ids  = set()
with open(INDEX) as f:
    idx_html = f.read()
for pid in ["photo-1447452001526-6a43697ce720","photo-1520334363787-e34f23c69b44",
            "photo-1546519638-68954c8b5a11","photo-1614859324967-bdf413c35a04",
            "photo-1629909615957-be38d48fbbe4"]:
    broken_all_ids.add(pid)
broken_all_ids |= broken_json_ids
all_assigned -= broken_all_ids  # remove broken so we don't treat them as "taken"

all_slugs = {**BROKEN_IN_JSON, **BROKEN_INDEX_ONLY}
for slug, info in sorted(all_slugs.items()):
    topic = info["topic"]
    pid = find_working_id(topic, all_assigned)
    if pid:
        replacements[slug] = pid
        all_assigned.add(pid)
        print(f"  ✓ {slug}: {pid}")
    else:
        print(f"  ✗ NO CANDIDATE for {slug} (topic={topic})")

print(f"\nFound {len(replacements)} / {len(all_slugs)} replacements")
if len(replacements) < len(all_slugs):
    print("WARNING: some slugs have no replacement — aborting")
    exit(1)

# ── Update blog_images.json ───────────────────────────────────────────────────
print("\n=== Step 2: Updating blog_images.json ===\n")

for slug in BROKEN_IN_JSON:
    if slug in replacements:
        BLOG_IMAGES[slug] = {"photo_id": replacements[slug], "alt": BROKEN_IN_JSON[slug]["alt"]}
        print(f"  JSON: {slug} → {replacements[slug]}")

with open(JSON, "w", encoding="utf-8") as f:
    json.dump(BLOG_IMAGES, f, indent=2, ensure_ascii=False)
print("  blog_images.json saved.")

# ── Patch blog post HTML files ────────────────────────────────────────────────
print("\n=== Step 3: Patching blog post HTML files ===\n")

def build_figure(photo_id, alt):
    src = f"https://images.unsplash.com/{photo_id}?w=800&h=450&fit=crop&auto=format&q=80"
    return (
        f'<figure style="margin:2rem 0;text-align:center;">\n'
        f'  <img src="{src}" alt="{alt}"\n'
        f'       style="width:100%;max-width:750px;height:auto;border-radius:8px;'
        f'box-shadow:0 4px 20px rgba(0,0,0,0.15);" loading="lazy">\n'
        f'</figure>'
    )

def build_og(photo_id):
    return f"https://images.unsplash.com/{photo_id}?w=1200&h=630&fit=crop&auto=format&q=80"

def remove_unsplash_figures(html):
    return re.sub(
        r'<figure[^>]*>\s*<img[^>]*unsplash\.com[^>]*/?\s*>\s*</figure>',
        '', html, flags=re.DOTALL
    )

def inject_figure(html, photo_id, alt):
    fig = build_figure(photo_id, alt)
    og  = build_og(photo_id)
    html_clean = remove_unsplash_figures(html)

    for pattern in [
        r'(<div\s+class="content-wrap"[^>]*>)',
        r'(<div\s+class="article-container"[^>]*>)',
        r'(<main[^>]*>|<article[^>]*>)',
    ]:
        m = re.search(pattern, html_clean)
        if m:
            pos = m.end()
            new_html = html_clean[:pos] + '\n' + fig + '\n' + html_clean[pos:]
            # Update og:image
            new_html = re.sub(
                r'(<meta\s+property="og:image"\s+content=")[^"]*(")',
                lambda mx: mx.group(1) + og + mx.group(2),
                new_html
            )
            return new_html, True

    return html, False

patched = []
for slug in BROKEN_IN_JSON:
    if slug not in replacements:
        continue
    post_dir = os.path.join(BLOG, slug)
    idx_file = os.path.join(post_dir, "index.html")
    if not os.path.isfile(idx_file):
        print(f"  ⚠ Not found: {idx_file}")
        continue
    with open(idx_file, encoding="utf-8") as f:
        html = f.read()
    new_html, changed = inject_figure(html, replacements[slug], BROKEN_IN_JSON[slug]["alt"])
    if changed:
        with open(idx_file, "w", encoding="utf-8") as f:
            f.write(new_html)
        patched.append(slug)
        print(f"  ✓ Patched: {slug}")
    else:
        print(f"  ⚠ Could not inject: {slug}")

print(f"  Patched {len(patched)} post files.")

# ── Patch blog/index.html card thumbnails ─────────────────────────────────────
print("\n=== Step 4: Patching blog/index.html card thumbnails ===\n")

with open(INDEX, encoding="utf-8") as f:
    idx_html = f.read()

def patch_card(html, slug, new_pid):
    """Replace the card thumbnail for a given slug."""
    old_pattern = re.compile(r'(https://images\.unsplash\.com/)(photo-[a-zA-Z0-9_-]+)(\?w=400[^"]*)')

    # Find the card href position
    href_pat = re.compile(re.escape(f'href="/blog/{slug}"'))
    m = href_pat.search(html)
    if not m:
        return html, False

    # Find enclosing blog-card div
    card_start = html.rfind('<div class="blog-card"', 0, m.start())
    if card_start == -1:
        return html, False

    # Walk forward to find card end
    depth, pos = 0, card_start
    card_end = -1
    while pos < len(html):
        if html[pos:pos+4] == '<div':
            depth += 1
        elif html[pos:pos+6] == '</div>':
            depth -= 1
            if depth == 0:
                card_end = pos + 6
                break
        pos += 1
    if card_end == -1:
        return html, False

    card_html = html[card_start:card_end]
    new_src = f"https://images.unsplash.com/{new_pid}?w=400&h=220&fit=crop&auto=format&q=80"

    # Replace any unsplash ?w=400 image
    new_card = re.sub(
        r'(https://images\.unsplash\.com/)photo-[a-zA-Z0-9_-]+(\?w=400[^"]*)',
        lambda mx: mx.group(1) + new_pid + mx.group(2),
        card_html, count=1
    )
    if new_card == card_html:
        return html, False
    return html[:card_start] + new_card + html[card_end:], True

cards_updated = 0
for slug, new_pid in replacements.items():
    idx_html, changed = patch_card(idx_html, slug, new_pid)
    if changed:
        cards_updated += 1
        print(f"  ✓ Card: {slug} → {new_pid}")
    else:
        print(f"  ⚠ Card not found: {slug}")

with open(INDEX, "w", encoding="utf-8") as f:
    f.write(idx_html)
print(f"  Updated {cards_updated} card thumbnails.")

# ── Final audit ───────────────────────────────────────────────────────────────
print("\n=== Step 5: Final audit — checking all IDs in index.html ===\n")

with open(INDEX) as f:
    final_html = f.read()

all_card_ids = re.findall(r'unsplash\.com/(photo-[a-zA-Z0-9_-]+)\?w=400', final_html)
broken_still = set()
KNOWN_BROKEN = set([
    "photo-1447452001526-6a43697ce720","photo-1480720157182-3e1d9a37c3c2",
    "photo-1495454223154-c3a4c6a6c2e6","photo-1507537297848-b2839c4e3be8",
    "photo-1517517327823-31b30e5f3d8b","photo-1520334363787-e34f23c69b44",
    "photo-1522529590875-b7a2e84c26de","photo-1524177232136-68cfa7fe3e4b",
    "photo-1534368786749-b63e05c1d445","photo-1536939459926-301b70c5b0cb",
    "photo-1541534741688-6078c738b9cd","photo-1546519638-68954c8b5a11",
    "photo-1547892843-5f5b4db2bfdd","photo-1555953116-00fd3ebb7dd8",
    "photo-1559813114-f61e07debb12","photo-1571017772226-5f6e671e7ef8",
    "photo-1573507119838-6a9e80e1c2f8","photo-1574179560997-b217d2e7df9d",
    "photo-1594736797933-d0401ba2fe65","photo-1614859324967-bdf413c35a04",
    "photo-1616439369330-fb5f24e09e9c","photo-1629909615957-be38d48fbbe4",
])
remaining = set(all_card_ids) & KNOWN_BROKEN
if remaining:
    print(f"  ⚠ {len(remaining)} known-broken IDs still in index cards:")
    for pid in sorted(remaining):
        print(f"    {pid}")
else:
    print(f"  ✓ No known-broken IDs remain in index cards ({len(all_card_ids)} cards total)")

# Check duplicates
dup_check = Counter(all_card_ids)
dups = [(pid, cnt) for pid, cnt in dup_check.items() if cnt >= 3]
if dups:
    print(f"\n  ⚠ IDs used 3+ times in cards:")
    for pid, cnt in sorted(dups, key=lambda x: -x[1]):
        print(f"    {pid}: {cnt}x")
else:
    unique = len(set(all_card_ids))
    print(f"  ✓ Card images: {len(all_card_ids)} total, {unique} unique (max reuse: {max(dup_check.values()) if dup_check else 0}x)")

print("\n✅ Done.")
