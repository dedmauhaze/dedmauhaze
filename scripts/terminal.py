#!/usr/bin/env python3
"""Génère assets/terminal.svg : portrait ASCII + bloc « neofetch » avec les stats GitHub.

Usage : GITHUB_TOKEN=... python scripts/terminal.py   (ou --demo pour un aperçu hors ligne)
Les textes se modifient dans profil.json, le portrait dans assets/portrait.txt.
"""
import calendar
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "profil.json").read_text(encoding="utf-8"))

# Palette Koroz
BG, BORDER = "#0b0b0b", "#2a2a1a"
YELLOW, TEXT, DIM, GREEN, RED = "#FFD60A", "#E8E8E8", "#5c5c5c", "#7CDA6B", "#FF6B5B"

W = 64  # largeur du bloc texte, en caractères
FS, LH = 14, 19.5  # police et interligne du bloc texte
AFS, ALH = 11, 12.1  # police et interligne du portrait ASCII
CW, ACW = FS * 0.6, AFS * 0.6
FONT = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"


def fetch_stats(user):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN manquant (utilise --demo pour un aperçu)")
    query = """query($login:String!){ user(login:$login){
      followers{totalCount}
      repositories(ownerAffiliations:OWNER, privacy:PUBLIC, first:100){totalCount nodes{stargazerCount}}
      repositoriesContributedTo(contributionTypes:[COMMIT,PULL_REQUEST], first:1){totalCount}
      contributionsCollection{totalCommitContributions restrictedContributionsCount
        contributionCalendar{totalContributions}}
    }}"""
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-readme"},
    )
    data = json.load(urllib.request.urlopen(req, timeout=30))
    if "errors" in data:
        raise RuntimeError(data["errors"])
    u = data["data"]["user"]
    cc = u["contributionsCollection"]
    return {
        "repos": u["repositories"]["totalCount"],
        "contrib": u["repositoriesContributedTo"]["totalCount"],
        "stars": sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
        "followers": u["followers"]["totalCount"],
        "commits": cc["totalCommitContributions"] + cc["restrictedContributionsCount"],
        "year": cc["contributionCalendar"]["totalContributions"],
    }


def uptime(birth):
    if not birth:
        return "depuis toujours"
    b, t = dt.date.fromisoformat(birth), dt.date.today()
    months = (t.year - b.year) * 12 + t.month - b.month - (t.day < b.day)
    y, m = divmod(b.month - 1 + months, 12)
    last = dt.date(b.year + y, m + 1, min(b.day, calendar.monthrange(b.year + y, m + 1)[1]))
    days = (t - last).days
    return f"{months // 12} ans, {months % 12} mois, {days} jours"


def num(n):
    return f"{n:,}".replace(",", " ")


# Chaque ligne = liste de (texte, couleur)
def kv(key, value, width=W):
    parts = [(". ", TEXT)]
    for i, seg in enumerate(key.split(".")):
        if i:
            parts.append((".", TEXT))
        parts.append((seg, YELLOW))
    parts.append((": ", TEXT))
    used = 2 + len(key) + 2 + 1 + len(value)
    parts += [("." * max(1, width - used), DIM), (" " + value, TEXT)]
    return parts


def stat_pair(k1, v1, k2, v2):
    left = kv(k1, v1, 34)
    right = kv(k2, v2, W - 34 - 3)[1:]  # sans le « . » initial
    return left + [(" | ", TEXT)] + right


def header(title):
    return [("- ", TEXT), (title, YELLOW), (" " + "—" * (W - len(title) - 3), DIM)]


def build_lines(stats):
    up = uptime(CFG.get("birthdate", ""))
    lines = [[(CFG["prompt"], YELLOW), (" " + "—" * (W - len(CFG["prompt"]) - 1), DIM)]]
    for i, sec in enumerate(CFG["sections"]):
        if i:
            lines.append([(".", TEXT)])
        lines += [kv(k, v.replace("{uptime}", up)) for k, v in sec]
    lines += [[(".", TEXT)], header("Contact")]
    lines += [kv(k, v) for k, v in CFG["contact"]]
    lines += [[(".", TEXT)], header("GitHub Stats")]
    s = {k: num(v) for k, v in stats.items()}
    lines.append(stat_pair("Repos", f"{s['repos']} {{Contribués: {s['contrib']}}}", "Stars", s["stars"]))
    lines.append(stat_pair("Commits", s["commits"], "Followers", s["followers"]))
    lines.append(kv("Contributions", f"{s['year']} sur les 12 derniers mois"))
    return lines


def render(stats, fx=(), out_name="terminal.svg"):
    ascii_path = ROOT / "assets" / "portrait.txt"
    art = ascii_path.read_text(encoding="utf-8").rstrip("\n").split("\n") if ascii_path.exists() else []
    lines = build_lines(stats)

    pad = 28
    art_w = max((len(l) for l in art), default=0) * ACW
    art_h = len(art) * ALH
    tx = pad + art_w + (32 if art else 0)
    text_h = (len(lines) + 2) * LH
    width = round(tx + W * CW + pad)
    height = round(max(art_h, text_h) + 2 * pad)
    ay = pad + (height - 2 * pad - art_h) / 2
    ty = pad + (height - 2 * pad - text_h) / 2 + FS

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'font-family="{FONT}" role="img" aria-label="Profil de {escape(CFG["user"])}">',
        "<style>"
        ".l{white-space:pre}"
        "@keyframes in{from{opacity:0}to{opacity:1}}"
        ".a{opacity:0;animation:in .25s ease-out forwards}"
        "@keyframes blink{50%{opacity:0}}.c{animation:blink 1s steps(1) infinite}"
        "@keyframes type{from{transform:translateX(0)}to{transform:translateX(var(--w))}}"
        ".t{animation:type var(--d) steps(var(--n)) forwards}"
        "@keyframes glitch{0%,88%,100%{transform:none;opacity:1}89%{transform:translate(5px,0) skewX(-8deg);opacity:.75}"
        "90%{transform:translate(-4px,1px);opacity:1}91%{transform:translate(2px,0) skewX(5deg);opacity:.6}92%{transform:none}"
        "95%{opacity:1}95.5%{opacity:.4}96%{opacity:1}}"
        ".g{animation:glitch 4s steps(1) 2s infinite}"
        "</style>",
        f'<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>',
    ]
    # Portrait : apparition ligne par ligne, du haut vers le bas
    out.append(f'<g font-size="{AFS}" fill="{YELLOW}"{' class="g"' if "glitch" in fx else ""}>')
    for i, row in enumerate(art):
        if row.strip("\u2800 "):
            out.append(
                f'<text class="l a" style="animation-delay:{i * 0.03:.2f}s" x="{pad}" y="{ay + (i + 1) * ALH:.1f}" '
                f'textLength="{len(row) * ACW:.1f}" lengthAdjust="spacingAndGlyphs" xml:space="preserve">{escape(row)}</text>'
            )
    out.append("</g>")
    if "glitch" in fx and art:  # lignes de balayage façon écran CRT
        out.append(
            '<defs><pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse">'
            f'<rect width="4" height="1" fill="{BG}" opacity=".55"/></pattern></defs>'
            f'<rect x="{pad}" y="{ay:.1f}" width="{art_w:.1f}" height="{art_h + ALH:.1f}" fill="url(#scan)"/>'
        )
    # Bloc texte
    out.append(f'<g font-size="{FS}">')
    typing = "typing" in fx
    delay0 = 0.3 if typing else len(art) * 0.03 * 0.5
    covers, t = [], delay0
    for i, parts in enumerate(lines):
        spans = "".join(f'<tspan fill="{c}">{escape(t)}</tspan>' for t, c in parts)
        y = ty + i * LH
        cls = "l" if typing else "l a"
        style = "" if typing else f' style="animation-delay:{delay0 + i * 0.05:.2f}s"'
        out.append(f'<text class="{cls}"{style} x="{tx:.1f}" y="{y:.1f}" xml:space="preserve">{spans}</text>')
        if typing:  # un cache noir qui glisse caractère par caractère
            n = max(1, len("".join(p[0] for p in parts).rstrip()))
            d = 0.04 + n * 0.0025
            covers.append(
                f'<rect class="t" x="{tx - 1:.1f}" y="{y - FS:.1f}" width="{W * CW + 2:.1f}" height="{LH:.1f}" fill="{BG}" '
                f'style="--w:{W * CW + 2:.1f}px;--n:{n};--d:{d:.2f}s;animation-delay:{t:.2f}s"/>'
            )
            t += d
    if covers:
        out.append(
            f'<clipPath id="txt"><rect x="{tx - 1:.1f}" y="0" width="{W * CW + 2:.1f}" height="{height}"/></clipPath>'
            f'<g clip-path="url(#txt)">{"".join(covers)}</g>'
        )
    py = ty + (len(lines) + 1) * LH
    out.append(
        f'<text x="{tx:.1f}" y="{py:.1f}" fill="{YELLOW}">&gt; <tspan class="c">█</tspan></text>'
    )
    out.append("</g></svg>")
    (ROOT / "assets" / out_name).write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    demo = "--demo" in sys.argv
    stats = (
        {"repos": 12, "contrib": 3, "stars": 8, "followers": 5, "commits": 640, "year": 712}
        if demo
        else fetch_stats(CFG["user"])
    )
    render(stats, CFG.get("effets", []))
    if "--apercu-effets" in sys.argv:
        render(stats, ("typing", "glitch"), "terminal-effets.svg")
    print("assets/terminal.svg généré", "(démo)" if demo else "")
