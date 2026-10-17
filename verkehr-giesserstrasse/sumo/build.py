#!/usr/bin/env python3
"""Baut die SUMO-Netze und die Nachfrage aller Varianten.

Aufruf
    python3 build.py              # Busse im Regelbetrieb Sued <-> West
    python3 build.py --bus SN     # Baustellenumleitung geradeaus Sued <-> Nord (Stand OSM Oktober 2026)

Ergebnis liegt in netze/<variante>.net.xml, netze/<variante>.rou.xml und
netze/haltestelle.add.xml. Die Geometrie der vier Arme kommt aus
../daten/map.osm, alles andere (Spuren, Vorfahrt, Querungen, Nachfrage)
ist unten in den Konstanten beschrieben.
"""
import argparse
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

VARIANTEN = ['bestand', 'rvl', 'minikreisel', 't30_zebra']

J_OSM = '60015219'          # Knoten Giesserstrasse / Naumburger Strasse
ARM_LEN = 120.0             # Laenge jedes Arms in Metern
# Abstand Knotenmitte bis Querungsknoten (Fussgaengerquerung, Zebra), je Arm so, dass zwischen
# Knoten und Querung rund 3 m Platz bleiben
MUND = {'N': 15.0, 'S': 16.0, 'W': 18.0, 'E': 17.0}
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

# Tempo laut OSM. Ost hat kein Schild, also innerorts 50 (Annahme).
TEMPO_OSM = {'S': V50, 'N': V50, 'W': V30, 'E': V50}

# Querschnitte je Arm, konstant ueber die ganze Laenge (Abgleich mit OSM width und Luftbild
# Geoportal Leipzig, Massstab 20 m). Jede Liste geht von rechts nach links in Fahrtrichtung,
# ohne Gehweg. 'kfz' Fahrspur, 'park' Parkstreifen (keine Fahrten), 'bus' Haltestellenstreifen
# (nur Bus und Rad), 'sperr' Sperrflaeche (nur Minikreisel).
#   Gießerstraße Süd 13,0 m: West Parken 2,2 + südwärts 3,6 | nordwärts 3,6 + Haltestellenstreifen
#                            bzw. Rechtsspur 3,6. Vor dem Knoten Linksabbieger und geradeaus/rechts.
#   Gießerstraße Nord 8,2 m: je Richtung 4,1, kein Parkstreifen.
#   Naumburger West 9,5 m:   Südseite Parken 2,0 + ostwärts 3,75 | westwärts 3,75.
#   Naumburger Ost 9,5 m:    beidseitig Parken 2,0 + je Richtung 2,75.
GEHWEG = 2.5
QUERSCHNITT = {
    # (Arm, Richtung): {Abschnitt: Spuren}, Abschnitt '*' gilt fuer alle uebrigen
    ('S', 'out'): {'*': [('park', 2.2), ('kfz', 3.6)]},
    ('S', 'in'): {'m': [('kfz', 3.6), ('kfz', 3.6)], '': [('kfz', 3.6), ('kfz', 3.6)],
                  '*': [('bus', 3.6), ('kfz', 3.6)]},
    ('N', 'out'): {'*': [('kfz', 4.1)]},
    ('N', 'in'): {'*': [('kfz', 4.1)]},
    ('W', 'out'): {'*': [('kfz', 3.75)]},
    ('W', 'in'): {'*': [('park', 2.0), ('kfz', 3.75)]},
    ('E', 'out'): {'*': [('park', 2.0), ('kfz', 2.75)]},
    ('E', 'in'): {'*': [('park', 2.0), ('kfz', 2.75)]},
}
# Eckausbildung der Bordsteine (Beobachtung Luftbild): Nordecken ein Radius, Suedecken
# abgeschraegt mit zwei kleinen Radien. Wird von der Darstellung genutzt (abspieler/export.py).
ECKEN = {'NE': ('rund', 5.0), 'WN': ('rund', 5.0), 'ES': ('schraeg', 3.5, 1.2), 'SW': ('schraeg', 3.5, 1.2)}
KNOTEN_RADIUS = 3.0


def querschnitt(a, richtung, teil, kreisel=False):
    q = QUERSCHNITT[(a, richtung)]
    spuren = list(q.get(teil, q['*']))
    if kreisel and a == 'S' and richtung == 'in' and teil in ('m', ''):
        # Minikreisel: nur eine Zufahrtspur, rechts Sperrflaeche
        spuren = [('sperr', 3.6), ('kfz', 3.6)]
    return spuren


def breite(a, richtung):
    return sum(w for _, w in querschnitt(a, richtung, 'fern' if a == 'S' else ''))


# Abschnitte am Suedarm (Abstand zur Knotenmitte). Haltestelle laut OSM ref 0505 etwa
# 45 bis 70 m suedlich auf dem rechten Streifen der Fahrbahn (keine Bucht), davor die
# Grenzmarkierung. Linksabbiegestreifen auf den letzten 25 m.
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
    """Folgt der Strasse ab dem Knoten und gibt eine Polylinie bis ARM_LEN zurueck."""
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
    # zu kurz (Suedarm endet am Rand des OSM-Ausschnitts): gerade verlaengern
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


def grenzlinie(a, achse):
    """Mittelmarkierung zwischen Hin- und Rueckrichtung. Sie liegt so, dass die Fahrbahn
    symmetrisch um die OSM-Achse liegt (beim Suedarm 0,7 m westlich der Achse)."""
    (x0, y0), (x1, y1) = achse
    d = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / d, (y1 - y0) / d
    rx, ry = uy, -ux                     # rechts der Richtung nach aussen
    k = (breite(a, 'in') - breite(a, 'out')) / 2
    return [(x0 + rx * k, y0 + ry * k), (x1 + rx * k, y1 + ry * k)]


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


def fmt(pts):
    return ' '.join(f'{x:.2f},{y:.2f}' for x, y in pts)


# ---------------------------------------------------------------- Netz
class Netz:
    def __init__(self):
        self.nodes, self.edges, self.cons, self.crossings, self.roundabouts = [], [], [], [], []

    def node(self, nid, p, typ='priority', **kw):
        a = ' '.join(f'{k}="{v}"' for k, v in kw.items())
        self.nodes.append(f'    <node id="{nid}" x="{p[0]:.2f}" y="{p[1]:.2f}" type="{typ}" {a}/>')

    def edge(self, eid, frm, to, shape, lanes, speed, prio):
        """lanes ist eine Liste von (allow, breite) von rechts nach links, Gehweg zuerst."""
        s = [f'    <edge id="{eid}" from="{frm}" to="{to}" priority="{prio}" numLanes="{len(lanes)}" '
             f'speed="{speed}" shape="{fmt(shape)}">']
        erlaubt = {'park': 'custom1', 'sperr': 'custom2', 'bus': 'bus bicycle', 'pedestrian': 'pedestrian'}
        for i, (allow, w) in enumerate(lanes):
            if allow == 'kfz':
                s.append(f'        <lane index="{i}" disallow="pedestrian custom1 custom2" width="{w}"/>')
            else:
                s.append(f'        <lane index="{i}" allow="{erlaubt[allow]}" width="{w}"/>')
        s.append('    </edge>')
        self.edges.append('\n'.join(s))

    def con(self, frm, to, fl, tl):
        self.cons.append(f'    <connection from="{frm}" to="{to}" fromLane="{fl}" toLane="{tl}"/>')

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


def baue_variante(var, arme):
    n = Netz()
    kreisel = var == 'minikreisel'
    # Umbauvarianten mit Tempo 30. Beim Minikreisel bremst real die Ablenkung, das bildet SUMO
    # nicht ab, deshalb auch dort Tempo 30 auf den Armen.
    tempo = {a: (V30 if var in ('rvl', 't30_zebra', 'minikreisel') else TEMPO_OSM[a]) for a in arme}
    prio = {'S': 3, 'W': 3, 'N': 1, 'E': 1}
    if var == 'rvl':
        prio = {a: 1 for a in arme}

    jtyp = {'bestand': 'priority', 't30_zebra': 'priority', 'rvl': 'right_before_left'}.get(var)
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
        # Knoten entlang des Arms
        stationen = [MUND[a], ARM_LEN]
        if a == 'S':
            stationen = [MUND[a], S_ABBIEGER, S_BUCHT[0], S_BUCHT[1], ARM_LEN]
        namen = {MUND[a]: f'M{a}', ARM_LEN: f'{a}0'}
        if a == 'S':
            namen.update({S_ABBIEGER: 'S25', S_BUCHT[0]: 'S45', S_BUCHT[1]: 'S70'})
        for s in stationen:
            n.node(namen[s], punkt_bei(pts, s))
        knoten = [(s_inner, inner)] + [(s, namen[s]) for s in stationen]
        # Edge-Namen je Abschnitt (innen nach aussen)
        teile = ['m', ''] if a != 'S' else ['m', '', 'mitte', 'bucht', 'fern']
        grenze = grenzlinie(a, pts)
        for (s0, k0), (s1, k1), teil in zip(knoten, knoten[1:], teile):
            # Im Kreisel beginnt die Zufahrt gerade am Aussenrand der Kreisfahrbahn. Ein Knick zum
            # Ringknoten wuerde die Form des Querungsknotens verzerren.
            sh = schneide(grenze, max(s0 + (KREISEL_B if kreisel and s0 == s_inner else 0), 0.01), s1)
            suf = f'_{teil}' if teil else ''
            zu = [('pedestrian', GEHWEG)] + querschnitt(a, 'in', teil, kreisel)      # zum Knoten
            von = [('pedestrian', GEHWEG)] + querschnitt(a, 'out', teil, kreisel)    # vom Knoten weg
            n.edge(f'{a}_in{suf}', k1, k0, list(reversed(sh)), zu, tempo[a], prio[a])
            n.edge(f'{a}_out{suf}', k0, k1, sh, von, tempo[a], prio[a])

    # Querungen
    zebra = {'bestand': set(), 'rvl': set(), 't30_zebra': {'N', 'W'}, 'minikreisel': set(arme)}[var]
    for a in arme:
        # Alle Querungen liegen auf einem eigenen Knoten direkt am Knotenrand. Laegen sie im
        # Hauptknoten, wuerde ein Abbieger, der fuer Fussgaenger wartet, auf der Bahn des
        # einfaedelnden Gegenverkehrs stehen. SUMO erkennt ihn dort nicht als Vordermann und
        # meldet Zusammenstoesse (siehe README, Abschnitt Ueberlappungen).
        n.crossing(f'M{a}', f'{a}_in {a}_out', a in zebra)

    # Spurzuordnung Suedarm vor dem Knoten (nur ohne Kreisel)
    if not kreisel:
        n.con('S_in', 'S_in_m', 1, 1)
        n.con('S_in', 'S_in_m', 2, 2)
        n.con('S_in_m', 'N_out_m', 1, 1)
        n.con('S_in_m', 'E_out_m', 1, 2)   # Ost hat Parkstreifen auf Spur 1
        n.con('S_in_m', 'W_out_m', 2, 1)
        n.con('S_in_mitte', 'S_in', 1, 1)    # Haltestellenstreifen (Bus, Rad) wird zur Rechtsspur
        n.con('S_in_mitte', 'S_in', 2, 1)
        n.con('S_in_mitte', 'S_in', 2, 2)
    else:
        # Kreisel: der Haltestellenstreifen endet vor der Sperrflaeche. Bus und Rad wechseln vorher
        # regulaer auf die Fahrspur. Ein Einfaedeln im Knoten S25 wuerde Wartende quer auf die
        # Fahrspur stellen.
        n.con('S_in_mitte', 'S_in', 2, 2)
        n.con('S_in', 'S_in_m', 2, 2)
    if var in ('bestand', 't30_zebra'):
        # Abknickende Vorfahrt: Wer aus West geradeaus nach Ost faehrt, verlaesst die
        # Vorfahrtstrasse und wartet auf den Hauptstrom Sued nach West.
        n.verbot('S_in_m->W_out_m', 'W_in_m->E_out_m')
        # Nord und Ost sind beide wartepflichtig, untereinander gilt rechts vor links (Ost wartet auf Nord)
        n.verbot('N_in_m->E_out_m', 'E_in_m->W_out_m')
        n.verbot('N_in_m->W_out_m', 'E_in_m->W_out_m')
    return n


def netconvert(prefix, net):
    cmd = ['netconvert', '-n', prefix + '.nod.xml', '-e', prefix + '.edg.xml', '-x', prefix + '.con.xml',
           '-o', net, '--no-turnarounds', 'true', '--tls.guess', 'false', '--walkingareas', 'true',
           '--junctions.corner-detail', '6', '--internal-junctions.vehicle-width', '3.2', '--no-warnings', 'false', '--offset.disable-normalization', 'true']
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        sys.exit(f'netconvert fehlgeschlagen fuer {net}')
    warn = [l for l in r.stderr.splitlines() if 'Warning' in l]
    for l in warn:
        print('   ', l)


# ---------------------------------------------------------------- Nachfrage
# Spitzenstunde aus dem Browsermodell (modell/src/sim.js, DEMAND), Fahrzeuge je Stunde
KFZ = {'SW': 260, 'WS': 240, 'SN': 110, 'NS': 120, 'NW': 55, 'WN': 60, 'NE': 12,
       'SE': 20, 'WE': 20, 'EW': 22, 'ES': 10, 'EN': 12}
LKW = {'SW': 8, 'WS': 8, 'NS': 4, 'SN': 3, 'NW': 2, 'WN': 2}
SATTEL = {'SW': 3, 'WS': 3}
RAD = {'SW': 45, 'WS': 45, 'SN': 25, 'NS': 30, 'WN': 22, 'NW': 15, 'EW': 8, 'WE': 8}
BUS_TAKT = 6   # je Richtung und Stunde, Annahme 10-Minuten-Takt (Linien 60 und 60E)

# Fussgaenger je Stunde, Schaetzung nach Beobachtung des Nutzers (Oktober 2026).
# Die Nordquerung ueber die Giesserstrasse Nord ist die meistgenutzte (etwa 100 je Stunde),
# West etwa 50, Sued und Ost je etwa 30. Der Strom zum Kiosk an der Suedwestecke kommt von der
# Ostseite der Giesserstrasse Nord, quert erst den Nordarm und dann den Westarm.
# Jeder Eintrag ist (id, Personen je Stunde, Etappen), eine Etappe ist (von, Pos, nach, Pos).
# Gehweg rechts der Fahrtrichtung, also z.B. N_in = Westseite Nordarm, W_out = Nordseite Westarm.
FUSS = [
    ('pNw2e', 25, [('W_out', 40, 'E_in', -40)]),                      # Nordseite West nach Ost, quert Nordarm
    ('pNe2w', 25, [('E_in', -40, 'W_out', 40)]),                      # Nordseite Ost nach West, quert Nordarm
    ('pKiosk', 28, [('N_out', 60, 'W_out', 3), ('W_out', 3, 'W_in', -3)]),       # Nordost zum Kiosk, quert Nord und West
    ('pKioskBack', 22, [('W_in', -3, 'W_out', 3), ('W_out', 3, 'N_out', 60)]),   # zurueck, quert West und Nord
    ('pSued', 30, [('S_in_m', 2, 'S_out_m', 2)]),                     # quert Suedarm am Knoten (beide Richtungen gemischt)
    ('pEastN', 15, [('S_in_fern', -10, 'N_out', 60)]),                # Ostseite Sued nach Nord, quert Ostarm
    ('pEastS', 15, [('N_out', 60, 'S_in_fern', -10)]),
]
FUSS_SUMME = {'N': 100, 'W': 50, 'S': 30, 'E': 30}   # Zielwerte, siehe README

# impatience 0.5: Wartepflichtige akzeptieren nach laengerem Warten kleinere Luecken.
# Ohne diesen Wert ueberschaetzt SUMO die Wartezeiten am Nordarm stark (siehe README).
IMPATIENCE = 0.5

VTYPES = '''    <vType id="pkw" impatience="{imp}" vClass="passenger" length="4.5" width="1.85" accel="2.6" decel="4.5" sigma="0.5" speedFactor="normc(1,0.1,0.8,1.3)"/>
    <vType id="lkw" impatience="{imp}" vClass="truck" length="10.0" width="2.5" accel="1.3" decel="4.0" sigma="0.5" maxSpeed="12.5" speedFactor="normc(1,0.05,0.8,1.1)"/>
    <vType id="sattel" impatience="{imp}" vClass="truck" length="16.5" width="2.55" accel="1.0" decel="4.0" sigma="0.5" maxSpeed="11.7" guiShape="truck/semitrailer"/>
    <vType id="bus" impatience="{imp}" vClass="bus" length="18.0" width="2.55" accel="1.1" decel="4.0" sigma="0.3" maxSpeed="11.1" guiShape="bus/flexible" personCapacity="100"/>
    <vType id="rad" impatience="{imp}" vClass="bicycle" length="1.8" width="0.8" accel="1.0" decel="3.0" sigma="0.5" maxSpeed="6.5" speedFactor="normc(0.85,0.15,0.5,1.2)"/>
    <vType id="fuss" vClass="pedestrian" width="0.6" length="0.3" speedFactor="normc(1,0.15,0.6,1.4)" jmDriveAfterRedTime="-1"/>'''

KANTE = {'S': ('S_in_fern', 'S_out_fern'), 'N': ('N_in', 'N_out'), 'W': ('W_in', 'W_out'), 'E': ('E_in', 'E_out')}


def nachfrage(var, bus, ende):
    stopp_nord = var in ('bestand', 't30_zebra')   # Stoppschild am Nordarm
    z = ['<routes>', VTYPES.replace('{imp}', str(IMPATIENCE))]
    flows = []

    def flow(fid, typ, rel, q, extra=''):
        if q <= 0:
            return
        o, d = rel[0], rel[1]
        stop = ''
        if stopp_nord and o == 'N':
            stop = '\n        <stop edge="N_in_m" endPos="-0.5" duration="1"/>'
        if extra:
            stop += extra
        flows.append((0, f'    <flow id="{fid}" type="{typ}" begin="0" end="{ende}" period="exp({q / 3600:.6f})" '
                           f'from="{KANTE[o][0]}" to="{KANTE[d][1]}" departLane="best" departSpeed="max">{stop}\n    </flow>'))

    for rel, q in KFZ.items():
        flow(f'pkw_{rel}', 'pkw', rel, q)
    for rel, q in LKW.items():
        flow(f'lkw_{rel}', 'lkw', rel, q)
    for rel, q in SATTEL.items():
        flow(f'sattel_{rel}', 'sattel', rel, q)
    for rel, q in RAD.items():
        flow(f'rad_{rel}', 'rad', rel, q)
    halt = '\n        <stop busStop="hst_naumburger" duration="20"/>'

    def busflow(fid, rel, beginn, extra=''):
        # Busse fahren nach Takt, nicht zufaellig
        o, d = rel[0], rel[1]
        flows.append((beginn, f'    <flow id="{fid}" type="bus" begin="{beginn}" end="{ende}" period="{3600 // BUS_TAKT}" '
                           f'from="{KANTE[o][0]}" to="{KANTE[d][1]}" departLane="best" departSpeed="max">{extra}\n    </flow>'))
    if bus == 'SN':
        busflow('bus_SN', 'SN', 60, halt)
        busflow('bus_NS', 'NS', 360, stopp_nord and '\n        <stop edge="N_in_m" endPos="-0.5" duration="1"/>' or '')
    else:
        busflow('bus_SW', 'SW', 60, halt)
        busflow('bus_WS', 'WS', 360)
    for pid, q, etappen in FUSS:
        walks = ''.join(f'\n        <walk from="{von}" to="{nach}" arrivalPos="{np_}"/>' for von, _, nach, np_ in etappen)
        flows.append((0, f'    <personFlow id="{pid}" type="fuss" begin="0" end="{ende}" period="exp({q / 3600:.6f})" '
                         f'departPos="{etappen[0][1]}">{walks}\n    </personFlow>'))
    # SUMO verlangt Sortierung nach Startzeit
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
    ap.add_argument('--bus', choices=['SW', 'SN'], default='SW', help='Busroute, SW Regelbetrieb (Standard), SN Baustellenumleitung wie derzeit in OSM')
    ap.add_argument('--ende', type=int, default=4200, help='Ende der Nachfrage in s (600 Einschwingen plus 3600)')
    args = ap.parse_args()

    xy, nachbarn, _ = lade_osm()
    arme = {a: arm_polylinie(xy, nachbarn, name, ri) for a, (name, ri) in ARME.items()}
    os.makedirs(OUT, exist_ok=True)
    if os.path.isdir(PLAIN):
        shutil.rmtree(PLAIN)
    os.makedirs(PLAIN)
    for var in VARIANTEN:
        print(f'Variante {var}')
        n = baue_variante(var, arme)
        prefix = os.path.join(PLAIN, var)
        n.schreibe(prefix)
        netconvert(prefix, os.path.join(OUT, f'{var}.net.xml'))
        with open(os.path.join(OUT, f'{var}.rou.xml'), 'w') as f:
            f.write(nachfrage(var, args.bus, args.ende))
    with open(os.path.join(OUT, 'haltestelle.add.xml'), 'w') as f:
        f.write(HALTESTELLE)
    with open(os.path.join(OUT, 'bus.txt'), 'w') as f:
        f.write(args.bus + '\n')
    print('fertig, Busroute', args.bus)


if __name__ == '__main__':
    main()
