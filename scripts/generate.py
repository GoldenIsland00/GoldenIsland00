#!/usr/bin/env python3
"""Generates the animated SVG cards for the profile README from live GitHub data."""
import os, json, re, html, random, datetime as dt, urllib.request

USER = os.environ.get("PROFILE_USER", "GoldenIsland00")
TOKEN = os.environ.get("GH_TOKEN", "")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
CACHE = os.path.join(ASSETS, "data.json")

BG, BORDER, ACC, TXT, MUT, DIM = "#080d1a", "#1b2745", "#4f8cff", "#e6edf3", "#6b7694", "#2a3556"
FONT = "font-family=\"'SFMono-Regular',Consolas,'Liberation Mono',monospace\""
LANG_COLORS = {"HTML": "#e44d26", "Python": "#3b82c4", "CSS": "#7c4dbb", "JavaScript": "#f0db4f",
               "TypeScript": "#3178c6", "Shell": "#4eb84e", "PHP": "#777bb4", "Java": "#e76f00",
               "C++": "#00599c", "C": "#555555", "Go": "#00add8", "Rust": "#dea584"}

CSS = """<style>
@keyframes fade{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes pulse{0%,100%{opacity:.10}50%{opacity:.32}}
@keyframes flow{to{stroke-dashoffset:-24}}
@keyframes twinkle{0%,100%{opacity:.2}50%{opacity:1}}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
@keyframes scan{from{transform:translateY(0)}to{transform:translateY(230px)}}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.25}}
.a{opacity:0;animation:fade .8s ease forwards}
.g{transform-box:fill-box;transform-origin:left center;transform:scaleX(0);animation:grow 1.4s ease forwards}
.p{animation:pulse 3.2s ease-in-out infinite}
.f{animation:flow 1.6s linear infinite}
.t1{animation:twinkle 2.6s ease-in-out infinite}
.t2{animation:twinkle 3.7s ease-in-out infinite .8s}
.t3{animation:twinkle 4.4s ease-in-out infinite 1.6s}
.spin{transform-box:fill-box;transform-origin:center;animation:spin 40s linear infinite}
.scan{animation:scan 5s ease-in-out infinite alternate}
.live{animation:blink 1.4s ease-in-out infinite}
.d{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 2.4s ease forwards}
@media (prefers-reduced-motion:reduce){*{animation:none!important;opacity:1!important;transform:none!important}}
</style>"""

def esc(s): return html.escape(str(s), quote=True)

def req(url, data=None):
    h = {"Accept": "application/vnd.github+json", "User-Agent": "profile-gen"}
    if TOKEN: h["Authorization"] = "Bearer " + TOKEN
    r = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(r, timeout=30) as resp:
        return json.load(resp)

def gql(q):
    if not TOKEN: return None
    try:
        return req("https://api.github.com/graphql", json.dumps({"query": q}).encode())
    except Exception as e:
        print("graphql failed:", e); return None

# ------------------------------------------------------------------ data
user = req(f"https://api.github.com/users/{USER}")
repos = [r for r in req(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner")
         if not r["fork"]]
stars = sum(r["stargazers_count"] for r in repos)

lang_bytes = {}
for r in repos:
    try:
        for k, v in req(r["languages_url"]).items():
            lang_bytes[k] = lang_bytes.get(k, 0) + v
    except Exception: pass
total_b = sum(lang_bytes.values()) or 1
langs = sorted(((k, v / total_b) for k, v in lang_bytes.items()), key=lambda x: -x[1])[:5]

cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {"days": [], "total": 0}
res = gql('query{user(login:"%s"){contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}' % USER)
try:
    cal = res["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    cache = {"total": cal["totalContributions"],
             "days": [[d["date"], d["contributionCount"]] for w in cal["weeks"] for d in w["contributionDays"]]}
    json.dump(cache, open(CACHE, "w"))
except Exception:
    print("using cached contribution data")
days = cache["days"]; contributions = cache["total"]
active = sum(1 for _, c in days if c > 0)
streak = 0
for _, c in reversed(days[:-1] if days and days[-1][1] == 0 else days):
    if c > 0: streak += 1
    else: break
if not days: active, streak = 0, 0

# ------------------------------------------------------------------ svg helpers
def wrap(w, h, body, defs=""):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{CSS}
<defs><radialGradient id="g" cx="80%" cy="0%" r="90%"><stop offset="0" stop-color="#1a2a5a" stop-opacity=".55"/><stop offset="1" stop-color="{BG}" stop-opacity="0"/></radialGradient>{defs}</defs>
<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="18" fill="{BG}" stroke="{BORDER}"/>
<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="18" fill="url(#g)"/>
{body}
<text x="{w-22}" y="{h-14}" text-anchor="end" fill="{DIM}" font-size="10" {FONT}>live · updated {dt.datetime.now(dt.timezone.utc):%Y-%m-%d}</text>
</svg>'''

def T(x, y, s, size=12, fill=TXT, weight="normal", anchor="start", ls=0, cls="", delay=None):
    st = f' style="animation-delay:{delay}s"' if delay is not None else ""
    c = f' class="{cls}"' if cls else ""
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}" letter-spacing="{ls}"{c}{st} {FONT}>{esc(s)}</text>'

def head(kicker, title):
    return (T(36, 38, kicker, 10, MUT, ls=3) + T(36, 80, title, 20, TXT, cls="a", delay=.1) +
            f'<line x1="36" y1="98" x2="864" y2="98" stroke="{BORDER}" stroke-dasharray="3 5"/>')

def save(name, s): open(os.path.join(ASSETS, name + ".svg"), "w").write(s)

# divider
save("divider", f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="20" viewBox="0 0 900 20">{CSS}
<line x1="20" y1="10" x2="880" y2="10" stroke="{BORDER}"/>
<rect class="live" x="16" y="7" width="6" height="6" transform="rotate(45 19 10)" fill="{ACC}"/>
<rect class="live" x="878" y="7" width="6" height="6" transform="rotate(45 881 10)" fill="{ACC}" style="animation-delay:.7s"/>
<rect x="447" y="7" width="6" height="6" transform="rotate(45 450 10)" fill="{MUT}"/></svg>''')

# ------------------------------------------------------------------ hero
random.seed(7)
b = T(36, 38, "GITSKINS / LIVING IDENTITY", 10, MUT, ls=3) + T(864, 38, f"@{USER.lower()}", 10, MUT, anchor="end")
b += T(36, 100, "HELLO, WORLD. I'M", 10, "#d1445a", ls=4, cls="live")
for i, (word, y) in enumerate([("Sirgae", 160), ("youfski", 226)]):
    b += (f'<text x="36" y="{y}" font-size="64" fill="none" stroke="#5d6784" stroke-width="1.2" font-weight="bold" '
          f'class="a" style="animation-delay:{.2+i*.25}s" {FONT}>{word}</text>')
top = "  /  ".join(k for k, _ in langs[:3]) or "HTML / Python / CSS"
b += T(36, 262, top.replace("  /  ", " / "), 12, MUT, cls="a", delay=.7) + T(36, 290, "In the public internet", 10, DIM, cls="a", delay=.9)
dots = ""
for gx in range(40):
    for gy in range(30):
        x, y = 560 + gx * 7.2, 70 + gy * 7.2
        cx, cy = (gx - 20) / 9.0, (gy - 11) / 8.5
        head_ = cx * cx + cy * cy < 1
        sh = gy > 20 and abs(gx - 20) < (gy - 17) * 1.6
        if (head_ or sh) and random.random() < (0.85 if head_ else 0.55):
            cl = random.choice(["", "", "t1", "t2", "t3"])
            attr = f'class="{cl}" ' if cl else ""
            dots += f'<circle {attr}cx="{x:.1f}" cy="{y:.1f}" r="{random.choice([1.1,1.6,2.0])}" fill="#d9deea" opacity="{random.uniform(.35,.9):.2f}"/>'
b += dots
b += f'<g class="spin"><circle cx="700" cy="170" r="150" fill="none" stroke="#d1445a" stroke-opacity=".4" stroke-dasharray="4 10"/></g>'
b += f'<rect class="scan" x="550" y="70" width="300" height="2" fill="{ACC}" opacity=".35"/>'
b += f'<line x1="36" y1="346" x2="864" y2="346" stroke="{BORDER}"/>'
for i, (lab, v) in enumerate([("REPOSITORIES", len(repos)), ("STARS", stars), ("CONTRIBUTIONS", contributions), ("FOLLOWERS", user["followers"])]):
    x = 36 + i * 210
    b += T(x, 370, lab, 9, MUT, ls=3) + f'<circle class="live" cx="{x+175}" cy="366" r="2.5" fill="#d1445a" style="animation-delay:{i*.3}s"/>'
    b += T(x, 402, v, 22, TXT, "bold", cls="a", delay=.8 + i * .15)
save("hero", wrap(900, 430, b))

# ------------------------------------------------------------------ focus
b = head("CURRENT FOCUS", "Ideas taking shape")
labels = ["Current focus", "In the build queue", "In the build queue"]
for i in range(3):
    name = langs[i][0] if i < len(langs) else "—"
    x = 36 + i * 285
    b += T(x, 150, f"0{i+1}", 30, ACC, cls="a", delay=.3 + i * .2)
    b += f'<line x1="{x}" y1="172" x2="{x+250}" y2="172" stroke="{BORDER}"/>'
    b += T(x, 206, name, 13, TXT, "bold", cls="a", delay=.5 + i * .2) + T(x, 230, labels[i], 10, MUT, cls="a", delay=.6 + i * .2)
save("focus", wrap(900, 400, b))

# ------------------------------------------------------------------ tools
b = head("TECHNOLOGY SPECTRUM", "The tools behind the work")
for i, (n, f) in enumerate(langs):
    x = 36 + (i % 4) * 210; y = 130 + (i // 4) * 100
    c = LANG_COLORS.get(n, ACC)
    b += f'<rect class="a" style="animation-delay:{i*.15}s" x="{x}" y="{y}" width="26" height="26" rx="5" fill="{c}" opacity=".9"/>'
    b += T(x, y + 50, n, 12, TXT, "bold") + T(x, y + 66, f"{f*100:.0f}% of public code", 9, MUT)
    b += f'<rect x="{x}" y="{y+74}" width="170" height="2" fill="{BORDER}"/>'
    b += f'<rect class="g" style="animation-delay:{.3+i*.2}s" x="{x}" y="{y+74}" width="{max(170*f,2):.0f}" height="2" fill="{c}"/>'
save("tools", wrap(900, 330, b))

# ------------------------------------------------------------------ constellation
feat = sorted(repos, key=lambda r: r["created_at"])[:5] if len(repos) <= 5 else \
       sorted(sorted(repos, key=lambda r: (-r["stargazers_count"], r["created_at"]))[:5], key=lambda r: r["created_at"])
feat = feat[:4] if len(feat) > 4 else feat
slots = [(410, 235), (150, 190), (690, 170), (620, 290), (240, 300)]
order = sorted(feat, key=lambda r: -r["stargazers_count"])
b = head("PROJECT CONSTELLATION", "A universe of work")
pos = {}
for r, (x, y) in zip(order, slots): pos[r["name"]] = (x, y)
c0 = pos[order[0]["name"]] if order else (410, 235)
for r in order[1:]:
    x, y = pos[r["name"]]
    b += f'<line class="f" x1="{c0[0]}" y1="{c0[1]}" x2="{x}" y2="{y}" stroke="{ACC}" stroke-opacity=".5" stroke-dasharray="3 5"/>'
for i, r in enumerate(order):
    x, y = pos[r["name"]]
    c = LANG_COLORS.get(r["language"] or "", "#4f6bd6")
    rad = 22 + min(r["stargazers_count"] * 6, 18) + (6 if i == 0 else 0)
    sub = f'{r["language"] or "Open source"} · {r["stargazers_count"]} stars'
    b += f'<circle class="p" style="animation-delay:{i*.5}s" cx="{x}" cy="{y}" r="{rad+10}" fill="{c}"/>'
    b += f'<circle cx="{x}" cy="{y}" r="{rad}" fill="{c}" fill-opacity=".35" stroke="{c}" stroke-opacity=".7"/>'
    b += T(x, y + rad + 24, r["name"], 12, TXT, anchor="middle") + T(x, y + rad + 40, sub, 9, MUT, anchor="middle")
save("constellation", wrap(900, 380, b))

# ------------------------------------------------------------------ timeline
b = head("PROJECT LAUNCH SEQUENCE", "Where the work went next")
b += f'<line class="f" x1="70" y1="215" x2="830" y2="215" stroke="{ACC}" stroke-opacity=".6" stroke-dasharray="5 6"/>'
n = max(len(feat), 1)
b += f'<circle r="4" cy="215" fill="{ACC}"><animate attributeName="cx" values="70;830" dur="6s" repeatCount="indefinite"/></circle>'
for i, r in enumerate(feat):
    x = 110 + (i * (680 // max(n - 1, 1)) if n > 1 else 340)
    c = LANG_COLORS.get(r["language"] or "", ACC)
    d = dt.datetime.strptime(r["created_at"][:10], "%Y-%m-%d")
    up = i % 2 == 0
    b += f'<circle class="p" cx="{x}" cy="215" r="22" fill="{c}" style="animation-delay:{i*.4}s"/><circle cx="{x}" cy="215" r="18" fill="{c}" fill-opacity=".3" stroke="{c}"/><circle cx="{x}" cy="215" r="6" fill="{c}"/>'
    b += T(x, 168 if up else 262, f"{i+1:02d} / {d:%b %Y}", 9, MUT, anchor="middle")
    b += T(x, 150 if up else 282, r["name"], 13, TXT, anchor="middle")
b += T(36, 330, f"{len(feat)} featured repositories · follow the line from first signal to latest motion", 10, MUT)
save("timeline", wrap(900, 360, b))

# ------------------------------------------------------------------ momentum (weekly line chart)
weeks = [days[i:i + 7] for i in range(0, len(days), 7)]
vals = [sum(c for _, c in wk) for wk in weeks] or [0] * 52
mx = max(vals) or 1
W, H, X0, Y0 = 828, 170, 36, 130
pts = [(X0 + i * W / max(len(vals) - 1, 1), Y0 + H - v / mx * (H - 10)) for i, v in enumerate(vals)]
line = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
area = line + f" L{pts[-1][0]:.1f},{Y0+H} L{pts[0][0]:.1f},{Y0+H} Z"
b = head("MOMENTUM", "Weekly contribution signal")
b += f'<path d="{area}" fill="{ACC}" fill-opacity=".12" class="a" style="animation-delay:1.2s"/>'
b += f'<path d="{line}" pathLength="1" fill="none" stroke="{ACC}" stroke-width="2" stroke-linejoin="round" class="d"/>'
b += f'<line x1="{X0}" y1="{Y0+H}" x2="{X0+W}" y2="{Y0+H}" stroke="{BORDER}"/>'
if pts:
    b += f'<circle class="live" cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="4" fill="{TXT}"/>'
b += T(36, 340 + 0, f"{contributions} contributions in the last year · peak week {mx}", 10, MUT)
save("momentum", wrap(900, 360, b))

# ------------------------------------------------------------------ energy field (heatmap)
b = head("ENERGY FIELD", f"{contributions} contributions in the last year")
def lvl(c): return 0 if c == 0 else 1 if c < 3 else 2 if c < 6 else 3 if c < 10 else 4
cols = ["#101a36", "#17306a", "#1f4fb0", "#3b78f0", "#8fb8ff"]
cell, gap = 13, 3
cellsvg = ""
for wi, wk in enumerate(weeks or [[]] * 53):
    for di in range(7):
        c = wk[di][1] if di < len(wk) else 0
        l = lvl(c)
        x, y = 36 + wi * (cell + gap), 124 + di * (cell + gap)
        cl = f' class="t{(wi+di)%3+1}"' if l >= 3 else ""
        cellsvg += f'<rect{cl} x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{cols[l]}"/>'
b += cellsvg
b += T(36, 270, f"{streak} day current streak · {active} active days", 10, MUT)
for i, c in enumerate(cols):
    b += f'<rect x="{700+i*30}" y="260" width="12" height="12" rx="3" fill="{c}"/>'
b += T(690, 270, "Less", 9, MUT, anchor="end") + T(864, 270, "More", 9, MUT, anchor="end")
save("energy", wrap(900, 300, b))

# ------------------------------------------------------------------ README markers
def sub(tag, content, text):
    return re.sub(rf"(<!--{tag}:START-->).*?(<!--{tag}:END-->)", lambda m: f"{m.group(1)}\n{content}\n{m.group(2)}", text, flags=re.S)

rp = os.path.join(ROOT, "README.md")
rd = open(rp, encoding="utf-8").read()
rd = sub("SIGNAL", f"`LIVE SIGNAL`\n\n**{len(repos)}** repos<br>\n**{stars}** stars<br>\n**{contributions}** contributions<br>\n**{user['followers']}** followers", rd)
cells = ""
for r in feat:
    desc = r["description"] or "A selected project from this public body of work."
    cells += (f'<td width="{100//max(len(feat),1)}%" valign="top">\n\n**[{r["name"]}]({r["html_url"]})**\n\n{desc}\n\n'
              f'<sub>{r["language"] or "Open source"} · ⭐ {r["stargazers_count"]}</sub>\n\n</td>\n')
rd = sub("REPOS", f"<table>\n<tr>\n{cells}</tr>\n</table>", rd)
rd = sub("STREAK", f"<sub>{streak} day current streak · {active} active days</sub>", rd)
open(rp, "w", encoding="utf-8").write(rd)
print("done:", len(repos), "repos,", stars, "stars,", contributions, "contributions")
