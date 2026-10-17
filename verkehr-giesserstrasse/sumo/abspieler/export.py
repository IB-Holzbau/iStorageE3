#!/usr/bin/env python3
"""Baut den Browser-Abspieler grafik/abspieler.html.

Aufruf (nach build.py, werkzeuge/schleppkurve.py und run.py)
    python3 abspieler/export.py

Je Variante laeuft SUMO einmal mit 0,2 s Schrittweite. Aufgezeichnet werden fuenf
Minuten nach zehn Minuten Einschwingzeit. Fuer jedes Fahrzeug wird hier die Lage der
Glieder mit Schleppkurve berechnet (kinematik.py), dazu Blinker. Diagonalquerer kommen aus
diagonal.py. Bahnen, Konflikte und Kartengeometrie stehen kompakt in einer HTML-Datei, die
im Browser mit 60 Bildern je Sekunde abspielt.
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
from shapely.ops import unary_union

HIER = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HIER)
sys.path.insert(0, ROOT)
import run as R          # noqa: E402
import build as B        # noqa: E402
import kinematik as K    # noqa: E402
import diagonal as DG    # noqa: E402
import strassenraum as SR  # noqa: E402

NETZE = os.path.join(ROOT, 'netze')
OSM = os.path.join(ROOT, '..', 'daten', 'map.osm')
ZIEL = os.path.join(ROOT, 'grafik', 'abspieler.html')
VORLAGE = os.path.join(HIER, 'vorlage.html')

VARIANTEN = list(B.VERGLEICH)
SCHRITT = 0.2
START, DAUER = 600.0, 300.0
SEED = 1
# Sichtfenster in SUMO-Koordinaten (Meter, Norden oben, Knoten bei 0,0). Nach Sueden so weit,
# dass Haltestelle, Keil und die Parker suedlich davon zu sehen sind.
FENSTER = (-48.0, -98.0, 48.0, 44.0)
RAND = 25.0
TYPEN = ['pkw', 'lkw', 'sattel', 'bus', 'rad', 'fuss', 'fussd', 'pkwx']
# Fehlspur-Fahrer fahren auf dem Suedarm sichtbar mittig zwischen den Spuren
FEHLSPUR_VERSATZ = 1.1


def r2(v):
    return round(v, 2)


def svgpts(pts):
    return [(r2(x), r2(-y)) for x, y in pts]


def pfad(geom):
    """Shapely-Flaeche als SVG-Pfad (mit Loechern)."""
    if geom is None or geom.is_empty:
        return ''
    polys = [geom] if geom.geom_type == 'Polygon' else [g for g in getattr(geom, 'geoms', []) if g.geom_type == 'Polygon']
    teile = []
    for p in polys:
        for ring in [p.exterior] + list(p.interiors):
            c = svgpts(list(ring.coords))
            teile.append('M' + ' L'.join(f'{x} {y}' for x, y in c) + 'Z')
    return ''.join(teile)


def linie(pts):
    c = svgpts(pts)
    return 'M' + ' L'.join(f'{x} {y}' for x, y in c)


def winkel_svg(ux, uy):
    """Drehwinkel fuer SVG (y nach unten), damit lokales +x in Richtung (ux, uy) zeigt."""
    return round(math.degrees(math.atan2(-uy, ux)), 1)


# ---------------------------------------------------------------- Simulation
def simuliere(var, ordner):
    f = {k: os.path.join(ordner, f'{var}_{k}.xml') for k in ('fcd', 'ssm')}
    cmd = [R.sumo_bin(), '-n', os.path.join(NETZE, f'{var}.net.xml'), '-r', os.path.join(NETZE, f'{var}.rou.xml'),
           '-a', os.path.join(NETZE, 'haltestelle.add.xml'),
           '--step-length', str(SCHRITT), '--begin', '0', '--end', str(START + DAUER + 20), '--seed', str(SEED),
           '--no-step-log', '--no-warnings', '--time-to-teleport', '300', '--ignore-junction-blocker', '15',
           '--pedestrian.striping.jamtime', '30',
           '--device.ssm.probability', '1', '--device.ssm.measures', 'TTC DRAC PET',
           '--device.ssm.thresholds', f'{R.TTC} {R.DRAC} {R.PET}', '--device.ssm.range', '50',
           '--device.ssm.trajectories', 'false', '--device.ssm.write-positions', 'true', '--device.ssm.file', f['ssm'],
           '--fcd-output', f['fcd'], '--fcd-output.attributes', 'x,y,angle,speed,lane,pos,edge']
    subprocess.run(cmd, check=True, capture_output=True)
    return f


def in_fenster(x, y, rand=RAND):
    x0, y0, x1, y1 = FENSTER
    return x0 - rand <= x <= x1 + rand and y0 - rand <= y <= y1 + rand


def fehlspur_versatz(lane):
    e = lane.rsplit('_', 1)[0]
    return e in ('S_in', 'S_in_f', 'S_in_m') or lane.startswith(':J')


def bahnen_und_konflikte(var, f):
    lanelen, querung, form, nach = R.netzinfo(var)
    n_frames = int(round(DAUER / SCHRITT))
    roh = defaultdict(list)          # id -> [(frame, x, y, angle, lane)]
    fuss_konf = []
    paare = set()
    ne, sw = DG.ecken(B)
    diag = DG.Diagonal(SEED, B.DIAGONAL, 0, START + DAUER, ne, sw)
    for _, ts in ET.iterparse(f['fcd']):
        if ts.tag != 'timestep':
            continue
        t = float(ts.get('time'))
        fz = ts.findall('vehicle')
        pers = ts.findall('person')
        leute = diag.schritt(t, SCHRITT, [(float(v.get('x')), float(v.get('y')), float(v.get('speed'))) for v in fz])
        # Fahrzeuge schon vor dem Fenster aufzeichnen, damit die Schleppkurve eingeschwungen ist
        if t < START - 20 - 1e-6 or t >= START + DAUER - 1e-6:
            ts.clear()
            continue
        fr = int(round((t - START) / SCHRITT))
        for v in fz:
            roh[v.get('id')].append((fr, float(v.get('x')), float(v.get('y')), float(v.get('angle')), v.get('lane')))
        if fr < 0:
            ts.clear()
            continue
        for p in pers:
            roh['p:' + p.get('id')].append((fr, float(p.get('x')), float(p.get('y')), 0.0, ''))
        for pid, x, y, vx, vy, geht in leute:
            roh['d:' + pid].append((fr, x, y, 0.0, ''))
        # Fussgaenger auf Querungen und Diagonalquerer gegen schnelle Fahrzeuge (wie run.py)
        kand = []
        for p in pers:
            m = re.match(r'(:\w+_c\d+)', p.get('edge') or '')
            if not m:
                continue
            pa = math.radians(float(p.get('angle')))
            kand.append((p.get('id'), 'f', float(p.get('x')), float(p.get('y')),
                         float(p.get('speed')) * math.sin(pa), float(p.get('speed')) * math.cos(pa)))
        for pid, x, y, vx, vy, geht in leute:
            if geht:
                kand.append((pid, 'd', x, y, vx, vy))
        for pid, art, px, py, pvx, pvy in kand:
            for v in fz:
                sp = float(v.get('speed'))
                if sp < R.FUSS_TEMPO:
                    continue
                typ = R.typ_von(v.get('id'))
                treffer = R.fuss_ttc(px, py, pvx, pvy, v.get('lane'), float(v.get('pos')), sp, R.LAENGE[typ],
                                     R.BREITE[typ], lanelen, form, nach)
                if treffer is not None and sp / (2 * max(treffer, 0.05)) > R.FUSS_DRAC:
                    paar = (pid, v.get('id'))
                    if paar not in paare:
                        paare.add(paar)
                        fuss_konf.append([round(t - START, 1), r2(px), r2(-py), art, 1 if sp > 30 / 3.6 else 0])
        ts.clear()

    out = []
    kinem = {}
    for vid, seq in roh.items():
        if vid.startswith(('p:', 'd:')):
            typ = 'fuss' if vid.startswith('p:') else 'fussd'
        else:
            typ = R.typ_von(vid)
            if '_SNx' in vid:
                typ = 'pkwx'
        # Luecken teilen die Spur in Abschnitte
        abschnitte, akt = [], [seq[0]]
        for a, b in zip(seq, seq[1:]):
            if b[0] != a[0] + 1:
                abschnitte.append(akt)
                akt = []
            akt.append(b)
        abschnitte.append(akt)
        for ab in abschnitte:
            if not any(in_fenster(x, y) for _, x, y, _, _ in ab):
                continue
            xs = [p[1] for p in ab]
            ys = [p[2] for p in ab]
            ws = [p[3] for p in ab]
            if typ in ('fuss', 'fussd'):
                frames = [(x, y) for x, y in zip(xs, ys)]
                poses = None
            else:
                ktyp = 'pkw' if typ == 'pkwx' else typ
                if typ == 'pkwx':
                    # sichtbar mittig zwischen den Spuren: Versatz nach rechts auf dem Suedarm
                    for i, p in enumerate(ab):
                        if fehlspur_versatz(p[4]):
                            a = math.radians(ws[i])
                            xs[i] += math.cos(a) * FEHLSPUR_VERSATZ
                            ys[i] -= math.sin(a) * FEHLSPUR_VERSATZ
                poses = K.posen(ktyp, xs, ys, ws)
                blink = K.blinker(ws, xs, ys, int(7 / SCHRITT)) if ktyp != 'rad' else [0] * len(xs)
            # nur Frames ab Fensterbeginn
            k0 = next((i for i, p in enumerate(ab) if p[0] >= 0), None)
            if k0 is None:
                continue
            f0 = ab[k0][0]
            d = [TYPEN.index(typ), f0, len(ab) - k0]
            prev = None
            for i in range(k0, len(ab)):
                if poses is None:
                    vals = [round(xs[i] * 10), round(-ys[i] * 10)]
                    cur = vals
                    d += vals if prev is None else [vals[0] - prev[0], vals[1] - prev[1]]
                    prev = cur
                    continue
                Fx, Fy, h1, h2 = poses[i]
                vals = [round(Fx * 10), round(-Fy * 10), round(h1) % 360]
                if h2 is not None:
                    vals.append(round(h2) % 360)
                if prev is None:
                    d += vals
                else:
                    dv = [vals[0] - prev[0], vals[1] - prev[1]] + [((v - p + 180) % 360) - 180 for v, p in zip(vals[2:], prev[2:])]
                    d += dv
                d.append(blink[i])
                prev = vals
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
        if math.hypot(x, y) > R.KNOTENBEREICH:
            continue
        schwer = (ttc is not None and ttc < 1.0) or (pet is not None and pet < 0.5)
        konf.append([round(zeit, 1), r2(x), r2(-y), 'a' if art in (1, 2, 3, 4, 18) else 'k', 1 if schwer else 0])
    konf += fuss_konf
    konf.sort()
    return {'n': n_frames, 'tracks': out, 'konflikte': konf}


# ---------------------------------------------------------------- Karte
def lies_netz(var):
    r = ET.parse(os.path.join(NETZE, f'{var}.net.xml')).getroot()
    lanes, cross = [], []
    for e in r.findall('edge'):
        fn = e.get('function')
        for l in e.findall('lane'):
            pts = [tuple(map(float, p.split(','))) for p in l.get('shape').split()]
            info = dict(edge=e.get('id'), id=l.get('id'), index=int(l.get('index')), width=float(l.get('width', 3.2)),
                        allow=l.get('allow', ''), disallow=l.get('disallow', ''), pts=pts, fn=fn)
            if fn == 'crossing':
                info['kanten'] = e.get('crossingEdges')
                cross.append(info)
            elif fn not in ('walkingarea', 'internal'):
                lanes.append(info)
    con = os.path.join(ROOT, 'build', f'{var}.con.xml')
    zebra = set()
    if os.path.exists(con):
        for c in ET.parse(con).getroot().findall('crossing'):
            if c.get('priority') == 'true':
                zebra.add(frozenset(c.get('edges').split()))
    for c in cross:
        c['zebra'] = frozenset(c['kanten'].split()) in zebra
    return lanes, cross


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
    j = [n for n in r.findall('node') if n.get('id') == B.J_OSM][0]
    lat0, lon0 = float(j.get('lat')), float(j.get('lon'))
    kx = 111320 * math.cos(math.radians(lat0))
    return lambda p: ((p[1] - lon0) * kx, (p[0] - lat0) * 110540)


def ende_info(pts, am_ende=True):
    if am_ende:
        a, b = pts[-2], pts[-1]
        p = b
    else:
        a, b = pts[0], pts[1]
        p = a
    d = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
    return p, ((b[0] - a[0]) / d, (b[1] - a[1]) / d)


def _schraffur(poly, abstand=1.0, winkel=45):
    x0, y0, x1, y1 = poly.bounds
    L = (x1 - x0) + (y1 - y0)
    ux, uy = math.cos(math.radians(winkel)), math.sin(math.radians(winkel))
    out = []
    k = -L
    while k < L:
        cx, cy = (x0 + x1) / 2 + k * -uy, (y0 + y1) / 2 + k * ux
        seg = LineString([(cx - ux * L, cy - uy * L), (cx + ux * L, cy + uy * L)]).intersection(poly)
        for g in getattr(seg, 'geoms', [seg]):
            if g.geom_type == 'LineString' and g.length > 0.2:
                out.append(linie(list(g.coords)))
        k += abstand
    return out


ARME = None


def rahmen(a, teil='m'):
    global ARME
    if ARME is None:
        ARME = B.achsen()
    r = B.Rahmen(a, ARME[a])
    if teil != 'm':
        g = B.grenzlinie(a, ARME[a], teil)
        r.p0 = g[0]
    return r


def kante_q(a, seite, mit_park=True, teil='m'):
    """Querlage der Bordsteinkante (Seite out positiv, in negativ)."""
    q = sum(w for k, w in B.querschnitt(a, seite, teil) if mit_park or k != 'park')
    return q if seite == 'out' else -q


def punkt(a, seite, s, aussen, teil='m'):
    """Punkt am Arm a, Seite seite, Abstand s, aussen Meter hinter der Bordsteinkante."""
    r = rahmen(a, teil)
    q = kante_q(a, seite, True, teil)
    q += aussen if seite == 'out' else -aussen
    return r.punkt(s, q)


# Parkreihen je Variante (Arm, Seite, von s, bis s, Abschnitt fuer die Querlage), aus Luftbild,
# Strassenfotos und Angaben der Initiative
def parkreihen(var):
    G = SR.geschuetzt()['G'] if var == 'geschuetzt' else None
    r = [
        ('W', 'in', 40.0, 120.0, 'm'),     # Naumburger West Suedseite, die letzten 30 m Halteverbot Mo-Fr
        ('S', 'out', 45.0, 120.0, 'm'),    # Giesserstrasse Sued Westseite ab etwa 45 m
        ('S', 'in', 73.0, 120.0, 'fern'),  # Giesserstrasse Sued Ostseite suedlich der Haltestelle
        ('N', 'in', 31.0, 120.0, ''),      # Giesserstrasse Nord Westseite ab dem Halteverbotsschild
    ]
    if var == 'geschuetzt':
        r += [('E', 'in', G['d_p']['E'] + 2.5, 120.0, 'm'), ('E', 'out', 31.0, 120.0, 'm')]
    else:
        r += [('E', 'in', 1.0, 120.0, 'm'), ('E', 'out', 10.0, 120.0, 'm')]   # Nord bis an die Ecke, Sued ab 10 m
    return r


def parkautos(var):
    out = []
    lanes_m = {'W': 14.6, 'E': 13.8, 'S': 17.0, 'N': 13.8}
    for a, seite, s0, s1, teil in parkreihen(var):
        r = rahmen(a, teil)
        pw = sum(w for k, w in B.querschnitt(a, seite, teil) if k == 'park')
        q_aussen = kante_q(a, seite, True, teil)
        q = q_aussen - pw / 2 if seite == 'out' else q_aussen + pw / 2
        if var != 'geschuetzt' and a == 'E' and s0 < 5:
            s0 = max(s0, 9.5)        # ab der Knotenkante
        s = s0
        i = 0
        while s + 4.4 <= min(s1, 118):
            h = (i * 37 + int(s0) * 11 + len(a) * 7) % 100
            if h > 10:
                p = r.punkt(s + 2.2, q)
                pr = r.punkt(s + 3.2, q)
                out.append([r2(p[0]), r2(-p[1]), winkel_svg(pr[0] - p[0], pr[1] - p[1]), h % 5])
            s += 5.6
            i += 1
    return out


def schilder(var, lanes, cross):
    """Schilder [x, y, art, zusatz]. Arten: vf (306), vg (205), stop (206), rvl (102), t30 (274),
    zone (274.1), hv (283), zebra (350). Zusatz bei vf, vg, stop ist die Zufahrt (fuer 1002)."""
    out = []
    abkn = var in ('bestand', 't30_zebra', 'geschuetzt')
    if abkn:
        out.append(list(punkt('S', 'in', 14.0, 3.0)) + ['vf', 'S'])
        out.append(list(punkt('W', 'in', 22.0, 2.4)) + ['vf', 'W'])
        out.append(list(punkt('N', 'in', B.MUND['N'] + 4.5, 2.3)) + ['stop', 'N'])
        out.append(list(punkt('E', 'in', 15.0, 2.4)) + ['vg', 'E'])
    if var == 'rvl':
        for a in 'SNWE':
            out.append(list(punkt(a, 'in', 16.0, 2.4)) + ['rvl', ''])
    if var in ('rvl', 't30_zebra', 'geschuetzt'):
        for a in 'SNWE':
            out.append(list(punkt(a, 'in', 27.0, 2.4)) + ['t30', ''])
    else:
        # Tempo-30-Zone Naumburger West beginnt am Knoten (Zeichen 274.1)
        out.append(list(punkt('W', 'out', 17.0, 2.2)) + ['zone', ''])
    # absolutes bzw. zeitweises Halteverbot
    out.append(list(punkt('W', 'in', 38.0, 0.6)) + ['hv', 'Mo–Fr'])
    out.append(list(punkt('N', 'in', 30.5, 0.6, '')) + ['hv', ''])
    # Zeichen 350 an den Zebrastreifen
    for c in cross:
        if c['zebra']:
            # ein Schild je Zebrastreifen, am rechten Ende fuer den ankommenden Verkehr
            p, (ux, uy) = ende_info(c['pts'], True)
            out.append([p[0] + ux * 2.4, p[1] + uy * 2.4, 'zebra', ''])
    return [[r2(x), r2(-y), art, z] for x, y, art, z in out]


def karte(var, bauten):
    lanes, cross = lies_netz(var)
    sicht = box(FENSTER[0] - 5, FENSTER[1] - 5, FENSTER[2] + 5, FENSTER[3] + 5)
    alt = SR.fahrbahn_bestand()
    fahrbahn = SR.fahrbahn(var)
    gehweg = alt.buffer(4.5, join_style=2, mitre_limit=2.0).difference(alt)
    gehweg = gehweg.difference(unary_union(bauten)).intersection(sicht)
    k = {'fahrbahn': pfad(fahrbahn.intersection(sicht).simplify(0.02)), 'gehweg': pfad(gehweg.simplify(0.03))}
    if var == 'geschuetzt':
        g = SR.geschuetzt()
        k['insel'] = pfad(g['insel'].simplify(0.02))
        k['pflaster'] = pfad(g['pflaster'].simplify(0.02)) if not g['pflaster'].is_empty else ''
        furten = {e: l for e, l in g['linien'].items() if e[0] == 'r'}
        wege = {e: l for e, l in g['linien'].items() if e[0] != 'r'}
        k['radweg'] = pfad(unary_union([l.buffer(B.G_RAD_B / 2, cap_style=2, join_style=2) for l in wege.values()]).simplify(0.02))
        # Furten: zusammenhaengend je Arm, mit Blockmarkierung und Fahrradsymbolen
        k['radfurt'] = []
        k['radsym'] = []
        for arm in ('S', 'E'):
            l1, l2 = furten[f'r{arm}1'], furten[f'r{arm}2']
            pts = list(l1.coords) + list(l2.coords)[1:]
            k['radfurt'].append([linie(pts), B.G_RAD_B])
            ln = LineString(pts)
            for frac in (0.3, 0.7):
                p = ln.interpolate(frac, normalized=True)
                q = ln.interpolate(min(frac + 0.02, 1), normalized=True)
                k['radsym'].append([r2(p.x), r2(-p.y), winkel_svg(q.x - p.x, q.y - p.y)])
        for e, l in wege.items():
            p = l.interpolate(0.5, normalized=True)
            q = l.interpolate(0.52, normalized=True)
            k['radsym'].append([r2(p.x), r2(-p.y), winkel_svg(q.x - p.x, q.y - p.y)])

    # Markierungen: nur der Suedarm hat Leit- und Fahrstreifenlinien
    leit, trenn, halt, warte, zick, schmal, sperr, texte = [], [], [], [], [], [], [], []
    kfz = [l for l in lanes if l['allow'] not in ('pedestrian', 'custom1', 'bicycle') and not l['id'].startswith(':')]
    proedge = defaultdict(list)
    for l in kfz:
        proedge[l['edge']].append(l)
    for e, ls in proedge.items():
        ls.sort(key=lambda l: l['index'])
        if not e.startswith('S_') or e.startswith('ring'):
            continue
        links = ls[-1]
        if '_in' in e and len(links['pts']) >= 2:
            off = LineString(links['pts']).offset_curve(links['width'] / 2)
            if not off.is_empty and off.length > 1:
                leit.append(linie(list(off.coords)))
        for l, nachbar in zip(ls[:-1], ls[1:]):
            off = LineString(l['pts']).offset_curve(l['width'] / 2)
            if off.is_empty or off.length <= 1 or 'custom2' in (l['allow'], nachbar['allow']):
                continue
            if 'bus' in l['allow']:
                schmal.append(linie(list(off.coords)))     # breite Strichlinie Haltebereich
            else:
                trenn.append(linie(list(off.coords)))

    abkn = var in ('bestand', 't30_zebra', 'geschuetzt')
    if abkn:
        # Bogen der Leitlinie durch den Knoten: abknickende Vorfahrt Sued -> West (Luftbild)
        rs, rw = rahmen('S'), rahmen('W')
        sS = 11.0 if var != 'geschuetzt' else SR.geschuetzt()['G']['d_f']['S'] - 1.2
        P0, P3 = rs.punkt(sS, 0), rw.punkt(12.5 if var != 'geschuetzt' else 9.0, 0)
        P1 = (P0[0] - rs.u[0] * 6, P0[1] - rs.u[1] * 6)
        P2 = (P3[0] - rw.u[0] * 6, P3[1] - rw.u[1] * 6)
        bogen = []
        for i in range(25):
            t = i / 24
            bogen.append(((1 - t) ** 3 * P0[0] + 3 * (1 - t) ** 2 * t * P1[0] + 3 * (1 - t) * t * t * P2[0] + t ** 3 * P3[0],
                          (1 - t) ** 3 * P0[1] + 3 * (1 - t) ** 2 * t * P1[1] + 3 * (1 - t) * t * t * P2[1] + t ** 3 * P3[1]))
        k['bogen'] = linie(bogen)
        # schmale Sperrflaeche links der Linksabbiegespur (Strassenfoto Sued)
        if var != 'geschuetzt':
            f = Polygon([rs.punkt(18.5, -0.45), rs.punkt(25.0, -0.45), rs.punkt(25.0, 0.45), rs.punkt(18.5, 0.45)])
            sperr.append(pfad(f))

    def querlinie(edge):
        ls = sorted(proedge.get(edge, []), key=lambda l: l['index'])
        if not ls:
            return None
        teile = []
        for l in ls:
            p, (ux, uy) = ende_info(l['pts'])
            nx, ny = uy, -ux
            w = l['width'] / 2
            teile.append(((p[0] + nx * w - ux * 0.3, p[1] + ny * w - uy * 0.3), (p[0] - nx * w - ux * 0.3, p[1] - ny * w - uy * 0.3)))
        return linie([teile[0][0], teile[-1][1]])
    if abkn:
        q = querlinie('N_in_b')
        if q:
            halt.append(q)
        l = proedge.get('N_in_b', [None])[0]
        if l:
            ls_ = LineString(l['pts'])
            p = ls_.interpolate(ls_.length - 3.2)
            qq = ls_.interpolate(ls_.length - 2.2)
            texte.append(['STOP', r2(p.x), r2(-p.y), winkel_svg(qq.x - p.x, qq.y - p.y) + 90, 2.0])
        q = querlinie('E_in_m')
        if q:
            warte.append(q)
    # Haltestelle: Zickzack, BUS, Keil am Suedende, Wartehaeuschen
    for l in lanes:
        if l['edge'] == 'S_in_bucht' and 'bus' in l['allow']:
            ls = LineString(l['pts'])
            n = max(int(ls.length / 2.4), 2)
            pts = []
            for i in range(n + 1):
                p = ls.interpolate(i / n, normalized=True)
                q = ls.interpolate(min(i / n + 0.001, 1), normalized=True)
                ux, uy = q.x - p.x, q.y - p.y
                d = math.hypot(ux, uy) or 1
                nx, ny = -uy / d, ux / d
                sg = (1 if i % 2 else -1) * (l['width'] / 2 - 0.35)
                pts.append((p.x + nx * sg, p.y + ny * sg))
            zick.append(linie(pts))
            p = ls.interpolate(0.55, normalized=True)
            q = ls.interpolate(0.56, normalized=True)
            texte.append(['BUS', r2(p.x), r2(-p.y), winkel_svg(q.x - p.x, q.y - p.y) + 180, 2.6])
            # Keil: Sperrflaeche am Suedende (Einschwenken aus der Fahrspur)
            a0 = ls.coords[0]
            p_, (ux, uy) = ende_info(l['pts'], am_ende=False)
            nx, ny = uy, -ux       # rechts
            w = l['width'] / 2
            keil = Polygon([(a0[0] + nx * w, a0[1] + ny * w), (a0[0] - nx * w, a0[1] - ny * w),
                            (a0[0] + nx * w - ux * 6.5, a0[1] + ny * w - uy * 6.5)])
            sperr += _schraffur(keil, 0.9, 30)
            sperr.append(pfad(keil))
            mitte = ls.interpolate(0.5, normalized=True)
            ab = w + 2.0
            k['haltestelle'] = [r2(mitte.x + nx * ab), r2(-(mitte.y + ny * ab))]
            hh = [(mitte.x + nx * (w + 2.2) + ux * dx + nx * dq, mitte.y + ny * (w + 2.2) + uy * dx + ny * dq)
                  for dx, dq in ((-2.2, 0), (2.2, 0), (2.2, 1.5), (-2.2, 1.5))]
            k['haeuschen'] = pfad(Polygon(hh))
    k.update(leit=leit, trenn=trenn, halt=halt, warte=warte, zick=zick, schmal=schmal, sperr=sperr, texte=texte)

    k['zebra'] = [[linie(c['pts']), r2(c['width'])] for c in cross if c['zebra']]
    k['querung'] = [[linie(c['pts']), r2(c['width'])] for c in cross if not c['zebra']]

    pfeile = []
    for l in kfz:
        if l['edge'] == 'S_in' and l['index'] > 0:
            ls = LineString(l['pts'])
            if ls.length < 6:
                continue
            p = ls.interpolate(ls.length - 4.0)
            q = ls.interpolate(ls.length - 3.0)
            idx = sorted(x['index'] for x in proedge['S_in'])
            pfeile.append([r2(p.x), r2(-p.y), winkel_svg(q.x - p.x, q.y - p.y), 'L' if l['index'] == idx[-1] else 'GR'])
    k['pfeile'] = pfeile
    k['park'] = parkautos(var)
    k['schilder'] = schilder(var, lanes, cross)
    # Kiosk in der abgeschraegten Hausecke, davor Stehtische, Schaltkasten als Sichthindernis
    kiosk = punkt('W', 'in', 10.5, 5.2)
    k['kiosk'] = [r2(kiosk[0]), r2(-kiosk[1])]
    rw = rahmen('W')
    qk = kante_q('W', 'in') - 0.9
    kasten = Polygon([rw.punkt(15.6, qk), rw.punkt(17.4, qk), rw.punkt(17.4, qk - 0.7), rw.punkt(15.6, qk - 0.7)])
    k['kasten'] = pfad(kasten)
    return k


def namen():
    return [
        ['Gießerstraße', -16.0, -36.0, -80],
        ['Gießerstraße', 15.0, -60.0, -80],
        ['Gießerstraße', 13.5, 28.0, -80],
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
            'rad': m(var, 'konflikte_fz', 'kfz_rad'),
            'fuss': m(var, 'konflikte_fuss', 'alle'),
            'diag': m(var, 'konflikte_fuss', 'diag'),
            'fehlspur': m(var, 'konflikte_fz', 'fehlspur'),
            'verlust': m(var, 'zeitverlust_s', 'alle|Kfz'),
            'verlustN': m(var, 'zeitverlust_s', 'N|Kfz'),
            'wartendN': m(var, 'anteil_zeit_wartend', 'N'),
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
             'geom': {t: {k: v for k, v in g.items() if not isinstance(v, bool)} for t, g in K.GEOM.items()},
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
