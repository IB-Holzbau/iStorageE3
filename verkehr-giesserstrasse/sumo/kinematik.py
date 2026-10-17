"""Fahrzeugkinematik fuer Darstellung und Pruefungen.

SUMO liefert je Zeitschritt die Position der Fahrzeugfront und die Richtung der Fahrspur dort.
Daraus wird hier die Lage der Fahrzeugglieder berechnet wie im Browsermodell der Initiative
(modell/src/sim.js, rigidUpdate und artUpdate): Die Vorderachse folgt der Bahn, die Hinterachse
laeuft als Schleppkurve (Traktrix) nach. Gelenkbus und Sattelzug haben zwei Glieder, beim
Gelenkbus fuehren die zweite und dritte Achse mit den Anteilen k1 und k2 zur Bahn zurueck
(Lenkunterstuetzung wie bei Bussen mit gelenkter Nachlaufachse).

Winkel sind SUMO-Winkel in Grad (0 = Nord, im Uhrzeigersinn), Koordinaten SUMO-Meter (y nach oben).
"""
import math

# Masse in Metern (aus sim.js, RIG und ART)
GEOM = {
    'pkw': dict(art=False, fo=0.9, wb=2.7, ro=0.9, w=1.85),
    'lkw': dict(art=False, fo=1.4, wb=5.0, ro=3.6, w=2.5),
    'rad': dict(art=False, fo=0.35, wb=1.1, ro=0.35, w=0.65),
    'bus': dict(art=True, front=2.7, wb=5.9, hitch=-1.6, back=1.9, fo=0.3, L=5.9, ro=2.0, k1=0.35, k2=0.5, w=2.55),
    'sattel': dict(art=True, front=1.4, wb=3.7, hitch=0.5, back=1.0, fo=1.6, L=7.8, ro=4.2, k1=0.0, k2=0.0, w=2.55),
}
SCHRITT_M = 0.25        # Unterteilung der Bahn fuer die Schleppkurve


def richtung(winkel):
    a = math.radians(winkel)
    return math.sin(a), math.cos(a)


def winkel_von(ux, uy):
    return math.degrees(math.atan2(ux, uy)) % 360


class Bahn:
    """Bahn der Vorderachse mit Bogenlaenge, nach hinten gerade verlaengert."""

    def __init__(self, p0, u0):
        self.pts = [p0]
        self.cum = [0.0]
        self.u0 = u0

    def add(self, p):
        q = self.pts[-1]
        d = math.hypot(p[0] - q[0], p[1] - q[1])
        if d < 1e-6:
            return
        self.pts.append(p)
        self.cum.append(self.cum[-1] + d)

    @property
    def s(self):
        return self.cum[-1]

    def punkt(self, s):
        if s <= 0:
            return (self.pts[0][0] + self.u0[0] * s, self.pts[0][1] + self.u0[1] * s)
        lo, hi = 0, len(self.cum) - 1
        if s >= self.cum[hi]:
            return self.pts[hi]
        while hi - lo > 1:
            m = (lo + hi) // 2
            if self.cum[m] <= s:
                lo = m
            else:
                hi = m
        d = self.cum[hi] - self.cum[lo]
        f = (s - self.cum[lo]) / d if d else 0
        a, b = self.pts[lo], self.pts[hi]
        return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)


def _nachziehen(vorne, hinten, abstand):
    dx, dy = vorne[0] - hinten[0], vorne[1] - hinten[1]
    d = math.hypot(dx, dy) or 1e-9
    return (vorne[0] - dx / d * abstand, vorne[1] - dy / d * abstand), (dx / d, dy / d)


def posen(typ, xs, ys, winkel):
    """Lage je Zeitschritt: Liste von (Fx, Fy, h1, h2). F ist die Vorderachse, h1 und h2 sind die
    Richtungen der Glieder (h2 None bei starren Fahrzeugen). Eingabe ist die SUMO-Frontposition."""
    g = GEOM[typ]
    vorn = g['front'] if g['art'] else g['fo']
    u0 = richtung(winkel[0])
    F0 = (xs[0] - u0[0] * vorn, ys[0] - u0[1] * vorn)
    bahn = Bahn(F0, u0)
    out = []
    if not g['art']:
        R = (F0[0] - u0[0] * g['wb'], F0[1] - u0[1] * g['wb'])
        h = u0
        for i, (x, y, w) in enumerate(zip(xs, ys, winkel)):
            u = richtung(w)
            F = (x - u[0] * vorn, y - u[1] * vorn)
            if i:
                _unterteilt(bahn, F)
                for p in bahn_neu(bahn):
                    R, h = _nachziehen(p, R, g['wb'])
            out.append((F[0], F[1], winkel_von(*h), None))
        return out
    wb, hitch, L = g['wb'], g['hitch'], g['L']
    A = bahn.punkt(-wb)
    T = bahn.punkt(-(wb - hitch) - L)
    u1 = u2 = u0
    for i, (x, y, w) in enumerate(zip(xs, ys, winkel)):
        u = richtung(w)
        F = (x - u[0] * vorn, y - u[1] * vorn)
        if i:
            _unterteilt(bahn, F)
            for p in bahn_neu(bahn):
                A, u1 = _nachziehen(p, A, wb)
                if g['k1']:
                    Ap = bahn.punkt(bahn.s_teil - wb)
                    A = (A[0] + (Ap[0] - A[0]) * g['k1'], A[1] + (Ap[1] - A[1]) * g['k1'])
                    A, u1 = _nachziehen(p, A, wb)
                H = (A[0] + u1[0] * hitch, A[1] + u1[1] * hitch)
                T, u2 = _nachziehen(H, T, L)
                if g['k2']:
                    Tp = bahn.punkt(bahn.s_teil - (wb - hitch + L))
                    T = (T[0] + (Tp[0] - T[0]) * g['k2'], T[1] + (Tp[1] - T[1]) * g['k2'])
                    T, u2 = _nachziehen(H, T, L)
        out.append((F[0], F[1], winkel_von(*u1), winkel_von(*u2)))
    return out


def _unterteilt(bahn, F):
    """Haengt F an die Bahn an, in Schritten von hoechstens SCHRITT_M, und merkt sich die neuen Punkte."""
    q = bahn.pts[-1]
    d = math.hypot(F[0] - q[0], F[1] - q[1])
    n = max(1, int(math.ceil(d / SCHRITT_M)))
    bahn._neu = []
    for k in range(1, n + 1):
        p = (q[0] + (F[0] - q[0]) * k / n, q[1] + (F[1] - q[1]) * k / n)
        bahn.add(p)
        bahn._neu.append((p, bahn.s))


def bahn_neu(bahn):
    for p, s in getattr(bahn, '_neu', []):
        bahn.s_teil = s
        yield p


def umrisse(typ, F, h1, h2, schrumpf=0.0):
    """Eckpunkte der Glieder als Listen von vier Punkten."""
    g = GEOM[typ]
    w = g['w'] / 2 - schrumpf
    u1 = richtung(h1)

    def rechteck(vorn, hinten, u):
        n = (u[1], -u[0])
        return [(vorn[0] + n[0] * w, vorn[1] + n[1] * w), (vorn[0] - n[0] * w, vorn[1] - n[1] * w),
                (hinten[0] - n[0] * w, hinten[1] - n[1] * w), (hinten[0] + n[0] * w, hinten[1] + n[1] * w)]
    if not g['art']:
        vorn = (F[0] + u1[0] * (g['fo'] - schrumpf), F[1] + u1[1] * (g['fo'] - schrumpf))
        hinten = (F[0] - u1[0] * (g['wb'] + g['ro'] - schrumpf), F[1] - u1[1] * (g['wb'] + g['ro'] - schrumpf))
        return [rechteck(vorn, hinten, u1)]
    u2 = richtung(h2)
    A = (F[0] - u1[0] * g['wb'], F[1] - u1[1] * g['wb'])
    v1 = (F[0] + u1[0] * (g['front'] - schrumpf), F[1] + u1[1] * (g['front'] - schrumpf))
    h1p = (A[0] - u1[0] * (g['back'] - schrumpf), A[1] - u1[1] * (g['back'] - schrumpf))
    H = (A[0] + u1[0] * g['hitch'], A[1] + u1[1] * g['hitch'])
    v2 = (H[0] + u2[0] * (g['fo'] - schrumpf), H[1] + u2[1] * (g['fo'] - schrumpf))
    h2p = (H[0] - u2[0] * (g['L'] + g['ro'] - schrumpf), H[1] - u2[1] * (g['L'] + g['ro'] - schrumpf))
    return [rechteck(v1, h1p, u1), rechteck(v2, h2p, u2)]


def blinker(winkel, xs, ys, schritte_voraus, radius=45.0):
    """Blinker je Zeitschritt: 0 aus, 1 links, 2 rechts. Geblinkt wird, wenn sich die Richtung
    in den naechsten Schritten um mehr als 30 Grad aendert und das Fahrzeug nahe am Knoten ist."""
    n = len(winkel)
    out = [0] * n
    for i in range(n):
        if math.hypot(xs[i], ys[i]) > radius:
            continue
        best = 0.0
        for k in range(i + 1, min(n, i + schritte_voraus)):
            d = (winkel[k] - winkel[i] + 180) % 360 - 180
            if abs(d) > abs(best):
                best = d
        if abs(best) > 30:
            out[i] = 2 if best > 0 else 1
    return out
