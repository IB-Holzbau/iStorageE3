"""Kritische Szenen fuer den Abspieler, aus den echten SUMO-Laeufen gesucht.

Grundlage sind die Rohdaten des ersten Laufs je Variante aus run.py (ergebnisse/roh/<var>_01,
Startwert 1, Schrittweite 0,5 s). Fuer die seltene Szene 1 (Kinderwagen) werden alle Laeufe
durchsucht, dafuer run.py mit --behalte-roh starten. Jede Szene hat einen Suchfilter. Gewaehlt wird je Variante die
deutlichste echte Stelle. Daraus wird ein kurzer Ausschnitt (etwa 12 s vor bis 10 s nach dem
kritischen Moment) mit allen Fahrzeugen und Fussgaengern kodiert. Es wird nichts erfunden: findet
der Filter in einer Variante nichts, gibt es dort keinen Ausschnitt, sondern nur die Kennzahl.
"""
import math
import os
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

HIER = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HIER)
sys.path.insert(0, ROOT)
import run as R      # noqa: E402

ROH = os.path.join(ROOT, 'ergebnisse', 'roh')
DT = R.SCHRITT
VOR, NACH, VORLAUF = 12.0, 10.0, 20.0
WARMUP, ENDE = R.WARMUP, R.WARMUP + R.DAUER

# Texte in einfacher Sprache
SZENEN = [
    dict(nr=1, titel='Kinderwagen an der Nordquerung, von Süden kommt es schnell',
         text='Eine Person mit Kinderwagen will an der Nordquerung von West nach Ost über die Gießerstraße. Beim Warten ragt der Kinderwagen etwa 1 m in die Fahrbahn. Sie muss dreimal schauen, nach Süden, nach Norden und wieder nach Süden. Von Süden kommt ein Auto mit {kmh} km/h.',
         kennzahl=('fuss', 'Fußgänger auf der Querung bedrängt')),
    dict(nr=2, titel='Rad biegt nach Nord ab und steht im Verkehr',
         text='Ein Rad will von West nach Nord links abbiegen. Es steht {warte} Sekunden mitten im Knoten, um es herum fährt der Verkehr der Vorfahrtstraße.',
         kennzahl=('rad', 'Konflikte Kfz gegen Rad')),
    dict(nr=3, titel='Nord gegen Ost, wer darf zuerst?',
         text='Aus Nord und aus Ost wollen zwei Fahrzeuge gleichzeitig los. Beide müssen die Vorfahrtstraße beachten, untereinander gilt rechts vor links. Das ist schwer zu durchschauen, es wird knapp.',
         text_zone='In der Zone gilt überall rechts vor links. Nord und Ost begegnen sich mit einfacher Regel.',
         kennzahl=('konflikte', 'Fahrzeugkonflikte je Stunde')),
    dict(nr=4, titel='Engstelle Ost, Begegnung zwischen Parkern',
         text='Auf der Naumburger Straße Ost parken beidseitig Autos bis an die Ecke. Zwei Fahrzeuge begegnen sich in der engen Restfahrbahn. Im Modell kommen sie knapp aneinander vorbei, in echt muss oft einer warten.',
         kennzahl=None),
    dict(nr=5, titel='Stopp Nord, Vorfahrt genommen',
         text='Ein Fahrzeug fährt nach dem Halt am Stoppschild los und schneidet {opfer} auf der Vorfahrtstraße. Es wird knapp.',
         text_zone='In der Zone gibt es kein Stoppschild mehr. Ein Fahrzeug aus Nord fährt in den Knoten und kommt {opfer} aus Süd oder West nahe. Alle fahren hier langsamer.',
         kennzahl=('schwer', 'schwere Fahrzeugkonflikte')),
    dict(nr=6, titel='Ohne Blinker geradeaus aus der Abbiegespur',
         text='Ein Auto (orange) fährt in der Linksabbiegespur, blinkt aber nicht, denn es will geradeaus nach Nord. Wer an der Nordquerung oder in Nord und Ost wartet, kann nicht erkennen, ob es abbiegt. Dann fährt es geradeaus auf die Querung zu.',
         kennzahl=('fehlspur', 'Konflikte durch Geradeausfahrer aus der Abbiegespur')),
    dict(nr=7, titel='Bus wechselt nach dem Halt quer auf die Abbiegespur',
         text='Der Bus nach West hält rechts. Danach muss er quer über die Geradeausspur auf die Linksabbiegespur wechseln.',
         kennzahl=None),
    dict(nr=8, titel='Sicht vom Kiosk über die Naumburger Straße',
         text='Wer vom Kiosk über die Naumburger Straße West will, sieht wegen Schaltkasten und Parkern die Autos spät. Grüne Linien zeigen, wen die Person sieht, rote gestrichelte, wer verdeckt ist.',
         kennzahl=('fuss', 'Fußgänger auf der Querung bedrängt')),
    dict(nr=9, titel='Kurzhalter am Kiosk im Haltverbot',
         text='Jemand hält mit Warnblinker im absoluten Haltverbot auf der Nordseite der Naumburger Straße und holt schnell etwas am Kiosk. Der Wagen verdeckt die Sicht, die Person quert die Straße. Die Person ist nur gezeichnet, SUMO lässt die anderen Fahrzeuge am Halter vorbei.',
         kennzahl=None),
]


def herkunft(vid):
    try:
        return vid.split('_')[1][0]
    except IndexError:
        return '?'


def lade(var, lauf=1):
    """Liest FCD und SSM eines Laufs (Standard Lauf 1). Gibt Zeitschritte und Konflikte zurueck."""
    d = os.path.join(ROH, f'{var}_{lauf:02d}')
    zeit = []
    for _, ts in ET.iterparse(os.path.join(d, 'fcd.xml')):
        if ts.tag != 'timestep':
            continue
        t = float(ts.get('time'))
        fz = [(v.get('id'), float(v.get('x')), float(v.get('y')), float(v.get('angle')), float(v.get('speed')),
               v.get('lane') or '', float(v.get('pos') or 0)) for v in ts.findall('vehicle')]
        ps = [(p.get('id'), float(p.get('x')), float(p.get('y')), float(p.get('angle')), float(p.get('speed')),
               p.get('edge') or '') for p in ts.findall('person')]
        zeit.append((t, fz, ps))
        ts.clear()
    konf = []
    for c in ET.parse(os.path.join(d, 'ssm.xml')).getroot().findall('conflict'):
        def w(tag, attr='value'):
            e = c.find(tag)
            return None if e is None or e.get(attr) in (None, 'NA') else e.get(attr)
        for tag in ('minTTC', 'PET'):
            v, t, pos, sp = w(tag), w(tag, 'time'), w(tag, 'position'), w(tag, 'speed')
            if v is None or t is None or pos is None:
                continue
            if w(tag, 'type') == '111':
                continue
            x, y = map(float, pos.split(','))
            if math.hypot(x, y) > R.KNOTENBEREICH:
                continue
            konf.append(dict(ego=c.get('ego'), foe=c.get('foe'), art=tag, wert=float(v), t=float(t), x=x, y=y,
                             langsam=float(sp or 0) < R.KONFLIKT_TEMPO))
    return zeit, konf


def im_fenster(t):
    return WARMUP + VOR <= t <= ENDE - NACH


# ---------------------------------------------------------------- Suchfilter
def s1_kinderwagen_suche(var, mn):
    """Szene 1: Person mit Kinderwagen (pKiwa) wartet an der Westseite der Nordquerung, ein
    Fahrzeug aus Sued faehrt vorbei. Kinderwagen sind selten (etwa 6 je Stunde), deshalb werden
    alle gespeicherten Laeufe durchsucht. Gewertet wird das Tempo des Fahrzeugs plus die
    Wartezeit (hoechstens 6 s). Gibt (wert, lauf, t, person, fahrzeug, kmh) zurueck."""
    best = None
    for lauf in range(1, 11):
        f = os.path.join(ROH, f'{var}_{lauf:02d}', 'fcd.xml')
        if not os.path.exists(f):
            continue
        warte = defaultdict(float)
        for _, ts in ET.iterparse(f):
            if ts.tag != 'timestep':
                continue
            t = float(ts.get('time'))
            if not im_fenster(t):
                ts.clear()
                continue
            ks = [p for p in ts.findall('person') if p.get('id').startswith('pKiwa') and p.get('edge') == ':MN_w0'
                  and float(p.get('speed')) < 0.2]
            for p in ks:
                warte[p.get('id')] += DT
            for p in ks:
                if warte[p.get('id')] < 2:
                    continue
                for v in ts.findall('vehicle'):
                    if herkunft(v.get('id')) != 'S' or float(v.get('speed')) < 5:
                        continue
                    a = math.radians(float(v.get('angle')))
                    ux, uy = math.sin(a), math.cos(a)
                    dx, dy = mn[0] - float(v.get('x')), mn[1] - float(v.get('y'))
                    d = dx * ux + dy * uy
                    if not 0 < d < 20 or abs(dx * uy - dy * ux) > 6:
                        continue
                    kmh = float(v.get('speed')) * 3.6
                    wert = kmh + min(warte[p.get('id')], 6) - d * 0.1
                    if best is None or wert > best[0]:
                        best = (wert, lauf, t, p.get('id'), v.get('id'), round(kmh))
            ts.clear()
    return best


def s2_rad_links(zeit, konf):
    warte = defaultdict(float)
    best = None
    for t, fz, ps in zeit:
        for v in fz:
            if v[0].startswith('rad_WN') and v[5].startswith(':J') and v[4] < 0.5:
                warte[v[0]] += DT
                if im_fenster(t) and warte[v[0]] >= 2:
                    um = sum(1 for o in fz if o[0] != v[0] and o[4] > 3 and math.hypot(o[1] - v[1], o[2] - v[2]) < 15)
                    sc = warte[v[0]] + um
                    if best is None or sc > best[0]:
                        best = (sc, t, [v[0]], (v[1], v[2]), dict(warte=round(warte[v[0]])))
    return best


def _konflikt(konf, test, auch_langsam=False):
    best = None
    for c in konf:
        if not im_fenster(c['t']) or not test(c['ego'], c['foe']) or (c['langsam'] and not auch_langsam):
            continue
        sc = -c['wert']
        if best is None or sc > best[0]:
            best = (sc, c['t'], [c['ego'], c['foe']], (c['x'], c['y']), {})
    return best


def s3_nord_ost(zeit, konf):
    # Nord und Ost treffen sich meist langsam, deshalb hier auch Konflikte unter 15 km/h
    r = _konflikt(konf, lambda a, b: {herkunft(a), herkunft(b)} == {'N', 'E'}, auch_langsam=True)
    if r:
        return r
    # sonst aus den Bewegungsdaten: je ein Fahrzeug aus Nord und Ost gleichzeitig am Knoten, eines
    # faehrt schon ein (engste Begegnung)
    best = None
    for t, fz, ps in zeit:
        if not im_fenster(t):
            continue
        n = [v for v in fz if herkunft(v[0]) == 'N' and math.hypot(v[1], v[2]) < 16]
        e = [v for v in fz if herkunft(v[0]) == 'E' and math.hypot(v[1], v[2]) < 16]
        for a in n:
            for b in e:
                if max(a[4], b[4]) < 1.0:
                    continue
                d = math.hypot(a[1] - b[1], a[2] - b[2])
                if best is None or -d > best[0]:
                    best = (-d, t, [a[0], b[0]], ((a[1] + b[1]) / 2, (a[2] + b[2]) / 2), {})
    return best


def s4_engstelle(zeit, konf):
    best = None
    for t, fz, ps in zeit:
        if not im_fenster(t):
            continue
        ost = [v for v in fz if v[1] > 8 and v[1] < 45 and abs(v[2]) < 8 and v[4] > 1]
        for a in ost:
            for b in ost:
                if a[0] >= b[0]:
                    continue
                gegen = abs(((a[3] - b[3]) + 180) % 360 - 180) > 150
                d = math.hypot(a[1] - b[1], a[2] - b[2])
                if not gegen or d > 14:
                    continue
                schwer = sum(1 for v in (a, b) if R.typ_von(v[0]) in ('lkw', 'sattel', 'bus'))
                sc = schwer * 10 + (14 - d)
                if best is None or sc > best[0]:
                    best = (sc, t, [a[0], b[0]], ((a[1] + b[1]) / 2, (a[2] + b[2]) / 2), {})
    return best


def s5_stopp(zeit, konf):
    def test(a, b):
        for n, o in ((a, b), (b, a)):
            if herkunft(n) == 'N' and R.typ_von(n) != 'rad' and herkunft(o) in ('S', 'W') and o.split('_')[1][:2] in ('SW', 'WS'):
                return True
        return False
    r = _konflikt(konf, lambda a, b: test(a, b) and 'rad' in (R.typ_von(a), R.typ_von(b)))
    if r:
        r[4]['opfer'] = 'ein Rad'
        return r
    r = _konflikt(konf, test)
    if r:
        r[4]['opfer'] = 'ein Auto'
    return r


def s6_fehlspur(zeit, konf, mn):
    best = None
    for t, fz, ps in zeit:
        if not im_fenster(t):
            continue
        for v in fz:
            if '_SNx' not in v[0] or math.hypot(v[1] - mn[0], v[2] - mn[1]) > 18:
                continue
            nahe = [p for p in ps if math.hypot(p[1] - mn[0], p[2] - mn[1]) < 6]
            sc = (10 if nahe else 0) + v[4] - math.hypot(v[1] - mn[0], v[2] - mn[1]) * 0.1
            if best is None or sc > best[0]:
                best = (sc, t, [v[0]] + ([nahe[0][0]] if nahe else []), (mn[0], mn[1]), {})
    return best


def s7_bus(zeit, konf):
    vorher = {}
    best = None
    for t, fz, ps in zeit:
        for v in fz:
            if not v[0].startswith('bus_SW'):
                continue
            e, _, i = v[5].rpartition('_')
            if e in ('S_in_mitte', 'S_in') and v[0] in vorher and vorher[v[0]] != v[5] and vorher[v[0]].rpartition('_')[0] == e:
                if im_fenster(t):
                    um = sum(1 for o in fz if o[0] != v[0] and math.hypot(o[1] - v[1], o[2] - v[2]) < 20)
                    if best is None or um > best[0]:
                        best = (um, t, [v[0]], (v[1], v[2]), {})
            vorher[v[0]] = v[5]
    return best


def s9_kurz(zeit, konf):
    steh = defaultdict(float)
    best = None
    for t, fz, ps in zeit:
        for v in fz:
            if '.k' in v[0] and v[4] < 0.1 and v[1] < -8:
                steh[v[0]] += DT
                if im_fenster(t) and steh[v[0]] > 20:
                    nah = sum(1 for o in fz if o[0] != v[0] and o[4] > 2 and math.hypot(o[1] - v[1], o[2] - v[2]) < 25)
                    sc = nah - abs(steh[v[0]] - 40) * 0.05
                    if best is None or sc > best[0]:
                        best = (sc, t, [v[0], 'kurz_' + v[0]], (v[1], v[2]), {})
    return best


def s8_kiosk(zeit, konf, mw):
    warte = defaultdict(float)
    best = None
    for t, fz, ps in zeit:
        for p in ps:
            if p[4] < 0.15 and math.hypot(p[1] - mw[0], p[2] - mw[1]) < 6 and p[2] < mw[1] + 1:
                warte[p[0]] += DT
                if im_fenster(t) and warte[p[0]] >= 1.5:
                    nah = sum(1 for v in fz if v[4] > 3 and math.hypot(v[1] - p[1], v[2] - p[2]) < 35)
                    sc = nah + warte[p[0]] * 0.2
                    if best is None or sc > best[0]:
                        best = (sc, t, [p[0]], (p[1], p[2]), {})
    return best


# ---------------------------------------------------------------- Ausschnitt
def ausschnitt(zeit, konf, te, fokus, export):
    t0, t1 = te - VOR, te + NACH
    roh = defaultdict(list)
    for t, fz, ps in zeit:
        if t < t0 - VORLAUF or t > t1:
            continue
        fr = int(round((t - t0) / DT))
        for v in fz:
            roh[v[0]].append((fr, v[1], v[2], v[3], v[5]))
        if fr >= 0:
            for p in ps:
                roh['p:' + p[0]].append((fr, p[1], p[2], 0.0, p[5]))
    tracks, ids = export.kodiere(roh, DT, fenster=False)
    kurz = [k for k, i in enumerate(ids) if '.k' in i and not i.startswith('p:')]
    fk = []
    for f in fokus:
        for key in (f, 'p:' + f):
            if key in ids:
                fk.append(ids.index(key))
                break
    ringe = [[round(c['t'] - t0, 1), round(c['x'], 2), round(-c['y'], 2), 'k', 1 if c['wert'] < 1 else 0]
             for c in konf if t0 <= c['t'] <= t1 and not c['langsam']]
    return dict(n=int(round((t1 - t0) / DT)) + 1, schritt=DT, tracks=tracks, konflikte=sorted(ringe),
                te=round(te - t0, 1), fokus=fk, kurz=kurz)


def baue(varianten, export, mn, mw):
    """Gibt {'liste': SZENEN ohne Suchfunktion, 'clips': {nr: {var: clip}}} zurueck."""
    filter_ = {2: s2_rad_links, 3: s3_nord_ost, 4: s4_engstelle,
               5: s5_stopp, 6: lambda z, k: s6_fehlspur(z, k, mn), 7: s7_bus, 8: lambda z, k: s8_kiosk(z, k, mw),
               9: s9_kurz}
    clips = defaultdict(dict)
    texte = defaultdict(dict)
    for var in varianten:
        if not os.path.isdir(os.path.join(ROH, f'{var}_01')):
            continue
        zeit, konf = lade(var)
        for sz in SZENEN:
            lauf = 1
            if sz['nr'] == 1:
                k = s1_kinderwagen_suche(var, mn)
                if k:
                    _, lauf, te, pid, vid, kmh = k
                    z1, k1 = lade(var, lauf) if lauf != 1 else (zeit, konf)
                    pos = next((p[1], p[2]) for t, _, ps in z1 if abs(t - te) < 1e-6 for p in ps if p[0] == pid)
                    c = ausschnitt(z1, k1, te, [pid, vid], export)
                    c['blick'] = 'S'
                    r = None
                    extra = dict(kmh=kmh)
                else:
                    r = None
                    c = None
                if c is None:
                    print(f'   Szene 1 {var}: kein Kinderwagen gefunden')
                    continue
            else:
                r = filter_[sz['nr']](zeit, konf)
            if sz['nr'] != 1:
                if not r:
                    print(f'   Szene {sz["nr"]} {var}: nicht gefunden')
                    continue
                _, te, fokus, pos, extra = r
                c = ausschnitt(zeit, konf, te, fokus, export)
            c['lauf'] = lauf
            c['ort'] = [round(pos[0], 2), round(-pos[1], 2)]
            c['zeit'] = round(te - WARMUP)
            txt = sz.get('text_' + var, sz['text'])
            try:
                c['text'] = txt.format(**extra)
            except KeyError:
                c['text'] = sz['text']
            if lauf != 1:
                c['text'] += f' (Lauf {lauf} von 10)'
            clips[sz['nr']][var] = c
            print(f'   Szene {sz["nr"]} {var}: Lauf {lauf} bei {te - WARMUP:.0f} s, {len(c["tracks"])} Bahnen')
    liste = [{k: v for k, v in sz.items()} for sz in SZENEN]
    return {'liste': liste, 'clips': clips}
