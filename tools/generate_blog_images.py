#!/usr/bin/env python3
"""
Generate data/blog_images.json with one unique Unsplash photo_id per real blog post.
- Preserves existing Unsplash images found in white/var posts
- Assigns topic-appropriate new IDs to posts without images (76 dark posts)
- Guarantees zero duplicate photo_ids across all entries
- Excludes redirect stubs and category hubs
"""

import os, re, json
from collections import Counter

BLOG_DIR  = "/Users/ezra/Documents/Claude/empower-site/blog"
DATA_DIR  = "/Users/ezra/Documents/Claude/empower-site/data"
OUTPUT    = os.path.join(DATA_DIR, "blog_images.json")

HUB_SLUGS = {
    "physical-therapy", "fitness", "weight-loss", "sports-therapy",
    "comprehensive-physical-therapy", "physical-therapy-vertigo", "empower-fitness",
}

# ── Pool of unique Unsplash photo IDs, organized by topic ────────────────────
# Every ID appears exactly once across all pools.
# IDs come from Unsplash's public free-to-use library.

POOLS = {
    "back": [
        "photo-1559757148-5c350d0d3c56",   # spine anatomy / back
        "photo-1578662996442-48f60103fc96", # woman with back pain
        "photo-1547489432-cf93fa6c71ee",    # back stretch
        "photo-1524177232136-68cfa7fe3e4b", # PT hands on back
        "photo-1573507119838-6a9e80e1c2f8", # lower back PT
        "photo-1498837167922-ddd27525d352", # fitness / health general
        "photo-1486825586573-7131f7991bdd", # runner/active
    ],
    "neck": [
        "photo-1566241440091-ec10de8db2e1", # neck stretch
        "photo-1551190822-a9333d879b1f",    # shoulder/neck stretch
        "photo-1534438327276-14e5300c3a48", # upper back / shoulder
        "photo-1597347316205-36f6c451902a", # neck/shoulder pain
        "photo-1629909615957-be38d48fbbe4", # neck pillow / sleep
    ],
    "knee": [
        "photo-1527689368864-3a821dbccc34",  # knee PT / kinesiology tape
        "photo-1555953116-00fd3ebb7dd8",     # knee / leg close-up
        "photo-1549060279-7e168fcee0c2",     # legs stretching exercise
        "photo-1547892843-5f5b4db2bfdd",     # hip / knee therapy
        "photo-1544716278-ca5e3f4abd8c",     # yoga / flexibility
        "photo-1581009137042-c552e485697a",  # gym / knee exercise
    ],
    "ankle": [
        "photo-1476480862126-209bfaa8edc8",  # running / ankle
        "photo-1558618666-fcd25c85cd64",     # ankle / foot close-up
        "photo-1548445929-4f60a497f851",     # balance / yoga ankle
    ],
    "hip": [
        "photo-1616439369330-fb5f24e09e9c",  # hip stretch
        "photo-1541534741688-6078c738b9cd",  # hip / piriformis stretch
    ],
    "senior": [
        "photo-1576765608535-5f04d1e3f289",  # elderly exercise group
        "photo-1559813114-f61e07debb12",     # senior stretching
        "photo-1573496359142-b8d87734a5a2",  # seniors walking
        "photo-1491438590914-bc09fcaaf77a",  # group fitness older adults
        "photo-1582213782179-e0d53f98f2ca",  # senior fitness
        "photo-1506869640319-fe1a24fd76dc",  # senior yoga / balance
        "photo-1522529590875-b7a2e84c26de",  # senior with mobility aid
        "photo-1594736797933-d0401ba2fe65",  # senior active lifestyle
    ],
    "sauna": [
        "photo-1536939459926-301b70c5b0cb",  # sauna interior
        "photo-1432888498266-38ffec3eaf0a",  # cold water / ice bath
        "photo-1526256262350-7da7584cf5eb",  # cold plunge / wellness
    ],
    "nutrition": [
        "photo-1490645935967-10de6ba17061",  # healthy food spread
        "photo-1504674900247-0877df9cc836",  # healthy meal prep
        "photo-1506084868230-bb9d95c24759",  # supplement / health pills
        "photo-1467453678174-768ec283a940",  # nutrition / vitamins
    ],
    "sleep": [
        "photo-1545205597-3d9d02c29597",     # person sleeping
        "photo-1596462502278-27bfdc403348",  # pillow / bed comfort
        "photo-1455636366818-bf7e8f1b2f05",  # night / sleep peaceful
    ],
    "pregnancy": [
        "photo-1519823551278-64ac92734fb1",  # prenatal yoga
        "photo-1555252333-9f8e92e65df9",     # pregnancy fitness / exercise
    ],
    "sports": [
        "photo-1517838277536-f5f99be501cd",  # football / sports
        "photo-1471864190281-a93a3070b6de",  # athlete injury / sports
        "photo-1534368786749-b63e05c1d445",  # sports performance
        "photo-1540497077202-7c8a3999166f",  # stretching / cool-down
        "photo-1552693673-1bf958298935",     # icing / cold compress injury
        "photo-1574179560997-b217d2e7df9d",  # athletic training
        "photo-1520869562399-e772f042f422",  # sports physical
    ],
    "neuro": [
        "photo-1576091160399-112ba8d25d1d",  # medical / brain health
        "photo-1516549655169-df83a0774514",  # home care / medical
        "photo-1480720157182-3e1d9a37c3c2",  # balance / neurological
        "photo-1559839734-2b71ea197ec2",     # concussion / head
    ],
    "quotes": [
        "photo-1499750310107-5fef28a66643",  # journal / inspiration
        "photo-1542435503-956c469947f6",     # writing / notes
        "photo-1474631245212-32dc3c8310c6",  # motivation / sunrise fitness
        "photo-1543352634-99a5d50ae78e",     # music / headphones
        "photo-1501196354995-cbb51c65aaea",  # empowerment / women
    ],
    "pilates": [
        "photo-1600881333168-2ef49b341f30",  # pilates / core stability
        "photo-1588286840104-8957b019727f",  # yoga / balance ball
        "photo-1545389336-cf090694435e",     # pilates reformer / core
    ],
    "pt_clinic": [
        "photo-1628348068343-c6a848d2b6dd",  # PT clinic / treatment
        "photo-1594824476967-48c8b964273f",  # medical professional / clinic
        "photo-1551601651-2a8555f1a136",     # in-home PT / treatment
        "photo-1604079628040-94301bb21b91",  # dry needling / acupuncture
        "photo-1579684385127-1ef15d508118",  # physical therapy hands
    ],
    "fitness": [
        "photo-1517836357463-d25dfeac3438",  # gym workout
        "photo-1574680096145-d05b474e2155",  # resistance band
        "photo-1532938911079-1b06ac7ceec7",  # fitness / healthcare
        "photo-1614859324967-bdf413c35a04",  # gym equipment
        "photo-1538805060514-97d9cc17730c",  # fitness studio
        "photo-1554284126-aa88f22d8b74",     # strength training
    ],
    "default": [
        "photo-1571019613454-1cb2f99b2d8b",  # PT / home treatment
        "photo-1576091160550-2173dba999ef",  # fitness general
        "photo-1517517327823-31b30e5f3d8b",  # general wellness
        "photo-1507537297848-b2839c4e3be8",  # active lifestyle
        "photo-1571017772226-5f6e671e7ef8",  # medical professional
        "photo-1489389944381-3471b5b30f04",  # wellness / spa
        "photo-1440778303588-435521a205bc",  # outdoor fitness
        "photo-1495454223154-c3a4c6a6c2e6",  # healthcare / PT
        "photo-1554568218-0f1715e72254",     # fitness aging
        "photo-1612277795421-9bc7706a4a34",  # PT treatment room
    ],
}

# ── Topic keyword → pool key mapping ─────────────────────────────────────────
def pool_for_slug(slug):
    s = slug.lower()
    if any(k in s for k in ["sauna"]):
        return "sauna"
    if any(k in s for k in ["cold-plunge", "cold_plunge", "plunge", "ice-bath"]):
        return "sauna"
    if any(k in s for k in ["pilates", "balance-ball", "balance_ball", "yoga"]):
        return "pilates"
    if any(k in s for k in ["prenatal", "pregnancy", "pregnant"]):
        return "pregnancy"
    if any(k in s for k in ["senior", "elderly", "aging", "walker", "scooter",
                              "mobility-scooter", "adjustable-bed", "mattress", "pillow",
                              "exercise-bike", "leg-exerciser"]):
        return "senior"
    if any(k in s for k in ["sleep", "sleeping", "pillow", "mattress", "bed", "neck-pain-from"]):
        return "sleep"
    if any(k in s for k in ["supplement", "nutrition", "calcium", "vitamin",
                              "weight-gain", "food", "diet"]):
        return "nutrition"
    if any(k in s for k in ["quote", "quotes", "empowering", "empower",
                              "songs", "inspiration", "wellness"]):
        return "quotes"
    if any(k in s for k in ["ankle", "achilles", "tendon", "plantar", "heel", "foot"]):
        return "ankle"
    if any(k in s for k in ["back", "spine", "lumbar", "spasm", "sciatica", "disc",
                              "herniat", "pinched", "constipat"]):
        return "back"
    if any(k in s for k in ["neck", "cervical", "stiff-neck", "shoulder",
                              "rotator", "shoulder-blade"]):
        return "neck"
    if any(k in s for k in ["knee", "mcl", "lcl", "pcl", "meniscus", "patell",
                              "acl", "ligament"]):
        return "knee"
    if any(k in s for k in ["hip", "piriformis", "si-joint", "sacroiliac", "flexor",
                              "hip-replacement"]):
        return "hip"
    if any(k in s for k in ["senior", "elder", "aging", "walker", "balance",
                              "fall-prevent", "parkinson", "neurolog",
                              "stroke", "vertigo", "vestibular", "concussion"]):
        return "neuro"
    if any(k in s for k in ["concussion", "neurolog", "stroke", "parkinson",
                              "vertigo", "vestibular"]):
        return "neuro"
    if any(k in s for k in ["soccer", "football", "stinger", "ucl", "baseball",
                              "sport", "athletic", "ice", "injury", "tendon"]):
        return "sports"
    if any(k in s for k in ["concierge", "in-home", "physical-therapy", "pt-visit",
                              "dry-needl", "sports-medicine", "physician"]):
        return "pt_clinic"
    if any(k in s for k in ["fitness", "strength", "workout", "gym", "training"]):
        return "fitness"
    return "default"

# ── Extract existing photo_id from HTML file ──────────────────────────────────
def extract_photo_id(html_content):
    m = re.search(r'unsplash\.com/(photo-[a-zA-Z0-9_-]+)', html_content)
    return m.group(1) if m else None

def is_stub(html_content):
    return 'http-equiv="refresh"' in html_content or 'window.location.replace' in html_content

# ── Scan all blog posts ───────────────────────────────────────────────────────
print("Scanning blog posts for existing Unsplash images...")
existing = {}  # slug → photo_id (from HTML scan)
real_slugs = []  # ordered list of non-stub, non-hub slugs

for name in sorted(os.listdir(BLOG_DIR)):
    if name == "index.html":
        continue
    post_dir = os.path.join(BLOG_DIR, name)
    idx = os.path.join(post_dir, "index.html")
    if not os.path.isfile(idx):
        continue

    with open(idx, encoding="utf-8") as f:
        html = f.read()

    if is_stub(html):
        continue
    if name in HUB_SLUGS:
        continue

    real_slugs.append(name)
    pid = extract_photo_id(html)
    if pid:
        existing[name] = pid

print(f"  Real posts: {len(real_slugs)}")
print(f"  With existing images: {len(existing)}")
print(f"  Need new images: {len(real_slugs) - len(existing)}")

# ── Check for duplicate existing IDs ─────────────────────────────────────────
id_counts = Counter(existing.values())
dupes = {pid: slugs for pid, slugs in
         ((pid, [s for s,v in existing.items() if v==pid]) for pid in set(existing.values()))
         if len(slugs) > 1}
if dupes:
    print(f"  ⚠ Duplicate existing IDs found: {len(dupes)}")
    for pid, slugs in dupes.items():
        print(f"    {pid}: {slugs}")
else:
    print("  ✓ All existing IDs are unique")

# ── Flatten pool into an ordered list, skipping already-used IDs ──────────────
used_ids = set(existing.values())
pool_flat = []
pool_by_topic = {}

for topic, ids in POOLS.items():
    pool_by_topic[topic] = []
    for pid in ids:
        if pid not in used_ids:
            pool_flat.append((topic, pid))
            pool_by_topic[topic].append(pid)

# Remove duplicate entries within pool (sanity check)
seen_pool = set()
pool_flat_deduped = []
for topic, pid in pool_flat:
    if pid not in seen_pool:
        seen_pool.add(pid)
        pool_flat_deduped.append((topic, pid))
pool_flat = pool_flat_deduped

print(f"\nAvailable pool IDs (excl. already-used): {len(pool_flat)}")

# ── Assign photo_ids to posts needing them ────────────────────────────────────
result = dict(existing)  # start with confirmed existing IDs

# Build topic bucket iterators
topic_buckets = {t: list(ids) for t, ids in pool_by_topic.items()}
topic_iters   = {t: iter(ids) for t, ids in topic_buckets.items()}

assigned_ids = set(existing.values())

def next_from_topic(topic):
    """Get next unused ID from a topic pool, falling back to 'default'."""
    for t in [topic, "default", "fitness", "pt_clinic"]:
        bucket = topic_buckets.get(t, [])
        while bucket:
            pid = bucket.pop(0)
            if pid not in assigned_ids:
                assigned_ids.add(pid)
                return pid, t
    return None, None

needs_image = [s for s in real_slugs if s not in result]
print(f"\nAssigning {len(needs_image)} new photo IDs...")

for slug in needs_image:
    topic = pool_for_slug(slug)
    pid, actual_topic = next_from_topic(topic)
    if pid is None:
        print(f"  ⚠ EXHAUSTED POOL for {slug} (topic: {topic})")
        continue
    result[slug] = pid
    print(f"  {slug[:45]:<45} → {pid}  [{actual_topic}]")

# ── Build final JSON structure ────────────────────────────────────────────────
def make_alt(slug):
    """Generate a clean alt text from slug."""
    words = slug.replace("-", " ").replace("_", " ")
    # Capitalize and clean
    words = re.sub(r'\b(pt|dpt|mcl|lcl|acl|ucl|si|oa|ra|boca|raton|fl|south|florida)\b',
                   lambda m: m.group().upper(), words)
    return words.title()

json_data = {}
for slug in sorted(real_slugs):
    pid = result.get(slug)
    if pid:
        json_data[slug] = {
            "photo_id": pid,
            "alt": make_alt(slug),
        }

# ── Verify uniqueness ─────────────────────────────────────────────────────────
all_ids = [v["photo_id"] for v in json_data.values()]
dup_ids = [pid for pid, cnt in Counter(all_ids).items() if cnt > 1]
print(f"\nFinal JSON entries: {len(json_data)}")
print(f"Duplicate photo_ids: {len(dup_ids)}")
if dup_ids:
    print(f"  DUPLICATES: {dup_ids}")
    raise SystemExit("Aborting — fix duplicate IDs before writing JSON")

# ── Write file ────────────────────────────────────────────────────────────────
os.makedirs(DATA_DIR, exist_ok=True)
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(json_data, f, indent=2, ensure_ascii=False)

print(f"\n✅ Written: {OUTPUT}")
print(f"   Entries: {len(json_data)}")
print(f"   Unique photo_ids: {len(set(all_ids))}")
