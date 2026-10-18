#!/usr/bin/env python3
"""Spurenbild: gefahrene Bahnen aus den SUMO-Rohdaten ueber dem Netz, zum Vergleich mit dem
Luftbild (Reifenspuren). Je Fahrzeug eine duenne Linie, nach Typ gefaerbt.

Aufruf
    python3 werkzeuge/spurenbild.py [variante ...] [--minuten 30] [--lauf 1]

Ohne Variante alle Vergleichsvarianten. Grundlage ist ergebnisse/roh/<variante>_<lauf>
(run.py behaelt Lauf 1). Ausgabe grafik/spuren_<variante>.png.
"""
import argparse
import math
import os
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                      # noqa: E402
from matplotlib.patches import Polygon as MPoly      # noqa: E402
from shapely.geometry import LineString              # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import build as B   # noqa: E402
import run as R     # noqa: E402

FARBE = {'pkw': '#2b5aa8', 'lkw': '#b03a2e', 'sattel': '#b03a2e', 'bus': '#e67e22', 'rad': '#1e9e4a'}
NAME = {'pkw': 'Pkw', 'lkw': 'Lkw, Sattelzug', 'bus': 'Bus', 'rad': 'Rad'}
FLAECHE = {'pedestrian': '#ddd8cc', 'custom1': '#c9c3b6', 'custom2': '#b9b9b9'}
AUSSCHNITT = (-55, -135, 55, 65)     # x0, y0, x1, y1 in SUMO-Koordinaten


def netz_zeichnen(ax, var):
    r = ET.parse(os.path.join(R.NETZE, f'{var}.net.xml')).getroot()
    for j in r.findall('junction'):
        # nur Hauptknoten und Querungsknoten als Flaeche, die weichen Uebergaenge zeigen ihre Bahnen
        if j.get('type') == 'internal' or not j.get('shape') or not (j.get('id') == 'J' or j.get('id', '').startswith('M')):
            continue
        pts = [tuple(map(float, p.split(','))) for p in j.get('shape').split()]
        if len(pts) >= 3:
            ax.add_patch(MPoly(pts, closed=True, fc='#a9adb5', ec='none', zorder=1))
    for e in r.findall('edge'):
        if e.get('function') in ('crossing', 'walkingarea'):
            continue
        for l in e.findall('lane'):
            pts = [tuple(map(float, p.split(','))) for p in l.get('shape').split()]
            if len(pts) < 2:
                continue
            poly = LineString(pts).buffer(float(l.get('width', 3.2)) / 2, cap_style=2)
            if poly.is_empty or poly.geom_type != 'Polygon':
                continue
            fc = FLAECHE.get(l.get('allow') or '', '#a9adb5')
            ax.add_patch(MPoly(list(poly.exterior.coords), closed=True, fc=fc, ec='#f4f1ea', lw=0.4, zorder=1))


def bahnen(var, lauf, minuten):
    f = os.path.join(R.ROH, f'{var}_{lauf:02d}', 'fcd.xml')
    t0, t1 = R.WARMUP, R.WARMUP + minuten * 60
    tr = defaultdict(list)
    for _, ts in ET.iterparse(f):
        if ts.tag != 'timestep':
            continue
        t = float(ts.get('time'))
        if t0 <= t <= t1:
            for v in ts.findall('vehicle'):
                tr[v.get('id')].append((float(v.get('x')), float(v.get('y'))))
        ts.clear()
        if t > t1:
            break
    return tr


def zeichne(var, lauf=1, minuten=30):
    fig, ax = plt.subplots(figsize=(7.2, 10.4), dpi=200)
    ax.set_facecolor('#efebe2')
    netz_zeichnen(ax, var)
    zahl = defaultdict(int)
    for vid, pts in bahnen(var, lauf, minuten).items():
        typ = R.typ_von(vid)
        typ = 'lkw' if typ == 'sattel' else typ
        if typ not in FARBE:
            continue
        zahl[typ] += 1
        # Spruenge (Teleport, Einsetzen) trennen die Linie
        teile, akt = [], [pts[0]]
        for a, b in zip(pts, pts[1:]):
            if math.dist(a, b) > 6:
                teile.append(akt)
                akt = []
            akt.append(b)
        teile.append(akt)
        for t in teile:
            if len(t) > 1:
                xs, ys = zip(*t)
                ax.plot(xs, ys, color=FARBE[typ], lw=0.35 if typ == 'pkw' else 0.6, alpha=0.45 if typ == 'pkw' else 0.7,
                        zorder=3 if typ == 'pkw' else 4, solid_capstyle='round')
    x0, y0, x1, y1 = AUSSCHNITT
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect('equal')
    ax.set_xticks([])
    ax.set_yticks([])
    titel = {'bestand': 'Bestand'}.get(var, R.TITEL.get(var, var))
    ax.set_title(f'Gefahrene Bahnen im SUMO-Modell, {titel}\n{minuten} Minuten Spitzenstunde, Lauf {lauf}, '
                 'je dichter, desto häufiger befahren', fontsize=8)
    for typ, c in FARBE.items():
        if typ in NAME and zahl[typ]:
            ax.plot([], [], color=c, lw=1.5, label=f'{NAME[typ]} ({zahl[typ]} Fahrten)')
    ax.legend(loc='lower right', fontsize=6, framealpha=0.9)
    fig.tight_layout()
    aus = os.path.join(ROOT, 'grafik', f'spuren_{var}.png')
    fig.savefig(aus)
    plt.close(fig)
    print('geschrieben', aus)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('varianten', nargs='*', default=list(B.AKTIV))
    ap.add_argument('--minuten', type=int, default=30)
    ap.add_argument('--lauf', type=int, default=1)
    a = ap.parse_args()
    for v in a.varianten:
        zeichne(v, a.lauf, a.minuten)


if __name__ == '__main__':
    main()
