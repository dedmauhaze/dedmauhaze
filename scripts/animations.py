#!/usr/bin/env python3
"""Animations SVG aux couleurs Koroz pour le README (aucun JavaScript : CSS + SMIL uniquement).

python scripts/animations.py --demo   → grille fictive, pour l'aperçu
python scripts/animations.py          → vraie grille de contributions (GITHUB_TOKEN requis)
"""
import json
import math
import os
import random
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
BG, BORDER, Y, DIM, TEXT = "#0b0b0b", "#2a2a1a", "#FFD60A", "#5c5c5c", "#E8E8E8"
LEVELS = ["#161616", "#3d3505", "#7a6a0a", "#c9a400", "#FFD60A"]
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
CELL, GAP = 12, 4
STEP = CELL + GAP


def frame(w, h, body, label=None):
    lab = (
        f'<text x="20" y="26" font-family="{FONT}" font-size="12" fill="{DIM}">{label}</text>' if label else ""
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>{lab}{body}</svg>'
    )


# ---------- Grille de contributions ----------
def grid_demo(seed=7):
    rnd = random.Random(seed)
    weeks = []
    for w in range(53):
        activity = 0.25 + 0.6 * (0.5 + 0.5 * math.sin(w / 6))
        weeks.append([rnd.choice([1, 1, 2, 2, 3, 4]) if rnd.random() < activity else 0 for _ in range(7)])
    return weeks


def grid_real(user):
    q = """query($l:String!){user(login:$l){contributionsCollection{contributionCalendar{
      weeks{contributionDays{contributionLevel}}}}}}"""
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": q, "variables": {"l": user}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "User-Agent": "profile-readme"},
    )
    data = json.load(urllib.request.urlopen(req, timeout=30))
    lv = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [[lv[d["contributionLevel"]] for d in w["contributionDays"]] + [0] * (7 - len(w["contributionDays"])) for w in weeks]


def cells(weeks, ox, oy, eaten_at, total):
    """Cases de la grille ; celles qui ont une valeur disparaissent à leur instant eaten_at[(x, y)]."""
    out, css = [], []
    for x, col in enumerate(weeks):
        for y, lvl in enumerate(col):
            px, py = ox + x * STEP, oy + y * STEP
            if lvl and (x, y) in eaten_at:
                p = eaten_at[(x, y)] / total * 100
                k = f"e{x}_{y}"
                css.append(f"@keyframes {k}{{0%,{p:.2f}%{{fill:{LEVELS[lvl]}}}{p + 0.01:.2f}%,99.5%{{fill:{LEVELS[0]}}}100%{{fill:{LEVELS[lvl]}}}}}")
                out.append(f'<rect x="{px}" y="{py}" width="{CELL}" height="{CELL}" rx="2.5" fill="{LEVELS[lvl]}" style="animation:{k} {total}s linear infinite"/>')
            else:
                out.append(f'<rect x="{px}" y="{py}" width="{CELL}" height="{CELL}" rx="2.5" fill="{LEVELS[lvl]}"/>')
    return "".join(out), "".join(css)


def pacman(weeks, name="anim-pacman.svg"):
    ox, oy, dt = 24, 44, 0.035
    path = [(x, y) for y in range(7) for x in (range(len(weeks)) if y % 2 == 0 else range(len(weeks) - 1, -1, -1))]
    total = round(len(path) * dt + 1.5, 2)
    eaten = {p: i * dt for i, p in enumerate(path)}
    body, css = cells(weeks, ox, oy, eaten, total)
    # Trajet de Pac-Man : keyframes de position + orientation
    kf, rot = [], []
    for i, (x, y) in enumerate(path):
        p = i * dt / total * 100
        flip = 1 if y % 2 == 0 else -1
        kf.append(f"{p:.2f}%{{transform:translate({ox + x * STEP + CELL / 2}px,{oy + y * STEP + CELL / 2}px) scaleX({flip})}}")
    end = len(path) * dt / total * 100
    kf.append(f"{end + 0.01:.2f}%,100%{{transform:translate(-40px,{oy}px)}}")
    css += "@keyframes pm{" + "".join(kf) + "}"
    pm = (
        f'<g style="animation:pm {total}s linear infinite"><path fill="{Y}" d="M0 0L8 -5A9.5 9.5 0 1 0 8 5Z">'
        '<animate attributeName="d" dur="0.25s" repeatCount="indefinite" '
        'values="M0 0L8 -5A9.5 9.5 0 1 0 8 5Z;M0 0L9.5 -0.5A9.5 9.5 0 1 0 9.5 0.5Z;M0 0L8 -5A9.5 9.5 0 1 0 8 5Z"/></path>'
        f'<circle cx="1" cy="-5" r="1.4" fill="{BG}"/></g>'
    )
    w, h = ox * 2 + len(weeks) * STEP - GAP, oy + 7 * STEP + 20
    (OUT / name).write_text(frame(w, h, f"<style>{css}</style>{body}{pm}", "contributions.eat()"), encoding="utf-8")


def shooter(weeks, name="anim-vaisseau.svg"):
    ox, oy, dt = 24, 44, 0.12
    shipy = oy + 7 * STEP + 26
    cols = [x for x, c in enumerate(weeks) if any(c)]
    total = round(len(cols) * dt + 1.2, 2)
    eaten = {}
    kf_ship, kf_laser = [], []
    for i, x in enumerate(cols):
        t = i * dt
        for y, lvl in enumerate(weeks[x]):
            if lvl:
                eaten[(x, y)] = t + 0.03
        p, q = t / total * 100, (t + 0.06) / total * 100
        cx = ox + x * STEP + CELL / 2
        kf_ship.append(f"{p:.2f}%{{transform:translateX({cx}px)}}")
        kf_laser.append(f"{p:.2f}%{{transform:translateX({cx}px);opacity:1}}{q:.2f}%{{transform:translateX({cx}px);opacity:0}}")
    end = len(cols) * dt / total * 100
    kf_ship.append(f"100%{{transform:translateX({ox}px)}}")
    body, css = cells(weeks, ox, oy, eaten, total)
    css += "@keyframes sh{" + "".join(kf_ship) + "}"
    css += "@keyframes lz{0%{opacity:0}" + "".join(kf_laser) + f"{end + 0.1:.2f}%,100%{{opacity:0}}}}"
    ship = (
        f'<g style="animation:sh {total}s linear infinite"><g transform="translate(0 {shipy})">'
        f'<path d="M0 -9L7 6L0 2L-7 6Z" fill="{Y}"/><rect x="-1" y="6" width="2" height="4" fill="#c9a400">'
        '<animate attributeName="height" values="4;7;4" dur="0.2s" repeatCount="indefinite"/></rect></g></g>'
        f'<rect x="-1" y="{oy - 4}" width="2" height="{shipy - oy - 6}" fill="{Y}" opacity="0" '
        f'style="animation:lz {total}s linear infinite"/>'
    )
    w, h = ox * 2 + len(weeks) * STEP - GAP, shipy + 22
    (OUT / name).write_text(frame(w, h, f"<style>{css}</style>{body}{ship}", "contributions.shoot()"), encoding="utf-8")


# ---------- Clin d'œil à 303 - Orbite ----------
def acid_wave(name="anim-onde-acid.svg"):
    w, h, n = 880, 190, 220
    cy, amp = 110, 52

    def wave(cut, res, phase):
        pts = []
        for i in range(n + 1):
            t = i / n * 4 + phase  # 4 périodes
            f = t % 1
            saw = 1 - 2 * f
            ring = 1.3 * res * math.exp(-f * (2 + 5 * (1 - cut))) * math.sin(f * 2 * math.pi * (3 + 6 * cut))
            v = math.tanh((saw * (0.35 + 0.65 * cut) + ring) * 1.4)
            pts.append(f"{20 + i / n * (w - 40):.1f} {cy - v * amp:.1f}")
        return "M" + " L".join(pts)

    frames = [wave(0.5 + 0.45 * math.sin(k / 12 * 2 * math.pi), 0.55 + 0.35 * math.cos(k / 12 * 2 * math.pi), k / 12) for k in range(13)]
    values = ";".join(frames)
    body = (
        f'<text x="{w - 20}" y="26" text-anchor="end" font-family="{FONT}" font-size="12" fill="{Y}">303 - ORBITE</text>'
        f'<line x1="20" x2="{w - 20}" y1="{cy}" y2="{cy}" stroke="#2a2a1a"/>'
        f'<path d="{frames[0]}" fill="none" stroke="{Y}" stroke-width="5" opacity=".18"><animate attributeName="d" dur="3.2s" repeatCount="indefinite" values="{values}"/></path>'
        f'<path d="{frames[0]}" fill="none" stroke="{Y}" stroke-width="1.8"><animate attributeName="d" dur="3.2s" repeatCount="indefinite" values="{values}"/></path>'
    )
    (OUT / name).write_text(frame(w, h, body, "acid.cutoff ~ resonance"), encoding="utf-8")


def sequencer(name="anim-sequenceur.svg"):
    w, h = 880, 150
    pattern = [1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1]
    accent = [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1]
    notes = ["C", "", "C", "D#", "", "G", "", "C", "A#", "", "C", "", "F", "G", "", "C"]
    bpm, steps = 140, 16
    dur = 60 / bpm / 4 * steps
    pw, gap, ox, oy = 46, 6, 24, 54
    css = "@keyframes hit{0%{fill:#FFF3B0}12%,100%{fill:" + Y + "}}@keyframes hd{0%{opacity:1}6.25%,100%{opacity:0}}"
    out = []
    for i in range(steps):
        x = ox + i * (pw + gap)
        delay = i / steps * dur
        on = pattern[i]
        fill = Y if on else "#161616"
        anim = f' style="animation:hit {dur}s linear {delay:.3f}s infinite"' if on else ""
        out.append(f'<rect x="{x}" y="{oy}" width="{pw}" height="{pw}" rx="6" fill="{fill}" stroke="{"#c9a400" if accent[i] else "#2a2a1a"}" stroke-width="{2 if accent[i] else 1}"{anim}/>')
        out.append(f'<rect x="{x - 2}" y="{oy - 2}" width="{pw + 4}" height="{pw + 4}" rx="8" fill="none" stroke="#FFFFFF" stroke-width="2" opacity="0" style="animation:hd {dur}s steps(1) {delay:.3f}s infinite"/>')
        out.append(f'<text x="{x + pw / 2}" y="{oy + pw + 22}" text-anchor="middle" font-family="{FONT}" font-size="12" fill="{Y if on else DIM}">{notes[i] or "·"}</text>')
        if i % 4 == 0:
            out.append(f'<text x="{x}" y="{oy - 10}" font-family="{FONT}" font-size="10" fill="{DIM}">{i + 1:02d}</text>')
    body = f"<style>{css}</style>" + "".join(out) + f'<text x="{w - 20}" y="26" text-anchor="end" font-family="{FONT}" font-size="12" fill="{Y}">{bpm} BPM</text>'
    (OUT / name).write_text(frame(w, h, body, "seq.play(16)"), encoding="utf-8")


def equalizer(name="anim-egaliseur.svg", bars=48, seed=3):
    w, h = 880, 140
    rnd = random.Random(seed)
    bw = (w - 48) / bars
    out, css = [], []
    for i in range(bars):
        x = 24 + i * bw
        d = rnd.uniform(0.7, 1.6)
        lo, hi = rnd.uniform(0.08, 0.3), rnd.uniform(0.55, 1)
        mid = rnd.uniform(lo, hi)
        css.append(f"@keyframes b{i}{{0%,100%{{transform:scaleY({lo:.2f})}}35%{{transform:scaleY({hi:.2f})}}70%{{transform:scaleY({mid:.2f})}}}}")
        out.append(
            f'<rect x="{x + 1.5:.1f}" y="30" width="{bw - 3:.1f}" height="90" rx="2" fill="url(#g)" '
            f'style="transform-origin:0 120px;transform-box:view-box;animation:b{i} {d:.2f}s ease-in-out {-rnd.uniform(0, d):.2f}s infinite"/>'
        )
    body = (
        f'<defs><linearGradient id="g" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#7a6a0a"/>'
        f'<stop offset=".7" stop-color="{Y}"/><stop offset="1" stop-color="#FFF3B0"/></linearGradient></defs>'
        f"<style>{''.join(css)}</style>" + "".join(out)
    )
    (OUT / name).write_text(frame(w, h, body), encoding="utf-8")


if __name__ == "__main__":
    weeks = grid_demo() if "--demo" in sys.argv else grid_real(os.environ.get("PROFILE_USER", "dedmauhaze"))
    pacman(weeks)
    if "--vaisseau" in sys.argv:
        shooter(weeks)
    equalizer()
    if "--303" in sys.argv:  # onde acid et séquenceur (retirés du profil, gardés en option)
        acid_wave()
        sequencer()
    print("animations générées dans assets/")
