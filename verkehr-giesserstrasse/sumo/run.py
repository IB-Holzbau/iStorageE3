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
import xml.etree.ElementTree as ET
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
NETZE = os.path.join(ROOT, 'netze')
ERG = os.path.join(ROOT, 'ergebnisse')
ROH = os.path.join(ERG, 'roh')

VARIANTEN = ['bestand', 'rvl', 'minikreisel', 't30_zebra']
TITEL = {'bestand': 'Bestand', 'rvl': 'Rechts vor links, Tempo 30',
         'minikreisel': 'Minikreisel mit Zebrastreifen', 't30_zebra': 'Bestand mit Tempo 30 und Zebra Nord und West'}
ARME = ['S', 'N', 'W', 'E']
ARMNAME = {'S': 'Süd (Gießerstr.)', 'N': 'Nord (Gießerstr.)', 'W': 'West (Naumburger Str.)', 'E': 'Ost (Naumburger Str.)'}
ZUFAHRT = {'S': ['S_in_fern', 'S_in_bucht', 'S_in_mitte', 'S_in', 'S_in_m'],
           'N': ['N_in', 'N_in_m'], 'W': ['W_in', 'W_in_m'], 'E': ['E_in', 'E_in_m']}
LAENGE = {'pkw': 4.5, 'lkw': 10.0, 'sattel': 16.5, 'bus': 18.0, 'rad': 1.8}
BREITE = {'pkw': 1.85, 'lkw': 2.5, 'sattel': 2.55, 'bus': 2.55, 'rad': 0.8}

WEG = {'pNw2e': 'Nordseite West nach Ost, quert Nordarm', 'pNe2w': 'Nordseite Ost nach West, quert Nordarm',
       'pKiosk': 'Von Nordost zum Kiosk, quert Nord- und Westarm', 'pKioskBack': 'Vom Kiosk nach Nordost, quert West- und Nordarm',
       'pSued': 'Quert Südarm am Knoten', 'pEastN': 'Ostseite Süd nach Nord, quert Ostarm', 'pEastS': 'Ostseite Nord nach Süd, quert Ostarm'}

WARMUP, DAUER = 600, 3600
SCHRITT = 0.5

# Grenzwerte
TTC, DRAC, PET = 1.5, 3.0, 1.0
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
           '--device.ssm.probability', '1', '--device.ssm.measures', 'TTC DRAC PET',
           '--device.ssm.thresholds', f'{TTC} {DRAC} {PET}', '--device.ssm.range', '50',
           '--device.ssm.trajectories', 'false', '--device.ssm.file', f['ssm'],
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


def rel_von(vid):
    return vid.split('_')[1].split('.')[0]


def im_fenster(t):
    return WARMUP <= t < WARMUP + DAUER


def auswerten(var, seed, f):
    lanelen, querung, form, nach = netzinfo(var)
    werte = []   # (kennzahl, gruppe, wert)

    # ---- Fahrten
    verlust = defaultdict(list)
    for t in ET.parse(f['trip']).getroot().findall('tripinfo'):
        if not im_fenster(float(t.get('depart'))):
            continue
        typ, rel = typ_von(t.get('id')), rel_von(t.get('id'))
        mittel = {'pkw': 'Kfz', 'lkw': 'Kfz', 'sattel': 'Kfz', 'bus': 'Bus', 'rad': 'Rad'}[typ]
        # Zeitverlust inklusive Einfahrverzug (Rueckstau ueber den Netzrand hinaus)
        tl = float(t.get('timeLoss')) + float(t.get('departDelay'))
        verlust[(rel[0], mittel)].append(tl)
        verlust[('alle', mittel)].append(tl)
        verlust[(rel[0], 'einfahrverzug')].append(float(t.get('departDelay')))
    for (arm, m), v in verlust.items():
        if m == 'einfahrverzug':
            werte.append(('einfahrverzug_s', arm, st.mean(v)))
        else:
            werte.append(('zeitverlust_s', f'{arm}|{m}', st.mean(v)))
            werte.append(('fahrten', f'{arm}|{m}', len(v)))

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
    for g in fuss_v:
        werte.append(('fuss_zeitverlust_s', g, st.mean(fuss_v[g])))
        werte.append(('fuss_wartezeit_s', g, st.mean(fuss_w[g])))
        werte.append(('fuss_wege', g, len(fuss_v[g])))

    # ---- Konflikte zwischen Fahrzeugen (SSM)
    konf = defaultdict(int)
    gesehen = set()
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
        # SSM-Typen 1 bis 3 sind Folgeverkehr (Auffahren), uebrige Kreuzen oder Einfaedeln
        konf[f'typ{art}'] += 1
        if art == 111:
            # SUMO meldet hier eine Ueberschneidung der Fahrzeugumrisse im Knoteninneren.
            # Das ist meist ein Geometrieeffekt (Warteposition ragt in die Fahrlinie) und wird getrennt gezaehlt.
            konf['ueberschneidung'] += 1
            continue
        gruppe = 'auffahren' if art in (1, 2, 3, 4, 18) else 'kreuzen_einbiegen'
        konf['alle'] += 1
        konf[gruppe] += 1
        if 'rad' in (typ_von(a), typ_von(b)):
            konf['mit_rad'] += 1
        if {'bus', 'lkw', 'sattel'} & {typ_von(a), typ_von(b)}:
            konf['mit_bus_lkw'] += 1
        if (ttc is not None and ttc < 1.0) or (pet is not None and pet < 0.5):
            konf['schwer'] += 1
    for g in ('alle', 'kreuzen_einbiegen', 'auffahren', 'mit_rad', 'mit_bus_lkw', 'schwer', 'ueberschneidung'):
        werte.append(('konflikte_fz', g, konf[g]))
    for g, n in konf.items():
        if g.startswith('typ'):
            werte.append(('konflikte_fz_ssmtyp', g[3:], n))

    # ---- FCD: Fussgaenger-Beinahekonflikte und Rueckstau
    stau = {a: [] for a in ARME}
    fuss_konf = defaultdict(int)
    fuss_paare = set()
    kette = {}
    for a, edges in ZUFAHRT.items():
        rest = 0.0
        for e in reversed(edges):
            kette[e] = (a, rest)   # Restlaenge hinter dieser Kante bis zur Haltlinie
            rest += max(lanelen.get(f'{e}_1', 0), lanelen.get(f'{e}_2', 0))
    for _, ts in ET.iterparse(f['fcd']):
        if ts.tag != 'timestep':
            continue
        t = float(ts.get('time'))
        if not im_fenster(t):
            ts.clear()
            continue
        fz, pers = [], []
        for v in ts.findall('vehicle'):
            fz.append(v)
        for p in ts.findall('person'):
            pers.append(p)
        # Rueckstau je Zufahrt
        proarm = defaultdict(list)
        for v in fz:
            lane = v.get('lane')
            e, li = lane.rsplit('_', 1)
            if e not in kette:
                continue
            if e in ('S_in_fern', 'S_in_bucht', 'S_in_mitte') and li == '1':   # Haltestellenstreifen (Bus, Rad)
                continue
            arm, rest = kette[e]
            dist = lanelen[lane] - float(v.get('pos')) + rest
            proarm[arm].append((dist, float(v.get('speed')), LAENGE[typ_von(v.get('id'))]))
        for arm in ARME:
            q, ende = 0.0, 0.0
            for dist, sp, ln in sorted(proarm[arm]):
                if sp >= STAU_TEMPO or dist - ende > STAU_LUECKE:
                    break
                ende = dist + ln
                q = ende
            stau[arm].append(q)
        # Fussgaenger auf Querungen gegen schnelle Fahrzeuge
        for p in pers:
            m = re.match(r'(:\w+_c\d+)', p.get('edge') or '')
            if not m:
                continue
            arm = querung.get(m.group(1), '?')
            px, py = float(p.get('x')), float(p.get('y'))
            pa = math.radians(float(p.get('angle')))
            pvx, pvy = float(p.get('speed')) * math.sin(pa), float(p.get('speed')) * math.cos(pa)
            for v in fz:
                sp = float(v.get('speed'))
                if sp < FUSS_TEMPO:
                    continue
                typ = typ_von(v.get('id'))
                treffer = fuss_ttc(px, py, pvx, pvy, v.get('lane'), float(v.get('pos')), sp, LAENGE[typ], BREITE[typ],
                                   lanelen, form, nach)
                # noetige Verzoegerung, um vor der Person zu halten (DRAC)
                if treffer is not None and sp / (2 * max(treffer, 0.05)) > FUSS_DRAC:
                    paar = (p.get('id'), v.get('id'))
                    if paar not in fuss_paare:
                        fuss_paare.add(paar)
                        fuss_konf[arm] += 1
                        fuss_konf['alle'] += 1
                        if sp > 30 / 3.6:
                            fuss_konf['ueber30'] += 1
                        if typ == 'rad':
                            fuss_konf['durch_rad'] += 1
        ts.clear()
    for g in ['alle', 'ueber30', 'durch_rad'] + ARME:
        werte.append(('konflikte_fuss', g, fuss_konf[g]))
    for arm in ARME:
        werte.append(('rueckstau_mittel_m', arm, st.mean(stau[arm]) if stau[arm] else 0))
        werte.append(('rueckstau_p95_m', arm, perzentil(stau[arm], 95)))
        werte.append(('rueckstau_max_m', arm, max(stau[arm]) if stau[arm] else 0))

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
    return [(var, seed, k, g, round(w, 3)) for k, g, w in werte]


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
    vs = [v for v in VARIANTEN if v in data]
    L = []
    L.append('# Vergleich der Varianten (SUMO)\n')
    L.append(f'Je Variante {laeufe} Läufe mit festen Startwerten, je Lauf {DAUER // 60} Minuten Spitzenstunde nach '
             f'{WARMUP // 60} Minuten Einschwingzeit. Angegeben ist Mittelwert ± Standardabweichung über die Läufe. '
             f'Busroute {bus}. Die Nachfrage ist geschätzt und das Modell ist nicht kalibriert, die Zahlen zeigen '
             'Unterschiede zwischen den Varianten, keine absoluten Werte für die echte Kreuzung.\n')
    L.append('## Überblick je Stunde\n')
    L.append('| Kennzahl | ' + ' | '.join(TITEL[v] for v in vs) + ' |')
    L.append('|---|' + '---|' * len(vs))
    zeilen = [
        ('Konflikte Fahrzeug mit Fahrzeug (TTC < 1,5 s, PET < 1 s oder DRAC > 3 m/s²)', ('konflikte_fz', 'alle')),
        ('davon Kreuzen und Einbiegen', ('konflikte_fz', 'kreuzen_einbiegen')),
        ('davon Auffahren', ('konflikte_fz', 'auffahren')),
        ('davon mit Rad', ('konflikte_fz', 'mit_rad')),
        ('davon mit Bus oder Lkw', ('konflikte_fz', 'mit_bus_lkw')),
        ('davon schwer (TTC < 1 s oder PET < 0,5 s)', ('konflikte_fz', 'schwer')),
        ('Fußgänger auf Querung, Fahrzeug über 15 km/h müsste mit über 3 m/s² bremsen', ('konflikte_fuss', 'alle')),
        ('davon Fahrzeug schneller als 30 km/h', ('konflikte_fuss', 'ueber30')),
        ('davon durch Rad', ('konflikte_fuss', 'durch_rad')),
        ('Mittlerer Zeitverlust Kfz in s', ('zeitverlust_s', 'alle|Kfz')),
        ('Mittlerer Zeitverlust Rad in s', ('zeitverlust_s', 'alle|Rad')),
        ('Mittlerer Zeitverlust Bus in s', ('zeitverlust_s', 'alle|Bus')),
        ('Mittlere Wartezeit Fußgänger in s', ('fuss_wartezeit_s', 'alle')),
        ('Mittlerer Zeitverlust Fußgänger in s', ('fuss_zeitverlust_s', 'alle')),
        ('Teleports (Verklemmungen im Modell)', ('teleports', 'alle')),
        ('Überlappungen im Modell (SUMO-Zusammenstöße, Modellfehler)', ('ueberlappungen', 'alle')),
        ('Überschneidungen im Knoteninneren (SSM-Typ 111, nicht mitgezählt)', ('konflikte_fz', 'ueberschneidung')),
    ]
    for name, key in zeilen:
        L.append(f'| {name} | ' + ' | '.join(ms(data[v][key]) for v in vs) + ' |')

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
    ap.add_argument('--varianten', nargs='+', default=VARIANTEN, choices=VARIANTEN)
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 2)
    ap.add_argument('--behalte-roh', action='store_true', help='Rohdaten nicht loeschen')
    ap.add_argument('--nur-bericht', action='store_true', help='nur vergleich.md aus kennzahlen.csv neu schreiben')
    args = ap.parse_args()
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
