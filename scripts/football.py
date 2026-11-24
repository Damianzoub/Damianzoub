#!/usr/bin/env python3
"""Football-themed, data-driven SVGs for a GitHub profile README.

  python scripts/football.py matchday            # rebuild assets/matchday.svg from real contributions
  python scripts/football.py matchday --mock     # same, with random data (local testing)
  python scripts/football.py penalty             # process a penalty issue (env: ISSUE_TITLE, ISSUE_USER)
  python scripts/football.py penalty-render      # re-render assets/penalty.svg from data/penalties.json

Standard library only, so the workflows need no pip install.
"""
import datetime as dt
import html
import json
import os
import random
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
DATA = ROOT / "data" / "penalties.json"
USER = os.environ.get("PROFILE_USER", "Damianzoub")
TEAM = os.environ.get("TEAM_NAME", "DAMIANOS FC")

BG, PURPLE, LILAC, PALE, GREY, TEXT = "#0d1117", "#8b5cf6", "#a78bfa", "#c4b5fd", "#6b7280", "#e5e7eb"
FONT = "Segoe UI, Helvetica, Arial, sans-serif"
DIRECTIONS = ("left", "centre", "right")


def esc(s):
    return html.escape(str(s), quote=True)


# --------------------------------------------------------------------------- matchday
QUERY = """
query($login: String!, $from30: DateTime!, $now: DateTime!) {
  user(login: $login) {
    year: contributionsCollection {
      contributionCalendar { weeks { contributionDays { date contributionCount } } }
    }
    month: contributionsCollection(from: $from30, to: $now) {
      commitContributionsByRepository(maxRepositories: 6) {
        repository { name }
        contributions { totalCount }
      }
    }
  }
}"""


def fetch_real():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GH_TOKEN is not set")
    now = dt.datetime.now(dt.timezone.utc)
    body = json.dumps({"query": QUERY, "variables": {
        "login": USER,
        "from30": (now - dt.timedelta(days=30)).isoformat(),
        "now": now.isoformat(),
    }}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        sys.exit(f"GraphQL error: {payload['errors']}")
    u = payload["data"]["user"]
    days = [(d["date"], d["contributionCount"])
            for w in u["year"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    repos = [(x["repository"]["name"], x["contributions"]["totalCount"])
             for x in u["month"]["commitContributionsByRepository"]]
    return days, repos


def fetch_mock():
    today = dt.date.today()
    days = [((today - dt.timedelta(days=i)).isoformat(), random.choice([0, 0, 1, 2, 3, 5, 8, 12]))
            for i in range(364, -1, -1)]
    repos = [("OpenJarvis", 41), ("ai_automation_platform", 27), ("portfolio", 15),
             ("approximate-nearest-neighbor-graphs", 9), ("wattwise", 6)]
    return days, repos


def streak(days):
    counts = [c for _, c in days]
    if counts and counts[-1] == 0:      # today not started yet: don't break the streak
        counts = counts[:-1]
    n = 0
    for c in reversed(counts):
        if c == 0:
            break
        n += 1
    return n


def render_matchday(days, repos):
    this_wk, last_wk = days[-7:], days[-14:-7]
    us, them = sum(c for _, c in this_wk), sum(c for _, c in last_wk)
    result, rcol = ("WIN", "#22c55e") if us > them else (("LOSS", "#ef4444") if us < them else ("DRAW", LILAC))
    wd = lambda d: dt.date.fromisoformat(d).strftime("%a")
    motm = max(this_wk, key=lambda x: x[1])
    active = sum(1 for _, c in this_wk if c)
    st = streak(days)
    start, end = dt.date.fromisoformat(this_wk[0][0]), dt.date.fromisoformat(this_wk[-1][0])

    W, H = 860, 470
    x0, x1, ty = 150, 815, 215          # timeline
    loop, sweep = 10, 0.8               # seconds per loop, fraction spent sweeping
    minute = lambda i: 6 + i * 13       # day i -> match minute
    mx = lambda m: x0 + (x1 - x0) * m / 90

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">',
         f'<rect width="{W}" height="{H}" rx="14" fill="{BG}"/>',
         f'<rect x="20" y="20" width="{W-40}" height="96" rx="10" fill="#161b22" stroke="{PURPLE}" stroke-opacity=".35"/>',
         f'<text x="40" y="46" fill="{GREY}" font-size="11" letter-spacing="2">MATCHDAY · {start:%d %b} – {end:%d %b %Y}</text>',
         f'<text x="40" y="92" fill="#f5f3ff" font-size="26" font-weight="800">{esc(TEAM)}</text>',
         f'<text x="{W/2}" y="96" fill="#fff" font-size="46" font-weight="800" text-anchor="middle">{us} <tspan fill="{GREY}">–</tspan> {them}</text>',
         f'<text x="{W-40}" y="92" fill="{GREY}" font-size="26" font-weight="800" text-anchor="end">LAST WEEK</text>',
         f'<rect x="{W-110}" y="32" width="70" height="22" rx="11" fill="{rcol}" fill-opacity=".15" stroke="{rcol}"/>',
         f'<text x="{W-75}" y="47.5" fill="{rcol}" font-size="12" font-weight="800" text-anchor="middle">{result}</text>',
         # timeline
         f'<text x="40" y="{ty-26}" fill="{LILAC}" font-size="11" font-weight="700" letter-spacing="1.5">▲ THIS WEEK</text>',
         f'<text x="40" y="{ty-12}" fill="{GREY}" font-size="9">1 contribution = 1 goal</text>',
         f'<text x="40" y="{ty+30}" fill="{GREY}" font-size="11" font-weight="700" letter-spacing="1.5">▼ LAST WEEK</text>',
         f'<line x1="{x0}" y1="{ty}" x2="{x1}" y2="{ty}" stroke="{PURPLE}" stroke-opacity=".5" stroke-width="2"/>']
    for m in (0, 45, 90):
        o.append(f'<text x="{mx(m)}" y="{ty+4}" fill="{GREY}" font-size="10" text-anchor="middle" dy="-8">{m}\'</text>')
    # sweeping match clock
    o.append(f'<line y1="{ty-48}" y2="{ty+48}" stroke="{PALE}" stroke-width="1.5" stroke-dasharray="3 3">'
             f'<animate attributeName="x1" values="{x0};{x1};{x1}" keyTimes="0;{sweep};1" dur="{loop}s" repeatCount="indefinite"/>'
             f'<animate attributeName="x2" values="{x0};{x1};{x1}" keyTimes="0;{sweep};1" dur="{loop}s" repeatCount="indefinite"/></line>')

    def event(i, count, above, fill, label):
        x, m = mx(minute(i)), minute(i)
        t = round(sweep * m / 90, 3)
        y = ty - 30 if above else ty + 30
        size = min(9 + count, 18)
        anim = (f'<animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;{t};{t+.02};.96;1" dur="{loop}s" repeatCount="indefinite"/>'
                f'<animateTransform attributeName="transform" type="translate" values="0 {-14 if above else 14};0 {-14 if above else 14};0 0;0 0;0 0" '
                f'keyTimes="0;{t};{t+.04};.96;1" dur="{loop}s" repeatCount="indefinite"/>')
        return (f'<g opacity="0">{anim}'
                f'<circle cx="{x}" cy="{y}" r="{size}" fill="{fill}" stroke="#fff" stroke-opacity=".7" stroke-width="1.5"/>'
                f'<text x="{x}" y="{y}" fill="#fff" font-size="11" font-weight="800" text-anchor="middle" dominant-baseline="central">{count}</text>'
                f'<text x="{x}" y="{y + (-size-8 if above else size+15)}" fill="{GREY}" font-size="10" text-anchor="middle">{label}</text></g>')

    for i, (d, c) in enumerate(this_wk):
        o.append(f'<text x="{mx(minute(i))}" y="{ty+4}" fill="{GREY}" font-size="9" text-anchor="middle" dy="14">{m_label(minute(i))}</text>')
        if c:
            o.append(event(i, c, True, PURPLE, wd(d)))
    for i, (d, c) in enumerate(last_wk):
        if c:
            o.append(event(i, c, False, "#374151", wd(d)))

    # full-time whistle
    o.append(f'<text x="{x1}" y="146" fill="{rcol}" font-size="13" font-weight="800" text-anchor="end" opacity="0">FULL TIME · {result}'
             f'<animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;{sweep};{sweep+.02};.96;1" dur="{loop}s" repeatCount="indefinite"/></text>')

    # league table
    ly = 330
    o += [f'<line x1="20" y1="{ly-14}" x2="{W-20}" y2="{ly-14}" stroke="#30363d"/>',
          f'<text x="40" y="{ly+6}" fill="#f5f3ff" font-size="13" font-weight="700">LEAGUE TABLE <tspan fill="{GREY}" font-weight="400" font-size="11">· commits per repo, last 30 days</tspan></text>']
    top = max([c for _, c in repos] or [1])
    for k, (name, c) in enumerate(repos[:5]):
        y = ly + 30 + k * 22
        w = 170 * c / top
        o += [f'<text x="40" y="{y}" fill="{LILAC if k == 0 else GREY}" font-size="12" font-weight="700">{k+1}</text>',
              f'<text x="62" y="{y}" fill="{TEXT}" font-size="12">{esc(name if len(name) <= 26 else name[:25] + '…')}</text>',
              f'<rect x="290" y="{y-10}" width="{w:.1f}" height="11" rx="3" fill="{PURPLE}" fill-opacity="{1 - k*0.15:.2f}">'
              f'<animate attributeName="width" from="0" to="{w:.1f}" dur="1.2s" fill="freeze"/></rect>',
              f'<text x="{296 + w:.1f}" y="{y}" fill="{GREY}" font-size="11">{c}</text>']
    if not repos:
        o.append(f'<text x="40" y="{ly+34}" fill="{GREY}" font-size="12">Pre-season: no commits in the last 30 days.</text>')

    # match facts
    fx = 560
    facts = [("Player of the match", f"{wd(motm[0])} · {motm[1]} contributions" if motm[1] else "—"),
             ("Days on the pitch", f"{active} / 7"),
             ("Unbeaten run", f"{st} day{'s' if st != 1 else ''} in a row")]
    o.append(f'<text x="{fx}" y="{ly+6}" fill="#f5f3ff" font-size="13" font-weight="700">MATCH FACTS</text>')
    for k, (a, b) in enumerate(facts):
        y = ly + 34 + k * 30
        o += [f'<text x="{fx}" y="{y}" fill="{GREY}" font-size="10" letter-spacing="1">{a.upper()}</text>',
              f'<text x="{fx}" y="{y+15}" fill="{TEXT}" font-size="13" font-weight="600">{b}</text>']
    o.append(f'<text x="{W-24}" y="{H-12}" fill="#30363d" font-size="9" text-anchor="end">updated {dt.datetime.now(dt.timezone.utc):%d %b %H:%M} UTC</text>')
    o.append("</svg>")
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / "matchday.svg").write_text("\n".join(o))


def m_label(m):
    return ""   # minute ticks kept clean; day names sit on the events themselves


# --------------------------------------------------------------------------- penalties
def load():
    if DATA.exists():
        return json.loads(DATA.read_text())
    return {"goals": 0, "saves": 0, "shots": [], "scorers": {}}


def keeper_dive(state):
    """The keeper reads the crowd: half the time he dives where recent visitors shot most."""
    recent = [s["dir"] for s in state["shots"][-15:]]
    if recent and random.random() < 0.5:
        return max(DIRECTIONS, key=recent.count)
    return random.choice(DIRECTIONS)


def take_penalty():
    title = os.environ.get("ISSUE_TITLE", "").strip().lower()
    user = os.environ.get("ISSUE_USER", "").strip()
    parts = title.split("|")
    if len(parts) != 2 or parts[1].strip() not in DIRECTIONS or not user:
        Path("/tmp/penalty_msg.md").write_text(
            "🟨 That doesn't look like a valid penalty. Use one of the links in the README "
            "(`penalty|left`, `penalty|centre`, `penalty|right`).")
        return
    shot = parts[1].strip()
    state = load()
    dive = keeper_dive(state)
    goal = dive != shot
    state["goals" if goal else "saves"] += 1
    if goal:
        state["scorers"][user] = state["scorers"].get(user, 0) + 1
    state["shots"] = (state["shots"] + [{
        "user": user, "dir": shot, "dive": dive, "goal": goal,
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}])[-50:]
    DATA.parent.mkdir(exist_ok=True)
    DATA.write_text(json.dumps(state, indent=2))
    render_penalty(state)
    readme = f"https://github.com/{USER}"
    msg = (f"⚽ **GOAL!** You went {shot}, the keeper dived {dive}. You're on "
           f"{state['scorers'][user]} career goal(s).") if goal else \
          (f"🧤 **SAVED!** You went {shot} and the keeper guessed right. "
           f"He's been watching where people shoot…")
    Path("/tmp/penalty_msg.md").write_text(
        f"{msg}\n\nScore: Visitors **{state['goals']}** – **{state['saves']}** Keeper.\n\n"
        f"See the replay on [the profile]({readme}) (it can take a minute to refresh). Thanks for playing!")


def render_penalty(state):
    W, H = 860, 380
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">',
         f'<rect width="{W}" height="{H}" rx="14" fill="{BG}"/>',
         f'<text x="{W/2}" y="40" fill="{GREY}" font-size="11" letter-spacing="2" text-anchor="middle">PENALTY SHOOTOUT · OPEN TO EVERYONE</text>',
         f'<text x="{W/2}" y="80" fill="#fff" font-size="32" font-weight="800" text-anchor="middle">{state["goals"]} – {state["saves"]}</text>',
         f'<text x="{W/2 - 62}" y="74" fill="{LILAC}" font-size="13" font-weight="700" letter-spacing="1" text-anchor="end">VISITORS</text>',
         f'<text x="{W/2 + 62}" y="74" fill="{GREY}" font-size="13" font-weight="700" letter-spacing="1">KEEPER</text>']
    # pitch strip + goal
    gl, gr, gt, gb = 250, 610, 110, 250
    o.append(f'<rect x="210" y="{gb}" width="440" height="120" fill="#13201a" opacity=".55"/>')
    o.append(f'<line x1="210" y1="{gb}" x2="650" y2="{gb}" stroke="#fff" stroke-opacity=".35"/>')
    for x in range(gl, gr + 1, 20):
        o.append(f'<line x1="{x}" y1="{gt}" x2="{x}" y2="{gb}" stroke="#fff" stroke-opacity=".08"/>')
    for y in range(gt, gb + 1, 20):
        o.append(f'<line x1="{gl}" y1="{y}" x2="{gr}" y2="{y}" stroke="#fff" stroke-opacity=".08"/>')
    o.append(f'<path d="M{gl} {gb} V{gt} H{gr} V{gb}" fill="none" stroke="#f5f3ff" stroke-width="6" stroke-linejoin="round"/>')
    o.append(f'<ellipse cx="430" cy="335" rx="5" ry="2" fill="#fff" opacity=".6"/>')  # penalty spot

    last = state["shots"][-1] if state["shots"] else None
    target = {"left": (300, 150), "centre": (430, 140), "right": (560, 150)}
    dive_dx = {"left": -105, "centre": 0, "right": 105}
    dive_rot = {"left": -65, "centre": 0, "right": 65}
    loop = 4
    kt = "0;0.25;0.45;0.85;1"
    if last:
        dx, rot = dive_dx[last["dive"]], dive_rot[last["dive"]]
        dy = -25 if last["dive"] == "centre" else 15
    else:
        dx = rot = dy = 0
    # keeper (outer group = slide, inner = tilt)
    o.append(f'<g><animateTransform attributeName="transform" type="translate" values="0 0;0 0;{dx} {dy};{dx} {dy};0 0" keyTimes="{kt}" dur="{loop}s" repeatCount="indefinite"/>'
             f'<g><animateTransform attributeName="transform" type="rotate" values="0 430 215;0 430 215;{rot} 430 215;{rot} 430 215;0 430 215" keyTimes="{kt}" dur="{loop}s" repeatCount="indefinite"/>'
             f'<line x1="400" y1="180" x2="460" y2="180" stroke="{LILAC}" stroke-width="7" stroke-linecap="round"/>'
             f'<rect x="417" y="172" width="26" height="46" rx="8" fill="{PURPLE}"/>'
             f'<circle cx="430" cy="160" r="11" fill="#e9d5ff"/>'
             f'<line x1="423" y1="216" x2="418" y2="248" stroke="#1f2937" stroke-width="7" stroke-linecap="round"/>'
             f'<line x1="437" y1="216" x2="442" y2="248" stroke="#1f2937" stroke-width="7" stroke-linecap="round"/></g></g>')
    # ball
    if last:
        tx, tyy = target[last["dir"]]
        if last["goal"]:
            vals, bt = f"430 330;430 330;{tx} {tyy};{tx} {tyy + 8};430 330", kt
        else:  # parried back out
            vals, bt = f"430 330;430 330;{tx} {tyy + 25};{tx + (430 - tx) * .4} 290;430 330", kt
        o.append(f'<g><animateTransform attributeName="transform" type="translate" values="{vals}" keyTimes="{bt}" dur="{loop}s" repeatCount="indefinite"/>'
                 f'<circle r="9" fill="#fff" stroke="{PURPLE}" stroke-width="2"/></g>')
        word, col = ("GOAL!", "#22c55e") if last["goal"] else ("SAVED!", "#ef4444")
        o.append(f'<text x="430" y="300" fill="{col}" font-size="24" font-weight="900" text-anchor="middle" opacity="0">{word}'
                 f'<animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;0.45;0.5;0.85;1" dur="{loop}s" repeatCount="indefinite"/></text>')
        o.append(f'<text x="430" y="366" fill="{GREY}" font-size="11" text-anchor="middle">last kick: @{esc(last["user"])} went {last["dir"]}, keeper dived {last["dive"]}</text>')
    else:
        o.append(f'<circle cx="430" cy="330" r="9" fill="#fff" stroke="{PURPLE}" stroke-width="2"/>')
        o.append(f'<text x="430" y="366" fill="{GREY}" font-size="11" text-anchor="middle">No kicks yet. Be the first.</text>')

    # left: recent kicks
    o.append(f'<text x="30" y="128" fill="#f5f3ff" font-size="13" font-weight="700">RECENT KICKS</text>')
    for k, s in enumerate(reversed(state["shots"][-6:])):
        y = 156 + k * 24
        mark, col = ("●", "#22c55e") if s["goal"] else ("✕", "#ef4444")
        o.append(f'<text x="30" y="{y}" fill="{col}" font-size="12" font-weight="800">{mark}</text>'
                 f'<text x="48" y="{y}" fill="{TEXT}" font-size="12">@{esc(s["user"][:16])}</text>'
                 f'<text x="190" y="{y}" fill="{GREY}" font-size="11" text-anchor="end">{s["dir"]}</text>')
    # right: golden boot
    o.append(f'<text x="680" y="128" fill="#f5f3ff" font-size="13" font-weight="700">GOLDEN BOOT</text>')
    board = sorted(state["scorers"].items(), key=lambda kv: (-kv[1], kv[0]))[:6]
    for k, (u, g) in enumerate(board):
        y = 156 + k * 24
        o.append(f'<text x="680" y="{y}" fill="{LILAC if k == 0 else GREY}" font-size="12" font-weight="700">{k+1}</text>'
                 f'<text x="698" y="{y}" fill="{TEXT}" font-size="12">@{esc(u[:16])}</text>'
                 f'<text x="836" y="{y}" fill="{LILAC}" font-size="12" font-weight="700" text-anchor="end">{g}</text>')
    if not board:
        o.append(f'<text x="680" y="156" fill="{GREY}" font-size="12">Empty. Your name here?</text>')
    o.append("</svg>")
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / "penalty.svg").write_text("\n".join(o))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "matchday":
        render_matchday(*(fetch_mock() if "--mock" in sys.argv else fetch_real()))
    elif cmd == "penalty":
        take_penalty()
    elif cmd == "penalty-render":
        render_penalty(load())
    else:
        sys.exit(__doc__)
