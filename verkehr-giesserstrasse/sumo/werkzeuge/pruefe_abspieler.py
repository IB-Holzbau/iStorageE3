#!/usr/bin/env python3
"""Prueft den Abspieler auf sich ueberlappende Fahrzeuge.

Aufruf
    python3 werkzeuge/pruefe_abspieler.py [grafik/abspieler.html]

Liest die eingebetteten Bahnen, setzt die Fahrzeuge wie der Browser (Front auf der Bahn,
Heck entlang der eigenen Spur) und testet jeden zweiten Frame alle Fahrzeugumrisse
gegeneinander. Fussgaenger und Raeder untereinander werden nicht geprueft, Raeder gegen
Kfz schon. Ausgabe je Variante: Zahl der Frames mit Ueberlappung und die betroffenen Paare.
"""
import json
import math
import os
import re
import sys
from bisect import bisect_right

from shapely.geometry import Polygon

HIER = os.path.dirname(os.path.abspath(__file__))
DATEI = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HIER, '..', 'grafik', 'abspieler.html')
FORM = {'pkw': (4.5, 1.85), 'lkw': (10.0, 2.5), 'sattel': (16.5, 2.55), 'bus': (18.0, 2.55), 'rad': (1.8, 0.65)}
# Kleine Toleranz: Umrisse werden um 5 cm verkleinert, Beruehren zaehlt nicht
SCHRUMPF = 0.05


def lade():
    html = open(DATEI, encoding='utf-8').read()
    m = re.search(r'const D=(\{.*?\});\nconst NS=', html, re.S)
    return json.loads(m.group(1))


def dekodiere(raw, typen):
    out = []
    for d in raw['tracks']:
        n = d[2]
        xs, ys, cum = [], [], []
        x = y = 0
        for i in range(n):
            o = 3 + i * 3
            if i == 0:
                x, y = d[o], d[o + 1]
            else:
                x += d[o]
                y += d[o + 1]
            xs.append(x / 10)
            ys.append(y / 10)
            cum.append(cum[-1] + math.hypot(xs[-1] - xs[-2], ys[-1] - ys[-2]) if i else 0.0)
        out.append(dict(typ=typen[d[0]], f0=d[1], n=n, xs=xs, ys=ys, cum=cum, a0=d[5]))
    return out


def punkt(t, s):
    if s <= 0:
        a = math.radians(t['a0'])
        return t['xs'][0] + math.sin(a) * s, t['ys'][0] - math.cos(a) * s
    c = t['cum']
    if s >= c[-1]:
        return t['xs'][-1], t['ys'][-1]
    i = bisect_right(c, s) - 1
    d = c[i + 1] - c[i]
    f = (s - c[i]) / d if d > 0 else 0
    return t['xs'][i] + (t['xs'][i + 1] - t['xs'][i]) * f, t['ys'][i] + (t['ys'][i + 1] - t['ys'][i]) * f


def umriss(t, k):
    L, W = FORM[t['typ']]
    x, y = t['xs'][k], t['ys'][k]
    s = t['cum'][k]
    teile = []
    # wie im Browser: Teil beginnt am Punkt v hinter der Front, Richtung zum Punkt h, gezeichnete Laenge g
    if t['typ'] == 'bus':
        stuecke = [(0.0, 11.0, 11.0), (11.0, 18.0, 7.0)]
    elif t['typ'] == 'sattel':
        stuecke = [(0.0, 3.4, 3.6), (2.8, 16.5, 13.4)]
    else:
        stuecke = [(0.0, max(L, 1.0), L)]
    for v, h, g in stuecke:
        p = punkt(t, s - v) if v else (x, y)
        q = punkt(t, s - h)
        dx, dy = p[0] - q[0], p[1] - q[1]
        d = math.hypot(dx, dy)
        if d < 0.3:
            continue
        ux, uy = dx / d, dy / d
        q = (p[0] - ux * g, p[1] - uy * g)
        nx, ny = -uy * (W / 2 - SCHRUMPF), ux * (W / 2 - SCHRUMPF)
        p = (p[0] - ux * SCHRUMPF, p[1] - uy * SCHRUMPF)
        q = (q[0] + ux * SCHRUMPF, q[1] + uy * SCHRUMPF)
        teile.append(Polygon([(p[0] + nx, p[1] + ny), (p[0] - nx, p[1] - ny), (q[0] - nx, q[1] - ny), (q[0] + nx, q[1] + ny)]))
    return teile


def main():
    D = lade()
    gesamt = 0
    for var, raw in D['varianten'].items():
        tr = [t for t in dekodiere(raw, D['typen']) if t['typ'] != 'fuss']
        frames, paare = 0, {}
        for f in range(0, raw['n'], 2):
            aktiv = []
            for i, t in enumerate(tr):
                k = f - t['f0']
                if 0 <= k < t['n']:
                    aktiv.append((i, t, umriss(t, k)))
            treffer = False
            for a in range(len(aktiv)):
                for b in range(a + 1, len(aktiv)):
                    ia, ta, ua = aktiv[a]
                    ib, tb, ub = aktiv[b]
                    if ta['typ'] == 'rad' and tb['typ'] == 'rad':
                        continue
                    if abs(ta['xs'][f - ta['f0']] - tb['xs'][f - tb['f0']]) > 20:
                        continue
                    if any(p.intersects(q) for p in ua for q in ub):
                        treffer = True
                        key = (ia, ib)
                        paare.setdefault(key, [ta['typ'], tb['typ'], f * D['schritt']])
            frames += treffer
        gesamt += len(paare)
        print(f'{var}: {frames} Frames mit Ueberlappung, {len(paare)} Paare')
        for (ia, ib), (a, b, t) in list(paare.items())[:8]:
            print(f'   {a} und {b} ab {t:.1f} s')
    return gesamt


if __name__ == '__main__':
    sys.exit(1 if main() else 0)
