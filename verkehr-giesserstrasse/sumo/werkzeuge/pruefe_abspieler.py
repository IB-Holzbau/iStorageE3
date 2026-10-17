#!/usr/bin/env python3
"""Prueft den Abspieler auf sich ueberlappende Fahrzeuge und auf Fahrzeuge ueber dem Bordstein.

Aufruf
    python3 werkzeuge/pruefe_abspieler.py [grafik/abspieler.html]

Liest die eingebetteten Bahnen (Vorderachse und Richtung jedes Glieds), setzt die Glieder wie
der Browser (kinematik.umrisse) und testet jeden zweiten Frame alle Umrisse gegeneinander.
Raeder untereinander werden nicht geprueft, Raeder gegen Kfz schon. Zusaetzlich wird gezaehlt,
wie viele Kfz mit einem Glied ueber den Bordstein bzw. ueber Inseln oder Pflaster fahren.
"""
import json
import math
import os
import re
import sys

from shapely.geometry import Polygon
from shapely.prepared import prep

HIER = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HIER)
sys.path.insert(0, ROOT)
import kinematik as K       # noqa: E402
import strassenraum as SR   # noqa: E402

DATEI = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'grafik', 'abspieler.html')
SCHRUMPF = 0.05
STRIDE = {'pkw': 4, 'pkwx': 4, 'lkw': 4, 'rad': 4, 'bus': 5, 'sattel': 5, 'fuss': 2, 'fussd': 2}


def lade():
    html = open(DATEI, encoding='utf-8').read()
    m = re.search(r'const D=(\{.*?\});\nconst NS=', html, re.S)
    return json.loads(m.group(1))


def dekodiere(raw, typen):
    out = []
    for d in raw['tracks']:
        typ = typen[d[0]]
        n, st = d[2], STRIDE[typ]
        if st == 2:
            continue
        frames = []
        x = y = a = b = 0
        for i in range(n):
            o = 3 + i * st
            if i == 0:
                x, y, a = d[o], d[o + 1], d[o + 2]
                b = d[o + 3] if st == 5 else 0
            else:
                x += d[o]
                y += d[o + 1]
                a += d[o + 2]
                if st == 5:
                    b += d[o + 3]
            # zurueck in SUMO-Koordinaten (y nach oben)
            frames.append((x / 10, -y / 10, a % 360, (b % 360) if st == 5 else None))
        out.append(dict(typ='pkw' if typ == 'pkwx' else typ, f0=d[1], n=n, frames=frames))
    return out


def main():
    D = lade()
    gesamt = 0
    for var, raw in D['varianten'].items():
        tr = dekodiere(raw, D['typen'])
        fb = SR.fahrbahn(var)
        fb_p = prep(fb)
        insel = SR.inseln(var)
        frames, paare = 0, {}
        bord, ins = set(), set()
        for f in range(0, raw['n'], 2):
            aktiv = []
            for i, t in enumerate(tr):
                k = f - t['f0']
                if 0 <= k < t['n']:
                    Fx, Fy, h1, h2 = t['frames'][k]
                    polys = [Polygon(e) for e in K.umrisse(t['typ'], (Fx, Fy), h1, h2, SCHRUMPF)]
                    aktiv.append((i, t, polys, Fx))
                    if t['typ'] != 'rad' and math.hypot(Fx, Fy) < 35:
                        for p in polys:
                            if fb_p.contains(p):
                                continue
                            aus = p.difference(fb)
                            if aus.area < 0.2:
                                continue
                            if not insel.is_empty and aus.intersection(insel).area > 0.1:
                                ins.add(i)
                            else:
                                bord.add(i)
            treffer = False
            for a in range(len(aktiv)):
                for b in range(a + 1, len(aktiv)):
                    ia, ta, ua, xa = aktiv[a]
                    ib, tb, ub, xb = aktiv[b]
                    if ta['typ'] == 'rad' and tb['typ'] == 'rad':
                        continue
                    if abs(xa - xb) > 25:
                        continue
                    if any(p.intersects(q) for p in ua for q in ub):
                        treffer = True
                        paare.setdefault((ia, ib), [ta['typ'], tb['typ'], f * D['schritt']])
            frames += treffer
        gesamt += len(paare)
        # groesster Knickwinkel je Gelenkfahrzeug gegen die physikalische Grenze
        knick = {}
        for t in tr:
            if t['typ'] in K.KNICK_MAX:
                m = max(K.knickwinkel(h1, h2) for _, _, h1, h2 in t['frames'])
                knick[t['typ']] = max(knick.get(t['typ'], 0.0), m)
        zu_stark = {k: round(v, 1) for k, v in knick.items() if v > K.KNICK_MAX[k] + 0.6}
        if zu_stark:
            gesamt += 1
        print(f'{var}: {frames} Frames mit Ueberlappung, {len(paare)} Paare; Kfz ueber Bordstein {len(bord)}, ueber Insel/Pflaster {len(ins)}; '
              f'groesster Knick {", ".join(f"{k} {v:.0f} Grad" for k, v in knick.items())}' + (f' UEBER GRENZE {zu_stark}' if zu_stark else ''))
        for (ia, ib), (a, b, t) in list(paare.items())[:8]:
            print(f'   {a} und {b} ab {t:.1f} s')
    return gesamt


if __name__ == '__main__':
    sys.exit(1 if main() else 0)
