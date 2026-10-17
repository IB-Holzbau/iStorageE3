#!/usr/bin/env python3
"""Baut den Browser-Abspieler grafik/abspieler.html.

Aufruf (nach build.py und run.py)
    python3 abspieler/export.py

Je Variante laeuft SUMO einmal mit 0,2 s Schrittweite. Aufgezeichnet werden drei
Minuten nach zehn Minuten Einschwingzeit. Die Bahnen aller Fahrzeuge und Personen,
die Konflikte und die Kartengeometrie werden kompakt in eine einzige HTML-Datei
geschrieben, die im Browser mit 60 Bildern je Sekunde abspielt.
"""
import csv
import json
import math
import os
import re
import statistics as st
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import defaultdict

from shapely.geometry import LineString, Polygon, Point, box
from shapely.ops import substring, unary_union

HIER = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HIER)
sys.path.insert(0, ROOT)
import run as R          # noqa: E402  (Netzinfo und Fussgaengerkonflikte wiederverwenden)

NETZE = os.path.join(ROOT, 'netze')
OSM = os.path.join(ROOT, '..', 'daten', 'map.osm')
ZIEL = os.path.join(ROOT, 'grafik', 'abspieler.html')
VORLAGE = os.path.join(HIER, 'vorlage.html')

VARIANTEN = ['bestand', 'rvl', 'minikreisel', 't30_zebra']
SCHRITT = 0.2
START, DAUER = 600.0, 300.0
SEED = 1
# Sichtfenster in SUMO-Koordinaten (Meter, Norden oben, Knoten bei 0,0)
FENSTER = (-48.0, -80.0, 48.0, 46.0)
RAND = 25.0              # Bahnen etwas ueber das Fenster hinaus aufzeichnen


def r2(v):
    return round(v, 2)


def svgpts(pts):
    """SUMO (y nach oben) in SVG (y nach unten)."""
    return [(r2(x), r2(-y)) for x, y in pts]


def pfad(geom):
    """Shapely-Flaeche als SVG-Pfad."""
    if geom.is_empty:
        return ''
    polys = [geom] if geom.geom_type == 'Polygon' else list(geom.geoms)
    teile = []
    for p in polys:
        if p.geom_type != 'Polygon':
            continue
        for ring in [p.exterior] + list(p.interiors):
            c = svgpts(list(ring.coords))
            teile.append('M' + ' L'.join(f'{x} {y}' for x, y in c) + 'Z')
    return ''.join(teile)


def linie(pts):
    c = svgpts(pts)
    return 'M' + ' L'.join(f'{x} {y}' for x, y in c)


# ---------------------------------------------------------------- Simulation
def simuliere(var, ordner):
    f = {k: os.path.join(ordner, f'{var}_{k}.xml') for k in ('fcd', 'ssm')}
    cmd = [R.sumo_bin(), '-n', os.path.join(NETZE, f'{var}.net.xml'), '-r', os.path.join(NETZE, f'{var}.rou.xml'),
           '-a', os.path.join(NETZE, 'haltestelle.add.xml'),
           '--step-length', str(SCHRITT), '--begin', '0', '--end', str(START + DAUER), '--seed', str(SEED),
           '--no-step-log', '--no-warnings', '--time-to-teleport', '300', '--ignore-junction-blocker', '15',
           '--pedestrian.striping.jamtime', '30',
           '--device.ssm.probability', '1', '--device.ssm.measures', 'TTC DRAC PET',
           '--device.ssm.thresholds', f'{R.TTC} {R.DRAC} {R.PET}', '--device.ssm.range', '50',
           '--device.ssm.trajectories', 'false', '--device.ssm.write-positions', 'true', '--device.ssm.file', f['ssm'],
           '--fcd-output', f['fcd'], '--fcd-output.attributes', 'x,y,angle,speed,lane,pos,edge']
    subprocess.run(cmd, check=True, capture_output=True)
    return f


TYPEN = ['pkw', 'lkw', 'sattel', 'bus', 'rad', 'fuss']


def in_fenster(x, y, rand=RAND):
    x0, y0, x1, y1 = FENSTER
    return x0 - rand <= x <= x1 + rand and y0 - rand <= y <= y1 + rand


def bahnen_und_konflikte(var, f):
    lanelen, querung, form, nach = R.netzinfo(var)
    n_frames = int(round(DAUER / SCHRITT))
    spuren = {}          # id -> [typ, f0, [x], [y], [a]]
    fuss_konf = []
    paare = set()
    for _, ts in ET.iterparse(f['fcd']):
        if ts.tag != 'timestep':
            continue
        t = float(ts.get('time'))
        if t < START - 1e-6 or t >= START + DAUER - 1e-6:
            ts.clear()
            continue
        fr = int(round((t - START) / SCHRITT))
        fz = ts.findall('vehicle')
        pers = ts.findall('person')
        for el, istp in [(v, False) for v in fz] + [(p, True) for p in pers]:
            x, y = float(el.get('x')), float(el.get('y'))
            vid = ('p:' if istp else '') + el.get('id')
            typ = 'fuss' if istp else R.typ_von(el.get('id'))
            s = spuren.get(vid)
            if s is None or s[1] + len(s[2]) != fr:
                # neue Spur (oder Luecke): eigener Abschnitt
                key = vid if s is None else f'{vid}#{fr}'
                s = spuren[key] = [typ, fr, [], [], []]
                spuren[vid] = s
            s[2].append(x)
            s[3].append(y)
            s[4].append(float(el.get('angle')))
        # Fussgaenger auf Querungen gegen schnelle Fahrzeuge (wie run.py)
        for p in pers:
            m = re.match(r'(:\w+_c\d+)', p.get('edge') or '')
            if not m:
                continue
            px, py = float(p.get('x')), float(p.get('y'))
            pa = math.radians(float(p.get('angle')))
            pvx, pvy = float(p.get('speed')) * math.sin(pa), float(p.get('speed')) * math.cos(pa)
            for v in fz:
                sp = float(v.get('speed'))
                if sp < R.FUSS_TEMPO:
                    continue
                typ = R.typ_von(v.get('id'))
                treffer = R.fuss_ttc(px, py, pvx, pvy, v.get('lane'), float(v.get('pos')), sp, R.LAENGE[typ],
                                     R.BREITE[typ], lanelen, form, nach)
                if treffer is not None and sp / (2 * max(treffer, 0.05)) > R.FUSS_DRAC:
                    paar = (p.get('id'), v.get('id'))
                    if paar not in paare:
                        paare.add(paar)
                        fuss_konf.append([round(t - START, 1), r2(px), r2(-py), 'f',
                                          1 if sp > 30 / 3.6 else 0])
        ts.clear()

    # Spuren kodieren: Dezimeter und Grad, ab dem zweiten Wert als Differenz
    eindeutig = {id(s): s for s in spuren.values()}.values()
    out = []
    for typ, f0, xs, ys, angs in eindeutig:
        if not any(in_fenster(x, y) for x, y in zip(xs, ys)):
            continue
        d = [TYPEN.index(typ), f0, len(xs)]
        px = py = pa = None
        for x, y, a in zip(xs, ys, angs):
            ix, iy, ia = round(x * 10), round(-y * 10), round(a) % 360
            if px is None:
                d += [ix, iy, ia]
            else:
                da = (ia - pa + 180) % 360 - 180
                d += [ix - px, iy - py, da]
            px, py, pa = ix, iy, ia
        out.append(d)

    # Fahrzeugkonflikte aus SSM, Filter wie run.py
    konf = []
    gesehen = set()
    for c in ET.parse(f['ssm']).getroot().findall('conflict'):
        a, b = c.get('ego'), c.get('foe')
        key = (min(a, b), max(a, b), round(float(c.get('begin')) / 5))
        if key in gesehen:
            continue
        gesehen.add(key)

        def wert(tag, attr='value'):
            e = c.find(tag)
            return None if e is None or e.get(attr) in (None, 'NA') else e.get(attr)
        ttc, drac, pet = (wert(t) for t in ('minTTC', 'maxDRAC', 'PET'))
        ttc, drac, pet = (float(v) if v is not None else None for v in (ttc, drac, pet))
        if ttc is not None and float(wert('minTTC', 'speed') or 0) < R.KONFLIKT_TEMPO:
            ttc = None
        if drac is not None and float(wert('maxDRAC', 'speed') or 0) < R.KONFLIKT_TEMPO:
            drac = None
        if pet is not None and float(wert('PET', 'speed') or 0) < R.KONFLIKT_TEMPO:
            pet = None
        tag = 'minTTC' if ttc is not None else ('PET' if pet is not None else 'maxDRAC')
        kritisch = (ttc is not None and ttc < R.TTC) or (pet is not None and pet < R.PET) or (drac is not None and drac > R.DRAC)
        if not kritisch:
            continue
        art = wert(tag, 'type')
        art = int(art) if art is not None else -1
        if art == 111:
            continue
        zeit, pos = wert(tag, 'time'), wert(tag, 'position')
        if zeit is None or pos is None:
            continue
        zeit = float(zeit) - START
        if not 0 <= zeit < DAUER:
            continue
        x, y = map(float, pos.split(','))
        schwer = (ttc is not None and ttc < 1.0) or (pet is not None and pet < 0.5)
        konf.append([round(zeit, 1), r2(x), r2(-y), 'a' if art in (1, 2, 3, 4, 18) else 'k', 1 if schwer else 0])
    konf += fuss_konf
    konf.sort()
    return {'n': n_frames, 'tracks': out, 'konflikte': konf}


# ---------------------------------------------------------------- Karte
def lies_netz(var):
    r = ET.parse(os.path.join(NETZE, f'{var}.net.xml')).getroot()
    lanes, junctions, walk, cross = [], [], [], []
    for e in r.findall('edge'):
        fn = e.get('function')
        for l in e.findall('lane'):
            pts = [tuple(map(float, p.split(','))) for p in l.get('shape').split()]
            info = dict(edge=e.get('id'), id=l.get('id'), index=int(l.get('index')), width=float(l.get('width', 3.2)),
                        allow=l.get('allow', ''), disallow=l.get('disallow', ''), pts=pts, fn=fn,
                        length=float(l.get('length')))
            if fn == 'walkingarea':
                walk.append(info)
            elif fn == 'crossing':
                info['prio'] = e.get('crossingEdges')
                cross.append(info)
            else:
                lanes.append(info)
    # Zebrastreifen (Querung mit Vorrang) aus den Plain-Daten von build.py lesen
    con = os.path.join(ROOT, 'build', f'{var}.con.xml')
    zebra = set()
    if os.path.exists(con):
        for c in ET.parse(con).getroot().findall('crossing'):
            if c.get('priority') == 'true':
                zebra.add(frozenset(c.get('edges').split()))
    for c in cross:
        c['zebra'] = frozenset(c['prio'].split()) in zebra
    for j in r.findall('junction'):
        if j.get('type') == 'internal' or not j.get('shape'):
            continue
        pts = [tuple(map(float, p.split(','))) for p in j.get('shape').split()]
        if len(pts) >= 3:
            junctions.append((j.get('id'), pts))
    return lanes, junctions, walk, cross


def ist_fuss(l):
    return l['allow'] == 'pedestrian'


def ist_park(l):
    return l['allow'] == 'custom1'


def flaeche(l, extra=0.0):
    ls = LineString(l['pts'])
    if ls.length == 0:
        return Polygon()
    return ls.buffer(l['width'] / 2 + extra, cap_style=2, join_style=2, mitre_limit=3)


def gebaeude(xy_proj):
    r = ET.parse(OSM).getroot()
    nodes = {n.get('id'): (float(n.get('lat')), float(n.get('lon'))) for n in r.findall('node')}
    out = []
    for w in r.findall('way'):
        t = {x.get('k'): x.get('v') for x in w.findall('tag')}
        if 'building' not in t:
            continue
        nd = [x.get('ref') for x in w.findall('nd') if x.get('ref') in nodes]
        if len(nd) < 4:
            continue
        out.append(Polygon([xy_proj(nodes[i]) for i in nd]))
    return out


def osm_projektion():
    r = ET.parse(OSM).getroot()
    j = [n for n in r.findall('node') if n.get('id') == '60015219'][0]
    lat0, lon0 = float(j.get('lat')), float(j.get('lon'))
    kx = 111320 * math.cos(math.radians(lat0))
    return lambda p: ((p[1] - lon0) * kx, (p[0] - lat0) * 110540)


def ende_info(pts, am_ende=True):
    """Punkt und Richtungseinheitsvektor am Ende (oder Anfang) einer Polylinie."""
    if am_ende:
        a, b = pts[-2], pts[-1]
        p = b
    else:
        a, b = pts[0], pts[1]
        p = a
    d = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
    return p, ((b[0] - a[0]) / d, (b[1] - a[1]) / d)


def winkel_svg(ux, uy):
    """Drehwinkel fuer SVG, damit lokales +x in Fahrtrichtung zeigt."""
    return round(math.degrees(math.atan2(-uy, ux)), 1)


def karte(var, bauten):
    lanes, junctions, walk, cross = lies_netz(var)
    sicht = box(FENSTER[0] - 5, FENSTER[1] - 5, FENSTER[2] + 5, FENSTER[3] + 5)

    fahr = [flaeche(l) for l in lanes if not ist_fuss(l) and l['width'] > 0]
    fahr += [Polygon(p) .buffer(0) for _, p in junctions]
    fahr += [flaeche(c) for c in cross]
    geh = [flaeche(l) for l in lanes if ist_fuss(l) and not l['id'].startswith(':')]
    # Gehflaechen der Zwischenknoten liegen in SUMO teils quer ueber der Fahrbahn, deshalb die
    # Fahrspuren (auch die inneren Spuren im Knoten) davon abziehen
    spuren = unary_union([flaeche(l) for l in lanes if not ist_fuss(l) and l['width'] > 0])
    geh += [Polygon(w['pts']).buffer(0).difference(spuren) for w in walk if len(w['pts']) >= 3]
    gehweg = unary_union(geh).buffer(0.15).buffer(-0.15).intersection(sicht)
    # Knotenflaechen der Zwischenknoten (Bucht, Spuraufweitung) ragen sonst ueber den Gehweg hinaus
    haupt = [Polygon(p).buffer(0) for jid, p in junctions if jid == 'J' or jid.startswith('R')]
    korridor = unary_union([flaeche(l) for l in lanes if not l["id"].startswith(":")] + geh + haupt).buffer(8.0).buffer(-8.0)
    fahrbahn = unary_union(fahr).buffer(0.2).buffer(-0.2).difference(gehweg).intersection(korridor).intersection(sicht)
    k = {
        'fahrbahn': pfad(fahrbahn.simplify(0.03)),
        'gehweg': pfad(gehweg.simplify(0.03)),
    }

    # Kreiselinsel
    ring = [l for l in lanes if l['edge'].startswith('ring_') and not ist_fuss(l)]
    if ring:
        rmin = min(math.hypot(x, y) for l in ring for x, y in l['pts'])
        k['insel'] = r2(max(rmin - ring[0]['width'] / 2, 1.0))
        k['inselring'] = r2(rmin + ring[0]['width'] / 2)

    # Markierungen
    leit, trenn, halt, warte, zick = [], [], [], [], []
    kfz = [l for l in lanes if not ist_fuss(l) and not ist_park(l) and not l['id'].startswith(':')]
    proedge = defaultdict(list)
    for l in kfz:
        proedge[l['edge']].append(l)
    for e, ls in proedge.items():
        ls.sort(key=lambda l: l['index'])
        links = ls[-1]
        if e.startswith('ring_'):
            continue
        # Leitlinie Mitte: linker Rand der linken Spur der Zufahrt (nur _in, sonst doppelt)
        if '_in' in e and len(links['pts']) >= 2:
            ls_ = LineString(links['pts']).offset_curve(links['width'] / 2)
            if not ls_.is_empty and ls_.length > 1:
                leit.append(linie(list(ls_.coords)))
        if len(ls) > 1 and e != 'S_in_bucht':
            for l in ls[:-1]:
                if l['allow'] == 'bus':
                    continue
                ls_ = LineString(l['pts']).offset_curve(l['width'] / 2)
                if not ls_.is_empty and ls_.length > 1:
                    trenn.append(linie(list(ls_.coords)))
    # Halt- und Wartelinien am Knotenrand
    def querlinie(edge):
        ls = sorted(proedge.get(edge, []), key=lambda l: l['index'])
        if not ls:
            return None
        teile = []
        for l in ls:
            p, (ux, uy) = ende_info(l['pts'])
            nx, ny = uy, -ux       # rechts
            w = l['width'] / 2
            teile.append(((p[0] + nx * w - ux * 0.3, p[1] + ny * w - uy * 0.3), (p[0] - nx * w - ux * 0.3, p[1] - ny * w - uy * 0.3)))
        a = teile[0][0]
        b = teile[-1][1]
        return linie([a, b])
    if var in ('bestand', 't30_zebra'):
        q = querlinie('N_in_m')
        if q:
            halt.append(q)
        for e in ('E_in_m',):
            q = querlinie(e)
            if q:
                warte.append(q)
    if var == 'minikreisel':
        for a in 'SNWE':
            q = querlinie(f'{a}_in_m')
            if q:
                warte.append(q)
    # Busbucht: Zickzack entlang der Busspur
    for l in lanes:
        if l['allow'] == 'bus':
            ls = LineString(l['pts'])
            ls = substring(ls, ls.length * 0.12, ls.length * 0.9)   # ohne die Verziehungen an den Enden
            n = max(int(ls.length / 2.2), 2)
            pts = []
            for i in range(n + 1):
                p = ls.interpolate(i / n, normalized=True)
                q = ls.interpolate(min(i / n + 0.001, 1), normalized=True)
                ux, uy = q.x - p.x, q.y - p.y
                d = math.hypot(ux, uy) or 1
                nx, ny = -uy / d, ux / d
                s = (1 if i % 2 else -1) * 0.75
                pts.append((p.x + nx * s, p.y + ny * s))
            zick.append(linie(pts))
            hp, (ux, uy) = ende_info(l['pts'])
            mitte = ls.interpolate(0.5, normalized=True)
            k['haltestelle'] = [r2(mitte.x + uy * 3.6), r2(-(mitte.y - ux * 3.6))]
    k.update(leit=leit, trenn=trenn, halt=halt, warte=warte, zick=zick)

    # Zebrastreifen
    k['zebra'] = []
    for c in cross:
        if c['zebra']:
            k['zebra'].append([linie(c['pts']), r2(c['width'])])

    # Richtungspfeile Suedarm (zwei Spuren vor dem Knoten)
    pfeile = []
    for l in kfz:
        if l['edge'] == 'S_in_m' and l['index'] > 0 and var != 'minikreisel':
            ls = LineString(l['pts'])
            p = ls.interpolate(ls.length - 1.5)
            q = ls.interpolate(ls.length - 0.5)
            pfeile.append([r2(p.x), r2(-p.y), winkel_svg(q.x - p.x, q.y - p.y), 'L' if l['index'] == 2 else 'GR'])
    k['pfeile'] = pfeile

    # Parkende Autos
    park = []
    for l in lanes:
        if not ist_park(l) or l['edge'].endswith('_m') or l['id'].startswith(':'):
            continue
        ls = LineString(l['pts'])
        s = 3.0 if '_in' in l['edge'] else 6.0
        ende = ls.length - (6.0 if '_in' in l['edge'] else 3.0)
        i = 0
        while s + 4.4 <= ende:
            h = (i * 37 + len(l['id']) * 11) % 100   # feste Pseudozufallszahl fuer Luecken
            if h > 12:      # einzelne Luecken
                p = ls.interpolate(s + 2.2)
                q = ls.interpolate(s + 3.2)
                park.append([r2(p.x), r2(-p.y), winkel_svg(q.x - p.x, q.y - p.y), h % 5])
            s += 5.7
            i += 1
    k['park'] = park

    # Schilder: an der rechten Bordsteinkante vor der Haltlinie
    schilder = []

    def schild(edge, art, vor=1.5, aussen=1.6):
        geh = [l for l in lanes if l['edge'] == edge and ist_fuss(l)]
        if not geh:
            return
        l = geh[0]
        ls = LineString(l['pts'])
        p = ls.interpolate(max(ls.length - vor, 0))
        q = ls.interpolate(ls.length)
        ux, uy = q.x - p.x, q.y - p.y
        d = math.hypot(ux, uy) or 1
        nx, ny = uy / d, -ux / d
        schilder.append([r2(p.x + nx * aussen * 0.3), r2(-(p.y + ny * aussen * 0.3)), art])

    def schild_tempo(arm, art):
        geh = [l for l in lanes if l['edge'] == f'{arm}_in' and ist_fuss(l)]
        if geh:
            ls = LineString(geh[0]['pts'])
            p = ls.interpolate(max(ls.length - 18, 0))
            schilder.append([r2(p.x), r2(-p.y), art])

    if var in ('bestand', 't30_zebra'):
        schild('S_in_m', 'vf')
        schild('W_in_m', 'vf')
        schild('N_in_m', 'stop')
        schild('E_in_m', 'vg')
    if var == 'minikreisel':
        for a in 'SNWE':
            schild(f'{a}_in_m', 'kr')
    if var == 'rvl':
        for a in 'SNWE':
            schild(f'{a}_in_m', 'rvl')
    if var in ('rvl', 'minikreisel', 't30_zebra'):
        for a in 'SNWE':
            schild_tempo(a, 't30')
    # Zeichen 350 an beiden Enden jedes Zebrastreifens, etwas auf den Gehweg versetzt
    for c in cross:
        if c['zebra']:
            for am_ende in (False, True):
                p, (ux, uy) = ende_info(c['pts'], am_ende)
                sgn = 1 if am_ende else -1
                schilder.append([r2(p[0] + ux * sgn * 1.8), r2(-(p[1] + uy * sgn * 1.8)), 'zebra'])
    k['schilder'] = schilder
    return k


def namen():
    # Beschriftung auf der Bebauung neben den Armen
    return [
        ['Gießerstraße', -15.5, -30.0, -80],
        ['Gießerstraße', 14.0, -64.0, -80],
        ['Naumburger Straße', -33.0, 15.0, 8],
        ['Naumburger Straße', 31.0, -15.0, 8],
    ]


# ---------------------------------------------------------------- Kennzahlen
def kennzahlen():
    data = defaultdict(list)
    with open(os.path.join(ROOT, 'ergebnisse', 'kennzahlen.csv')) as f:
        for r in csv.DictReader(f):
            data[(r['variante'], r['kennzahl'], r['gruppe'])].append(float(r['wert']))

    def m(var, k, g):
        v = data.get((var, k, g))
        return round(st.mean(v), 1) if v else None
    out = {}
    for var in VARIANTEN:
        out[var] = {
            'konflikte': m(var, 'konflikte_fz', 'alle'),
            'schwer': m(var, 'konflikte_fz', 'schwer'),
            'fuss': m(var, 'konflikte_fuss', 'alle'),
            'verlust': m(var, 'zeitverlust_s', 'alle|Kfz'),
            'verlustN': m(var, 'zeitverlust_s', 'N|Kfz'),
            'wartenFuss': m(var, 'fuss_wartezeit_s', 'alle'),
            'laeufe': len(data.get((var, 'konflikte_fz', 'alle'), [])),
        }
    return out


def main():
    proj = osm_projektion()
    bauten_alle = gebaeude(proj)
    sicht = box(FENSTER[0] - 5, FENSTER[1] - 5, FENSTER[2] + 5, FENSTER[3] + 5)
    bauten = [b for b in bauten_alle if b.is_valid and b.intersects(sicht)]
    daten = {'fenster': [FENSTER[0], -FENSTER[3], FENSTER[2] - FENSTER[0], FENSTER[3] - FENSTER[1]],
             'schritt': SCHRITT, 'dauer': DAUER, 'typen': TYPEN,
             'bauten': pfad(unary_union(bauten).intersection(sicht).simplify(0.05)),
             'namen': namen(), 'kennzahlen': kennzahlen(), 'bus': open(os.path.join(NETZE, 'bus.txt')).read().strip(),
             'varianten': {}}
    with tempfile.TemporaryDirectory() as tmp:
        for var in VARIANTEN:
            print('Variante', var)
            f = simuliere(var, tmp)
            v = bahnen_und_konflikte(var, f)
            v['karte'] = karte(var, bauten)
            daten['varianten'][var] = v
            print(f"   {len(v['tracks'])} Bahnen, {len(v['konflikte'])} Konflikte")
    js = json.dumps(daten, separators=(',', ':'), ensure_ascii=False)
    html = open(VORLAGE, encoding='utf-8').read().replace('/*__DATEN__*/null', js)
    os.makedirs(os.path.dirname(ZIEL), exist_ok=True)
    with open(ZIEL, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'geschrieben {ZIEL} ({os.path.getsize(ZIEL) / 1e6:.2f} MB)')


if __name__ == '__main__':
    main()
