#!/usr/bin/env python3
"""Baut die SUMO-Netze und die Nachfrage aller Varianten.

Aufruf
    python3 build.py              # Busse im Regelbetrieb Sued <-> West (beide Richtungen)
    python3 build.py --bus SN     # Baustellenumleitung geradeaus Sued <-> Nord (Stand OSM Oktober 2026)

Ergebnis liegt in netze/<variante>.net.xml, netze/<variante>.rou.xml und
netze/haltestelle.add.xml. Die Geometrie der vier Arme kommt aus
../daten/map.osm, alles andere (Spuren, Vorfahrt, Querungen, Nachfrage)
ist unten in den Konstanten beschrieben. Die Ortsbeobachtungen der Initiative
(Oktober 2026) sind im README aufgelistet und hier eingearbeitet.
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.abspath(__file__))
OSM = os.path.join(ROOT, '..', 'daten', 'map.osm')
OUT = os.path.join(ROOT, 'netze')
PLAIN = os.path.join(ROOT, 'build')

# Alle Varianten. Der Minikreisel wird weiter gebaut, ist aber nicht mehr Teil des Vergleichs
# (siehe README, er passt fuer den 18 m Gelenkbus und den 8,2 m breiten Nordarm nicht).
# Vergleich (Entscheidung der Initiative, Oktober 2026): Bestand, bessere Markierung mit Tempo 30,
# Tempo-30-Zone mit rechts vor links und rote Radwege. Die frueheren Varianten (rechts vor links
# ohne Markierung, Tempo 30 mit Zebra, geschuetzte Kreuzung, Minikreisel) sind verworfen und
# werden nur mit --alt gebaut (siehe README, Abschnitt verworfene Varianten).
VERGLEICH = ['bestand', 'markierung', 'zone', 'radwege']
VERWORFEN = ['rvl', 't30_zebra', 'geschuetzt', 'minikreisel']
VARIANTEN = VERGLEICH + VERWORFEN
# Gruppen fuer die Regeln
ABKNICKEND = {'bestand', 't30_zebra', 'markierung', 'radwege'}   # abknickende Vorfahrt Sued <-> West
RECHTS_VOR_LINKS = {'rvl', 'zone'}
ECK_SPERR = {'markierung', 'zone', 'radwege'}                    # Grenzmarkierung Zeichen 299 an den Ecken

J_OSM = '60015219'          # Knoten Giesserstrasse / Naumburger Strasse
ARM_LEN = 120.0             # Laenge jedes Arms in Metern
# Abstand Knotenmitte bis Querungsknoten. Ortsbeobachtung: Nord wird zwischen Haltlinie und
# Knoten gequert, Ost und West direkt an der Knotenkante (Wunschlinie zum Kiosk an der SW-Ecke).
# Die Querungsknoten liegen deshalb unmittelbar am Rand des Hauptknotens.
# Ortsbeobachtung (Oktober 2026): Fussgaenger queren so frueh wie moeglich, also direkt dort, wo
# die Gehwegkante in die Eckausrundung uebergeht. Die Querungsachse liegt 0,5 m hinter dem Beginn
# der Ausrundung (Tangentenpunkte aus ECKEN: Sued 9,2 m, Nord 9,8 m, West 10,8 m, Ost 10,2 m), die
# 3 m breite Querung reicht also 1 m in den Eckbogen. Naeher geht in SUMO nicht, weil die Querung
# einen eigenen Knoten am Rand des Hauptknotens braucht (siehe README, Ueberlappungen).
# Die Haltlinie Nord liegt vor der Querung.
MUND = {'N': 10.3, 'S': 9.7, 'W': 11.3, 'E': 10.7}
KREISEL_R = 4.0             # Innenrand der Kreisfahrbahn (ueberfahrbare Mitte), mit 4,0 m Fahrbahn rund 16 m Aussendurchmesser
KREISEL_B = 4.0

V50, V30, V20 = 13.89, 8.33, 5.56

# Arme mit Strassenname und Richtung grob in Grad (0 = Nord, im Uhrzeigersinn)
ARME = {
    'S': ('Gießerstraße', 190),
    'N': ('Gießerstraße', 10),
    'W': ('Naumburger Straße', 280),
    'E': ('Naumburger Straße', 100),
}

# Tempo heute. Gießerstraße 50. Naumburger West Tempo 30 per Streckenschild (Zeichen 274,
# Laermaktionsplan seit 12/2025, OSM maxspeed=30 sign). Naumburger Ost ist Tempo-30-Zone
# (Zeichen 274.1 kurz hinter dem Knoten, Foto der Initiative). Die fruehere Annahme Ost 50 nach
# OSM war falsch.
TEMPO_OSM = {'S': V50, 'N': V50, 'W': V30, 'E': V30}

# Querschnitte je Arm, konstant ueber die ganze Laenge (Abgleich mit OSM width und Luftbild
# Geoportal Leipzig, Massstab 20 m). Jede Liste geht von rechts nach links in Fahrtrichtung,
# ohne Gehweg. 'kfz' Fahrspur, 'park' Parkstreifen (keine Fahrten), 'bus' Haltestellenbereich
# (nur Bus und Rad), 'sperr' Sperrflaeche (nur Minikreisel).
#   Gießerstraße Süd 13,0 m: West Parken 2,2 + südwärts 3,6 | nordwärts 7,2. Nordwärts liegt
#       südlich der Haltestelle ein Parkstreifen am rechten Rand (Ortsbeobachtung), der Bus fährt
#       dort auf der breiten Spur und schwenkt erst an der Haltestelle (45 bis 70 m) nach rechts.
#       Zwischen Haltestelle und Knoten zwei Spuren, auf den letzten 25 m mit Pfeilen
#       links bzw. geradeaus und rechts.
#   Gießerstraße Nord 8,2 m: je Richtung 4,1, keine Mittelmarkierung. Ab 30 m noerdlich parken
#       Autos auf der Westseite (Luftbild), dort Westseite Parken 2,0 + 3,1 | 3,1.
#   Auf der Westseite des Suedarms wird erst ab etwa 45 m suedlich geparkt (Luftbild), der
#       Streifen davor bleibt frei (im Netz als Streifen ohne Verkehr).
#   Naumburger West 9,5 m:   Südseite Parken 2,0 + ostwärts 3,75 | westwärts 3,75, ohne Markierung.
#   Naumburger Ost 9,5 m:    beidseitig Parken 2,0 bis an die Knotenkante + je Richtung 2,75,
#                            ohne Markierung (Engstelle im Begegnungsverkehr).
GEHWEG = 2.5
QUERSCHNITT = {
    # (Arm, Richtung): {Abschnitt: Spuren}, Abschnitt '*' gilt fuer alle uebrigen
    ('S', 'out'): {'*': [('park', 2.2), ('kfz', 3.6)]},
    ('S', 'in'): {'fern': [('park', 2.4), ('kfz', 4.8)],
                  'bucht': [('bus', 3.6), ('kfz', 3.6)],
                  '*': [('kfz', 3.6), ('kfz', 3.6)]},
    # Nord: ab 30 m noerdlich Laengsparken auf der Westseite (Luftbild), Fahrspuren dort 3,1 m
    ('N', 'out'): {'': [('kfz', 3.1)], '*': [('kfz', 4.1)]},
    ('N', 'in'): {'': [('park', 2.0), ('kfz', 3.1)], '*': [('kfz', 4.1)]},
    ('W', 'out'): {'*': [('kfz', 3.75)]},
    ('W', 'in'): {'*': [('park', 2.0), ('kfz', 3.75)]},
    ('E', 'out'): {'*': [('park', 2.0), ('kfz', 2.75)]},
    ('E', 'in'): {'*': [('park', 2.0), ('kfz', 2.75)]},
}
# Eckausbildung der Bordsteine (Beobachtung Luftbild): Nordecken ein Radius, Suedecken
# abgeschraegt mit zwei kleinen Radien. Wird von der Darstellung genutzt (strassenraum.py).
ECKEN = {'NE': ('rund', 5.0), 'WN': ('rund', 5.0), 'ES': ('schraeg', 3.5, 1.2), 'SW': ('schraeg', 3.5, 1.2)}
KNOTEN_RADIUS = 3.0

# ---- Geschuetzte Kreuzung (nach niederlaendischem Vorbild, angepasst, siehe README)
G_RING = 3.5                # Abstand der Radfurt von der Fahrbahnkante der kreuzenden Strasse
G_RING_SUED = 4.5           # Abstand der Furt ueber den Suedarm von der Suedkante der Naumburger Strasse
G_RAD_OFF = 1.1             # Radweg entlang der Arme, Mitte in m hinter der Fahrbahnkante
G_RAD_B = 1.6               # Breite Radweg und Radfurt
G_INNEN = 30.0              # bis hierhin ersetzen Inseln und Radweg die Parkstreifen
G_ZEBRA = 3.2               # Zebrastreifen liegt so weit hinter der Radfurt (Mitte zu Mitte)
G_RADIUS = 3.5              # Eckradius der Fahrbahn an den Inseln
# Radfurt-Vorrang: Am wartepflichtigen Ostarm gehoert die Furt zur Vorfahrtstrasse (Rad parallel
# zur Hauptrichtung Sued), Kfz warten. Am Suedarm kreuzt der Radverkehr die Vorfahrtstrasse und wartet.
G_FURT_VORRANG = {'E': True, 'S': False}


def querschnitt(a, richtung, teil, var='bestand'):
    q = QUERSCHNITT[(a, richtung)]
    spuren = list(q.get(teil, q['*']))
    if var == 'minikreisel' and a == 'S' and richtung == 'in' and teil in ('m', ''):
        # Minikreisel: nur eine Zufahrtspur, rechts Sperrflaeche
        spuren = [('sperr', 3.6), ('kfz', 3.6)]
    if var == 'geschuetzt' and teil in ('m', 'f', 'b', 'innen'):
        spuren = [s for s in spuren if s[0] != 'park']
    if var in ECK_SPERR and a == 'E' and teil == 'm':
        # Grenzmarkierung (Zeichen 299) statt Parken an der Ecke, Sichtfeld frei
        spuren = [('sperr', w) if k == 'park' else (k, w) for k, w in spuren]
    if var == 'radwege':
        spuren = RADWEGE.get((a, richtung, teil), RADWEGE.get((a, richtung, '*'), spuren))
    return spuren


# Rote Radwege (Variante radwege). Breiten nach ERA 2010: Radfahrstreifen 1,85 m einschliesslich
# Breitstrich, Sicherheitstrennstreifen zu Parkern 0,5 m. Die Summen je Seite bleiben wie heute,
# damit Bordsteine und Mittellinie unveraendert liegen.
#   Suedarm nordwaerts: Radfahrstreifen am rechten Rand, im Haltebereich teilen sich Bus und Rad
#       den Streifen (wie heute), suedlich davon bleibt das Parken mit Trennstreifen.
#   Suedarm suedwaerts: Radfahrstreifen 2,0 m statt Parkstreifen auf der Westseite.
#   Naumburger West ostwaerts: Radfahrstreifen auf den letzten 30 m im heutigen Halteverbot.
#       Westwaerts reicht die Breite nicht (3,75 m), dort Fahrbahn mit Piktogrammen.
#   Nordarm (8,2 m) und Ostarm (Engstelle) bleiben ohne Radstreifen, Piktogramme.
RADWEGE = {
    ('S', 'in', 'fern'): [('park', 2.0), ('sperr', 0.5), ('rad', 1.85), ('kfz', 2.85)],
    ('S', 'in', 'bucht'): [('bus', 3.6), ('kfz', 3.6)],
    ('S', 'in', '*'): [('rad', 1.85), ('kfz', 2.8), ('kfz', 2.55)],
    ('S', 'out', '*'): [('rad', 2.0), ('kfz', 3.8)],
    ('W', 'in', 'm'): [('rad', 1.85), ('kfz', 3.9)],
    ('W', 'in', 'b'): [('rad', 1.85), ('kfz', 3.9)],
}


def kfz_breite(a, richtung, teil='m'):
    """Breite der Fahrspuren ohne Parken am Knoten (fuer Bordsteinlinien der geschuetzten Kreuzung)."""
    return sum(w for k, w in querschnitt(a, richtung, teil) if k != 'park')


def breite(a, richtung, teil='m'):
    return sum(w for _, w in querschnitt(a, richtung, teil))


# Abschnitte am Suedarm (Abstand zur Knotenmitte). Haltestelle laut OSM ref 0505 etwa
# 45 bis 70 m suedlich auf dem rechten Streifen der Fahrbahn (keine Bucht).
S_BUCHT = (45.0, 70.0)
S_ABBIEGER = 25.0


# ---------------------------------------------------------------- Geometrie
def lade_osm():
    r = ET.parse(OSM).getroot()
    nodes = {n.get('id'): (float(n.get('lat')), float(n.get('lon'))) for n in r.findall('node')}
    lat0, lon0 = nodes[J_OSM]
    kx = 111320 * math.cos(math.radians(lat0))
    ky = 110540

    def xy(i):
        la, lo = nodes[i]
        return ((lo - lon0) * kx, (la - lat0) * ky)

    nachbarn = {}
    for w in r.findall('way'):
        t = {x.get('k'): x.get('v') for x in w.findall('tag')}
        if 'highway' not in t or 'name' not in t:
            continue
        nd = [x.get('ref') for x in w.findall('nd') if x.get('ref') in nodes]
        for a, b in zip(nd, nd[1:]):
            nachbarn.setdefault(a, []).append((b, t['name']))
            nachbarn.setdefault(b, []).append((a, t['name']))
    return xy, nachbarn, (lat0, lon0)


def peilung(p, q):
    return math.degrees(math.atan2(q[0] - p[0], q[1] - p[1])) % 360


def arm_polylinie(xy, nachbarn, name, richtung):
    """Folgt der Strasse ab dem Knoten und gibt die gerade Achse bis ARM_LEN zurueck."""
    j = J_OSM
    kand = [(b, n) for b, n in nachbarn[j] if n == name]
    start = min(kand, key=lambda c: abs((peilung(xy(j), xy(c[0])) - richtung + 180) % 360 - 180))[0]
    pts = [xy(j), xy(start)]
    prev, cur = j, start
    while True:
        weiter = [b for b, n in nachbarn.get(cur, []) if n == name and b != prev]
        if not weiter:
            break
        h = peilung(xy(prev), xy(cur))
        nxt = min(weiter, key=lambda b: abs((peilung(xy(cur), xy(b)) - h + 180) % 360 - 180))
        if abs((peilung(xy(cur), xy(nxt)) - h + 180) % 360 - 180) > 40:
            break
        pts.append(xy(nxt))
        prev, cur = cur, nxt
        if laenge(pts) > ARM_LEN:
            break
    if laenge(pts) < ARM_LEN:
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
        d = math.hypot(x2 - x1, y2 - y1)
        rest = ARM_LEN - laenge(pts)
        pts.append((x2 + (x2 - x1) / d * rest, y2 + (y2 - y1) / d * rest))
    pts = schneide(pts, 0, ARM_LEN)
    # gerade Achse: Richtung vom Knoten zu dem Punkt 60 m weiter (glaettet kleine Knicke in OSM)
    q = punkt_bei(pts, 60.0)
    d = math.hypot(q[0] - pts[0][0], q[1] - pts[0][1])
    ux, uy = (q[0] - pts[0][0]) / d, (q[1] - pts[0][1]) / d
    return [pts[0], (pts[0][0] + ux * ARM_LEN, pts[0][1] + uy * ARM_LEN)]


def achsen():
    xy, nachbarn, _ = lade_osm()
    return {a: arm_polylinie(xy, nachbarn, name, ri) for a, (name, ri) in ARME.items()}


def grenzlinie(a, achse, teil='m'):
    """Mittelmarkierung zwischen Hin- und Rueckrichtung. Sie liegt so, dass die Fahrbahn
    symmetrisch um die OSM-Achse liegt (beim Suedarm 0,7 m westlich der Achse). Am Nordarm
    springt sie dort, wo das Parken beginnt, um 1 m nach Osten."""
    (x0, y0), (x1, y1) = achse
    d = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / d, (y1 - y0) / d
    rx, ry = uy, -ux                     # rechts der Richtung nach aussen
    k = (breite(a, 'in', teil) - breite(a, 'out', teil)) / 2
    return [(x0 + rx * k, y0 + ry * k), (x1 + rx * k, y1 + ry * k)]


class Rahmen:
    """Lokales Koordinatensystem eines Arms: s entlang der Mittellinie nach aussen, q quer
    (positiv nach rechts in Fahrtrichtung nach aussen, also zur Seite der abfuehrenden Spuren)."""

    def __init__(self, a, achse):
        g = grenzlinie(a, achse)
        self.a = a
        self.p0 = g[0]
        d = math.hypot(g[1][0] - g[0][0], g[1][1] - g[0][1])
        self.u = ((g[1][0] - g[0][0]) / d, (g[1][1] - g[0][1]) / d)
        self.r = (self.u[1], -self.u[0])

    def punkt(self, s, q):
        return (self.p0[0] + self.u[0] * s + self.r[0] * q, self.p0[1] + self.u[1] * s + self.r[1] * q)

    def lokal(self, p):
        dx, dy = p[0] - self.p0[0], p[1] - self.p0[1]
        return dx * self.u[0] + dy * self.u[1], dx * self.r[0] + dy * self.r[1]

    def kante(self, seite, off=0.0):
        """Gerade (Punkt, Richtung) parallel zur Fahrbahnkante der Kfz-Spuren am Knoten, um off nach aussen."""
        q = kfz_breite(self.a, 'out') + off if seite == 'out' else -(kfz_breite(self.a, 'in') + off)
        return self.punkt(0, q), self.u


def laenge(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def punkt_bei(pts, s):
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        if acc + d >= s:
            f = (s - acc) / d if d else 0
            return (a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]))
        acc += d
    return pts[-1]


def schneide(pts, s0, s1):
    """Teilstueck der Polylinie zwischen den Bogenlaengen s0 und s1."""
    out = [punkt_bei(pts, s0)]
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        acc += math.hypot(b[0] - a[0], b[1] - a[1])
        if s0 < acc < s1:
            out.append(b)
    out.append(punkt_bei(pts, s1))
    return out


def schnitt(g1, g2):
    """Schnittpunkt zweier Geraden (Punkt, Richtung)."""
    (p, u), (q, v) = g1, g2
    det = u[0] * (-v[1]) - u[1] * (-v[0])
    t = ((q[0] - p[0]) * (-v[1]) - (q[1] - p[1]) * (-v[0])) / det
    return (p[0] + u[0] * t, p[1] + u[1] * t)


def fmt(pts):
    return ' '.join(f'{x:.2f},{y:.2f}' for x, y in pts)


# ---------------------------------------------------------------- Netz
class Netz:
    def __init__(self):
        self.nodes, self.edges, self.cons, self.crossings, self.roundabouts = [], [], [], [], []
        self.spuren = {}

    def node(self, nid, p, typ='priority', **kw):
        a = ' '.join(f'{k}="{v}"' for k, v in kw.items())
        self.nodes.append(f'    <node id="{nid}" x="{p[0]:.2f}" y="{p[1]:.2f}" type="{typ}" {a}/>')

    def edge(self, eid, frm, to, shape, lanes, speed, prio, ohne_rad=False, spread=None):
        """lanes ist eine Liste von (art, breite) von rechts nach links, Gehweg zuerst."""
        sp = f' spreadType="{spread}"' if spread else ''
        s = [f'    <edge id="{eid}" from="{frm}" to="{to}" priority="{prio}" numLanes="{len(lanes)}" '
             f'speed="{speed}" shape="{fmt(shape)}"{sp}>']
        erlaubt = {'park': 'custom1', 'sperr': 'custom2', 'bus': 'bus bicycle', 'pedestrian': 'pedestrian',
                   'rad': 'bicycle'}
        for i, (allow, w) in enumerate(lanes):
            if allow == 'kfz':
                dis = 'pedestrian custom1 custom2' + (' bicycle' if ohne_rad else '')
                s.append(f'        <lane index="{i}" disallow="{dis}" width="{w}"/>')
            else:
                s.append(f'        <lane index="{i}" allow="{erlaubt[allow]}" width="{w}"/>')
        s.append('    </edge>')
        self.edges.append('\n'.join(s))
        self.spuren[eid] = [k for k, _ in lanes]

    def kfz(self, eid):
        """Indizes der Kfz-Spuren einer Kante von rechts nach links."""
        return [i for i, k in enumerate(self.spuren[eid]) if k in ('kfz', 'bus')]

    def con(self, frm, to, fl, tl, **kw):
        a = ''.join(f' {k}="{v}"' for k, v in kw.items())
        self.cons.append(f'    <connection from="{frm}" to="{to}" fromLane="{fl}" toLane="{tl}"{a}/>')

    def verbot(self, vorrang, wartet):
        self.cons.append(f'    <prohibition prohibitor="{vorrang}" prohibited="{wartet}"/>')

    def crossing(self, node, edges, prio, width=3.0):
        self.crossings.append(f'    <crossing node="{node}" edges="{edges}" priority="{"true" if prio else "false"}" width="{width}"/>')

    def schreibe(self, prefix):
        with open(prefix + '.nod.xml', 'w') as f:
            f.write('<nodes>\n' + '\n'.join(self.nodes) + '\n</nodes>\n')
        with open(prefix + '.edg.xml', 'w') as f:
            f.write('<edges>\n' + '\n'.join(self.edges + self.roundabouts) + '\n</edges>\n')
        with open(prefix + '.con.xml', 'w') as f:
            f.write('<connections>\n' + '\n'.join(self.cons + self.crossings) + '\n</connections>\n')


def tempo_von(var, arme):
    # Umbauvarianten mit Tempo 30. Beim Minikreisel bremst real die Ablenkung, das bildet SUMO
    # nicht ab, deshalb auch dort Tempo 30 auf den Armen.
    return {a: (TEMPO_OSM[a] if var == 'bestand' else V30) for a in arme}


def suedarm_verbindungen(n, var, gesch=False):
    """Spurzuordnung am Suedarm. Ortsbeobachtung: rund ein Viertel der Geradeausfahrer nutzt die
    Linksabbiegespur. Das ist im Netz eine zusaetzliche Verbindung von der linken Spur nach Nord,
    die nur Fahrzeuge der Klasse taxi (Typ pkwx, 'Fehlspur') benutzen duerfen. Alle anderen fahren
    regelgerecht von der rechten Spur geradeaus."""
    k = n.kfz
    # Parkstreifen suedlich der Haltestelle: Bus und Rad schwenken an S70 in den Haltebereich
    n.con('S_in_fern', 'S_in_bucht', k('S_in_fern')[0], k('S_in_bucht')[0])
    n.con('S_in_fern', 'S_in_bucht', k('S_in_fern')[0], k('S_in_bucht')[1])
    n.con('S_in_bucht', 'S_in_mitte', k('S_in_bucht')[0], k('S_in_mitte')[0])
    n.con('S_in_bucht', 'S_in_mitte', k('S_in_bucht')[1], k('S_in_mitte')[0])
    n.con('S_in_bucht', 'S_in_mitte', k('S_in_bucht')[1], k('S_in_mitte')[1])
    if var == 'minikreisel':
        # der rechte Streifen endet vor der Sperrflaeche, Wechsel vorher regulaer
        n.con('S_in_mitte', 'S_in', k('S_in_mitte')[1], k('S_in')[0])
        n.con('S_in', 'S_in_m', k('S_in')[0], k('S_in_m')[0])
        return
    r, l = k('S_in')
    n.con('S_in_mitte', 'S_in', k('S_in_mitte')[0], r, **({'disallow': 'bicycle'} if gesch else {}))
    n.con('S_in_mitte', 'S_in', k('S_in_mitte')[1], r)
    n.con('S_in_mitte', 'S_in', k('S_in_mitte')[1], l)
    if gesch:
        n.con('S_in_mitte', 'aS', k('S_in_mitte')[0], 0)
    kette = ['S_in', 'S_in_f', 'S_in_m'] if gesch else ['S_in', 'S_in_m']
    for a, b in zip(kette, kette[1:]):
        n.con(a, b, k(a)[0], k(b)[0])
        n.con(a, b, k(a)[1], k(b)[1])
    m = kette[-1]
    rm, lm = k(m)
    if var == 'radwege':
        # Radfahrstreifen: Haltebereich -> Streifen -> Knoten, geradeaus und rechts vom Streifen,
        # links (nach West) wechseln Radfahrende vorher auf die Linksabbiegespur.
        rad = lambda e: n.spuren[e].index('rad')
        n.con('S_in_fern', 'S_in_bucht', rad('S_in_fern'), k('S_in_bucht')[0])
        n.con('S_in_bucht', 'S_in_mitte', k('S_in_bucht')[0], rad('S_in_mitte'), allow='bicycle')
        n.con('S_in_mitte', 'S_in', rad('S_in_mitte'), rad('S_in'))
        n.con('S_in', 'S_in_m', rad('S_in'), rad('S_in_m'))
        n.con('S_in_m', 'N_out_m', rad('S_in_m'), k('N_out_m')[0], allow='bicycle')
        n.con('S_in_m', 'E_out_m', rad('S_in_m'), k('E_out_m')[0], allow='bicycle')
    # In der geschuetzten Kreuzung nehmen Radfahrende geradeaus und rechts den Radweg, auf der
    # Fahrbahn bleibt nur das direkte Linksabbiegen nach West.
    n.con(m, 'N_out_m', rm, k('N_out_m')[0], disallow='taxi bicycle' if gesch else 'taxi')
    n.con(m, 'E_out_m', rm, k('E_out_m')[0], **({'disallow': 'bicycle'} if gesch else {}))
    n.con(m, 'W_out_m', lm, k('W_out_m')[0])
    if var != 'minikreisel':
        n.con(m, 'N_out_m', lm, k('N_out_m')[0], allow='taxi')


def vorfahrt_abknickend(n):
    # Abknickende Vorfahrt: Wer aus West geradeaus nach Ost faehrt, verlaesst die
    # Vorfahrtstrasse und wartet auf den Hauptstrom Sued nach West.
    n.verbot('S_in_m->W_out_m', 'W_in_m->E_out_m')
    # Nord und Ost sind beide wartepflichtig, untereinander gilt rechts vor links (Ost wartet auf Nord)
    n.verbot('N_in_m->E_out_m', 'E_in_m->W_out_m')
    n.verbot('N_in_m->W_out_m', 'E_in_m->W_out_m')


def baue_variante(var, arme):
    if var == 'geschuetzt':
        return baue_geschuetzt(arme)
    n = Netz()
    kreisel = var == 'minikreisel'
    tempo = tempo_von(var, arme)
    prio = {'S': 3, 'W': 3, 'N': 1, 'E': 1}
    if var in RECHTS_VOR_LINKS:
        prio = {a: 1 for a in arme}

    jtyp = None if kreisel else ('right_before_left' if var in RECHTS_VOR_LINKS else 'priority')
    if not kreisel:
        # edgePriority, damit die abknickende Vorfahrt Sued <-> West gilt
        n.node('J', (0, 0), jtyp, radius=str(KNOTEN_RADIUS), **({'rightOfWay': 'edgePriority'} if jtyp == 'priority' else {}))

    # Kreisfahrbahn: ein Knoten je Arm auf dem Radius, Reihenfolge gegen den Uhrzeigersinn
    winkel = {a: math.atan2(arme[a][1][1], arme[a][1][0]) for a in arme}
    if kreisel:
        for a in arme:
            p = (KREISEL_R * math.cos(winkel[a]), KREISEL_R * math.sin(winkel[a]))
            n.node(f'R{a}', p, 'priority', radius='1.5')
        folge = sorted(arme, key=lambda a: winkel[a])
        ring = []
        for i, a in enumerate(folge):
            b = folge[(i + 1) % len(folge)]
            w0, w1 = winkel[a], winkel[b]
            if w1 <= w0:
                w1 += 2 * math.pi
            k = 6
            shape = [(KREISEL_R * math.cos(w0 + (w1 - w0) * t / k), KREISEL_R * math.sin(w0 + (w1 - w0) * t / k)) for t in range(k + 1)]
            eid = f'ring_{a}{b}'
            n.edge(eid, f'R{a}', f'R{b}', shape, [('pedestrian', GEHWEG), ('kfz', KREISEL_B)], V20, 5)
            ring.append(eid)
        n.roundabouts.append(f'    <roundabout nodes="{" ".join("R" + a for a in folge)}" edges="{" ".join(ring)}"/>')

    for a, pts in arme.items():
        inner = f'R{a}' if kreisel else 'J'
        s_inner = KREISEL_R if kreisel else 0.0
        stationen = [MUND[a], ARM_LEN]
        if a == 'S':
            stationen = [MUND[a], S_ABBIEGER, S_BUCHT[0], S_BUCHT[1], ARM_LEN]
        if a == 'N' or (a == 'W' and var == 'radwege'):
            stationen = [MUND[a], G_INNEN, ARM_LEN]
        namen = {MUND[a]: f'M{a}', ARM_LEN: f'{a}0'}
        if a == 'W':
            namen[G_INNEN] = 'W30'
        if a == 'S':
            namen.update({S_ABBIEGER: 'S25', S_BUCHT[0]: 'S45', S_BUCHT[1]: 'S70'})
        if a == 'N':
            namen[G_INNEN] = 'N30'
        for s in stationen:
            n.node(namen[s], punkt_bei(pts, s))
        knoten = [(s_inner, inner)] + [(s, namen[s]) for s in stationen]
        teile = {'S': ['m', '', 'mitte', 'bucht', 'fern'], 'N': ['m', 'b', '']}.get(a, ['m', ''])
        if a == 'W' and var == 'radwege':
            teile = ['m', 'b', '']
        for (s0, k0), (s1, k1), teil in zip(knoten, knoten[1:], teile):
            grenze = grenzlinie(a, pts, teil)
            sh = schneide(grenze, max(s0 + (KREISEL_B if kreisel and s0 == s_inner else 0), 0.01), s1)
            suf = f'_{teil}' if teil else ''
            zu = [('pedestrian', GEHWEG)] + querschnitt(a, 'in', teil, var)
            von = [('pedestrian', GEHWEG)] + querschnitt(a, 'out', teil, var)
            n.edge(f'{a}_in{suf}', k1, k0, list(reversed(sh)), zu, tempo[a], prio[a])
            n.edge(f'{a}_out{suf}', k0, k1, sh, von, tempo[a], prio[a])

    # Querungen
    zebra = {'t30_zebra': {'N', 'W'}, 'minikreisel': set(arme)}.get(var, set())
    for a in arme:
        # Alle Querungen liegen auf einem eigenen Knoten direkt am Knotenrand. Laegen sie im
        # Hauptknoten, wuerde ein Abbieger, der fuer Fussgaenger wartet, auf der Bahn des
        # einfaedelnden Gegenverkehrs stehen (siehe README, Abschnitt Ueberlappungen).
        suf = '_b' if a == 'N' or (a == 'W' and var == 'radwege') else ''
        n.crossing(f'M{a}', f'{a}_in{suf} {a}_out{suf}', a in zebra)

    suedarm_verbindungen(n, var)
    if var in ABKNICKEND:
        vorfahrt_abknickend(n)
    return n


# ---------------------------------------------------------------- geschuetzte Kreuzung
def glatt(rahmen, knoten, schritt=0.6):
    """Polylinie entlang eines Arms aus Stuetzstellen (s, q). Zwischen den Stuetzstellen wird
    q mit einer Kosinuskurve weich uebergeblendet (Verschwenkung)."""
    pts = []
    for (s0, q0), (s1, q1) in zip(knoten, knoten[1:]):
        n = max(int(abs(s1 - s0) / schritt), 1)
        for i in range(n):
            t = i / n
            f = (1 - math.cos(math.pi * t)) / 2
            pts.append(rahmen.punkt(s0 + (s1 - s0) * t, q0 + (q1 - q0) * f))
    pts.append(rahmen.punkt(*knoten[-1]))
    return pts


def geschuetzt_geometrie(arme):
    """Lage von Ecken, Radfurten, Zebrastreifen und Radwegen der geschuetzten Kreuzung.

    Angepasst an den Platz: An der Nordost- und Nordwestecke stehen die Haeuser 1 bis 2 m hinter
    der Bordsteinkante, ein Radweg hinter einer Insel passt dort nicht. Abgesetzte Radfurten und
    Radwege gibt es deshalb nur dort, wo die Parkstreifen Platz machen: ueber den Suedarm
    (ostwaerts) und ueber den Ostarm (nordwaerts). Nord- und Westarm behalten den Radverkehr auf
    der Fahrbahn. Wird von build.py, strassenraum.py und der Schleppkurvenpruefung genutzt."""
    R = {a: Rahmen(a, arme[a]) for a in arme}
    o = G_RING
    o_s = G_RING_SUED
    ecke = {
        'SW': schnitt(R['W'].kante('in', o_s), R['S'].kante('out', o)),
        'SE': schnitt(R['S'].kante('in', o), R['E'].kante('out', o_s)),
    }
    # Furt ueber den Ostarm parallel zur Giesserstrasse, Nordende im frueheren Parkstreifen
    ecke['NE'] = schnitt(R['E'].kante('in', 1.0), (ecke['SE'], R['S'].u))
    paar = {'S': ('SW', 'SE'), 'E': ('SE', 'NE')}
    furt, d_f = {}, {}
    for a, (c1, c2) in paar.items():
        p, q = ecke[c1], ecke[c2]
        d = math.hypot(q[0] - p[0], q[1] - p[1])
        g = ((p[0], p[1]), ((q[0] - p[0]) / d, (q[1] - p[1]) / d))
        F = schnitt(g, (R[a].p0, R[a].u))
        furt[a] = F
        d_f[a] = R[a].lokal(F)[0]
    d_p = {'S': d_f['S'] + G_ZEBRA, 'E': d_f['E'] + G_ZEBRA, 'N': MUND['N'], 'W': MUND['W']}
    b_s = {'S': S_ABBIEGER, 'W': G_INNEN, 'E': G_INNEN, 'N': G_INNEN}

    def zu_ecke(a, seite, c):
        """Radweg entlang Arm a auf Seite seite von b_s bis zur Ecke c (in Richtung Knoten)."""
        r = R[a]
        s_c, q_c = r.lokal(ecke[c])
        sg = 1 if seite == 'out' else -1
        kw = kfz_breite(a, seite)
        # Am Ende steil auf die Fahrbahn, sonst laufen Radweg und Gehweg am Knoten parallel
        # nebeneinander ein und netconvert blaest den Knoten auf
        knoten = [(b_s[a], sg * (kw - 0.6)), (b_s[a] - 1.0, sg * (kw + G_RAD_OFF)),
                  (s_c + 6.0, sg * (kw + G_RAD_OFF)), (s_c, q_c)]
        return glatt(r, knoten)

    rad = {}
    rad['aW'] = ('BW', 'C_SW', zu_ecke('W', 'in', 'SW'))
    rad['aS'] = ('S25', 'C_SE', zu_ecke('S', 'in', 'SE'))
    rad['xS'] = ('C_SW', 'S25', list(reversed(zu_ecke('S', 'out', 'SW'))))
    rad['xE'] = ('C_SE', 'BE', list(reversed(zu_ecke('E', 'out', 'SE'))))
    for a, (c1, c2) in paar.items():
        rad[f'r{a}1'] = (f'C_{c1}', f'F{a}', [ecke[c1], furt[a]])
        rad[f'r{a}2'] = (f'F{a}', f'C_{c2}', [furt[a], ecke[c2]])
    # Von der Nordostecke zurueck auf die Fahrbahn des Nordarms. Fuer einen Radweg um die Ecke ist
    # kein Platz (Haus an der Ecke), die Radfahrenden fahren am Fahrbahnrand um die Ecke.
    rE, rN = R['E'], R['N']
    s_ne = rE.lokal(ecke['NE'])[0]
    kwE, kwN = kfz_breite('E', 'in'), kfz_breite('N', 'out')
    knoten_e = [rE.punkt(s_ne, rE.lokal(ecke['NE'])[1]), rE.punkt(s_ne - 2.5, -(kwE - 0.7)), rE.punkt(s_ne - 5.0, -(kwE - 0.7))]
    knoten_n = [rN.punkt(6.5, kwN - 0.8), rN.punkt(d_p['N'] - 3.0, kwN - 1.0), rN.punkt(d_p['N'] - 1.2, kwN / 2 + 0.5)]
    rad['xN'] = ('C_NE', 'MN', knoten_e + knoten_n)
    return dict(R=R, ecke=ecke, furt=furt, d_f=d_f, d_p=d_p, b_s=b_s, rad=rad, paar=paar)


def baue_geschuetzt(arme):
    """Geschuetzte Kreuzung, angepasst: Eckinseln an Suedwest-, Suedost- und Nordostecke anstelle
    der Parkstreifen, Radwege hinter den Inseln, abgesetzte Radfurten ueber Sued- und Ostarm,
    Zebrastreifen an allen Armen, Tempo 30, abknickende Vorfahrt bleibt, Stopp Nord."""
    G = geschuetzt_geometrie(arme)
    R = G['R']
    n = Netz()
    tempo = tempo_von('geschuetzt', arme)
    prio = {'S': 3, 'W': 3, 'N': 1, 'E': 1}
    n.node('J', (0, 0), 'priority', radius=str(G_RADIUS), rightOfWay='edgePriority')
    for a, pts in arme.items():
        if a == 'S':
            st = [(G['d_f'][a], 'FS', 'm'), (G['d_p'][a], 'MS', 'f'), (S_ABBIEGER, 'S25', ''),
                  (S_BUCHT[0], 'S45', 'mitte'), (S_BUCHT[1], 'S70', 'bucht'), (ARM_LEN, 'S0', 'fern')]
        elif a == 'E':
            st = [(G['d_f'][a], 'FE', 'm'), (G['d_p'][a], 'ME', 'f'), (G['b_s'][a], 'BE', 'b'),
                  (ARM_LEN, 'E0', '')]
        elif a == 'W':
            st = [(G['d_p'][a], 'MW', 'm'), (G['b_s'][a], 'BW', 'b'), (ARM_LEN, 'W0', '')]
        else:
            st = [(G['d_p'][a], 'MN', 'm'), (G['b_s'][a], 'N30', 'b'), (ARM_LEN, 'N0', '')]
        for s, nid, _ in st:
            # Feste Knotenflaechen: Radweg, Gehweg und Fahrbahn laufen hier parallel nebeneinander
            # ein, die automatische Knotenform von netconvert wuerde die Knoten aufblaehen.
            hl = {'F': 0.9, 'M': 1.6, 'B': 1.0, 'S': 1.0}.get(nid[0], 0)
            if nid in ('S0', 'E0', 'W0', 'N0', 'S45', 'S70', 'N30'):
                hl = 0
            if hl:
                r_ = R[a]
                q0 = 13.0
                rect = [r_.punkt(s - hl, -q0), r_.punkt(s + hl, -q0), r_.punkt(s + hl, q0), r_.punkt(s - hl, q0)]
                n.node(nid, punkt_bei(pts, s), shape=fmt(rect))
            else:
                n.node(nid, punkt_bei(pts, s), radius='0.5')
        knoten = [(0.0, 'J')] + [(s, nid) for s, nid, _ in st]
        for (s0, k0), (s1, k1), (_, _, teil) in zip(knoten, knoten[1:], st):
            suf = f'_{teil}' if teil else ''
            # Wo Radweg und Gehweg als eigene Kanten neben der Fahrbahn liegen, hat die Fahrbahn
            # nur Kfz-Spuren, sonst ueberlagern sich die Kanten und netconvert blaest die Knoten auf.
            innen = {'S': teil in ('m', 'f', ''), 'E': teil in ('m', 'f', 'b')}.get(a, teil in ('m', 'b'))
            qteil = 'innen' if innen else teil
            sh = schneide(grenzlinie(a, pts, 'm' if innen else teil), max(s0, 0.01), s1)
            if a in ('S', 'E'):
                geh_in = geh_out = not innen
            elif a == 'W':
                geh_in, geh_out = not innen, True        # Suedseite: Radweg und eigener Gehweg
            else:
                geh_in = geh_out = True
            zu = ([('pedestrian', GEHWEG)] if geh_in else []) + querschnitt(a, 'in', qteil, 'geschuetzt')
            von = ([('pedestrian', GEHWEG)] if geh_out else []) + querschnitt(a, 'out', qteil, 'geschuetzt')
            n.edge(f'{a}_in{suf}', k1, k0, list(reversed(sh)), zu, tempo[a], prio[a], ohne_rad=(innen and a == 'W'))
            n.edge(f'{a}_out{suf}', k0, k1, sh, von, tempo[a], prio[a])
        # Gehwege als eigene Kanten neben dem Radweg
        r = R[a]
        b_node = {'S': 'S25', 'E': 'BE', 'W': 'BW'}.get(a)
        seiten = {'S': ('out', 'in'), 'E': ('out', 'in'), 'W': ('in',)}.get(a, ())
        for seite in seiten:
            q = gehweg_q(a, seite)
            pts_g = [r.punkt(G['d_p'][a], q), r.punkt(G['b_s'][a], q)]
            n.edge(f'g{a}{seite[0]}', f'M{a}', b_node, pts_g, [('pedestrian', 2.0)], 1.5, 1)
        aussen = '' if a == 'S' else '_b'
        n.crossing(f'M{a}', f'{a}_in{aussen} {a}_out{aussen}', True)

    for eid, (frm, to, pts) in G['rad'].items():
        if eid.startswith('r'):
            pr = 6 if G_FURT_VORRANG[eid[1]] else 0
        elif eid.startswith('x'):
            pr = 0
        else:
            pr = 2
        n.edge(eid, frm, to, pts, [('rad', G_RAD_B)], 5.5, pr, spread='center')
    for c, p in G['ecke'].items():
        n.node(f'C_{c}', p, radius='1.5')

    # Fusswege um die Ecken hinter den Radwegen (Nordwestecke ueber den Knoten wie heute)
    for c, (a, sa, b, sb) in {'SW': ('W', 'in', 'S', 'out'), 'SE': ('S', 'in', 'E', 'out'),
                              'NE': ('E', 'in', 'N', 'out')}.items():
        pts = fussweg_ecke(G, c, a, sa, b, sb)
        n.edge(f'fw_{c}', f'M{a}', f'M{b}', pts, [('pedestrian', 2.0)], 1.5, 1)

    # Auf der Furt nur geradeaus weiter, kein Abbiegen auf die Fahrbahn
    for furt, strassen in (('rE1', ('E_in_m', 'E_out_f')), ('rS1', ('S_in_m', 'S_out_f'))):
        for st_ in strassen:
            n.cons.append(f'    <delete from="{furt}" to="{st_}"/>')
    suedarm_verbindungen(n, 'geschuetzt', gesch=True)
    vorfahrt_abknickend(n)
    return n


def gehweg_q(a, seite):
    """Querlage der Gehwegmitte am Knoten gegenueber der Mittellinie. Wo ein Radweg liegt,
    dahinter, sonst auf dem heutigen Gehweg."""
    rad = (a, seite) in (('S', 'out'), ('S', 'in'), ('E', 'out'), ('W', 'in'))
    park = sum(w for k, w in querschnitt(a, seite, 'm') if k == 'park')
    q = kfz_breite(a, seite) + (G_RAD_OFF + G_RAD_B / 2 + 1.2 if rad else park + GEHWEG / 2)
    return q if seite == 'out' else -q


def fussweg_ecke(G, c, a, sa, b, sb):
    """Fussweg vom Zebrastreifen an Arm a um die Ecke c zum Zebrastreifen an Arm b."""
    R = G['R']
    p0 = R[a].punkt(G['d_p'][a], gehweg_q(a, sa))
    p1 = R[b].punkt(G['d_p'][b], gehweg_q(b, sb))
    pa = R[a].kante(sa, abs(R[a].lokal(p0)[1]) - kfz_breite(a, sa))
    pb = R[b].kante(sb, abs(R[b].lokal(p1)[1]) - kfz_breite(b, sb))
    pc = schnitt(pa, pb)
    pts = []
    for i in range(13):
        t = i / 12
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * pc[0] + t * t * p1[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * pc[1] + t * t * p1[1]
        pts.append((x, y))
    return pts


# Rechtsabbieger an den engen Ecken holen weiter aus als die Standardbahn von netconvert, sonst
# streift schon ein Pkw mit dem Heck den Bordstein (werkzeuge/schleppkurve.py). k ist der Abstand
# der Bezier-Stuetzpunkte im Verhaeltnis zur Sehne.
WEITE_KURVEN = {('W_in_m', 'S_out_m'): 0.75, ('N_in_m', 'W_out_m'): 0.75}


def weite_kurven(prefix, net):
    r = ET.parse(net).getroot()
    lanes = {l.get('id'): [tuple(map(float, p.split(','))) for p in l.get('shape').split()]
             for e in r.findall('edge') for l in e.findall('lane')}
    zeilen = []
    von = {fr for fr, _ in WEITE_KURVEN}
    for c in r.findall('connection'):
        if c.get('from') not in von or c.get('to').startswith(':'):
            continue
        k = WEITE_KURVEN.get((c.get('from'), c.get('to')))
        if k is None:
            # Werden fuer eine Kante Verbindungen vorgegeben, raet netconvert dort keine weiteren.
            # Deshalb alle uebrigen Verbindungen dieser Kante unveraendert mit ausschreiben.
            extra = ''.join(f' {a}="{c.get(a)}"' for a in ('allow', 'disallow') if c.get(a))
            zeilen.append(f'    <connection from="{c.get("from")}" to="{c.get("to")}" fromLane="{c.get("fromLane")}" '
                          f'toLane="{c.get("toLane")}"{extra}/>')
            continue
        A = lanes[f"{c.get('from')}_{c.get('fromLane')}"]
        Bl = lanes[f"{c.get('to')}_{c.get('toLane')}"]
        a0, a1, b0, b1 = A[-2], A[-1], Bl[0], Bl[1]
        da, db = math.dist(a0, a1), math.dist(b0, b1)
        ua = ((a1[0] - a0[0]) / da, (a1[1] - a0[1]) / da)
        ub = ((b1[0] - b0[0]) / db, (b1[1] - b0[1]) / db)
        d = math.dist(a1, b0)
        P1 = (a1[0] + ua[0] * d * k, a1[1] + ua[1] * d * k)
        P2 = (b0[0] - ub[0] * d * k, b0[1] - ub[1] * d * k)
        pts = []
        for i in range(17):
            t = i / 16
            pts.append(((1 - t) ** 3 * a1[0] + 3 * (1 - t) ** 2 * t * P1[0] + 3 * (1 - t) * t * t * P2[0] + t ** 3 * b0[0],
                        (1 - t) ** 3 * a1[1] + 3 * (1 - t) ** 2 * t * P1[1] + 3 * (1 - t) * t * t * P2[1] + t ** 3 * b0[1]))
        zeilen.append(f'    <connection from="{c.get("from")}" to="{c.get("to")}" fromLane="{c.get("fromLane")}" '
                      f'toLane="{c.get("toLane")}" shape="{fmt(pts)}"/>')
    if not zeilen:
        return
    con = open(prefix + '.con.xml').read().replace('</connections>', '\n'.join(zeilen) + '\n</connections>')
    with open(prefix + '.con.xml', 'w') as f:
        f.write(con)
    netconvert(prefix, net)


def netconvert(prefix, net):
    cmd = ['netconvert', '-n', prefix + '.nod.xml', '-e', prefix + '.edg.xml', '-x', prefix + '.con.xml',
           '-o', net, '--no-turnarounds', 'true', '--tls.guess', 'false', '--walkingareas', 'true',
           '--junctions.corner-detail', '6', '--internal-junctions.vehicle-width', '3.2', '--no-warnings', 'false',
           '--offset.disable-normalization', 'true']
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        sys.exit(f'netconvert fehlgeschlagen fuer {net}')
    warn = [l for l in r.stderr.splitlines() if 'Warning' in l]
    for l in warn:
        print('   ', l)


# ---------------------------------------------------------------- Nachfrage
# Spitzenstunde aus dem Browsermodell (modell/src/sim.js, DEMAND), Fahrzeuge je Stunde.
# Zufluss Nord nach Ortsbeobachtung erhoeht (am Stoppschild warten haeufig 1 bis 3 Fahrzeuge).
# Gewuenscht waren rund 300 Kfz je Stunde (60 % Sued, 35 % West, 5 % Ost). Damit ist der Nordarm
# im Modell ueberlastet (Zeitverlust 80 bis 290 s, Schlange waechst). Gewaehlt sind 224 Kfz je
# Stunde in derselben Aufteilung: die Haelfte der Zeit wartet mindestens ein Fahrzeug, ein Viertel
# der Zeit zwei oder mehr, stabil (Schaetzung, siehe README).
KFZ = {'SW': 260, 'WS': 240, 'SN': 110, 'NS': 130, 'NW': 78, 'WN': 60, 'NE': 10,
       'SE': 20, 'WE': 20, 'EW': 22, 'ES': 10, 'EN': 12}
LKW = {'SW': 8, 'WS': 8, 'NS': 4, 'SN': 3, 'NW': 2, 'WN': 2}
SATTEL = {'SW': 3, 'WS': 3}
RAD = {'SW': 45, 'WS': 45, 'SN': 25, 'NS': 30, 'WN': 22, 'NW': 15, 'EW': 8, 'WE': 8}
BUS_TAKT = 6   # je Richtung und Stunde, Annahme 10-Minuten-Takt (Linien 60 und 60E)
# Anteil der Geradeausfahrer Sued nach Nord, die die Linksabbiegespur nutzen (Ortsbeobachtung
# Bestand etwa 25 %). Mit Tempo 30 und klarer Fuehrung weniger, mit Inseln kaum noch, im Kreisel nicht moeglich.
# Variante markierung und radwege: durchgezogene Fahrstreifenbegrenzung (Zeichen 295) zwischen
# Links- und Geradeausspur auf den letzten 25 m und klarer Bogen der Vorfahrt. Geradeaus aus der
# Linksabbiegespur heisst dann eine durchgezogene Linie ueberfahren, Annahme 8 %.
FEHLSPUR = {'bestand': 0.25, 'rvl': 0.15, 't30_zebra': 0.15, 'geschuetzt': 0.05, 'minikreisel': 0.0,
            'markierung': 0.08, 'radwege': 0.08, 'zone': 0.15}

# Fussgaenger je Stunde, Schaetzung nach Beobachtung des Nutzers (Oktober 2026).
# Die Nordquerung ueber die Giesserstrasse Nord ist die meistgenutzte (etwa 100 je Stunde),
# West etwa 50, Sued und Ost je etwa 30. Der Strom zum Kiosk an der Suedwestecke kommt von der
# Ostseite der Giesserstrasse Nord. 80 % queren erst den Nordarm und dann den Westarm, 20 % gehen
# diagonal ueber den Knoten (diagonal.py, nicht in SUMO, siehe README).
# Jeder Eintrag ist (id, Personen je Stunde, Etappen), eine Etappe ist (von, Pos, nach, Pos).
FUSS = [
    ('pNw2e', 25, [('W_out', 40, 'E_in', -40)]),
    ('pNe2w', 25, [('E_in', -40, 'W_out', 40)]),
    ('pKiosk', 22, [('N_out', 60, 'W_out', 3), ('W_out', 3, 'W_in', -3)]),
    ('pKioskBack', 18, [('W_in', -3, 'W_out', 3), ('W_out', 3, 'N_out', 60)]),
    ('pSued', 30, [('S_in', -1, 'S_out', 1)]),
    ('pEastN', 15, [('S_in_fern', -10, 'N_out', 60)]),
    ('pEastS', 15, [('N_out', 60, 'S_in_fern', -10)]),
]
DIAGONAL = 10    # Personen je Stunde diagonal NO <-> SW (5 je Richtung), Schaetzung
FUSS_SUMME = {'N': 100, 'W': 50, 'S': 30, 'E': 30}   # Zielwerte, siehe README
# In der geschuetzten Kreuzung liegen Gehwege erst hinter den Radfurten
FUSS_GESCH = {('W_out', 3): ('W_out_b', 1), ('W_in', -3): ('gWi', 1), ('S_in', -1): ('gSi', 1),
              ('S_out', 1): ('gSo', 1)}

# impatience 0.5: Wartepflichtige akzeptieren nach laengerem Warten kleinere Luecken.
IMPATIENCE = 0.5

VTYPES = '''    <vType id="pkw" impatience="{imp}" vClass="passenger" length="4.5" width="1.85" accel="2.6" decel="4.5" sigma="0.5" speedFactor="normc(1,0.1,0.8,1.3)"/>
    <vType id="pkwx" impatience="{imp}" vClass="taxi" length="4.5" width="1.85" accel="2.6" decel="4.5" sigma="0.5" speedFactor="normc(1,0.1,0.8,1.3)"/>
    <vType id="lkw" impatience="{imp}" vClass="truck" length="10.0" width="2.5" accel="1.3" decel="4.0" sigma="0.5" maxSpeed="12.5" speedFactor="normc(1,0.05,0.8,1.1)"/>
    <vType id="sattel" impatience="{imp}" vClass="truck" length="16.5" width="2.55" accel="1.0" decel="4.0" sigma="0.5" maxSpeed="11.7" guiShape="truck/semitrailer"/>
    <vType id="bus" impatience="{imp}" vClass="bus" length="18.0" width="2.55" accel="1.1" decel="4.0" sigma="0.3" maxSpeed="11.1" guiShape="bus/flexible" personCapacity="100"/>
    <vType id="rad" impatience="{imp}" vClass="bicycle" length="1.8" width="0.8" accel="1.0" decel="3.0" sigma="0.5" maxSpeed="6.5" speedFactor="normc(0.85,0.15,0.5,1.2)"/>
    <vType id="fuss" vClass="pedestrian" width="0.6" length="0.3" speedFactor="normc(1,0.15,0.6,1.4)" jmDriveAfterRedTime="-1"/>'''

KANTE = {'S': ('S_in_fern', 'S_out_fern'), 'N': ('N_in', 'N_out'), 'W': ('W_in', 'W_out'), 'E': ('E_in', 'E_out')}


def stopp_kante(var):
    """Stoppschild Nord. Haltlinie im Bestand noerdlich der Querung (Ortsbeobachtung: Fussgaenger
    queren zwischen Haltlinie und Knoten), in der geschuetzten Kreuzung vor Zebrastreifen und Radfurt
    (zwischen Furt und Knoten ist kein Platz fuer eine eigene Haltlinie)."""
    if var in ABKNICKEND:
        return 'N_in_b'
    if var == 'geschuetzt':
        return 'N_in_b'
    return None


def nachfrage(var, bus, ende):
    stopp = stopp_kante(var)
    z = ['<routes>', VTYPES.replace('{imp}', str(IMPATIENCE))]
    flows = []

    def flow(fid, typ, rel, q):
        if q <= 0:
            return
        o, d = rel[0], rel[1]
        stop = ''
        if stopp and o == 'N' and not (var == 'geschuetzt' and typ == 'rad'):
            stop = f'\n        <stop edge="{stopp}" endPos="-0.5" duration="1"/>'
        flows.append((0, f'    <flow id="{fid}" type="{typ}" begin="0" end="{ende}" period="exp({q / 3600:.6f})" '
                         f'from="{KANTE[o][0]}" to="{KANTE[d][1]}" departLane="best" departSpeed="max">{stop}\n    </flow>'))

    for rel, q in KFZ.items():
        if rel == 'SN':
            fx = FEHLSPUR[var]
            flow('pkw_SN', 'pkw', rel, q * (1 - fx))
            flow('pkw_SNx', 'pkwx', rel, q * fx)
        else:
            flow(f'pkw_{rel}', 'pkw', rel, q)
    for rel, q in LKW.items():
        flow(f'lkw_{rel}', 'lkw', rel, q)
    for rel, q in SATTEL.items():
        flow(f'sattel_{rel}', 'sattel', rel, q)
    for rel, q in RAD.items():
        flow(f'rad_{rel}', 'rad', rel, q)
    halt = '\n        <stop busStop="hst_naumburger" duration="20"/>'

    def busflow(fid, rel, beginn, extra=''):
        # Busse fahren nach Takt. Die Startzeiten liegen so, dass im Abspieler (Minute 10 bis 15)
        # beide Richtungen vorkommen.
        o, d = rel[0], rel[1]
        flows.append((beginn, f'    <flow id="{fid}" type="bus" begin="{beginn}" end="{ende}" period="{3600 // BUS_TAKT}" '
                              f'from="{KANTE[o][0]}" to="{KANTE[d][1]}" departLane="best" departSpeed="max">{extra}\n    </flow>'))
    if bus == 'SN':
        busflow('bus_SN', 'SN', 60, halt)
        busflow('bus_NS', 'NS', 120, stopp and f'\n        <stop edge="{stopp}" endPos="-0.5" duration="1"/>' or '')
    else:
        # Beide Richtungen Sued <-> West. Die Haltestelle der Gegenrichtung liegt nicht im
        # OSM-Ausschnitt (dort nur Bussteig 0505 an der Ostseite), Busse West nach Sued halten hier nicht.
        busflow('bus_SW', 'SW', 60, halt)
        busflow('bus_WS', 'WS', 120)
    for pid, q, etappen in FUSS:
        if var == 'radwege':
            # Westarm ist hier in zwei Kanten geteilt (Radfahrstreifen auf den letzten 30 m)
            m_ = {('W_out', 3): ('W_out_b', 1), ('W_in', -3): ('W_in_b', -1), ('W_out', 40): ('W_out', 25)}
            etappen = [(*m_.get((v, p), (v, p)), *m_.get((n_, np_), (n_, np_))) for v, p, n_, np_ in etappen]
        if var == 'geschuetzt':
            etappen = [(*FUSS_GESCH.get((v, p), (v, p)), *FUSS_GESCH.get((n_, np_), (n_, np_))) for v, p, n_, np_ in etappen]
        walks = ''.join(f'\n        <walk from="{von}" to="{nach}" arrivalPos="{np_}"/>' for von, _, nach, np_ in etappen)
        flows.append((0, f'    <personFlow id="{pid}" type="fuss" begin="0" end="{ende}" period="exp({q / 3600:.6f})" '
                         f'departPos="{etappen[0][1]}">{walks}\n    </personFlow>'))
    z += [f for _, f in sorted(flows, key=lambda x: x[0])]
    z.append('</routes>')
    return '\n'.join(z) + '\n'


HALTESTELLE = '''<additional>
    <!-- Haltestelle Naumburger Strasse (LVB ref 0505), Halt auf dem rechten Streifen der Fahrbahn am Suedarm Richtung Norden -->
    <busStop id="hst_naumburger" name="Naumburger Straße" lane="S_in_bucht_1" startPos="2" endPos="-2"/>
</additional>
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--bus', choices=['SW', 'SN'], default='SW', help='Busroute, SW Regelbetrieb Sued <-> West (Standard), SN Baustellenumleitung')
    ap.add_argument('--ende', type=int, default=4200, help='Ende der Nachfrage in s (600 Einschwingen plus 3600)')
    ap.add_argument('--alt', action='store_true', help='auch die verworfenen Varianten bauen')
    args = ap.parse_args()

    arme = achsen()
    os.makedirs(OUT, exist_ok=True)
    if os.path.isdir(PLAIN):
        shutil.rmtree(PLAIN)
    os.makedirs(PLAIN)
    for var in (VARIANTEN if args.alt else VERGLEICH):
        print(f'Variante {var}')
        n = baue_variante(var, arme)
        prefix = os.path.join(PLAIN, var)
        n.schreibe(prefix)
        netconvert(prefix, os.path.join(OUT, f'{var}.net.xml'))
        if var not in ('geschuetzt', 'minikreisel'):
            weite_kurven(prefix, os.path.join(OUT, f'{var}.net.xml'))
        with open(os.path.join(OUT, f'{var}.rou.xml'), 'w') as f:
            f.write(nachfrage(var, args.bus, args.ende))
    with open(os.path.join(OUT, 'haltestelle.add.xml'), 'w') as f:
        f.write(HALTESTELLE)
    with open(os.path.join(OUT, 'bus.txt'), 'w') as f:
        f.write(args.bus + '\n')
    print('fertig, Busroute', args.bus)


if __name__ == '__main__':
    main()
