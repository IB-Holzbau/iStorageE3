#!/usr/bin/env python3
"""Simuliert alle Varianten mehrfach und wertet sie aus.

Aufruf
    python3 run.py                 # 10 Laeufe je Variante
    python3 run.py --laeufe 3      # schneller Probelauf
    python3 run.py --varianten bestand minikreisel

Vorher einmal python3 build.py ausfuehren. Ergebnisse
    ergebnisse/kennzahlen.csv   alle Werte je Lauf (Langformat)
    ergebnisse/vergleich.md     Mittelwert und Streuung je Variante
Die Rohdaten der Laeufe (fcd, ssm, tripinfo) liegen in ergebnisse/roh und
werden nicht eingecheckt.
"""
import argparse
import csv
import math
import os
import re
import statistics as st
import subprocess
import sys
import random
import xml.etree.ElementTree as ET
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

from shapely.geometry import LineString, Point, Polygon
from shapely.prepared import prep

import build as B
import diagonal as DG
import kinematik as K
import strassenraum as SR

ROOT = os.path.dirname(os.path.abspath(__file__))
NETZE = B.OUT
# Schneller Probemodus (--schnell): 3 Laeufe, 20 Minuten nach 5 Minuten Einschwingen, 1 s
# Schrittweite, Ergebnis in ergebnisse/schnell. Zaehlwerte werden auf eine Stunde hochgerechnet.
SCHNELL = os.environ.get('SUMO_SCHNELL') == '1'
ERG = os.environ.get('SUMO_ERG', os.path.join(ROOT, 'ergebnisse', 'schnell') if SCHNELL else os.path.join(ROOT, 'ergebnisse'))
ROH = os.path.join(ERG, 'roh')

VARIANTEN = list(B.AKTIV)   # vorübergehend nur Bestand, siehe build.py
ALLE = list(B.VARIANTEN)
TITEL = {'bestand': 'Bestand', 'vorschlag1': 'Vorschlag 1 der Initiative', 'markierung': 'Markierung und Tempo 30 (Empfehlung)', 'zone': 'Tempo-30-Zone, rechts vor links (Vergleich, nicht empfohlen)',
         'radwege': 'Rote Radwege', 'rvl': 'Rechts vor links, Tempo 30 (verworfen)',
         'minikreisel': 'Minikreisel mit Zebrastreifen (verworfen)', 't30_zebra': 'Tempo 30 und Zebra Nord und West (verworfen)',
         'geschuetzt': 'Geschützte Kreuzung (verworfen)'}
ARME = ['S', 'N', 'W', 'E']
ARMNAME = {'S': 'Süd (Gießerstr.)', 'N': 'Nord (Gießerstr.)', 'W': 'West (Naumburger Str.)', 'E': 'Ost (Naumburger Str.)'}
ZUFAHRT = {'S': ['S_in_fern', 'S_in_bucht', 'S_in_mitte', 'S_in', 'S_in_f', 'S_in_m'],
           'N': ['N_zu', 'N_in', 'N_in_b', 'N_in_f', 'N_in_m'], 'W': ['W_in', 'W_in_b', 'W_in_f', 'W_in_m'],
           'E': ['E_in', 'E_in_b', 'E_in_f', 'E_in_m']}
LAENGE = {'pkw': 4.5, 'lkw': 10.0, 'sattel': 16.5, 'bus': 18.0, 'rad': 1.8}
# Hoechstgeschwindigkeit je Fahrzeugtyp wie in build.py (Pkw ohne Grenze)
VMAX = {'pkw': 55.5, 'lkw': 12.5, 'sattel': 11.7, 'bus': 11.1, 'rad': 6.5}
# Zulauf Nord mit Ampel (build.py): Zeitverlust auf der kuenstlichen Strecke gehoert zur Ampel und
# zum Fahren im Pulk und wird abgezogen. Ausnahme ist ein Rueckstau vom Stopp Nord, der ueber den
# Modellrand (110 m vor der Haltlinie) hinausreicht: steht ein Fahrzeug auf N_zu in dieser
# Schlange, zaehlt sein Verlust zum Knoten. Auf N_ab gehoeren die letzten AB_AMPEL m vor der
# Ampel zur Ampel, der Rest zum Knoten.
AB_AMPEL = 100.0
# Durchfahrtstempo: Mittel des Tempos im Knotenkern (bis 12 m um die Mitte). Geradeaus: ohne
# Bremsen heisst innerhalb von 40 m um die Mitte nie langsamer als 85 % des eigenen Hoechsttempos
# dort. Abbieger: ohne Halt heisst dort nie langsamer als 15 km/h.
DURCH_KERN, DURCH_ANLAUF, DURCH_FREI, DURCH_HALT = 12.0, 40.0, 0.85, 15 / 3.6
GERADEAUS = {'SN', 'NS', 'WE', 'EW'}
RELATIONEN = ['SN', 'SW', 'SE', 'WS', 'WN', 'WE', 'NS', 'NW', 'NE', 'ES', 'EW', 'EN']
RELNAME = {'S': 'Süd', 'N': 'Nord', 'W': 'West', 'E': 'Ost'}
# Ueberholen von Raedern (Sublane-Modell): ein Kfz faehrt von hinten am Rad vorbei. Gemessen wird
# der kleinste seitliche Abstand zwischen den Umrissen, solange beide nebeneinander sind. StVO
# innerorts 1,5 m. Nur auf den Armen (Rad mindestens 15 m von der Knotenmitte).
UEBERHOL_ABSTAND = 1.5
LUECKE_FUSS = 7.0      # s, Zeitluecke, die man an der Nordquerung braucht (8 m bei etwa 1,2 m/s)
BREITE = {'pkw': 1.85, 'lkw': 2.5, 'sattel': 2.55, 'bus': 2.55, 'rad': 0.8}

WEG = {'pNw2e': 'Nordseite West nach Ost, quert Nordarm', 'pKiwa': 'Nordseite West nach Ost mit Kinderwagen, quert Nordarm', 'pNe2w': 'Nordseite Ost nach West, quert Nordarm',
       'pKiosk': 'Von Nordost zum Kiosk, quert Nord- und Westarm', 'pKioskBack': 'Vom Kiosk nach Nordost, quert West- und Nordarm',
       'pSued': 'Quert Südarm am Knoten', 'pEastN': 'Ostseite Süd nach Nord, quert Ostarm', 'pEastS': 'Ostseite Nord nach Süd, quert Ostarm',
       'diag': 'Diagonal über den Knoten zwischen Nordost- und Südwestecke (Kiosk)'}

WARMUP, DAUER = (300, 1200) if SCHNELL else (600, 3600)
SCHRITT = 1.0 if SCHNELL else 0.5
# Zaehlwerte (je Lauf gezaehlt) werden auf eine Stunde umgerechnet
ZAEHLWERTE = ('konflikte_fz', 'konflikte_fz_ssmtyp', 'konflikte_fuss', 'bus_spurwechsel', 'bus_spurwechsel_konflikte',
              'fahrten_knoten', 'ueberfahren_bordstein', 'ueberfahren_insel', 'teleports', 'fuss_teleports',
              'ueberlappungen', 'notbremsungen', 'ueberholen_rad', 'nordquerung_luecken', 'fuss_wege', 'fahrten',
              'durchfahrt_anzahl', 'konflikte_kfz_rad_ort', 'bus_furt_kiosk', 'bus_begegnung_west')
# Dauer eines Spurwechsels in s (kontinuierlicher Spurwechsel in SUMO). Bei 30 bis 40 km/h sind das 25 bis 40 m Fahrweg.
SPURWECHSEL_S = 6.0      # frueher --lanechange.duration, jetzt ueber maxSpeedLat im Sublane-Modell
SUBLANE_M = 0.6          # m, Breite der Teilspuren im Sublane-Modell (Raeder rechts in der Spur, Ueberholen in der Spur)

# Grenzwerte
TTC, DRAC, PET = 1.5, 3.0, 1.0
KNOTENBEREICH = 22.0     # m um die Knotenmitte, nur dort zaehlen Fahrzeugkonflikte (alle Varianten gleich)
KONFLIKT_TEMPO = 15 / 3.6  # m/s, langsamere Konflikte (Stop and go in der Schlange) zaehlen nicht
FUSS_TTC = 3.0           # s, Vorausschau fuer das Zusammentreffen
FUSS_DRAC = 3.0          # m/s², ab dieser noetigen Bremsung zaehlt es als Konflikt
FUSS_QUER = 0.3          # m Spielraum um den Fahrzeugumriss
FUSS_TEMPO = 15 / 3.6    # m/s, langsamere Fahrzeuge zaehlen nicht
STAU_TEMPO = 1.0         # m/s, darunter gilt ein Fahrzeug als stehend
STAU_LUECKE = 12.0       # m, groessere Luecke beendet die Schlange


def sumo_bin():
    try:
        import sumo
        return os.path.join(sumo.SUMO_HOME, 'bin', 'sumo')
    except ImportError:
        return 'sumo'


def lauf(var, seed):
    d = os.path.join(ROH, f'{var}_{seed:02d}')
    os.makedirs(d, exist_ok=True)
    f = {k: os.path.join(d, f'{k}.xml') for k in ('trip', 'ssm', 'fcd', 'stat', 'koll')}
    cmd = [sumo_bin(), '-n', os.path.join(NETZE, f'{var}.net.xml'), '-r', os.path.join(NETZE, f'{var}.rou.xml'),
           '-a', os.path.join(NETZE, 'haltestelle.add.xml'),
           '--step-length', str(SCHRITT), '--begin', '0', '--end', str(WARMUP + DAUER + 300), '--seed', str(seed),
           '--no-step-log', '--no-warnings', '--time-to-teleport', '300', '--ignore-junction-blocker', '15',
           '--pedestrian.striping.jamtime', '30',
           # Sublane-Modell: Spurwechsel wandern seitlich (maxSpeedLat), Raeder fahren rechts in der Spur und werden darin ueberholt
           '--lateral-resolution', str(SUBLANE_M),
           '--device.ssm.probability', '1', '--device.ssm.measures', 'TTC DRAC PET',
           '--device.ssm.thresholds', f'{TTC} {DRAC} {PET}', '--device.ssm.range', '50',
           '--device.ssm.trajectories', 'false', '--device.ssm.write-positions', 'true', '--device.ssm.file', f['ssm'],
           '--fcd-output', f['fcd'], '--fcd-output.attributes', 'x,y,speed,lane,pos,angle,edge',
           '--tripinfo-output', f['trip'], '--statistic-output', f['stat'],
           # Zusammenstoesse nur melden, nicht aufloesen. Sie zeigen Fehler im Modell (sich
           # ueberlappende Fahrzeuge) und werden je Lauf gezaehlt.
           '--collision.check-junctions', 'true', '--collision.action', 'warn', '--collision.mingap-factor', '0',
           '--collision-output', f['koll']]
    subprocess.run(cmd, check=True, capture_output=True)
    return auswerten(var, seed, f)


def netzinfo(var):
    r = ET.parse(os.path.join(NETZE, f'{var}.net.xml')).getroot()
    lanelen, querung, form = {}, {}, {}
    for e in r.findall('edge'):
        for l in e.findall('lane'):
            lanelen[l.get('id')] = float(l.get('length'))
            pts = [tuple(map(float, xy.split(','))) for xy in l.get('shape').split()]
            form[l.get('id')] = pts
        if e.get('function') == 'crossing':
            querung[e.get('id')] = e.get('crossingEdges').split()[0].split('_')[0]
    nach = defaultdict(set)
    for c in r.findall('connection'):
        von = f"{c.get('from')}_{c.get('fromLane')}"
        ziel = c.get('via') or f"{c.get('to')}_{c.get('toLane')}"
        nach[von].add(ziel)
    return lanelen, querung, form, nach


def bahn(lane, pos, weg, lanelen, form, nach):
    """Punkt und Richtung nach weg Metern entlang der Fahrspur, None wenn der Weg nicht eindeutig ist."""
    while True:
        pts = form.get(lane)
        if not pts:
            return None
        geo = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
        s = pos * geo / lanelen[lane] if lanelen[lane] > 0 else 0
        ziel = s + weg
        if ziel <= geo:
            acc = 0.0
            for a, b in zip(pts, pts[1:]):
                d = math.hypot(b[0] - a[0], b[1] - a[1])
                if acc + d >= ziel and d > 0:
                    f = (ziel - acc) / d
                    return (a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]), (b[0] - a[0]) / d, (b[1] - a[1]) / d)
                acc += d
            a, b = pts[-2], pts[-1]
            d = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
            return (b[0], b[1], (b[0] - a[0]) / d, (b[1] - a[1]) / d)
        folge = [x for x in nach.get(lane, ()) if x in form and not x.startswith(':') or (x.startswith(':') and '_c' not in x and '_w' not in x)]
        folge = [x for x in folge if x in form]
        if len(folge) != 1:
            return None
        weg = ziel - geo
        lane, pos = folge[0], 0.0


def typ_von(vid):
    return vid.split('_')[0]


RAD_ORTE = {'kiosk': 'Kiosk-Ecke (Südwest)', 'nord': 'vor der Haltlinie Nord (Außenbogen)',
            'sued_ost': 'Rechtsabbieger Süd nach Ost gegen Rad geradeaus', 'west_nord': 'Links abbiegen West nach Nord',
            'bogen_sn': 'Rad Süd nach West (Außenbogen) gegen Kfz geradeaus Süd nach Nord',
            'sonst': 'übrige'}


def rad_ort(kfz_rel, rad_rel, x, y):
    """Ort eines Kfz-Rad-Konflikts fuer die Auswertung (Vorschlag 1 gegen Bestand)."""
    if kfz_rel == 'SE' and rad_rel == 'SN':
        return 'sued_ost'
    if kfz_rel == 'SN' and rad_rel == 'SW':
        return 'bogen_sn'
    if 'WN' in (kfz_rel, rad_rel):
        return 'west_nord'
    if x < -3 and y < -3:
        return 'kiosk'
    if y > 3 or (kfz_rel[0] == 'N' and rad_rel == 'SW'):
        return 'nord'
    return 'sonst'


def kiosk_furt(var):
    """Flaeche der Radfurt West nach Sued an der Kioskecke und ihr Rand zur Fahrbahn, sonst None."""
    r = ET.parse(os.path.join(NETZE, f'{var}.net.xml')).getroot()
    lanes = {l.get('id'): l for e in r.findall('edge') for l in e.findall('lane')}
    for c in r.findall('connection'):
        if c.get('from') != 'W_in_m' or c.get('to') != 'S_out_m' or not c.get('via'):
            continue
        if (lanes[f"W_in_m_{c.get('fromLane')}"].get('allow') or '') != 'bicycle':
            continue
        l = lanes[c.get('via')]
        pts = [tuple(map(float, p.split(','))) for p in l.get('shape').split()]
        w = float(l.get('width', 1.6))
        ls = LineString(pts)
        return ls.buffer(w / 2, cap_style=2), ls.offset_curve(w / 2)   # links der Fahrtrichtung liegt die Fahrbahn
    return None


def rel_von(vid):
    return vid.split('_')[1].split('.')[0]


def im_fenster(t):
    return WARMUP <= t < WARMUP + DAUER


def auswerten(var, seed, f):
    lanelen, querung, form, nach = netzinfo(var)
    werte = []   # (kennzahl, gruppe, wert)

    trips = [t for t in ET.parse(f['trip']).getroot().findall('tripinfo')]
    sfak = {t.get('id'): float(t.get('speedFactor') or 1) for t in trips}
    lspeed = {}
    for e in ET.parse(os.path.join(NETZE, f'{var}.net.xml')).getroot().findall('edge'):
        for l in e.findall('lane'):
            lspeed[l.get('id')] = float(l.get('speed'))
    zul = set(B.ZULAUF_KANTEN)
    ext = defaultdict(float)          # Zeitverlust an der Ampel (abgezogen)
    ext_knoten = defaultdict(float)   # Zeitverlust ausserhalb des Modellrands durch den Knoten
    ampel_stau = {'zu': [], 'ab': []}  # groesster Abstand stehender Fahrzeuge von der Ampel
    nord_ein = []                      # Zeitpunkte, an denen Fahrzeuge aus Nord den Modellrand erreichen
    querung_n = []                     # Zeitpunkte, an denen Fahrzeuge die Nordquerung passieren
    zuletzt = {}
    offen = []                         # Verlust auf N_zu, Zuordnung nach der Schlangenlaenge
    bus_west = {}                      # (Bus West, Bus Ost) -> kleinster seitlicher Abstand der Umrisse
    ueberhol = {}                      # (Kfz, Rad) -> [war dahinter, kleinster Abstand]
    ueberhol_ab = []                   # kleinster Abstand je Ueberholvorgang
    durch = {}                         # Pkw: [Summe Tempo im Knoten, Schritte, kleinstes und groesstes Tempo bis 40 m, Startzeit]

    # ---- Fussgaenger
    fuss_v, fuss_w = defaultdict(list), defaultdict(list)
    for p in ET.parse(f['trip']).getroot().findall('personinfo'):
        if not im_fenster(float(p.get('depart'))):
            continue
        w = p.find('walk')
        if w is None:
            continue
        grp = p.get('id').split('.')[0]
        for g in (grp, 'alle'):
            fuss_v[g].append(float(w.get('timeLoss')))
            fuss_w[g].append(float(w.get('waitingTime')))

    # ---- Konflikte zwischen Fahrzeugen (SSM)
    konf = defaultdict(int)
    gesehen = set()
    bus_konf = defaultdict(list)       # Zeitpunkte der Konflikte je Bus
    for c in ET.parse(f['ssm']).getroot().findall('conflict'):
        if not im_fenster(float(c.get('begin'))):
            continue
        a, b = c.get('ego'), c.get('foe')
        key = (min(a, b), max(a, b), round(float(c.get('begin')) / 5))
        if key in gesehen:          # jeder Konflikt erscheint fuer ego und foe
            continue
        gesehen.add(key)

        def wert(tag):
            e = c.find(tag)
            return None if e is None or e.get('value') in (None, 'NA') else float(e.get('value'))

        def tempo(tag):
            e = c.find(tag)
            return None if e is None or e.get('speed') in (None, 'NA') else float(e.get('speed'))
        ttc, drac, pet = wert('minTTC'), wert('maxDRAC'), wert('PET')
        # nur Werte bei mindestens 15 km/h beruecksichtigen
        if ttc is not None and (tempo('minTTC') or 0) < KONFLIKT_TEMPO:
            ttc = None
        if drac is not None and (tempo('maxDRAC') or 0) < KONFLIKT_TEMPO:
            drac = None
        if pet is not None and (tempo('PET') or 0) < KONFLIKT_TEMPO:
            pet = None
        art_e = c.find('minTTC') if ttc is not None else (c.find('PET') if pet is not None else c.find('maxDRAC'))
        art = int(art_e.get('type')) if art_e is not None and art_e.get('type') not in (None, 'NA') else -1
        kritisch = (ttc is not None and ttc < TTC) or (pet is not None and pet < PET) or (drac is not None and drac > DRAC)
        if not kritisch:
            continue
        pos = art_e.get('position') if art_e is not None else None
        if pos and pos != 'NA':
            px_, py_ = map(float, pos.split(','))
            if math.hypot(px_, py_) > KNOTENBEREICH:
                # ausserhalb des Knotens (Haltestelle, Einfaedeln am Ende der Radwege): getrennt zaehlen
                konf['ausserhalb'] += 1
                continue
        konf[f'typ{art}'] += 1
        if art == 111:
            # Ueberschneidung der Fahrzeugumrisse im Knoteninneren, meist ein Geometrieeffekt
            konf['ueberschneidung'] += 1
            continue
        gruppe = 'auffahren' if art in (1, 2, 3, 4, 18) else 'kreuzen_einbiegen'
        konf['alle'] += 1
        konf[gruppe] += 1
        typen = {typ_von(a), typ_von(b)}
        if 'rad' in typen:
            konf['mit_rad'] += 1
            if len(typen) == 2:
                konf['kfz_rad'] += 1
                rad_id, kfz_id = (a, b) if typ_von(a) == 'rad' else (b, a)
                konf['kfz_rad_' + rad_ort(rel_von(kfz_id).replace('x', ''), rel_von(rad_id),
                                          *((px_, py_) if pos and pos != 'NA' else (0.0, 0.0)))] += 1
        if {'bus', 'lkw', 'sattel'} & typen:
            konf['mit_bus_lkw'] += 1
        if '_SNx' in a or '_SNx' in b:
            konf['fehlspur'] += 1
        for v in (a, b):
            if v.startswith('bus_'):
                bus_konf[v].append(float(c.get('begin')))
        if (ttc is not None and ttc < 1.0) or (pet is not None and pet < 0.5):
            konf['schwer'] += 1

    # ---- FCD: Fussgaenger-Beinahekonflikte, Diagonalquerer, Rueckstau, Busspurwechsel, Bordstein
    stau = {a: [] for a in ARME}
    stau_fz = {a: [] for a in ARME}
    fuss_konf = defaultdict(int)
    fuss_paare = set()
    ne, sw = DG.ecken(B)
    diag = DG.Diagonal(seed, B.DIAGONAL, 0, WARMUP + DAUER, ne, sw)
    kantenlaenge = defaultdict(float)
    for lid, ln in lanelen.items():
        e = lid.rsplit('_', 1)[0]
        kantenlaenge[e] = max(kantenlaenge[e], ln)
    kette = {}
    for a, edges in ZUFAHRT.items():
        rest = 0.0
        for e in reversed(edges):
            if e not in kantenlaenge:
                continue
            kette[e] = (a, rest)   # Restlaenge hinter dieser Kante bis zur Haltlinie
            rest += kantenlaenge[e]
    spuren = defaultdict(list)     # Kfz nahe am Knoten fuer die Schleppkurvenpruefung
    bus_spur = defaultdict(list)   # (t, Kante, Spur) der Busse Sued nach West am Suedarm
    for _, ts in ET.iterparse(f['fcd']):
        if ts.tag != 'timestep':
            continue
        t = float(ts.get('time'))
        fz = ts.findall('vehicle')
        pers = ts.findall('person')
        for vid_, los_, d_ in offen:
            ext[vid_] += los_
        offen = []
        st_zu = st_ab = 0.0
        for v in fz:
            vid = v.get('id')
            lane = v.get('lane')
            e = lane.rsplit('_', 1)[0]
            vorher = zuletzt.get(vid)
            zuletzt[vid] = e
            if e != vorher and im_fenster(t):
                if e == 'N_in' and vorher is not None and (vorher == 'N_zu' or vorher.startswith(':N0')):
                    nord_ein.append(t)
                if vorher is not None and e in ('N_in_m', 'N_out_b'):
                    querung_n.append(t)
            if e in zul or e.startswith(':NA_'):
                sp = float(v.get('speed'))
                pos = float(v.get('pos'))
                vm = min(VMAX.get(typ_von(vid), 55.5), lspeed.get(lane, 13.9) * sfak.get(vid, 1.0))
                los = SCHRITT * max(0.0, 1 - sp / vm)
                if e == 'N_zu' and 'N_zu' in kette:
                    offen.append((vid, los, lanelen[lane] - pos + kette['N_zu'][1]))
                elif e == 'N_ab' and pos <= lanelen[lane] - AB_AMPEL:
                    ext_knoten[vid] += los
                else:
                    ext[vid] += los
                if sp < 0.5 and im_fenster(t):
                    if e == 'N_vor':
                        st_zu = max(st_zu, lanelen[lane] - pos)
                    elif e == 'N_ab':
                        st_ab = max(st_ab, lanelen[lane] - pos)
        if im_fenster(t):
            ampel_stau['zu'].append(st_zu)
            ampel_stau['ab'].append(st_ab)
        if t > WARMUP + DAUER + 60:
            ts.clear()
            continue
        for v in fz:
            vid = v.get('id')
            x, y = float(v.get('x')), float(v.get('y'))
            if typ_von(vid) != 'rad' and math.hypot(x, y) < 70:
                spuren[vid].append((t, x, y, float(v.get('angle'))))
            r_ = math.hypot(x, y)
            if vid.startswith('pkw_') and r_ < DURCH_ANLAUF:
                d_ = durch.setdefault(vid, [0.0, 0, 99.0, 0.0, t])
                sp_ = float(v.get('speed'))
                d_[2] = min(d_[2], sp_)
                d_[3] = max(d_[3], sp_)
                if r_ < DURCH_KERN:
                    d_[0] += sp_
                    d_[1] += 1
            if vid.startswith('bus_SW'):
                e, li = v.get('lane').rsplit('_', 1)
                if e in ('S_in_mitte', 'S_in', 'S_in_f', 'S_in_m', 'S_in_bucht'):
                    bus_spur[vid].append((t, e, int(li)))
        diag_leute = diag.schritt(t, SCHRITT, [(float(v.get('x')), float(v.get('y')), float(v.get('speed'))) for v in fz])
        if not im_fenster(t):
            ts.clear()
            continue
        # Rueckstau je Zufahrt
        proarm = defaultdict(list)
        for v in fz:
            lane = v.get('lane')
            e, li = lane.rsplit('_', 1)
            if e not in kette or typ_von(v.get('id')) == 'rad':
                continue
            if e == 'S_in_bucht' and li == '1':   # Haltebereich Bus
                continue
            arm, rest = kette[e]
            dist = lanelen[lane] - float(v.get('pos')) + rest
            proarm[arm].append((dist, float(v.get('speed')), LAENGE[typ_von(v.get('id'))]))
        for arm in ARME:
            q, ende, n = 0.0, 0.0, 0
            for dist, sp, ln in sorted(proarm[arm]):
                if sp >= STAU_TEMPO or dist - ende > STAU_LUECKE:
                    break
                ende = dist + ln
                q = ende
                n += 1
            stau[arm].append(q)
            stau_fz[arm].append(n)
        # Verlust auf der Zulaufstrecke: in der Schlange vom Stopp Nord zum Knoten, sonst zur Ampel
        for vid_, los_, d_ in offen:
            if d_ <= stau['N'][-1] + 7.0:
                ext_knoten[vid_] += los_
            else:
                ext[vid_] += los_
        offen = []
        # Busse begegnen sich auf der Naumburger West (seitlicher Abstand der Umrisse)
        bw = [(v.get('id'), float(v.get('x')), float(v.get('y')), math.radians(float(v.get('angle')))) for v in fz
              if v.get('id').startswith('bus_') and float(v.get('x')) < -12 and abs(float(v.get('y'))) < 15]
        for i1, x1, y1, a1 in bw:
            for i2, x2, y2, a2 in bw:
                if i1 >= i2 or math.cos(a1 - a2) > -0.8:
                    continue
                ux, uy = math.sin(a1), math.cos(a1)
                dx, dy = x2 - x1, y2 - y1
                lang, quer = dx * ux + dy * uy, abs(dx * uy - dy * ux)
                if -LAENGE['bus'] < lang < LAENGE['bus']:
                    k_ = (i1, i2)
                    bus_west[k_] = min(bus_west.get(k_, 99.0), quer - BREITE['bus'])
        # Kfz ueberholen Raeder
        raeder, kfz_ = [], []
        for v in fz:
            x, y = float(v.get('x')), float(v.get('y'))
            if math.hypot(x, y) > 125:
                continue
            a_ = math.radians(float(v.get('angle')))
            (raeder if typ_von(v.get('id')) == 'rad' else kfz_).append((v.get('id'), x, y, math.sin(a_), math.cos(a_)))
        for rid, xr, yr, ux, uy in raeder:
            if math.hypot(xr, yr) < 15:              # im Knoten selbst kein Ueberholen im Sinne der StVO-Regel
                continue
            for kid, xk, yk, kx, ky in kfz_:
                if ux * kx + uy * ky < 0.9:          # nicht gleiche Richtung
                    continue
                dx, dy = xk - xr, yk - yr
                lang, quer = dx * ux + dy * uy, abs(dx * uy - dy * ux)
                if quer > 4.5 or abs(lang) > 25:
                    continue
                typ = typ_von(kid)
                st_ = ueberhol.setdefault((kid, rid), [False, 99.0])
                if lang < -LAENGE['rad']:
                    st_[0] = True
                elif lang - LAENGE[typ] < 0:
                    if st_[0]:
                        st_[1] = min(st_[1], quer - (BREITE[typ] + BREITE['rad']) / 2)
                elif st_[0] and st_[1] < 99:
                    ueberhol_ab.append(st_[1])
                    del ueberhol[(kid, rid)]
        # Fussgaenger auf Querungen und diagonal gegen schnelle Fahrzeuge
        kandidaten = []
        for p in pers:
            m = re.match(r'(:\w+_c\d+)', p.get('edge') or '')
            if not m:
                continue
            pa = math.radians(float(p.get('angle')))
            kandidaten.append((p.get('id'), querung.get(m.group(1), '?'), float(p.get('x')), float(p.get('y')),
                               float(p.get('speed')) * math.sin(pa), float(p.get('speed')) * math.cos(pa)))
        for pid, x, y, vx, vy, geht in diag_leute:
            if geht:
                kandidaten.append((pid, 'diag', x, y, vx, vy))
        for pid, arm, px, py, pvx, pvy in kandidaten:
            for v in fz:
                sp = float(v.get('speed'))
                if sp < FUSS_TEMPO:
                    continue
                typ = typ_von(v.get('id'))
                treffer = fuss_ttc(px, py, pvx, pvy, v.get('lane'), float(v.get('pos')), sp, LAENGE[typ], BREITE[typ],
                                   lanelen, form, nach)
                # noetige Verzoegerung, um vor der Person zu halten (DRAC)
                if treffer is not None and sp / (2 * max(treffer, 0.05)) > FUSS_DRAC:
                    paar = (pid, v.get('id'))
                    if paar in fuss_paare:
                        continue
                    fuss_paare.add(paar)
                    fuss_konf[arm] += 1
                    if arm != 'diag':
                        fuss_konf['alle'] += 1
                    if sp > 30 / 3.6:
                        fuss_konf['ueber30'] += 1
                    if typ == 'rad':
                        fuss_konf['durch_rad'] += 1
                    if '_SNx' in v.get('id'):
                        fuss_konf['durch_fehlspur'] += 1
        ts.clear()

    # ---- Fahrten
    verlust = defaultdict(list)
    for t in trips:
        if not im_fenster(float(t.get('depart'))):
            continue
        typ, rel = typ_von(t.get('id')), rel_von(t.get('id'))
        mittel = {'pkw': 'Kfz', 'lkw': 'Kfz', 'sattel': 'Kfz', 'bus': 'Bus', 'rad': 'Rad'}[typ]
        # Zeitverlust inklusive Einfahrverzug (Rueckstau ueber den Netzrand hinaus)
        # Mit Zulauf Nord: Verlust an der Ampel abziehen. Fahrten aus Nord starten vor der Ampel,
        # ihr Einfahrverzug ist dann Ampelwartezeit. Als Einfahrverzug (Rueckstau ueber den
        # Modellrand) zaehlt dort der Verlust auf der Zulaufstrecke kurz vor dem Modellrand.
        tid = t.get('id')
        verzug = ext_knoten.get(tid, 0.0) if rel[0] == 'N' and B.ZULAUF_NORD and var != 'geschuetzt' else float(t.get('departDelay'))
        tl = float(t.get('timeLoss')) - ext.get(tid, 0.0)
        if not (rel[0] == 'N' and B.ZULAUF_NORD and var != 'geschuetzt'):
            tl += float(t.get('departDelay'))
        verlust[(rel[0], mittel)].append(tl)
        verlust[('alle', mittel)].append(tl)
        verlust[(rel[0], 'einfahrverzug')].append(verzug)
    for (arm, m), v in verlust.items():
        if m == 'einfahrverzug':
            werte.append(('einfahrverzug_s', arm, st.mean(v)))
        else:
            werte.append(('zeitverlust_s', f'{arm}|{m}', st.mean(v)))
            werte.append(('fahrten', f'{arm}|{m}', len(v)))

    # ---- Zulauf Nord: Pulks, Luecken an der Nordquerung, Rueckstau an der Ampel
    if nord_ein:
        nord_ein.sort()
        h = [b - a for a, b in zip(nord_ein, nord_ein[1:])]
        if len(h) > 2:
            werte.append(('zulauf_nord_cv', 'N', st.pstdev(h) / st.mean(h)))
        # Anteil der Fahrzeuge, die mit hoechstens 3 s Abstand zum Vordermann ankommen
        werte.append(('zulauf_nord_dicht', 'N', 100 * sum(1 for x in h if x <= 3) / max(len(h), 1)))
    q = sorted(querung_n)
    grenzen = [WARMUP] + q + [WARMUP + DAUER]
    luecken = [b - a for a, b in zip(grenzen, grenzen[1:])]
    werte.append(('nordquerung_luecken', 'ab7', sum(1 for g in luecken if g >= LUECKE_FUSS)))
    werte.append(('nordquerung_luecken', 'ab15', sum(1 for g in luecken if g >= 15)))
    werte.append(('nordquerung_sofort', 'N', 100 * sum(max(0.0, g - LUECKE_FUSS) for g in luecken) / DAUER))
    # Wartezeit einer zufaellig ankommenden Person bis zur ersten Luecke von 7 s
    warte = []
    i = 0
    for t_an in range(WARMUP, WARMUP + DAUER):
        while i < len(luecken) - 1 and grenzen[i + 1] <= t_an:
            i += 1
        if grenzen[i + 1] - t_an >= LUECKE_FUSS:
            warte.append(0.0)
        else:
            k = i + 1
            while k < len(luecken) and luecken[k] < LUECKE_FUSS:
                k += 1
            warte.append((grenzen[k] - t_an) if k < len(luecken) else 0.0)
    werte.append(('nordquerung_warte_s', 'N', st.mean(warte)))
    werte.append(('nordquerung_warte_p95_s', 'N', perzentil(warte, 95)))
    for k_, v_ in ampel_stau.items():
        werte.append(('ampel_rueckstau_max_m', k_, max(v_) if v_ else 0))
        werte.append(('ampel_rueckstau_p95_m', k_, perzentil(v_, 95) if v_ else 0))

    # ---- Durchfahrtstempo der Pkw je Relation im Knoten (Mittel, 85 %, ohne Halt)
    je_rel = defaultdict(list)
    frei_rel = defaultdict(list)
    for vid, (summe, n_, vmin, vmax, t0) in durch.items():
        if n_ == 0 or not im_fenster(t0):
            continue
        rel = rel_von(vid).replace('x', '')
        kmh = summe / n_ * 3.6
        je_rel[rel].append(kmh)
        if (vmin >= DURCH_FREI * vmax) if rel in GERADEAUS else (vmin >= DURCH_HALT):
            frei_rel[rel].append(kmh)
    for rel, v_ in je_rel.items():
        werte.append(('durchfahrt_kmh', rel, st.mean(v_)))
        werte.append(('durchfahrt_p85_kmh', rel, perzentil(v_, 85)))
        werte.append(('durchfahrt_anzahl', rel, len(v_)))
    for rel, v_ in frei_rel.items():
        werte.append(('durchfahrt_frei_kmh', rel, st.mean(v_)))

    werte.append(('bus_begegnung_west', 'anzahl', len(bus_west)))
    if bus_west:
        werte.append(('bus_begegnung_west_abstand_m', 'min', min(bus_west.values())))
    werte.append(('ueberholen_rad', 'alle', len(ueberhol_ab)))
    werte.append(('ueberholen_rad', 'unter15', sum(1 for a in ueberhol_ab if a < UEBERHOL_ABSTAND)))
    werte.append(('ueberholen_rad', 'unter10', sum(1 for a in ueberhol_ab if a < 1.0)))
    if ueberhol_ab:
        werte.append(('ueberholen_rad_abstand_m', 'median', st.median(ueberhol_ab)))

    for g in fuss_v:
        werte.append(('fuss_zeitverlust_s', g, st.mean(fuss_v[g])))
        werte.append(('fuss_wartezeit_s', g, st.mean(fuss_w[g])))
        werte.append(('fuss_wege', g, len(fuss_v[g])))
    dw = diag.wartezeiten(WARMUP, WARMUP + DAUER)
    werte.append(('fuss_wartezeit_s', 'diag', st.mean(dw) if dw else 0))
    werte.append(('fuss_wege', 'diag', len(dw)))
    for g in ('alle', 'kreuzen_einbiegen', 'auffahren', 'mit_rad', 'kfz_rad', 'mit_bus_lkw', 'fehlspur', 'schwer', 'ueberschneidung', 'ausserhalb'):
        werte.append(('konflikte_fz', g, konf[g]))
    for o in RAD_ORTE:
        werte.append(('konflikte_kfz_rad_ort', o, konf['kfz_rad_' + o]))
    for g, n in konf.items():
        if g.startswith('typ'):
            werte.append(('konflikte_fz_ssmtyp', g[3:], n))
    for g in ['alle', 'ueber30', 'durch_rad', 'durch_fehlspur', 'diag'] + ARME:
        werte.append(('konflikte_fuss', g, fuss_konf[g]))
    for arm in ARME:
        werte.append(('rueckstau_mittel_m', arm, st.mean(stau[arm]) if stau[arm] else 0))
        werte.append(('rueckstau_p95_m', arm, perzentil(stau[arm], 95)))
        werte.append(('rueckstau_max_m', arm, max(stau[arm]) if stau[arm] else 0))
        werte.append(('schlange_fz_mittel', arm, st.mean(stau_fz[arm]) if stau_fz[arm] else 0))
        werte.append(('schlange_fz_max', arm, max(stau_fz[arm]) if stau_fz[arm] else 0))
        werte.append(('anteil_zeit_wartend', arm, 100 * sum(1 for n in stau_fz[arm] if n > 0) / max(len(stau_fz[arm]), 1)))
        werte.append(('schlange_fz_p95', arm, perzentil(stau_fz[arm], 95)))
        for k in (1, 2, 3, 4, 5):
            werte.append((f'anteil_zeit_{k}plus', arm, 100 * sum(1 for n in stau_fz[arm] if n >= k) / max(len(stau_fz[arm]), 1)))

    # ---- Bus Sued nach West: Wechsel vom Haltebereich ganz rechts auf die Linksabbiegespur
    wechsel, wechsel_konf = 0, 0
    for vid, seq in bus_spur.items():
        if not seq or not im_fenster(seq[0][0]):
            continue
        # Vom Haltebereich (rechte Spur) auf die Linksabbiegespur, als Spurwechsel oder ueber die
        # schraege Verbindung im weichen Uebergang S25
        rechts = [t for t, e, l in seq if e in ('S_in_bucht', 'S_in_mitte') and l == 1]
        links = [t for t, e, l in seq if e in ('S_in', 'S_in_m', 'S_in_f') and l == 2 and rechts and t > rechts[0]]
        if rechts and links:
            t1 = links[0]
            wechsel += 1
            wechsel_konf += sum(1 for tk in bus_konf.get(vid, []) if t1 - 6 <= tk <= t1 + 4)
    werte.append(('bus_spurwechsel', 'SW', wechsel))
    werte.append(('bus_spurwechsel_konflikte', 'SW', wechsel_konf))

    # ---- Bordstein und Inseln: Fahrzeugumrisse mit Schleppkurve gegen die Fahrbahnflaeche
    fb = SR.fahrbahn(var)
    fb_p = prep(fb)
    insel = SR.inseln(var)
    ueber = defaultdict(int)
    fahrten_k = defaultdict(int)
    for vid, seq in spuren.items():
        typ = typ_von(vid)
        if len(seq) < 2:
            continue
        nah = [i for i, (t, x, y, w) in enumerate(seq) if im_fenster(t) and math.hypot(x, y) < 35]
        if not nah or not im_fenster(seq[nah[0]][0]):
            continue
        posen = K.posen(typ, [p[1] for p in seq], [p[2] for p in seq], [p[3] for p in seq], SCHRITT, K.ausholen_fuer(vid))
        bord = ins = False
        for i in nah:
            F = posen[i]
            for ecken_ in K.umrisse(typ, (F[0], F[1]), F[2], F[3], schrumpf=0.1):
                P = Polygon(ecken_)
                if fb_p.contains(P):
                    continue
                aus = P.difference(fb)
                if aus.area < 0.2:
                    continue
                if not insel.is_empty and aus.intersection(insel).area > 0.1:
                    ins = True
                else:
                    bord = True
        fahrten_k[typ] += 1
        if bord:
            ueber[(typ, 'bordstein')] += 1
        if ins:
            ueber[(typ, 'insel')] += 1
    # Bus West nach Sued ueber die Radfurt an der Kioskecke (nur wo es sie gibt)
    furt = kiosk_furt(var)
    if furt is not None:
        fpoly, innen = furt
        bus_fahrten, bus_drauf, tiefe = 0, 0, []
        for vid, seq in spuren.items():
            if not vid.startswith('bus_WS') or len(seq) < 2 or not im_fenster(seq[0][0]):
                continue
            posen = K.posen('bus', [p[1] for p in seq], [p[2] for p in seq], [p[3] for p in seq], SCHRITT, K.ausholen_fuer(vid))
            bus_fahrten += 1
            t_max = 0.0
            for F in posen:
                if math.hypot(F[0], F[1]) > 30:
                    continue
                for ecken_ in K.umrisse('bus', (F[0], F[1]), F[2], F[3], schrumpf=0.05):
                    sch = Polygon(ecken_).intersection(fpoly)
                    if sch.is_empty or sch.area < 0.05:
                        continue
                    pts_ = list(sch.exterior.coords) if sch.geom_type == 'Polygon' else [c for g in sch.geoms for c in g.exterior.coords]
                    t_max = max(t_max, max(innen.distance(Point(p)) for p in pts_))
            if t_max > 0:
                bus_drauf += 1
                tiefe.append(t_max)
        werte.append(('bus_furt_kiosk', 'fahrten', bus_fahrten))
        werte.append(('bus_furt_kiosk', 'ueberfahren', bus_drauf))
        if tiefe:
            werte.append(('bus_furt_kiosk_tiefe_m', 'max', max(tiefe)))
            werte.append(('bus_furt_kiosk_tiefe_m', 'mittel', st.mean(tiefe)))
    for typ in ('pkw', 'lkw', 'sattel', 'bus'):
        werte.append(('fahrten_knoten', typ, fahrten_k[typ]))
        werte.append(('ueberfahren_bordstein', typ, ueber[(typ, 'bordstein')]))
        werte.append(('ueberfahren_insel', typ, ueber[(typ, 'insel')]))

    # ---- Statistik
    s = ET.parse(f['stat']).getroot()
    tp = s.find('teleports')
    werte.append(('teleports', 'alle', int(tp.get('total'))))
    pt = s.find('personTeleports')
    werte.append(('fuss_teleports', 'alle', int(pt.get('total'))))
    koll = [c for c in ET.parse(f['koll']).getroot().findall('collision') if im_fenster(float(c.get('time')))]
    paare = {(c.get('collider'), c.get('victim')) for c in koll}
    werte.append(('ueberlappungen', 'alle', len(paare)))
    sf = s.find('safety')
    werte.append(('notbremsungen', 'alle', int(sf.get('emergencyBraking'))))
    je_h = 3600 / DAUER
    return [(var, seed, k, g, round(w * je_h if k in ZAEHLWERTE else w, 3)) for k, g, w in werte]


def fuss_ttc(px, py, pvx, pvy, lane, pos, sp, laenge, breite, lanelen, form, nach):
    """Zeit bis Person und Fahrzeug bei gleichbleibendem Tempo zusammentreffen (None, wenn nicht
    innerhalb FUSS_TTC Sekunden). Das Fahrzeug folgt seiner Fahrspur (auch in Kurven), die Person geht geradeaus."""
    if math.hypot(px - form[lane][-1][0], py - form[lane][-1][1]) > 40 + sp * FUSS_TTC:
        return None
    t = 0.0
    while t <= FUSS_TTC + 1e-9:
        b = bahn(lane, pos, sp * t, lanelen, form, nach)
        if b is None:
            return None
        fx, fy, hx, hy = b
        rx = px + pvx * t - fx
        ry = py + pvy * t - fy
        laengs = rx * hx + ry * hy
        quer = abs(rx * hy - ry * hx)
        if -laenge < laengs < FUSS_QUER and quer < breite / 2 + FUSS_QUER:
            return t
        t += 0.1
    return None


def perzentil(v, p):
    if not v:
        return 0
    s = sorted(v)
    return s[min(len(s) - 1, int(round(p / 100 * (len(s) - 1))))]


# ---------------------------------------------------------------- Bericht
def qsv(w, verzug):
    """Qualitaetsstufe nach mittlerer Wartezeit, Knoten ohne Ampel (nach HBS 2015, am Original pruefen)."""
    if verzug > 10:
        return 'F'
    for g, s in ((10, 'A'), (20, 'B'), (30, 'C'), (45, 'D')):
        if w <= g:
            return s
    return 'E'


def ms(v):
    if not v:
        return 'n. v.'
    m = st.mean(v)
    sd = st.stdev(v) if len(v) > 1 else 0
    return f'{m:.1f} ± {sd:.1f}'


def bericht(rows, laeufe, bus):
    data = defaultdict(lambda: defaultdict(list))
    for var, seed, k, g, w in rows:
        data[var][(k, g)].append(w)
    vs = [v for v in ALLE if v in data]
    L = []
    L.append('# Vergleich der Varianten (SUMO)\n')
    L.append(f'Je Variante {laeufe} Läufe mit festen Startwerten, je Lauf {DAUER // 60} Minuten Spitzenstunde nach '
             f'{WARMUP // 60} Minuten Einschwingzeit. Angegeben ist Mittelwert ± Standardabweichung über die Läufe. '
             f'Busroute {bus}. Die Nachfrage ist geschätzt und das Modell ist nicht kalibriert, die Zahlen zeigen '
             'Unterschiede zwischen den Varianten, keine absoluten Werte für die echte Kreuzung.'
             + (' **Schneller Probemodus**: 1 s Schrittweite, Zählwerte auf eine Stunde hochgerechnet, nur zur groben Orientierung.' if SCHNELL else '')
             + '\n')
    L.append('## Überblick je Stunde\n')
    L.append('| Kennzahl | ' + ' | '.join(TITEL[v] for v in vs) + ' |')
    L.append('|---|' + '---|' * len(vs))
    zeilen = [
        ('Konflikte Fahrzeug mit Fahrzeug im Knotenbereich (22 m), TTC < 1,5 s, PET < 1 s oder DRAC > 3 m/s²', ('konflikte_fz', 'alle')),
        ('davon Kreuzen und Einbiegen', ('konflikte_fz', 'kreuzen_einbiegen')),
        ('davon Auffahren', ('konflikte_fz', 'auffahren')),
        ('davon Kfz gegen Rad', ('konflikte_fz', 'kfz_rad')),
        ('davon mit Bus oder Lkw', ('konflikte_fz', 'mit_bus_lkw')),
        ('davon mit Geradeausfahrer aus der Linksabbiegespur (Fehlspur)', ('konflikte_fz', 'fehlspur')),
        ('davon schwer (TTC < 1 s oder PET < 0,5 s)', ('konflikte_fz', 'schwer')),
        ('Fahrzeugkonflikte außerhalb des Knotenbereichs (nicht mitgezählt)', ('konflikte_fz', 'ausserhalb')),
        ('Fußgänger auf Querung, Fahrzeug über 15 km/h müsste mit über 3 m/s² bremsen', ('konflikte_fuss', 'alle')),
        ('davon Fahrzeug schneller als 30 km/h', ('konflikte_fuss', 'ueber30')),
        ('davon durch Rad', ('konflikte_fuss', 'durch_rad')),
        ('davon durch Fehlspur-Fahrer', ('konflikte_fuss', 'durch_fehlspur')),
        ('Kfz überholt Rad (Vorgänge je Stunde, Sublane-Modell)', ('ueberholen_rad', 'alle')),
        ('davon Überholabstand < 1,5 m (StVO innerorts)', ('ueberholen_rad', 'unter15')),
        ('davon Überholabstand < 1,0 m', ('ueberholen_rad', 'unter10')),
        ('Kfz gegen Rad an der Kiosk-Ecke (Südwest)', ('konflikte_kfz_rad_ort', 'kiosk')),
        ('Kfz gegen Rad vor der Haltlinie Nord bzw. im Außenbogen', ('konflikte_kfz_rad_ort', 'nord')),
        ('Kfz gegen Rad: Rechtsabbieger Süd nach Ost gegen Rad geradeaus', ('konflikte_kfz_rad_ort', 'sued_ost')),
        ('Kfz gegen Rad: links abbiegen West nach Nord', ('konflikte_kfz_rad_ort', 'west_nord')),
        ('Kfz gegen Rad: Rad Süd nach West gegen Kfz geradeaus Süd nach Nord', ('konflikte_kfz_rad_ort', 'bogen_sn')),
        ('Kfz gegen Rad: übrige', ('konflikte_kfz_rad_ort', 'sonst')),
        ('Bus West nach Süd: Fahrten', ('bus_furt_kiosk', 'fahrten')),
        ('davon über die Radfurt an der Kiosk-Ecke', ('bus_furt_kiosk', 'ueberfahren')),
        ('dabei größte Tiefe in die Furt in m (Furt 1,6 m breit)', ('bus_furt_kiosk_tiefe_m', 'max')),
        ('Busbegegnungen auf der Naumburger West je Stunde', ('bus_begegnung_west', 'anzahl')),
        ('dabei kleinster seitlicher Abstand der Busse in m', ('bus_begegnung_west_abstand_m', 'min')),
        ('Süd: größte Schlange (Fahrzeuge)', ('schlange_fz_max', 'S')),
        ('Süd: Rückstau größter Wert in m', ('rueckstau_max_m', 'S')),
        ('Überholabstand im Median in m', ('ueberholen_rad_abstand_m', 'median')),
        ('Mittlerer Zeitverlust Kfz in s', ('zeitverlust_s', 'alle|Kfz')),
        ('Mittlerer Zeitverlust Rad in s', ('zeitverlust_s', 'alle|Rad')),
        ('Mittlerer Zeitverlust Bus in s', ('zeitverlust_s', 'alle|Bus')),
        ('Mittlere Wartezeit Fußgänger in s', ('fuss_wartezeit_s', 'alle')),
        ('Nordarm: wartende Fahrzeuge im Mittel', ('schlange_fz_mittel', 'N')),
        ('Nordarm: größte Schlange (Fahrzeuge)', ('schlange_fz_max', 'N')),
        ('Nordarm: Anteil der Zeit mit mindestens 1 wartenden Fahrzeug in %', ('anteil_zeit_wartend', 'N')),
        ('Nordarm: Anteil der Zeit mit 2 oder mehr in %', ('anteil_zeit_2plus', 'N')),
        ('Nordarm: Anteil der Zeit mit 3 oder mehr in %', ('anteil_zeit_3plus', 'N')),
        ('Nordarm: Anteil der Zeit mit 5 oder mehr in %', ('anteil_zeit_5plus', 'N')),
        ('Nordarm: Schlange, 95 %-Wert (Fahrzeuge)', ('schlange_fz_p95', 'N')),
        ('Nordarm: Rückstau größter Wert in m (Modellrand bei 110 m vor der Haltlinie)', ('rueckstau_max_m', 'N')),
        ('Zulauf Nord: Pulkigkeit (Streuung der Abstände geteilt durch Mittel, 1 = zufällig)', ('zulauf_nord_cv', 'N')),
        ('Zulauf Nord: Anteil der Fahrzeuge höchstens 3 s hinter dem Vordermann in %', ('zulauf_nord_dicht', 'N')),
        ('Nordquerung: Lücken von mindestens 7 s je Stunde (beide Richtungen)', ('nordquerung_luecken', 'ab7')),
        ('Nordquerung: Lücken von mindestens 15 s je Stunde', ('nordquerung_luecken', 'ab15')),
        ('Nordquerung: Anteil der Zeit, in der man sofort gehen kann (Lücke ab 7 s) in %', ('nordquerung_sofort', 'N')),
        ('Nordquerung: Wartezeit auf eine Lücke von 7 s im Mittel in s', ('nordquerung_warte_s', 'N')),
        ('Nordquerung: Wartezeit auf eine Lücke von 7 s, 95 %-Wert in s', ('nordquerung_warte_p95_s', 'N')),
        ('Ampel Nord: Rückstau Richtung Norden, größter Wert in m (Knoten bei 340 m)', ('ampel_rueckstau_max_m', 'ab')),
        ('Bus Süd nach West: Spurwechsel vom Haltebereich zur Linksabbiegespur', ('bus_spurwechsel', 'SW')),
        ('dabei Konflikte (±5 s um den Wechsel)', ('bus_spurwechsel_konflikte', 'SW')),
        ('Bus überfährt Bordstein (Fahrten je Stunde)', ('ueberfahren_bordstein', 'bus')),
        ('Lkw überfährt Bordstein', ('ueberfahren_bordstein', 'lkw')),
        ('Sattelzug überfährt Bordstein', ('ueberfahren_bordstein', 'sattel')),
        ('Pkw überfährt Bordstein', ('ueberfahren_bordstein', 'pkw')),
        ('Bus überfährt Insel oder Pflaster', ('ueberfahren_insel', 'bus')),
        ('Lkw überfährt Insel oder Pflaster', ('ueberfahren_insel', 'lkw')),
        ('Sattelzug überfährt Insel oder Pflaster', ('ueberfahren_insel', 'sattel')),
        ('Pkw überfährt Insel oder Pflaster', ('ueberfahren_insel', 'pkw')),
        ('Teleports (Verklemmungen im Modell)', ('teleports', 'alle')),
        ('Überlappungen im Modell (SUMO-Zusammenstöße, Modellfehler)', ('ueberlappungen', 'alle')),
        ('Überschneidungen im Knoteninneren (SSM-Typ 111, nicht mitgezählt)', ('konflikte_fz', 'ueberschneidung')),
    ]
    for name, key in zeilen:
        L.append(f'| {name} | ' + ' | '.join(ms(data[v][key]) for v in vs) + ' |')

    L.append('\n## Durchfahrtstempo der Pkw im Knoten in km/h\n')
    L.append('Tempo im Knotenkern (bis 12 m um die Mitte), je Fahrzeug gemittelt. Angegeben Mittel / 85 %-Wert über alle Pkw, '
             'dahinter bei Geradeausfahrern das Mittel der Pkw ohne Bremsen (innerhalb 40 m um die Mitte nie unter 85 % ihres dortigen '
             'Höchsttempos, also ungehindert), bei Abbiegern ohne Halt (dort nie unter 15 km/h). Fehlspur-Fahrer zählen zu Süd nach Nord.\n')
    L.append('| Relation | ' + ' | '.join(TITEL[v] for v in vs) + ' |')
    L.append('|---|' + '---|' * len(vs))
    for rel in RELATIONEN:
        zellen = []
        for v in vs:
            m_, p_, f_ = data[v][('durchfahrt_kmh', rel)], data[v][('durchfahrt_p85_kmh', rel)], data[v][('durchfahrt_frei_kmh', rel)]
            zusatz = 'ohne Bremsen' if rel in GERADEAUS else 'ohne Halt'
            zellen.append(f'{st.mean(m_):.0f} / {st.mean(p_):.0f}, {zusatz} {st.mean(f_):.0f}' if m_ and f_ else
                          (f'{st.mean(m_):.0f} / {st.mean(p_):.0f}' if m_ else 'n. v.'))
        L.append(f'| {RELNAME[rel[0]]} nach {RELNAME[rel[1]]} | ' + ' | '.join(zellen) + ' |')

    L.append('\n## Fußgängerkonflikte je Querung\n')
    L.append('| Querung über Arm | ' + ' | '.join(TITEL[v] for v in vs) + ' |')
    L.append('|---|' + '---|' * len(vs))
    for a in ARME:
        L.append(f'| {ARMNAME[a]} | ' + ' | '.join(ms(data[v][('konflikte_fuss', a)]) for v in vs) + ' |')

    L.append('\n## Zufahrten, Zeitverlust Kfz und Qualitätsstufe\n')
    L.append('Qualitätsstufe aus dem mittleren Zeitverlust der Kfz je Zufahrt mit den Grenzen für Knoten ohne Ampel '
             'A bis 10 s, B bis 20 s, C bis 30 s, D bis 45 s, E darüber, F bei Überlastung (mittlerer Einfahrverzug '
             'über 10 s, die Schlange reicht also über den Modellrand). Nach HBS 2015, am Original prüfen. Das HBS '
             'bewertet nur wartepflichtige Ströme, hier wird vereinfacht die ganze Zufahrt betrachtet.\n')
    L.append('| Zufahrt | ' + ' | '.join(TITEL[v] for v in vs) + ' |')
    L.append('|---|' + '---|' * len(vs))
    for a in ARME:
        zellen = []
        for v in vs:
            w = data[v][('zeitverlust_s', f'{a}|Kfz')]
            vz = data[v][('einfahrverzug_s', a)]
            if w:
                zellen.append(f'{ms(w)} s, QSV {qsv(st.mean(w), st.mean(vz) if vz else 0)}')
            else:
                zellen.append('n. v.')
        L.append(f'| {ARMNAME[a]} | ' + ' | '.join(zellen) + ' |')

    L.append('\n## Rückstau je Zufahrt in Metern (Mittel / 95 %-Wert)\n')
    L.append('| Zufahrt | ' + ' | '.join(TITEL[v] for v in vs) + ' |')
    L.append('|---|' + '---|' * len(vs))
    for a in ARME:
        zellen = []
        for v in vs:
            m = data[v][('rueckstau_mittel_m', a)]
            p = data[v][('rueckstau_p95_m', a)]
            zellen.append(f'{st.mean(m):.0f} / {st.mean(p):.0f}' if m else 'n. v.')
        L.append(f'| {ARMNAME[a]} | ' + ' | '.join(zellen) + ' |')

    L.append('\n## Wartezeit der Fußgänger je Weg in s\n')
    gruppen = sorted({g for v in vs for (k, g) in data[v] if k == 'fuss_wartezeit_s' and g != 'alle'})
    L.append('| Weg | ' + ' | '.join(TITEL[v] for v in vs) + ' |')
    L.append('|---|' + '---|' * len(vs))
    for g in gruppen:
        L.append(f'| {WEG.get(g, g)} | ' + ' | '.join(ms(data[v][('fuss_wartezeit_s', g)]) for v in vs) + ' |')
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--laeufe', type=int, default=10)
    ap.add_argument('--varianten', nargs='+', default=VARIANTEN, choices=ALLE)
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 2)
    ap.add_argument('--behalte-roh', action='store_true', help='Rohdaten nicht loeschen')
    ap.add_argument('--nur-bericht', action='store_true', help='nur vergleich.md aus kennzahlen.csv neu schreiben')
    ap.add_argument('--schnell', action='store_true',
                    help='Probemodus: 3 Laeufe, 20 min, 1 s Schrittweite, Ergebnis in ergebnisse/schnell')
    args = ap.parse_args()
    if args.schnell and not SCHNELL:
        # Konstanten haengen am Modul, deshalb mit gesetzter Umgebungsvariable neu starten
        os.environ['SUMO_SCHNELL'] = '1'
        argv = [a for a in sys.argv if a != '--schnell']
        if '--laeufe' not in argv:
            argv += ['--laeufe', '3']
        os.execv(sys.executable, [sys.executable] + argv)
    if args.nur_bericht:
        with open(os.path.join(ERG, 'kennzahlen.csv')) as f:
            rows = [(r['variante'], int(r['lauf']), r['kennzahl'], r['gruppe'], float(r['wert'])) for r in csv.DictReader(f)]
        laeufe = len({r[1] for r in rows})
        bus = open(os.path.join(NETZE, 'bus.txt')).read().strip()
        with open(os.path.join(ERG, 'vergleich.md'), 'w') as f:
            f.write(bericht(rows, laeufe, bus))
        return
    for v in args.varianten:
        if not os.path.exists(os.path.join(NETZE, f'{v}.net.xml')):
            sys.exit('Netze fehlen, bitte zuerst python3 build.py ausfuehren')
    os.makedirs(ROH, exist_ok=True)
    jobs = [(v, s) for v in args.varianten for s in range(1, args.laeufe + 1)]
    rows = []
    with ProcessPoolExecutor(args.jobs) as ex:
        for r in ex.map(_lauf, jobs):
            rows += r
            print(f'  fertig {r[0][0]} Lauf {r[0][1]}', flush=True)
    rows.sort()
    with open(os.path.join(ERG, 'kennzahlen.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['variante', 'lauf', 'kennzahl', 'gruppe', 'wert'])
        w.writerows(rows)
    bus = open(os.path.join(NETZE, 'bus.txt')).read().strip()
    with open(os.path.join(ERG, 'vergleich.md'), 'w') as f:
        f.write(bericht(rows, args.laeufe, bus))
    if not args.behalte_roh:
        for v, s in jobs:
            d = os.path.join(ROH, f'{v}_{s:02d}')
            if s == 1:
                continue          # erster Lauf bleibt fuer Animation und Kontrolle
            for x in os.listdir(d):
                os.remove(os.path.join(d, x))
            os.rmdir(d)
    print('geschrieben', os.path.join(ERG, 'vergleich.md'))


def _lauf(job):
    return lauf(*job)


if __name__ == '__main__':
    main()
