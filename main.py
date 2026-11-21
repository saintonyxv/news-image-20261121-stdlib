#!/usr/bin/env python3
"""THE DAY IN ONE PICTURE - Saturday 21 November 2026.

Draws a newspaper front page that sums up the day's world news and
writes it to $MAKEFUN_OUTPUT_DIR/entry.png (default /output/entry.png).

Pure Python 3 standard library: the image is built as an RGB pixel
bytearray with hand-written primitives (scanline polygon fills,
Bresenham lines, quadratic-bezier trails, a 5x7 bitmap font defined
below) and encoded as a PNG with zlib + struct. No imports beyond
sys/os/zlib/struct/math, so it runs anywhere Python 3.13 does.
The render is fully deterministic: two runs write identical bytes.
"""

import os
import struct
import sys
import zlib
from math import cos, pi, sin, sqrt

W = 1024
H = 1024

# --- palette: ink black, paper cream, one red accent -------------------
PAPER = (246, 241, 226)
PAPER_DIM = (238, 232, 214)
INK = (20, 18, 15)
RED = (176, 22, 32)
RED_SOFT = (228, 118, 106)
ORANGE = (228, 122, 30)
CREAM = (250, 246, 235)
GREY = (96, 93, 84)
LAND_PL = (233, 222, 192)
LAND_UA = (206, 217, 231)
LAND_RU = (203, 203, 200)
BLUE_UK = (32, 52, 138)
BLUE_EU = (24, 44, 128)
YELLOW = (242, 200, 44)

img = bytearray(bytes(PAPER) * (W * H))


# --- pixel primitives ---------------------------------------------------
def px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        img[i] = c[0]
        img[i + 1] = c[1]
        img[i + 2] = c[2]


def rect(x0, y0, x1, y1, c):
    """Filled rectangle, [x0, x1) x [y0, y1), clipped to the canvas."""
    x0 = int(x0)
    y0 = int(y0)
    x1 = int(x1)
    y1 = int(y1)
    if x0 < 0:
        x0 = 0
    if y0 < 0:
        y0 = 0
    if x1 > W:
        x1 = W
    if y1 > H:
        y1 = H
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(c) * (x1 - x0)
    n = (x1 - x0) * 3
    for y in range(y0, y1):
        i = (y * W + x0) * 3
        img[i:i + n] = row


def outline(x0, y0, x1, y1, c, t=1):
    rect(x0, y0, x1, y0 + t, c)
    rect(x0, y1 - t, x1, y1, c)
    rect(x0, y0, x0 + t, y1, c)
    rect(x1 - t, y0, x1, y1, c)


def disc(cx, cy, r, c):
    r = int(r)
    for dy in range(-r, r + 1):
        dx = int(sqrt(r * r - dy * dy))
        rect(cx - dx, cy + dy, cx + dx + 1, cy + dy + 1, c)


def ring(cx, cy, r, c, t=2):
    steps = max(16, int(2 * pi * r))
    for i in range(steps + 1):
        a = 2 * pi * i / steps
        x = int(cx + r * cos(a))
        y = int(cy + r * sin(a))
        rect(x - t // 2, y - t // 2, x - t // 2 + t, y - t // 2 + t, c)


def line(x0, y0, x1, y1, c, t=1):
    """Bresenham line with a square brush of thickness t."""
    x0 = int(x0)
    y0 = int(y0)
    x1 = int(x1)
    y1 = int(y1)
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    r = t // 2
    while True:
        rect(x0 - r, y0 - r, x0 - r + t, y0 - r + t, c)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def poly(pts, c):
    """Scanline polygon fill."""
    ys = [p[1] for p in pts]
    y0 = max(0, int(min(ys)))
    y1 = min(H - 1, int(max(ys)))
    n = len(pts)
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            xa, ya = pts[i]
            xb, yb = pts[(i + 1) % n]
            if (ya <= y < yb) or (yb <= y < ya):
                xs.append(xa + (y - ya) * (xb - xa) / (yb - ya))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            rect(int(xs[i]), y, int(xs[i + 1]) + 1, y + 1, c)


def poly_outline(pts, c, t=1):
    n = len(pts)
    for i in range(n):
        xa, ya = pts[i]
        xb, yb = pts[(i + 1) % n]
        line(xa, ya, xb, yb, c, t)


def star(cx, cy, r_out, r_in, n, c, rot=-pi / 2):
    pts = []
    for i in range(2 * n):
        r = r_out if i % 2 == 0 else r_in
        a = rot + i * pi / n
        pts.append((cx + r * cos(a), cy + r * sin(a)))
    poly(pts, c)


def qbez(p0, p1, p2, c, t=3, steps=64):
    """Quadratic bezier stamped with small discs."""
    for i in range(steps + 1):
        u = i / steps
        v = 1 - u
        x = v * v * p0[0] + 2 * v * u * p1[0] + u * u * p2[0]
        y = v * v * p0[1] + 2 * v * u * p1[1] + u * u * p2[1]
        disc(int(x), int(y), max(1, t // 2), c)


# --- 5x7 bitmap font ------------------------------------------------------
FONT = {
    'A': (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'B': ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    'C': (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    'D': ("###..", "#..#.", "#...#", "#...#", "#...#", "#..#.", "###.."),
    'E': ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    'F': ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    'G': (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    'H': ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'I': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    'J': ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    'K': ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    'L': ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    'M': ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    'N': ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    'O': (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'P': ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    'Q': (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    'R': ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    'S': (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    'T': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'V': ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'W': ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    'X': ("#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"),
    'Y': ("#...#", ".#.#.", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    'Z': ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    '0': (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    '1': ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    '2': (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    '3': ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    '4': ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    '5': ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    '6': (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    '7': ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    '8': (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    '9': (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    ' ': (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    '.': (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ',': (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ':': (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ';': (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    "'": (".#...", ".#...", ".#...", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
    '-': (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    '·': (".....", ".....", ".....", ".##..", ".##..", ".....", "....."),
    '&': (".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    '/': ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    '%': ("##..#", "##.#.", "....#", "...#.", "..#..", ".#.##", "#..##"),
    '!': ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    '?': (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    '(': ("...##", "..#..", ".#...", ".#...", ".#...", "..#..", "...##"),
    ')': ("##...", "..#..", "...#.", "...#.", "...#.", "..#..", "##..."),
    '+': (".....", "..#..", "..#..", ".###.", "..#..", "..#..", "....."),
    '=': (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    '*': (".....", "#.#.#", ".###.", "#####", ".###.", "#.#.#", "....."),
    '#': (".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."),
    '$': ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    '_': (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
}

_TRANS = {
    '—': '-', '–': '-', '−': '-', '’': "'", '‘': "'",
    '“': '"', '”': '"', '«': '"', '»': '"',
}


def _norm(s):
    out = []
    for ch in s.upper():
        ch = _TRANS.get(ch, ch)
        if ch not in FONT:
            ch = ' '
        out.append(ch)
    return ''.join(out)


def text_w(s, scale, spacing=1):
    s = _norm(s)
    if not s:
        return 0
    return len(s) * (5 + spacing) * scale - spacing * scale


def draw_text(x, y, s, scale, c, spacing=1, bold=0):
    s = _norm(s)
    cx = int(x)
    y = int(y)
    for ch in s:
        g = FONT[ch]
        for ry in range(7):
            row = g[ry]
            for rx in range(5):
                if row[rx] == '#':
                    rect(cx + rx * scale, y + ry * scale,
                         cx + (rx + 1) * scale + bold,
                         y + (ry + 1) * scale, c)
        cx += (5 + spacing) * scale
    return cx


def draw_text_c(cx_center, y, s, scale, c, spacing=1, bold=0):
    w = text_w(s, scale, spacing)
    return draw_text(cx_center - w // 2, y, s, scale, c, spacing, bold)


def wrap(s, scale, maxw, spacing=1):
    words = s.split()
    lines = []
    cur = ''
    for wd in words:
        t = (cur + ' ' + wd).strip()
        if text_w(t, scale, spacing) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def draw_block(x, y, s, scale, c, maxw, line_gap=5, spacing=1):
    for ln in wrap(s, scale, maxw, spacing):
        draw_text(x, y, ln, scale, c, spacing)
        y += 7 * scale + line_gap
    return y


# --- map of the lead story -------------------------------------------------
MX, MY = 48, 392            # map box origin; box is 600 x 296
MW, MH = 600, 296

POLAND = [(55, 80), (80, 40), (130, 20), (185, 12), (235, 25), (265, 15),
          (300, 35), (315, 80), (300, 120), (312, 165), (295, 215),
          (255, 245), (200, 235), (160, 252), (105, 245), (60, 205),
          (42, 150), (45, 105)]
UKRAINE = [(312, 165), (300, 120), (315, 80), (345, 55), (400, 40),
           (460, 48), (520, 40), (565, 65), (580, 110), (568, 160),
           (582, 205), (545, 245), (480, 238), (420, 252), (360, 240),
           (320, 205)]
CRIMEA = [(428, 250), (468, 248), (486, 264), (458, 282), (424, 270)]
RUSSIA = [(345, 2), (598, 2), (598, 62), (565, 65), (520, 40), (460, 48),
          (400, 40), (345, 55)]


def mpt(p):
    return (MX + p[0], MY + p[1])


def draw_map():
    rect(MX, MY, MX + MW, MY + MH, PAPER_DIM)
    poly([mpt(p) for p in RUSSIA], LAND_RU)
    poly([mpt(p) for p in UKRAINE], LAND_UA)
    poly([mpt(p) for p in CRIMEA], LAND_UA)
    poly([mpt(p) for p in POLAND], LAND_PL)
    poly_outline([mpt(p) for p in UKRAINE], INK, 1)
    poly_outline([mpt(p) for p in CRIMEA], INK, 1)
    poly_outline([mpt(p) for p in POLAND], INK, 1)
    poly_outline([mpt(p) for p in RUSSIA], GREY, 1)

    # NATO compass badge, top-left over Poland
    bx, by = MX + 88, MY + 44
    disc(bx, by, 25, PAPER_DIM)
    ring(bx, by, 24, INK, 2)
    star(bx, by, 19, 6, 4, INK)

    # missile trails: from Russia in the east, arcing west
    bursts = [(278, 146), (284, 200), (402, 108)]
    starts = [(585, 22), (592, 96), (578, 52)]
    ctrls = [(430, 2), (452, 56), (486, 34)]
    for s0, c0, b0 in zip(starts, ctrls, bursts):
        qbez(mpt(s0), mpt(c0), mpt(b0), RED_SOFT, t=6, steps=56)
        qbez(mpt(s0), mpt(c0), mpt(b0), RED, t=3, steps=56)
    for b0 in bursts:
        bx2, by2 = mpt(b0)
        disc(bx2, by2, 9, ORANGE)
        star(bx2, by2, 17, 6, 8, RED)
        disc(bx2, by2, 3, CREAM)

    # drone glyph just inside the Polish side of the border
    dx, dy = mpt((298, 172))
    rect(dx - 7, dy - 3, dx + 7, dy + 3, INK)
    for ox, oy in ((-13, -9), (13, -9), (-13, 9), (13, 9)):
        line(dx, dy, dx + ox, dy + oy, INK, 2)
        disc(dx + ox, dy + oy, 4, INK)
        disc(dx + ox, dy + oy, 1, PAPER_DIM)
    disc(dx, dy, 2, RED)

    # cities
    wx, wy = mpt((150, 118))
    disc(wx, wy, 4, INK)
    draw_text(wx - 40, wy - 26, "WARSAW", 2, INK)
    kx, ky = mpt((402, 108))
    disc(kx, ky, 4, INK)
    draw_text(kx - 64, ky - 38, "KYIV", 2, INK)

    # country labels
    draw_text(MX + 92, MY + 188, "POLAND", 3, INK)
    draw_text(MX + 392, MY + 192, "UKRAINE", 3, INK)
    # RUSSIA sits in the grey wedge; patch over the trails so it reads
    rect(MX + 480, MY + 7, MX + 562, MY + 31, LAND_RU)
    draw_text(MX + 486, MY + 11, "RUSSIA", 2, GREY)
    outline(MX, MY, MX + MW, MY + MH, INK, 2)


# --- panel icons -------------------------------------------------------------
def icon_scales(ix, iy):
    cx = ix + 36
    rect(cx - 2, iy + 20, cx + 3, iy + 80, INK)          # post
    rect(cx - 31, iy + 15, cx + 31, iy + 20, INK)        # beam
    disc(cx, iy + 10, 5, INK)                            # finial
    for side in (-1, 1):
        ex = cx + side * 31
        line(ex, iy + 20, ex - 11, iy + 54, INK, 2)
        line(ex, iy + 20, ex + 11, iy + 54, INK, 2)
        pts = []
        for i in range(13):
            a = pi * i / 12
            pts.append((ex + 14 * cos(a), iy + 54 + 11 * sin(a)))
        poly(pts, INK)                                   # pan
    rect(cx - 19, iy + 80, cx + 19, iy + 85, INK)        # base


def _flag_us(x, y, w, h):
    rect(x, y, x + w, y + h, CREAM)
    sh = h // 7
    for i in range(0, 7, 2):
        rect(x, y + i * sh, x + w, y + (i + 1) * sh, RED)
    rect(x, y, x + w * 2 // 5, y + sh * 4, BLUE_UK)
    for dy in range(2, sh * 4 - 1, 4):
        for dx in range(2, w * 2 // 5 - 1, 4):
            px(x + dx, y + dy, CREAM)


def _flag_cn(x, y, w, h):
    rect(x, y, x + w, y + h, RED)
    disc(x + 5, y + 5, 3, YELLOW)
    for dx, dy in ((11, 2), (13, 5), (13, 9), (11, 12)):
        disc(x + dx, y + dy, 1, YELLOW)


def _flag_ru(x, y, w, h):
    t = h // 3
    rect(x, y, x + w, y + t, CREAM)
    rect(x, y + t, x + w, y + 2 * t, BLUE_EU)
    rect(x, y + 2 * t, x + w, y + h, RED)


def icon_flags(ix, iy):
    poles = [(ix + 4, iy + 4), (ix + 27, iy + 14), (ix + 50, iy + 4)]
    drawers = [_flag_us, _flag_cn, _flag_ru]
    for (fx, fy), fn in zip(poles, drawers):
        rect(fx - 1, fy, fx + 1, iy + 86, INK)
        disc(fx, fy - 2, 2, INK)
        fn(fx + 2, fy, 21, 15)


def icon_chart(ix, iy):
    line(ix + 10, iy + 8, ix + 10, iy + 80, INK, 2)
    line(ix + 10, iy + 80, ix + 68, iy + 80, INK, 2)
    pts = [(ix + 14, iy + 22), (ix + 26, iy + 31), (ix + 36, iy + 27),
           (ix + 47, iy + 45), (ix + 57, iy + 57), (ix + 65, iy + 69)]
    for i in range(len(pts) - 1):
        line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], RED, 3)
    ex, ey = pts[-1]
    poly([(ex + 3, ey + 4), (ex - 8, ey + 2), (ex + 1, ey - 7)], RED)


def icon_discs(ix, iy):
    cy = iy + 46
    ux, uy = ix + 27, cy
    r = 26
    for yy in range(uy - r, uy + r + 1):
        for xx in range(ux - r, ux + r + 1):
            dx = xx - ux
            dy = yy - uy
            if dx * dx + dy * dy <= r * r:
                c = BLUE_UK
                if abs(dx - dy) < 5 or abs(dx + dy) < 5:
                    c = CREAM
                if abs(dx) < 7 or abs(dy) < 7:
                    c = CREAM
                if abs(dx) < 4 or abs(dy) < 4:
                    c = (200, 30, 45)
                px(xx, yy, c)
    ex = ix + 49
    for yy in range(cy - r, cy + r + 1):
        for xx in range(ex - r, ex + r + 1):
            dx = xx - ex
            dy = yy - cy
            if dx * dx + dy * dy <= r * r:
                c = BLUE_EU
                for k in range(12):
                    a = 2 * pi * k / 12
                    sx = ex + 16 * cos(a)
                    sy = cy + 16 * sin(a)
                    if (xx - sx) ** 2 + (yy - sy) ** 2 < 7:
                        c = YELLOW
                        break
                px(xx, yy, c)
    ring(ex, cy, r, PAPER, 1)
    ring(ux, uy, r, PAPER, 1)


# --- the page ------------------------------------------------------------------
def draw_page():
    # frame
    outline(20, 20, 1004, 1004, INK, 3)
    outline(28, 28, 996, 996, INK, 1)

    # masthead
    draw_text_c(512, 44, "THE DAY IN ONE PICTURE", 7, INK, bold=2)
    rect(48, 104, 976, 107, INK)
    rect(48, 109, 976, 110, INK)

    # date band
    rect(48, 118, 976, 152, INK)
    draw_text_c(512, 124, "SATURDAY 21 NOVEMBER 2026", 3, CREAM)
    draw_text_c(512, 160, "LATE EDITION · FIVE STORIES · ONE PAGE", 2, INK)
    rect(48, 182, 976, 184, INK)

    # lead kicker + headline
    rect(48, 194, 976, 228, RED)
    draw_text(64, 200, "LEAD STORY - WAR IN EUROPE", 3, CREAM)
    draw_text(48, 242, "MISSILES FALL ON", 9, INK, bold=3)
    draw_text(48, 315, "NATO SOIL", 9, INK, bold=3)

    # lead visual + what-happened column
    draw_map()
    cx0 = 672
    draw_text(cx0, 396, "WHAT HAPPENED", 3, INK)
    rect(cx0, 424, 976, 427, RED)
    y = 438
    y = draw_block(cx0, y, "RUSSIAN MISSILES AND A DRONE CAME DOWN IN "
                           "POLAND DURING A MASS STRIKE ON UKRAINE.",
                   2, INK, 304, line_gap=5)
    y += 8
    y = draw_block(cx0, y, "WARSAW CALLED IT A DELIBERATE PROVOCATION. "
                           "NATO CALLED IT A GRAVE VIOLATION OF ITS "
                           "AIRSPACE.", 2, INK, 304, line_gap=5)
    y += 8
    draw_block(cx0, y, "IN KYIV, STRIKES HIT BRIDGES AND KILLED THREE "
                       "UTILITY WORKERS.", 2, INK, 304, line_gap=5)

    # secondary panels, 2 x 2
    rect(48, 698, 976, 700, INK)
    panels = [
        (48, 712, icon_scales,
         "WORLD COURT: MYANMAR COMMITTED GENOCIDE",
         "THE ICJ FINDS GENOCIDE AGAINST THE ROHINGYA PEOPLE."),
        (524, 712, icon_flags,
         "TRUMP, XI & PUTIN SUMMIT ENDS WITHOUT BREAKTHROUGH",
         "SHENZHEN TALKS CLOSE WITH NO DEAL ANNOUNCED."),
        (48, 838, icon_chart,
         "WALL STREET SLIDES INTO CORRECTION",
         "S&P AND DOW DROP 3.7% AS AI STOCKS SELL OFF."),
        (524, 838, icon_discs,
         "UK & EU SIGN LANDMARK POST-BREXIT DEALS",
         "DEALS ON FOOD, CARBON MARKETS AND YOUTH MOBILITY."),
    ]
    for x0, y0, icon, head, summ in panels:
        outline(x0, y0, x0 + 452, y0 + 116, INK, 1)
        icon(x0 + 12, y0 + 10)
        tx = x0 + 100
        hy = draw_block(tx, y0 + 14, head, 2, INK, 340, line_gap=4)
        draw_block(tx, max(hy + 4, y0 + 62), summ, 2, GREY, 340, line_gap=4)

    # footer
    rect(48, 966, 976, 968, INK)
    draw_text_c(512, 976, "DRAWN FROM THE DAY'S WIRE REPORTS · "
                          "SATURDAY 21 NOVEMBER 2026", 2, INK)


# --- PNG encoding ----------------------------------------------------------------
def _chunk(typ, data):
    return (struct.pack('>I', len(data)) + typ + data +
            struct.pack('>I', zlib.crc32(typ + data) & 0xFFFFFFFF))


def png_bytes():
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += img[y * stride:(y + 1) * stride]
    ihdr = struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + _chunk(b'IHDR', ihdr) +
            _chunk(b'IDAT', zlib.compress(bytes(raw), 9)) +
            _chunk(b'IEND', b''))


def main():
    draw_page()
    outdir = os.environ.get('MAKEFUN_OUTPUT_DIR', '/output')
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, 'entry.png')
    with open(path, 'wb') as f:
        f.write(png_bytes())
    return 0


if __name__ == '__main__':
    sys.exit(main())
