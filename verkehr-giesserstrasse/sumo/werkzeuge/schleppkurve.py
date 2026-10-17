#!/usr/bin/env python3
"""Schleppkurven aller Fahrbeziehungen am Knoten.

Aufruf (nach build.py)
    python3 werkzeuge/schleppkurve.py

Fuer jede Verbindung im Hauptknoten faehrt ein Pkw, ein Lkw, ein Sattelzug und ein 18 m
Gelenkbus die Bahn aus dem SUMO-Netz ab (Front auf der Spurmitte, Glieder mit Schleppkurve wie
in kinematik.py). Ergebnis
    netze/schleppkurve_<variante>.json   ueberstrichene Flaechen Pkw und Schwerverkehr
    ergebnisse/schleppkurven.md          Ueberfahren von Bordstein und Inseln je Fahrbeziehung
In der geschuetzten Kreuzung legt die Pkw-Flaeche die Kante der Inseln fest (die Fahrbahn
reicht so weit, wie ein Pkw sie braucht). Was Bus, Lkw und Sattelzug darueber hinaus brauchen,
wird als ueberfahrbare Pflasterflaeche gezeichnet.
"""
import json
import math
import os
import sys
import xml.etree.ElementTree as ET

from shapely.geometry import LineString, Polygon, mapping
from shapely.ops import unary_union

HIER = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HIER)
sys.path.insert(0, ROOT)
import build as B          # noqa: E402
import kinematik as K      # noqa: E402

NETZE = os.path.join(ROOT, 'netze')
ERG = os.path.join(ROOT, 'ergebnisse')

# Wer faehrt welche Beziehung (aus der Nachfrage in build.py)
SCHWER = {'lkw': set(B.LKW), 'sattel': set(B.SATTEL), 'bus': {'SW', 'WS'}}


def lade(var):
    r = ET.parse(os.path.join(NETZE, f'{var}.net.xml')).getroot()
    lanes = {}
    for e in r.findall('edge'):
        for l in e.findall('lane'):
            lanes[l.get('id')] = [tuple(map(float, p.split(','))) for p in l.get('shape').split()]
    cons = r.findall('connection')
    weiter = {}
    for c in cons:
        if c.get('from').startswith(':'):
            weiter[f"{c.get('from')}_{c.get('fromLane')}"] = (c.get('via'), f"{c.get('to')}_{c.get('toLane')}")
    return lanes, cons, weiter


def bahn(lanes, weiter, c):
    """Polylinie von der Zufahrt durch den Knoten in die Ausfahrt, an beiden Enden gerade verlaengert."""
    vor = lanes[f"{c.get('from')}_{c.get('fromLane')}"]
    pts = list(vor)
    via = c.get('via')
    ziel = f"{c.get('to')}_{c.get('toLane')}"
    while via:
        pts += lanes[via][1:]
        nxt = weiter.get(via)
        if not nxt:
            break
        via, ziel = nxt
    pts += lanes.get(ziel, [])[1:]
    (x0, y0), (x1, y1) = pts[0], pts[1]
    d = math.hypot(x1 - x0, y1 - y0) or 1
    start = [(x0 - (x1 - x0) / d * 30, y0 - (y1 - y0) / d * 30)]
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    d = math.hypot(x1 - x0, y1 - y0) or 1
    ende = [(x1 + (x1 - x0) / d * 25, y1 + (y1 - y0) / d * 25)]
    return LineString(start + pts + ende)


def ueberstrichen(typ, linie):
    n = int(linie.length / 0.25)
    xs, ys, ws = [], [], []
    for i in range(n + 1):
        p = linie.interpolate(i * 0.25)
        q = linie.interpolate(min(i * 0.25 + 0.3, linie.length))
        r = linie.interpolate(max(i * 0.25 - 0.3, 0))
        xs.append(p.x)
        ys.append(p.y)
        ws.append(K.winkel_von(q.x - r.x, q.y - r.y))
    pos = K.posen(typ, xs, ys, ws)
    polys = []
    for (x, y), F in zip(zip(xs, ys), pos):
        if math.hypot(x, y) > 40:
            continue
        for e in K.umrisse(typ, (F[0], F[1]), F[2], F[3]):
            polys.append(Polygon(e))
    return unary_union(polys)


def rel(c):
    return c.get('from')[0] + c.get('to')[0]


def main():
    import strassenraum as SR
    zeilen = ['# Schleppkurven am Knoten\n',
              'Für jede Fahrbeziehung im Hauptknoten fahren Pkw und die schweren Fahrzeuge, die es dort laut '
              'Nachfrage gibt, die Bahn aus dem SUMO-Netz ab. Angegeben ist die Fläche in m², die ein Fahrzeug '
              'außerhalb der Fahrbahn überstreicht (Gehweg bzw. Insel). Kleine Werte unter 0,3 m² sind Rundungen.\n']
    for var in B.VARIANTEN:
        lanes, cons, weiter = lade(var)
        flaechen = {'pkw': [], 'schwer': []}
        zeilen.append(f'\n## {var}\n')
        zeilen.append('| Beziehung | Fahrzeug | außerhalb Fahrbahn m² |')
        zeilen.append('|---|---|---|')
        knoten = 'J' if var != 'minikreisel' else 'R'
        tab = {}
        fb = SR.fahrbahn_bestand() if var != 'geschuetzt' else SR.geschuetzt(roh=True)['fahrbahn']
        for c in cons:
            via = c.get('via') or ''
            if not via.startswith(f':{knoten}'):
                continue
            if c.get('from').startswith(':') or c.get('from')[0] not in 'SNWE' or c.get('to')[0] not in 'SNWE':
                continue
            if c.get('from').startswith(('a', 'x', 'r', 'g', 'f')):
                continue
            lin = bahn(lanes, weiter, c)
            r_ = rel(c)
            pk = ueberstrichen('pkw', lin)
            flaechen['pkw'].append(pk)
            aus = pk.difference(fb).area
            tab[(r_, 'Pkw')] = max(tab.get((r_, 'Pkw'), 0), aus)
            for typ, rels in SCHWER.items():
                if r_ not in rels:
                    continue
                sw = ueberstrichen(typ, lin)
                flaechen['schwer'].append(sw)
                name = dict(lkw='Lkw', sattel='Sattelzug', bus='Gelenkbus 18 m')[typ]
                tab[(r_, name)] = max(tab.get((r_, name), 0), sw.difference(fb).area)
        for (r_, name), v in sorted(tab.items()):
            zeilen.append(f'| {r_} | {name} | {v:.1f} |')
        out = {k: mapping(unary_union(v).simplify(0.05)) if v else None for k, v in flaechen.items()}
        with open(os.path.join(NETZE, f'schleppkurve_{var}.json'), 'w') as f:
            json.dump(out, f)
    with open(os.path.join(ERG, 'schleppkurven.md'), 'w') as f:
        f.write('\n'.join(zeilen) + '\n')
    print('geschrieben', os.path.join(ERG, 'schleppkurven.md'))


if __name__ == '__main__':
    main()
