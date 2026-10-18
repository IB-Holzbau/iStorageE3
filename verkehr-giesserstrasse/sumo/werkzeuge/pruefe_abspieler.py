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

from shapely.geometry import LineString, Point, Polygon
from shapely.prepared import prep

HIER = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HIER)
sys.path.insert(0, ROOT)
import kinematik as K       # noqa: E402
import strassenraum as SR   # noqa: E402

DATEI = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'grafik', 'abspieler.html')
SCHRUMPF = 0.05
# Grenzen fuer die Quergeschwindigkeit beim Spurwechsel in m/s (Wunsch der Initiative)
QUER_MAX = {'pkw': 0.55, 'lkw': 0.5, 'bus': 0.5, 'sattel': 0.5}
NEIGUNG_MAX = 1 / 12
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


def bucht(var='bestand'):
    import xml.etree.ElementTree as ET
    r = ET.parse(os.path.join(ROOT, 'netze', f'{var}.net.xml')).getroot()
    for l in r.iter('lane'):
        if l.get('id') == 'S_in_bucht_1':
            pts = [tuple(map(float, p.split(','))) for p in l.get('shape').split()]
            return LineString(pts).buffer(2.0)


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
        # groesste Quergeschwindigkeit auf geraden Abschnitten (Spurwechsel), gegen die Grenze
        dt = D['schritt']
        quer = {}
        for t in tr:
            fr = t['frames']
            for i in range(5, len(fr) - 5):
                (x0, y0, a0, _), (x1, y1, a1, _) = fr[i - 1], fr[i]
                v = math.hypot(x1 - x0, y1 - y0) / dt
                # nur auf den Armen (Spurwechsel), im Knoten ist die Schraegfahrt Teil der Bahn
                if v < 1.0 or math.hypot(x1, y1) < 20 or abs(((fr[i + 5][2] - fr[i - 5][2]) + 180) % 360 - 180) > 6:
                    continue
                u = K.richtung(a1)
                q = abs((x1 - x0) * u[1] - (y1 - y0) * u[0]) / dt
                # bei schneller Fahrt gilt die Grenze als Neigung 1:12 (Spurwechsel ueber gut 40 m)
                q_rel = q - max(0.0, NEIGUNG_MAX * v - QUER_MAX.get(t['typ'], 9))
                quer[t['typ']] = max(quer.get(t['typ'], 0.0), q_rel)
        zu_quer = {k: round(v, 2) for k, v in quer.items() if k in QUER_MAX and v > QUER_MAX[k]}
        if zu_quer:
            gesamt += 1
        if zu_stark:
            gesamt += 1
        # Bus nordwaerts: steht mindestens 15 s im Haltebereich (Spur S_in_bucht_1)
        halt = []
        for t in tr:
            if t['typ'] != 'bus':
                continue
            fr = t['frames']
            nord = any(abs(((h - 10) + 180) % 360 - 180) < 30 and y < -40 for x, y, h, _ in fr)
            if not nord:
                continue
            steh = 0.0
            for (x0, y0, _, _), (x1, y1, _, _) in zip(fr, fr[1:]):
                if math.hypot(x1 - x0, y1 - y0) < 0.02 and bucht(var).contains(Point(x1, y1)):
                    steh += dt
            halt.append(round(steh, 1))
        if any(h < 15 for h in halt):
            gesamt += 1
        print(f'   Bus nordwaerts im Haltebereich stehend (s): {halt}' + (' ZU KURZ' if any(h < 15 for h in halt) else ''))
        print(f'{var}: {frames} Frames mit Ueberlappung, {len(paare)} Paare; Kfz ueber Bordstein {len(bord)}, ueber Insel/Pflaster {len(ins)}; '
              f'groesster Knick {", ".join(f"{k} {v:.0f} Grad" for k, v in knick.items())}' + (f' UEBER GRENZE {zu_stark}' if zu_stark else '')
              + '; groesste Quergeschwindigkeit ' + ', '.join(f'{k} {v:.2f} m/s' for k, v in sorted(quer.items()))
              + (f' UEBER GRENZE {zu_quer}' if zu_quer else ''))
        for (ia, ib), (a, b, t) in list(paare.items())[:8]:
            print(f'   {a} und {b} ab {t:.1f} s')
    return gesamt


if __name__ == '__main__':
    sys.exit(1 if main() else 0)
