#!/usr/bin/env python3
"""
Generates contribution-graph.svg with SMIL animations (GitHub-safe).
Usage:
  python3 gen_graph.py                        # uses seeded fake data (preview)
  GITHUB_TOKEN=ghp_xxx python3 gen_graph.py   # uses real contribution data
"""

import os, sys, json, datetime, urllib.request, urllib.error

USERNAME = "JatinSharma222"
COLORS   = ['#1c2030', '#3d2e0a', '#6b4e12', '#b07e1e', '#e8c97e']
MONTHS   = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
DAYS_LBL = {1:'Mon', 3:'Wed', 5:'Fri'}
CELL = 11
GAP  = 3
STEP = CELL + GAP
WEEKS = 52

# ── Data source ────────────────────────────────────────────────────────────────

def fetch_real_data(token):
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            weeks {
              contributionDays {
                date
                contributionCount
                contributionLevel
              }
            }
          }
        }
      }
    }"""
    payload = json.dumps({"query": query, "variables": {"login": USERNAME}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        raw = json.loads(r.read())

    LEVEL_MAP = {
        "NONE":        0,
        "FIRST_QUARTILE":  1,
        "SECOND_QUARTILE": 2,
        "THIRD_QUARTILE":  3,
        "FOURTH_QUARTILE": 4,
    }
    weeks_raw = raw["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    all_days  = [d for w in weeks_raw for d in w["contributionDays"]]
    # Keep last 52 weeks (364 days), pad to full grid
    all_days = all_days[-WEEKS*7:]
    data = []
    for w in range(WEEKS):
        col = []
        for d in range(7):
            idx = w*7 + d
            if idx < len(all_days):
                day = all_days[idx]
                col.append({
                    "level": LEVEL_MAP.get(day["contributionLevel"], 0),
                    "count": day["contributionCount"],
                    "date":  datetime.date.fromisoformat(day["date"])
                })
            else:
                col.append({"level":0,"count":0,"date":datetime.date.today()})
        data.append(col)
    return data

def fake_data():
    import random
    random.seed(42)
    today = datetime.date.today()
    start = today - datetime.timedelta(days=WEEKS*7 - 1)
    start -= datetime.timedelta(days=(start.weekday()+1) % 7)
    data = []
    for w in range(WEEKS):
        col = []
        for d in range(7):
            date = start + datetime.timedelta(days=w*7+d)
            is_we = date.weekday() >= 5
            r = random.random()
            burst = (w%8==3 or w%11==5)
            level = 0
            if not is_we and r < (0.68 if burst else 0.44):
                v = random.random()
                level = 1 if v<.30 else 2 if v<.58 else 3 if v<.80 else 4
            elif is_we and random.random() < 0.15:
                level = 1
            counts = [0,random.randint(1,3),random.randint(4,8),random.randint(9,15),random.randint(16,25)]
            col.append({"level":level,"count":counts[level],"date":date})
        data.append(col)
    return data

token = os.environ.get("GITHUB_TOKEN","")
if token:
    print("Fetching real GitHub data...", file=sys.stderr)
    try:
        data = fetch_real_data(token)
        print("Real data loaded.", file=sys.stderr)
    except Exception as e:
        print(f"API error: {e} — falling back to fake data", file=sys.stderr)
        data = fake_data()
else:
    print("No GITHUB_TOKEN — using preview data.", file=sys.stderr)
    data = fake_data()

total = sum(c["count"] for col in data for c in col)

# ── Layout ─────────────────────────────────────────────────────────────────────
W = 28 + WEEKS*STEP + 4
H = 20 + 7*STEP + 30   # month row + cells + legend

lines = []
lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
lines.append(f'<rect width="{W}" height="{H}" fill="#0d0f14"/>')

# Month labels
seen = set()
for w, col in enumerate(data):
    m = col[0]["date"].month
    if m not in seen:
        x = 28 + w*STEP
        lines.append(
            f'<text x="{x}" y="11" '
            f'font-family="\'SF Mono\',\'Fira Code\',monospace" '
            f'font-size="9" fill="#7d8590">{MONTHS[m-1]}</text>'
        )
        seen.add(m)

# Day labels
for d, label in DAYS_LBL.items():
    y = 20 + d*STEP + CELL - 1
    lines.append(
        f'<text x="0" y="{y}" '
        f'font-family="\'SF Mono\',\'Fira Code\',monospace" '
        f'font-size="9" fill="#7d8590">{label}</text>'
    )

# Cells with SMIL animations
for w, col in enumerate(data):
    for d, cell in enumerate(col):
        x  = 28 + w*STEP
        y  = 20 + d*STEP
        color  = COLORS[cell["level"]]
        delay  = round(w*0.018 + d*0.004, 3)

        # Tooltip via <title>
        ds  = cell["date"].strftime("%b %d, %Y")
        cnt = cell["count"]
        tip = f"No contributions on {ds}" if cnt==0 else f"{cnt} contribution{'s' if cnt>1 else ''} on {ds}"

        lines.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{color}" opacity="0">')
        lines.append(f'  <title>{tip}</title>')
        # fade + scale-in
        lines.append(
            f'  <animate attributeName="opacity" from="0" to="1" '
            f'dur="0.3s" begin="{delay}s" fill="freeze"/>'
        )
        # pulsing glow on highest-level cells
        if cell["level"] == 4:
            gd = round(delay + 0.5, 2)
            lines.append(
                f'  <animate attributeName="opacity" values="1;0.55;1" '
                f'dur="2.6s" begin="{gd}s" repeatCount="indefinite"/>'
            )
        lines.append('</rect>')

# Legend
ly   = H - 8
lx0  = W - len(COLORS)*(CELL+4) - 40
lines.append(
    f'<text x="{lx0-4}" y="{ly}" text-anchor="end" '
    f'font-family="\'SF Mono\',monospace" font-size="9" fill="#7d8590">less</text>'
)
for i, c in enumerate(COLORS):
    lx = lx0 + i*(CELL+4)
    lines.append(f'<rect x="{lx}" y="{ly-CELL+2}" width="{CELL}" height="{CELL}" rx="2" fill="{c}"/>')
lines.append(
    f'<text x="{lx0+len(COLORS)*(CELL+4)}" y="{ly}" '
    f'font-family="\'SF Mono\',monospace" font-size="9" fill="#7d8590">more</text>'
)

lines.append('</svg>')

outpath = os.environ.get("OUTPUT", "contribution-graph.svg")
with open(outpath, "w") as f:
    f.write("\n".join(lines))
print(f"Written {outpath}  ({total} contributions)", file=sys.stderr)
