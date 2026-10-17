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
    # k1 und k2 (Lenkunterstuetzung) sind 0: die vereinfachte Nachfuehrung machte den Hinterwagen
    # unruhig und den Knick zu gross, das Ausholen der Vorderachse ersetzt sie.
    'bus': dict(art=True, front=2.7, wb=5.9, hitch=-1.6, back=1.9, fo=0.3, L=5.9, ro=2.0, k1=0.0, k2=0.0, w=2.55),
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


# Groesster Knickwinkel zwischen Zugteil und Nachlaeufer in Grad (Gelenkbus etwa 40 bis 45,
# Sattelzug etwa 60 bis 70). Wird die Grenze erreicht, wird der Nachlaeufer mitgedreht.
KNICK_MAX = {'bus': 42.0, 'sattel': 65.0}
# Fahrzeuge, die beim Abbiegen ausholen: Ihre Hinterachse (beim Gelenkbus die Mittelachse) laeuft
# auf der SUMO-Bahn, die Vorderachse faehrt aussen einen weiteren Bogen. So laeuft das Heck innen
# nicht ueber den Bordstein, wie bei echten Bus- und Lkw-Fahrern.
AUSHOLEN = {'bus', 'lkw', 'sattel'}


def _tangente(bahn, s, h=0.75):
    a, b = bahn.punkt(s - h), bahn.punkt(s + h)
    return SR_einheit(b[0] - a[0], b[1] - a[1])


def SR_einheit(x, y):
    d = math.hypot(x, y) or 1e-9
    return x / d, y / d


def _begrenze(u1, u2, grenze):
    """Dreht u2 so weit zu u1, dass der Winkel zwischen beiden hoechstens grenze Grad ist."""
    w = math.degrees(math.atan2(u1[0] * u2[1] - u1[1] * u2[0], u1[0] * u2[0] + u1[1] * u2[1]))
    if abs(w) <= grenze:
        return u2, False
    g = math.radians(math.copysign(grenze, w))
    c, s_ = math.cos(g), math.sin(g)
    return (u1[0] * c - u1[1] * s_, u1[0] * s_ + u1[1] * c), True


# Groesste seitliche Geschwindigkeit der dargestellten Front in m/s. SUMO setzt Fahrzeuge an
# Uebergaengen zwischen Fahrspuren (z.B. am Ende des Haltebereichs) teils seitlich um; das wird
# hier auf ein weiches seitliches Wandern begrenzt (Spurwechsel ueber einige Sekunden).
V_SEITE = {'bus': 0.8, 'sattel': 0.8, 'lkw': 0.9, 'pkw': 1.2, 'rad': 1.0}
NEIGUNG = {'bus': 0.13, 'sattel': 0.13, 'lkw': 0.16, 'pkw': 0.25, 'rad': 0.35}


# Halbe Fensterlaenge in Metern fuer die Glaettung der Bahn entlang des Fahrwegs
GLATT_M = {'bus': 5.0, 'sattel': 5.0, 'lkw': 4.0, 'pkw': 2.0, 'rad': 1.0}


def glaetten(typ, xs, ys, winkel, dt):
    """Glaettet die SUMO-Frontbahn als gleitendes Mittel entlang des Fahrwegs (nicht der Zeit).
    Ein Spurwechsel, den SUMO beim langsamen Anfahren auf wenigen Metern macht, verteilt sich so
    ueber 10 bis 20 m, Kurven mit 8 bis 10 m Radius bleiben fast unveraendert. Im Stand bleibt
    der Punkt stehen. Gibt Positionen und Winkel (aus der geglaetteten Bahn) zurueck."""
    n = len(xs)
    h = GLATT_M.get(typ, 2.0)
    cum = [0.0]
    for i in range(1, n):
        cum.append(cum[-1] + math.hypot(xs[i] - xs[i - 1], ys[i] - ys[i - 1]))
    # gleichmaessig abgetastete Bahn (alle 0,25 m), am Anfang und Ende gerade verlaengert
    step = 0.25
    m = int(cum[-1] / step) + 1
    gx, gy = [], []
    j = 0
    for k in range(m):
        sv = k * step
        while j + 1 < n and cum[j + 1] < sv:
            j += 1
        if j + 1 < n and cum[j + 1] > cum[j]:
            f = (sv - cum[j]) / (cum[j + 1] - cum[j])
            gx.append(xs[j] + (xs[j + 1] - xs[j]) * f)
            gy.append(ys[j] + (ys[j + 1] - ys[j]) * f)
        else:
            gx.append(xs[j])
            gy.append(ys[j])
    u0 = richtung(winkel[0])
    u1 = richtung(winkel[-1])
    w = int(h / step)
    # Praefixsummen mit gerader Verlaengerung
    ext_x = [gx[0] - u0[0] * step * (w - k) for k in range(w)] + gx + [gx[-1] + u1[0] * step * (k + 1) for k in range(w)]
    ext_y = [gy[0] - u0[1] * step * (w - k) for k in range(w)] + gy + [gy[-1] + u1[1] * step * (k + 1) for k in range(w)]
    px, py = [0.0], [0.0]
    for a, b in zip(ext_x, ext_y):
        px.append(px[-1] + a)
        py.append(py[-1] + b)
    sx = [(px[k + 2 * w + 1] - px[k]) / (2 * w + 1) for k in range(m)]
    sy = [(py[k + 2 * w + 1] - py[k]) / (2 * w + 1) for k in range(m)]
    ox, oy, ws = [], [], []
    for i in range(n):
        k = min(int(round(cum[i] / step)), m - 1)
        ox.append(sx[k])
        oy.append(sy[k])
        k0, k1 = max(k - 4, 0), min(k + 4, m - 1)
        dx, dy = sx[k1] - sx[k0], sy[k1] - sy[k0]
        ws.append(winkel_von(dx, dy) if math.hypot(dx, dy) > 0.5 else winkel[i])
    return ox, oy, ws


# Wirksamer Radstand fuer das Ausholen: so weit muss die Vorderachse in Kurven nach aussen, damit
# das Heck (Hinterachse bzw. Nachlaeufer) etwa auf der Fahrspur bleibt. Nachlauf ungefaehr
# Radstand^2 / (2 R), begrenzt auf 2,2 m.
AUSHOL_RADSTAND = {'bus': 8.0, 'lkw': 5.0, 'sattel': 8.0}
AUSHOL_MAX = 2.2
# Krümmungsfenster relativ zum Radstand: etwas zurück (Fahrzeug steht noch in der Kurve) und
# voraus (Front schwenkt vor der Kurve aus). Faktor < 1, weil das Heck die Kurve etwas schneiden
# darf und die Front am Kurvenausgang nicht über den äußeren Bordstein soll.
AUSHOL_ZURUECK = 0.2
AUSHOL_VOR = 0.8
AUSHOL_FAKTOR = 0.6


def _ausholen(typ, Fs):
    """Verschiebt die Bahn der Vorderachse in Kurven nach aussen. Die Kruemmung wird ueber den
    Abschnitt gemittelt, den das Fahrzeug gerade ueberdeckt, und etwas voraus, so dass die Front
    schon vor der Kurve leicht ausschwenkt."""
    n = len(Fs)
    if n < 3:
        return Fs
    cum = [0.0]
    for a, b in zip(Fs, Fs[1:]):
        cum.append(cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    if cum[-1] < 5:
        return Fs

    def idx(sv):
        lo, hi = 0, n - 1
        if sv <= 0:
            return 0
        if sv >= cum[-1]:
            return n - 1
        while hi - lo > 1:
            m = (lo + hi) // 2
            if cum[m] <= sv:
                lo = m
            else:
                hi = m
        return lo

    def richt(sv, h=1.5):
        a, b = Fs[idx(sv - h)], Fs[idx(sv + h)]
        return math.atan2(b[1] - a[1], b[0] - a[0]), math.hypot(b[0] - a[0], b[1] - a[1])

    L = AUSHOL_RADSTAND[typ]
    out = []
    for i, F in enumerate(Fs):
        sv = cum[i]
        s0, s1 = sv - L * AUSHOL_ZURUECK, sv + L * AUSHOL_VOR
        w0, d0 = richt(s0)
        w1, d1 = richt(s1)
        if d0 < 1.0 or d1 < 1.0 or s1 - s0 <= 0:
            out.append(F)
            continue
        dw = (w1 - w0 + math.pi) % (2 * math.pi) - math.pi
        kappa = dw / (s1 - s0)                 # mittlere Kruemmung, positiv = Linkskurve
        e = max(-AUSHOL_MAX, min(AUSHOL_MAX, AUSHOL_FAKTOR * L * L * kappa / 2))
        w, _ = richt(sv, 0.8)
        nx, ny = math.sin(w), -math.cos(w)     # rechts der Fahrtrichtung
        # Linkskurve: nach rechts aussen holen, Rechtskurve: nach links
        out.append((F[0] + nx * e, F[1] + ny * e))
    return out


def posen(typ, xs, ys, winkel, dt=0.2):
    """Lage je Zeitschritt: Liste von (Fx, Fy, h1, h2). F ist die Vorderachse, h1 und h2 sind die
    Richtungen der Glieder (h2 None bei starren Fahrzeugen). Eingabe ist die SUMO-Frontposition.

    Die Bahn waechst nur bei Vorwaertsfahrt, kleines Rueckwaertszittern wird ignoriert. Bus, Lkw
    und Sattelzug holen in Kurven aus: Ihre Vorderachse faehrt aussen, das Heck folgt als
    Schleppkurve etwa auf der Fahrspur."""
    g = GEOM[typ]
    xs, ys, winkel = glaetten(typ, xs, ys, winkel, dt)
    vorn = g['front'] if g['art'] else g['fo']
    Fs = []
    for x, y, w in zip(xs, ys, winkel):
        u = richtung(w)
        Fs.append((x - u[0] * vorn, y - u[1] * vorn))
    if typ in AUSHOLEN:
        Fs = _ausholen(typ, Fs)
    u0 = richtung(winkel[0])
    F0 = Fs[0]
    bahn = Bahn(F0, u0)
    out = []
    if not g['art']:
        R = (F0[0] - u0[0] * g['wb'], F0[1] - u0[1] * g['wb'])
        h = u0
        for i, F in enumerate(Fs):
            if i:
                _unterteilt(bahn, F)
                for p in bahn_neu(bahn):
                    R, h = _nachziehen(p, R, g['wb'])
            P = bahn.pts[-1]
            out.append((P[0], P[1], winkel_von(*h), None))
        return out
    wb, hitch, L = g['wb'], g['hitch'], g['L']
    grenze = KNICK_MAX.get(typ, 90.0)
    A = bahn.punkt(-wb)
    T = bahn.punkt(-(wb - hitch) - L)
    u1 = u2 = u0
    for i, F in enumerate(Fs):
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
                u2, gekappt = _begrenze(u1, u2, grenze)
                if gekappt:
                    T = (H[0] - u2[0] * L, H[1] - u2[1] * L)
        P = bahn.pts[-1]
        out.append((P[0], P[1], winkel_von(*u1), winkel_von(*u2)))
    return out


def knickwinkel(h1, h2):
    """Knickwinkel in Grad zwischen zwei SUMO-Winkeln."""
    return abs((h1 - h2 + 180) % 360 - 180)


def _unterteilt(bahn, F):
    """Haengt F an die Bahn an, in Schritten von hoechstens SCHRITT_M, und merkt sich die neuen
    Punkte. Liegt F hinter der Fahrtrichtung (Rueckwaertssprung), wird nichts angehaengt."""
    q = bahn.pts[-1]
    bahn._neu = []
    dx, dy = F[0] - q[0], F[1] - q[1]
    d = math.hypot(dx, dy)
    if d < 1e-6:
        return
    if len(bahn.pts) > 1:
        p = bahn.pts[-2]
        if dx * (q[0] - p[0]) + dy * (q[1] - p[1]) < 0 and d < 0.6:
            return          # kleines Rueckwaertszittern ignorieren, groessere Spruenge uebernehmen
    n = max(1, int(math.ceil(d / SCHRITT_M)))
    for k in range(1, n + 1):
        p = (q[0] + dx * k / n, q[1] + dy * k / n)
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
