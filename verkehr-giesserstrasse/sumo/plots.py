#!/usr/bin/env python3
"""Zeichnet Netzbilder, das Vergleichsdiagramm und kurze Animationen.

Aufruf (nach build.py und run.py)
    python3 plots.py                # Netzbilder und Vergleich
    python3 plots.py --animation    # zusaetzlich GIF je Variante aus Lauf 1

Ausgabe in grafik/.
"""
import argparse
import csv
import math
import os
import statistics as st
import xml.etree.ElementTree as ET
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from shapely.geometry import LineString

ROOT = os.path.dirname(os.path.abspath(__file__))
NETZE = os.path.join(ROOT, 'netze')
ERG = os.path.join(ROOT, 'ergebnisse')
GRAFIK = os.path.join(ROOT, 'grafik')

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as B  # noqa: E402
VARIANTEN = list(B.AKTIV)   # vorübergehend nur Bestand, siehe build.py
KURZ = {'bestand': 'Bestand', 'vorschlag1': 'Vorschlag 1', 'markierung': 'Markierung, T30\n(Empfehlung)', 'zone': 'T30-Zone, rvl\n(nur Vergleich)',
        'radwege': 'Rote\nRadwege', 'rvl': 'Rechts vor links\nTempo 30', 'minikreisel': 'Minikreisel\nmit Zebras',
        't30_zebra': 'T30, Zebra\nNord + West', 'geschuetzt': 'Geschützt\nInseln, Radfurten'}
TITEL = {'bestand': 'Bestand', 'vorschlag1': 'Vorschlag 1 der Initiative', 'markierung': 'Markierung und Tempo 30 (Empfehlung)', 'zone': 'Tempo-30-Zone, rechts vor links (nur Vergleich, nicht empfohlen)',
         'radwege': 'Rote Radwege', 'rvl': 'Rechts vor links, Tempo 30', 'minikreisel': 'Minikreisel mit Zebrastreifen',
         't30_zebra': 'Bestand mit Tempo 30 und Zebra Nord und West', 'geschuetzt': 'Geschützte Kreuzung (angepasst)'}
FARBE = {'bestand': '#2a78d6', 'vorschlag1': '#c8402c', 'markierung': '#eda100', 'zone': '#eb6834', 'radwege': '#d03b3b', 'rvl': '#8a8a8a', 'geschuetzt': '#1baf7a', 't30_zebra': '#8a8a8a', 'minikreisel': '#8a8a8a'}
FLAECHE = '#fcfcfb'
TEXT1, TEXT2, RASTER = '#0b0b0b', '#52514e', '#e4e3df'
FAHRBAHN, GEHWEG, KNOTEN = '#5b5f66', '#d9d6cf', '#6b6f76'

ARMTEXT = {'S': 'Gießerstraße Süd', 'N': 'Gießerstraße Nord', 'W': 'Naumburger Str. West', 'E': 'Naumburger Str. Ost'}

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'text.color': TEXT1,
                     'axes.labelcolor': TEXT2, 'xtick.color': TEXT2, 'ytick.color': TEXT2})


def form(s):
    return [tuple(map(float, p.split(','))) for p in s.split()]


def lies_netz(var):
    r = ET.parse(os.path.join(NETZE, f'{var}.net.xml')).getroot()
    lanes, junc, cross, walk = [], [], [], []
    for e in r.findall('edge'):
        fn = e.get('function')
        for l in e.findall('lane'):
            pts = form(l.get('shape'))
            w = float(l.get('width', 3.2))
            if fn == 'crossing':
                cross.append((pts, w, e.get('id')))
            elif fn == 'walkingarea':
                walk.append(pts)
            elif fn == 'internal':
                continue
            else:
                lanes.append((pts, w, l.get('allow', '')))
    for j in r.findall('junction'):
        if j.get('type') in ('internal',) or not j.get('shape'):
            continue
        junc.append(form(j.get('shape')))
    # Prioritaet der Querungen steht in den Knoten-Requests nicht direkt, daher aus den Plain-Dateien
    con = os.path.join(ROOT, 'build', f'{var}.con.xml')
    zebra = set()
    if os.path.exists(con):
        for c in ET.parse(con).getroot().findall('crossing'):
            if c.get('priority') == 'true':
                zebra.add((c.get('node'), c.get('edges').split()[0].split('_')[0]))
    return lanes, junc, cross, walk, zebra


def zeichne_netz(ax, var, ausschnitt=45):
    lanes, junc, cross, walk, zebra = lies_netz(var)
    ax.set_facecolor(FLAECHE)
    for pts in walk:
        if len(pts) >= 3:
            ax.add_patch(Polygon(pts, closed=True, fc=GEHWEG, ec='none', zorder=1))
    for pts, w, allow in lanes:
        if len(pts) < 2:
            continue
        poly = LineString(pts).buffer(w / 2, cap_style=2, join_style=2)
        fc = GEHWEG if allow == 'pedestrian' else ('#7d8590' if allow == 'bus' else ('#c0473a' if allow == 'bicycle' else FAHRBAHN))
        ax.add_patch(Polygon(list(poly.exterior.coords), closed=True, fc=fc, ec='none', zorder=2 if allow == 'pedestrian' else 3))
    for pts in junc:
        if len(pts) >= 3:
            ax.add_patch(Polygon(pts, closed=True, fc=KNOTEN, ec='none', zorder=3))
    for pts, w, cid in cross:
        node = cid[1:].rsplit('_c', 1)[0]
        line = LineString(pts)
        ist_zebra = any(n == node for n, _ in zebra)
        if ist_zebra:
            # Zebrastreifen: weisse Balken quer zur Gehrichtung
            n = max(3, int(line.length / 1.0))
            for i in range(n):
                if i % 2:
                    continue
                seg = LineString([line.interpolate(i / n, normalized=True), line.interpolate((i + 1) / n, normalized=True)])
                p = seg.buffer(w / 2, cap_style=2)
                ax.add_patch(Polygon(list(p.exterior.coords), closed=True, fc='white', ec='none', zorder=5))
        else:
            p = line.buffer(w / 2, cap_style=2)
            ax.add_patch(Polygon(list(p.exterior.coords), closed=True, fc='none', ec='white', lw=0.8, ls=(0, (2, 2)), zorder=5))
    if var == 'geschuetzt':
        import strassenraum as SR
        g = SR.geschuetzt()
        for geom, fc in ((g['insel'], '#c9c4b8'), (g['pflaster'], '#a59a8a'), (g['rad'], '#b5523b')):
            for poly in getattr(geom, 'geoms', [geom]):
                if poly.geom_type == 'Polygon' and not poly.is_empty:
                    ax.add_patch(Polygon(list(poly.exterior.coords), closed=True, fc=fc, ec='none', zorder=4))
    if var == 'minikreisel':
        # ueberfahrbare Mittelinsel (gepflastert)
        from matplotlib.patches import Circle
        ax.add_patch(Circle((0, 0), 3.2, fc='#b9b4aa', ec='white', lw=1.2, zorder=6))
    ax.set_xlim(-ausschnitt, ausschnitt)
    ax.set_ylim(-ausschnitt, ausschnitt)
    ax.set_aspect('equal')
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)


def netzbilder():
    os.makedirs(GRAFIK, exist_ok=True)
    fig, axs = plt.subplots(2, 2, figsize=(10, 10.6), facecolor=FLAECHE)
    for ax, var in zip(axs.flat, VARIANTEN):
        zeichne_netz(ax, var)
        ax.set_title(TITEL[var], fontsize=11, color=TEXT1, loc='left')
        beschrifte(ax)
    fig.suptitle('Varianten im SUMO-Modell, Ausschnitt 90 m × 90 m, Norden oben', x=0.02, ha='left', fontsize=13, color=TEXT1)
    fig.text(0.02, 0.01, 'Weiße Strichlinie: Querung ohne Markierung. Weiße Balken: Zebrastreifen. Hellgrau: Gehwege. '
             'Geometrie aus OpenStreetMap, Spuren nach Beobachtung.', fontsize=8.5, color=TEXT2)
    fig.tight_layout(rect=(0, 0.03, 1, 0.96))
    fig.savefig(os.path.join(GRAFIK, 'netze.png'), dpi=130, facecolor=FLAECHE)
    plt.close(fig)
    for var in VARIANTEN:
        fig, ax = plt.subplots(figsize=(6, 6), facecolor=FLAECHE)
        zeichne_netz(ax, var)
        ax.set_title(TITEL[var], fontsize=11, color=TEXT1, loc='left')
        beschrifte(ax)
        fig.tight_layout()
        fig.savefig(os.path.join(GRAFIK, f'netz_{var}.png'), dpi=130, facecolor=FLAECHE)
        plt.close(fig)


def beschrifte(ax):
    kw = dict(fontsize=8, color=TEXT2, va='center')
    ax.text(-15, -40, 'Gießerstr.\nSüd', ha='right', **kw)
    ax.text(15, 40, 'Gießerstr.\nNord', ha='left', **kw)
    ax.text(-43, 15, 'Naumburger Str. West', ha='left', **kw)
    ax.text(43, -16, 'Naumburger Str. Ost', ha='right', **kw)


# ---------------------------------------------------------------- Vergleich
def lade_kennzahlen():
    d = defaultdict(lambda: defaultdict(list))
    with open(os.path.join(ERG, 'kennzahlen.csv')) as f:
        for r in csv.DictReader(f):
            d[(r['kennzahl'], r['gruppe'])][r['variante']].append(float(r['wert']))
    return d


def vergleich():
    d = lade_kennzahlen()
    tafeln = [
        ('Fahrzeugkonflikte im Knoten\nje Stunde', ('konflikte_fz', 'alle')),
        ('Schwere Fahrzeugkonflikte je Stunde\n(TTC < 1 s oder PET < 0,5 s)', ('konflikte_fz', 'schwer')),
        ('Konflikte Kfz gegen Rad\nje Stunde', ('konflikte_fz', 'kfz_rad')),
        ('Fußgänger auf Querung, Fahrzeug müsste\nüber 3 m/s² bremsen, je Stunde', ('konflikte_fuss', 'alle')),
        ('Mittlere Wartezeit Fußgänger\nin Sekunden', ('fuss_wartezeit_s', 'alle')),
        ('Mittlerer Zeitverlust Kfz\nalle Zufahrten, in Sekunden', ('zeitverlust_s', 'alle|Kfz')),
        ('Mittlerer Zeitverlust Kfz\nZufahrt Nord, in Sekunden', ('zeitverlust_s', 'N|Kfz')),
        ('Nordarm: Anteil der Zeit mit\nwartenden Fahrzeugen in %', ('anteil_zeit_wartend', 'N')),
    ]
    vs = [v for v in VARIANTEN if any(d[k][v] for _, k in tafeln)]
    fig, axs = plt.subplots(3, 3, figsize=(13, 12), facecolor=FLAECHE)
    for ax, (titel, key) in zip(axs.flat, tafeln):
        ax.set_facecolor(FLAECHE)
        werte = [d[key][v] for v in vs]
        mw = [st.mean(w) if w else 0 for w in werte]
        sd = [st.stdev(w) if len(w) > 1 else 0 for w in werte]
        x = range(len(vs))
        ax.bar(x, mw, width=0.62, color=[FARBE[v] for v in vs], edgecolor=FLAECHE, linewidth=2, zorder=3)
        ax.errorbar(x, mw, yerr=sd, fmt='none', ecolor=TEXT2, elinewidth=1.2, capsize=3, zorder=4)
        top = max(m + s for m, s in zip(mw, sd)) or 1
        for xi, m, s in zip(x, mw, sd):
            ax.text(xi, m + s + top * 0.03, f'{m:.0f}' if m >= 10 else f'{m:.1f}', ha='center', va='bottom', fontsize=9.5, color=TEXT1)
        ax.set_ylim(0, top * 1.18)
        ax.set_title(titel, fontsize=10.5, color=TEXT1, loc='left')
        ax.set_xticks(list(x))
        ax.set_xticklabels([KURZ[v] for v in vs], fontsize=8.5)
        ax.yaxis.grid(True, color=RASTER, lw=0.8, zorder=0)
        ax.set_axisbelow(True)
        for s in ('top', 'right', 'left'):
            ax.spines[s].set_visible(False)
        ax.spines['bottom'].set_color(RASTER)
        ax.tick_params(axis='y', length=0)
    n = len(next(iter(d[tafeln[0][1]].values()), []))
    fig.suptitle('Kreuzung Gießerstraße / Naumburger Straße, Vergleich der Varianten (SUMO)', x=0.01, ha='left', fontsize=13)
    fig.text(0.01, 0.955, f'Mittelwert aus {n} Läufen je Variante, Strich zeigt die Streuung. Spitzenstunde geschätzt, '
             'Modell nicht kalibriert. Kleinere Werte sind besser.', fontsize=9, color=TEXT2)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(os.path.join(GRAFIK, 'vergleich.png'), dpi=130, facecolor=FLAECHE)
    plt.close(fig)


# ---------------------------------------------------------------- Animation
TYPFARBE = {'pkw': '#e4e3df', 'lkw': '#c98500', 'sattel': '#c98500', 'bus': '#2a78d6', 'rad': '#1baf7a'}
LAENGE = {'pkw': 4.5, 'lkw': 10.0, 'sattel': 16.5, 'bus': 18.0, 'rad': 1.8}
BREITE = {'pkw': 1.85, 'lkw': 2.5, 'sattel': 2.55, 'bus': 2.55, 'rad': 0.8}


def animation(var, start=1200, dauer=60, schritt=0.5):
    from matplotlib.animation import FuncAnimation, PillowWriter
    fcd = os.path.join(ERG, 'roh', f'{var}_01', 'fcd.xml')
    if not os.path.exists(fcd):
        print('keine FCD-Datei fuer', var)
        return
    frames = []
    for _, ts in ET.iterparse(fcd):
        if ts.tag != 'timestep':
            continue
        t = float(ts.get('time'))
        if start <= t < start + dauer:
            fz = [(v.get('id'), float(v.get('x')), float(v.get('y')), float(v.get('angle'))) for v in ts.findall('vehicle')]
            ps = [(float(p.get('x')), float(p.get('y'))) for p in ts.findall('person')]
            frames.append((t, fz, ps))
        ts.clear()
        if t >= start + dauer:
            break
    fig, ax = plt.subplots(figsize=(5.4, 5.6), facecolor=FLAECHE)
    zeichne_netz(ax, var, ausschnitt=40)
    ax.set_title(TITEL[var], fontsize=10, loc='left')
    dyn = []
    uhr = ax.text(-38, 36, '', fontsize=9, color=TEXT1, zorder=10)

    def bild(i):
        for a in dyn:
            a.remove()
        dyn.clear()
        t, fz, ps = frames[i]
        for vid, x, y, ang in fz:
            typ = vid.split('_')[0]
            a = math.radians(ang)
            hx, hy = math.sin(a), math.cos(a)
            qx, qy = hy, -hx
            L, B = LAENGE[typ], BREITE[typ] / 2
            pts = [(x + qx * B, y + qy * B), (x - qx * B, y - qy * B),
                   (x - qx * B - hx * L, y - qy * B - hy * L), (x + qx * B - hx * L, y + qy * B - hy * L)]
            p = Polygon(pts, closed=True, fc=TYPFARBE[typ], ec='#0b0b0b', lw=0.5, zorder=8)
            ax.add_patch(p)
            dyn.append(p)
        if ps:
            sc = ax.scatter([p[0] for p in ps], [p[1] for p in ps], s=14, c='#e34948', edgecolors='white', linewidths=0.5, zorder=9)
            dyn.append(sc)
        m, s = divmod(int(t - 600), 60)
        uhr.set_text(f'Spitzenstunde {m:02d}:{s:02d}')
        return dyn

    anim = FuncAnimation(fig, bild, frames=len(frames), blit=False)
    fig.text(0.02, 0.01, 'Grau Pkw, gelb Lkw, blau Bus, grün Rad, rot Fußgänger', fontsize=7.5, color=TEXT2)
    anim.save(os.path.join(GRAFIK, f'animation_{var}.gif'), writer=PillowWriter(fps=int(1 / schritt)), dpi=80)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--animation', action='store_true')
    args = ap.parse_args()
    os.makedirs(GRAFIK, exist_ok=True)
    netzbilder()
    if os.path.exists(os.path.join(ERG, 'kennzahlen.csv')):
        vergleich()
    if args.animation:
        for v in VARIANTEN:
            animation(v)
    print('Grafiken in', GRAFIK)


if __name__ == '__main__':
    main()
