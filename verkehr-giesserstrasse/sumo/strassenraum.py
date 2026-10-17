"""Fahrbahn, Inseln und Radwege als Flaechen (shapely) fuer Darstellung und Pruefungen.

Die Fahrbahn wird aus den Achsen und Querschnitten in build.py selbst konstruiert: vier gerade
Arme konstanter Breite und die Bordsteinecken nach Beobachtung. In der geschuetzten Kreuzung
ersetzen am Knoten Inseln und Radwege die Parkstreifen, die Fahrbahnecken sind enger.
"""
import json
import math
import os

from shapely.geometry import LineString, Polygon, Point, shape
from shapely.ops import unary_union

import build as B

ROOT = os.path.dirname(os.path.abspath(__file__))


def _einheit(x, y):
    d = math.hypot(x, y) or 1.0
    return x / d, y / d


def _schnitt(p, u, q, v):
    det = u[0] * (-v[1]) - u[1] * (-v[0])
    t = ((q[0] - p[0]) * (-v[1]) - (q[1] - p[1]) * (-v[0])) / det
    return (p[0] + u[0] * t, p[1] + u[1] * t)


def _ausrundung(V, a, b, r, n=10):
    """Rundet die Blockecke V mit den Kantenrichtungen a und b (Einheitsvektoren, vom
    Eckpunkt weg) mit Radius r. Gibt die Bogenpunkte von der a-Seite zur b-Seite zurueck."""
    cosw = max(-1.0, min(1.0, a[0] * b[0] + a[1] * b[1]))
    w = math.acos(cosw)
    t = r / math.tan(w / 2)
    h = _einheit(a[0] + b[0], a[1] + b[1])
    m = r / math.sin(w / 2)
    C = (V[0] + h[0] * m, V[1] + h[1] * m)
    Ta = (V[0] + a[0] * t, V[1] + a[1] * t)
    Tb = (V[0] + b[0] * t, V[1] + b[1] * t)
    wa = math.atan2(Ta[1] - C[1], Ta[0] - C[0])
    wb = math.atan2(Tb[1] - C[1], Tb[0] - C[0])
    d = (wb - wa + math.pi) % (2 * math.pi) - math.pi
    return [(C[0] + r * math.cos(wa + d * i / n), C[1] + r * math.sin(wa + d * i / n)) for i in range(n + 1)]


_CACHE = {}


def _arme():
    if 'arme' not in _CACHE:
        _CACHE['arme'] = B.achsen()
    return _CACHE['arme']


def _arm_rechteck(R, s0, s1, q_rechts, q_links):
    return Polygon([R.punkt(s0, q_rechts), R.punkt(s1, q_rechts), R.punkt(s1, -q_links), R.punkt(s0, -q_links)])


def fahrbahn_bestand():
    """Fahrbahn heute: Arme mit Parkstreifen, Nordecken rund, Suedecken abgeschraegt."""
    if 'bestand' in _CACHE:
        return _CACHE['bestand']
    arme = _arme()
    info, teile = {}, []
    for a, achse in arme.items():
        R = B.Rahmen(a, achse)
        wr, wl = B.breite(a, 'out'), B.breite(a, 'in')
        info[a] = dict(u=R.u, rechts=R.punkt(0, wr), links=R.punkt(0, -wl))
        teile.append(_arm_rechteck(R, -3.0, B.ARM_LEN, wr, wl))
    for name, art in B.ECKEN.items():
        a, b = name[0], name[1]
        P = _schnitt(info[a]['rechts'], info[a]['u'], info[b]['links'], info[b]['u'])
        ua, ub = info[a]['u'], info[b]['u']
        if art[0] == 'rund':
            bogen = _ausrundung(P, ua, ub, art[1])
        else:
            c, r = art[1], art[2]
            Aa = (P[0] + ua[0] * c, P[1] + ua[1] * c)
            Ab = (P[0] + ub[0] * c, P[1] + ub[1] * c)
            k = _einheit(Ab[0] - Aa[0], Ab[1] - Aa[1])
            bogen = _ausrundung(Aa, ua, k, r) + _ausrundung(Ab, (-k[0], -k[1]), ub, r)
        teile.append(Polygon([P] + bogen).buffer(0))
    g = unary_union(teile).buffer(0.01).buffer(-0.01)
    _CACHE['bestand'] = g
    return g


# Ecke -> (Arm a, Seite a, Arm b, Seite b), gegen den Uhrzeigersinn um den Knoten
ECKSEITEN = {'SW': ('W', 'in', 'S', 'out'), 'SE': ('S', 'in', 'E', 'out'),
             'NE': ('E', 'in', 'N', 'out'), 'NW': ('N', 'in', 'W', 'out')}


def _halb(R, s0, s1, q0, q1):
    return Polygon([R.punkt(s0, q0), R.punkt(s1, q0), R.punkt(s1, q1), R.punkt(s0, q1)])


def geschuetzt(roh=False):
    """Fahrbahn, Inseln, Radwege und Radfurten der geschuetzten Kreuzung (angepasst).
    Ohne roh wird die Fahrbahn um die Flaeche erweitert, die Pkw beim Abbiegen brauchen
    (werkzeuge/schleppkurve.py), und was schwere Fahrzeuge darueber hinaus brauchen, wird
    ueberfahrbares Pflaster."""
    key = 'gesch_roh' if roh else 'gesch'
    if key in _CACHE:
        return _CACHE[key]
    arme = _arme()
    G = B.geschuetzt_geometrie(arme)
    R = G['R']
    # Bis wohin am Knoten Inseln bzw. Radweg den Parkstreifen ersetzen, je Arm und Seite
    innen = {('W', 'in'): G['b_s']['W'], ('S', 'out'): G['b_s']['S'], ('E', 'out'): G['b_s']['E'],
             ('E', 'in'): G['d_p']['E'] + 1.5}
    teile = []
    for a in arme:
        r = R[a]
        for seite in ('out', 'in'):
            sg = 1 if seite == 'out' else -1
            s_i = innen.get((a, seite), 0.0)
            if s_i > 0:
                teile.append(_halb(r, -3.0, s_i, 0, sg * B.kfz_breite(a, seite)))
            teile.append(_halb(r, max(s_i, -3.0), B.ARM_LEN, 0, sg * B.breite(a, seite)))
    # Fahrbahnecken: an den Inseln eng, Nordwestecke wie heute
    radien = {'SW': B.G_RADIUS, 'SE': B.G_RADIUS, 'NE': 3.0, 'NW': 5.0}
    for c, (a, sa, b, sb) in ECKSEITEN.items():
        ga, gb = R[a].kante(sa, 0), R[b].kante(sb, 0)
        P = B.schnitt(ga, gb)
        bogen = _ausrundung(P, ga[1], gb[1], radien[c])
        teile.append(Polygon([P] + bogen).buffer(0))
    fb = unary_union(teile).buffer(0.01).buffer(-0.01)

    linien = {eid: LineString(pts) for eid, (_, _, pts) in G['rad'].items()}
    rad = unary_union([l.buffer(B.G_RAD_B / 2, cap_style=2, join_style=2) for l in linien.values()])
    # Inselbereich: Ecke zwischen Fahrbahnkante und Radfurt, Streifen zwischen Fahrbahn und Radweg
    zonen = []
    for c in ('SW', 'SE', 'NE'):
        a, sa, b, sb = ECKSEITEN[c]
        ga, gb = R[a].kante(sa, 0), R[b].kante(sb, 0)
        K = B.schnitt(ga, gb)
        C = G['ecke'][c]
        A1 = R[a].punkt(R[a].lokal(C)[0], R[a].lokal(K)[1])
        A2 = R[b].punkt(R[b].lokal(C)[0], R[b].lokal(K)[1])
        zonen.append(Polygon([K, A1, C, A2]).buffer(0))
    armseite = {'aW': ('W', 'in'), 'aS': ('S', 'in'), 'xS': ('S', 'out'), 'xE': ('E', 'out')}
    for eid, (arm, seite) in armseite.items():
        pts = G['rad'][eid][2]
        r = R[arm]
        kw = B.kfz_breite(arm, seite)
        sg = 1 if seite == 'out' else -1
        fuss = [r.punkt(r.lokal(p)[0], sg * kw) for p in pts]
        poly = Polygon(pts + list(reversed(fuss))).buffer(0)
        if not poly.is_empty:
            zonen.append(poly)
    # Ostarm Nordseite: Insel anstelle der ersten Meter Parken bis hinter den Zebrastreifen
    rE = R['E']
    zonen.append(_halb(rE, 0, innen[('E', 'in')], -B.kfz_breite('E', 'in'), -B.breite('E', 'in')))
    zone = unary_union(zonen)
    rad_zone = rad.buffer(0.05)
    pflaster = Polygon()
    datei = os.path.join(ROOT, 'netze', 'schleppkurve_geschuetzt.json')
    if not roh and os.path.exists(datei):
        with open(datei) as f:
            d = json.load(f)
        if d.get('pkw'):
            pkw = shape(d['pkw']).buffer(0.3)
            nah = Point(0, 0).buffer(30)
            fb = unary_union([fb, pkw.intersection(nah)]).buffer(0.01).buffer(-0.01)
        if d.get('schwer'):
            pflaster = shape(d['schwer']).buffer(0.2)
    insel = zone.difference(fb).difference(rad_zone).buffer(-0.05).buffer(0.05)
    insel = unary_union([g for g in getattr(insel, 'geoms', [insel]) if g.area > 0.3])
    pflaster = pflaster.intersection(insel) if not pflaster.is_empty else pflaster
    res = dict(fahrbahn=fb, insel=insel, rad=rad, linien=linien, G=G, pflaster=pflaster)
    _CACHE[key] = res
    return res


def fahrbahn(var):
    if var == 'geschuetzt':
        return geschuetzt()['fahrbahn']
    return fahrbahn_bestand()


def inseln(var):
    if var == 'geschuetzt':
        return geschuetzt()['insel']
    if var == 'minikreisel':
        return Point(0, 0).buffer(B.KREISEL_R - 0.3)
    return Polygon()
