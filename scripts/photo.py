#!/usr/bin/env python3
"""À partir d'une photo détourée (PNG transparent) : avatar tramé noir/jaune (avatar.png)
et portrait ASCII (assets/portrait.txt).

Usage : python scripts/photo.py photo.png --crop x,y,w,h --ascii-crop x,y,w,h [--fond jaune|olive|noir]
Dépendances (locales uniquement) : pip install pillow numpy opencv-python-headless
Pour détourer une photo : pip install "rembg[cli]" onnxruntime, puis rembg i photo.jpg photo.png
La photo d'origine n'est jamais copiée dans le dépôt.
"""
import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
BLACK, YELLOW = (11, 11, 11), (255, 214, 10)
FONDS = {"jaune": YELLOW, "olive": (58, 50, 6), "noir": BLACK}
RAMP = " .'`:-=+*cxoO#%@"  # du vide au plein
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16


def load(path, crop):
    """Renvoie (luminosité 0..1 avec contraste local renforcé, masque du sujet 0..1)."""
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
    if crop:
        x, y, w, h = map(int, crop.split(","))
        img = img.crop((x, y, x + w, y + h))
    lum = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(4, 4)).apply(np.asarray(img.convert("L")))
    return lum / 255, np.asarray(img.getchannel("A")) / 255


def resize(a, size):
    return np.asarray(Image.fromarray((a * 255).astype("uint8")).resize(size, Image.LANCZOS)) / 255


def avatar(lum, alpha, fond, px=150, out=460, gamma=1.3):
    v, m = resize(lum, (px, px)) ** gamma, resize(alpha, (px, px)) > 0.5
    on = v > np.tile(BAYER, (px // 4 + 1, px // 4 + 1))[:px, :px]
    rgb = np.where(on[..., None], YELLOW, BLACK)
    rgb = np.where(m[..., None], rgb, FONDS[fond]).astype("uint8")
    Image.fromarray(rgb).resize((out, out), Image.NEAREST).save(ROOT / "avatar.png")


def portrait(lum, alpha, cols, gamma=0.95, char_w=0.6, line_h=1.1):
    """Portrait en caractères braille (2x4 points par caractère), tramé comme l'avatar."""
    h, w = lum.shape
    pw = cols * 2
    rows = round(pw * h / w * (char_w / 2) / (line_h / 4) / 4)
    ph = rows * 4
    v, m = resize(lum, (pw, ph)) ** gamma, resize(alpha, (pw, ph)) > 0.5
    on = (v > np.tile(BAYER, (ph // 4 + 1, pw // 4 + 1))[:ph, :pw]) & m
    bits = [(0, 0, 0x01), (1, 0, 0x02), (2, 0, 0x04), (0, 1, 0x08), (1, 1, 0x10), (2, 1, 0x20), (3, 0, 0x40), (3, 1, 0x80)]
    lines = []
    for r in range(rows):
        line = ""
        for c in range(cols):
            code = sum(b for dy, dx, b in bits if on[r * 4 + dy, c * 2 + dx])
            line += chr(0x2800 + code)
        lines.append(line)
    blank = chr(0x2800) * cols
    while lines and lines[0] == blank:
        lines.pop(0)
    while lines and lines[-1] == blank:
        lines.pop()
    (ROOT / "assets" / "portrait.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("photo")
    p.add_argument("--crop", help="recadrage de l'avatar : x,y,largeur,hauteur (carré conseillé)")
    p.add_argument("--ascii-crop", help="recadrage du portrait ASCII")
    p.add_argument("--cols", type=int, default=60)
    p.add_argument("--fond", choices=FONDS, default="jaune")
    args = p.parse_args()
    avatar(*load(args.photo, args.crop), args.fond)
    n = portrait(*load(args.photo, args.ascii_crop or args.crop), args.cols)
    print(f"avatar.png + assets/portrait.txt ({n} lignes) générés")
