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


def _tangente(bahn, s, h=1.5):
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
V_SEITE = {'bus': 0.25, 'sattel': 0.25, 'lkw': 0.25, 'pkw': 0.42, 'rad': 0.6}
NEIGUNG = {'bus': 0.13, 'sattel': 0.13, 'lkw': 0.16, 'pkw': 0.25, 'rad': 0.35}


# Halbe Fensterlaenge in Metern fuer die Glaettung der Bahn entlang des Fahrwegs. Auf geraden
# Abschnitten lang (Spurwechsel werden zu einer sanften S-Kurve ueber 30 bis 60 m), in Kurven kurz,
# damit Abbiegebahnen erhalten bleiben. Kurve heisst, die Fahrtrichtung aendert sich im Umkreis
# von 10 m um mehr als 20 Grad.
GLATT_GERADE = {'bus': 16.0, 'sattel': 16.0, 'lkw': 14.0, 'pkw': 10.0, 'rad': 4.0}
GLATT_KURVE = {'bus': 2.0, 'sattel': 2.0, 'lkw': 2.0, 'pkw': 1.5, 'rad': 1.0}


SPRUNG_MS = 0.6     # quer schneller als das (bezogen auf den letzten SUMO-Winkel) gilt als Sprung


def sprung_weg(typ, xs, ys, winkel, dt):
    """SUMO setzt Fahrzeuge an manchen Spuruebergaengen schlagartig seitlich um. Solche Spruenge
    (quer zur bisherigen Fahrtrichtung schneller als 1 m/s) werden hier als Versatz aufgefangen
    und dann mit hoechstens V_SEITE m/s abgebaut, so wird daraus ein weicher Spurwechsel."""
    vmax = V_SEITE.get(typ, 0.5) * dt
    ox, oy = [xs[0]], [ys[0]]
    offx = offy = 0.0
    for i in range(1, len(xs)):
        u = richtung(winkel[i - 1])
        dx, dy = xs[i] - xs[i - 1], ys[i] - ys[i - 1]
        quer = dx * u[1] - dy * u[0]
        if abs(quer) > SPRUNG_MS * dt:
            offx -= u[1] * quer
            offy += u[0] * quer
        d = math.hypot(offx, offy)
        if d > 0:
            f = max(d - vmax, 0.0) / d
            offx, offy = offx * f, offy * f
        ox.append(xs[i] + offx)
        oy.append(ys[i] + offy)
    return ox, oy


_ARME = None


def _arme():
    global _ARME
    if _ARME is None:
        import build
        _ARME = {}
        for a, ((x0, y0), (x1, y1)) in build.achsen().items():
            d = math.hypot(x1 - x0, y1 - y0)
            _ARME[a] = ((x0, y0), ((x1 - x0) / d, (y1 - y0) / d))
    return _ARME


NEIGUNG_QUER = 1 / 14     # hoechstens so viel Querversatz je Meter Fahrweg auf den Armen


def querversatz_weich(typ, xs, ys, dt):
    """Auf den Armen (mehr als 15 m vom Knoten) wird der Abstand zur Armachse so geglaettet, dass
    er sich hoechstens mit V_SEITE m/s und NEIGUNG_QUER je Meter aendert, als symmetrische Rampe
    (Mittel aus Vorwaerts- und Rueckwaertsfilter). Spurwechsel und Spruenge werden so zu langen,
    sanften Uebergaengen. Im Knoten bleibt die SUMO-Bahn."""
    arme = _arme()
    n = len(xs)
    lage = []
    for x, y in zip(xs, ys):
        best = None
        for a, (p0, u) in arme.items():
            sv = (x - p0[0]) * u[0] + (y - p0[1]) * u[1]
            q = (x - p0[0]) * u[1] - (y - p0[1]) * u[0]
            if sv > 15 and abs(q) < 10 and (best is None or sv > best[1]):
                best = (a, sv, q)
        lage.append(best)
    vmax = V_SEITE.get(typ, 0.5) * dt

    def filt(idx):
        out = {}
        prev = None
        for i in idx:
            L = lage[i]
            if L is None:
                prev = None
                continue
            if prev is None or prev[0] != L[0]:
                out[i] = L[2]
            else:
                ds = abs(L[1] - prev[1])
                g = min(vmax, NEIGUNG_QUER * ds) + 1e-4
                out[i] = prev[2] + max(-g, min(g, L[2] - prev[2]))
            prev = (L[0], L[1], out[i])
        return out
    vf = filt(range(n))
    vb = filt(range(n - 1, -1, -1))
    ox, oy = list(xs), list(ys)
    for i in range(n):
        L = lage[i]
        if L is None:
            continue
        q = (vf[i] + vb[i]) / 2
        p0, u = arme[L[0]]
        # weicher Uebergang zwischen 15 und 20 m zur SUMO-Bahn im Knoten
        w = min(1.0, (L[1] - 15) / 5)
        q = L[2] + (q - L[2]) * w
        ox[i] = p0[0] + u[0] * L[1] + u[1] * q
        oy[i] = p0[1] + u[1] * L[1] - u[0] * q
    return ox, oy


def glaetten(typ, xs, ys, winkel, dt):
    """Glaettet die SUMO-Frontbahn als gleitendes Mittel entlang des Fahrwegs (nicht der Zeit),
    mit langem Fenster auf Geraden und kurzem in Kurven. Im Stand bleibt der Punkt stehen. Gibt
    Positionen und Winkel (aus der geglaetteten Bahn) zurueck."""
    xs, ys = querversatz_weich(typ, xs, ys, dt)
    n = len(xs)
    cum = [0.0]
    for i in range(1, n):
        cum.append(cum[-1] + math.hypot(xs[i] - xs[i - 1], ys[i] - ys[i - 1]))
    step = 0.25
    m = int(cum[-1] / step) + 1
    gx, gy, gw = [], [], []
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
        gw.append(winkel[j])
    # Kurvenerkennung je Abtastpunkt aus der Geometrie: Richtung der Sehne 10 m zurueck gegen die
    # Sehne 10 m voraus. Ein seitlicher Versatz (Spurwechsel, Spuruebergang) ergibt nur wenige Grad,
    # ein Abbiegen viel mehr.
    # Die Sehnen lassen 5 m um den Punkt aus, damit ein seitlicher Sprung (SUMO setzt Fahrzeuge an
    # Spuruebergaengen teils schlagartig um) nicht als Kurve zaehlt.
    r, lu = int(15 / step), int(5 / step)
    kurve = [False] * m
    for k in range(m):
        a0, a1 = max(k - r, 0), min(k + r, m - 1)
        b0, b1 = max(k - lu, 0), min(k + lu, m - 1)
        if b0 - a0 < lu or a1 - b1 < lu:
            continue
        w0 = math.atan2(gy[b0] - gy[a0], gx[b0] - gx[a0])
        w1 = math.atan2(gy[a1] - gy[b1], gx[a1] - gx[b1])
        kurve[k] = abs((math.degrees(w1 - w0) + 180) % 360 - 180) > 25
    hg, hk = int(GLATT_GERADE.get(typ, 8.0) / step), int(GLATT_KURVE.get(typ, 1.5) / step)
    # Fensterbreite je Punkt: im Abstand zur naechsten Kurve weich von kurz nach lang
    abst = [10 ** 9] * m
    letzte = -10 ** 9
    for k in range(m):
        if kurve[k]:
            letzte = k
        abst[k] = k - letzte
    letzte = 10 ** 9
    for k in range(m - 1, -1, -1):
        if kurve[k]:
            letzte = k
        abst[k] = min(abst[k], letzte - k)
    wk = [hk if kurve[k] else min(hg, hk + abst[k]) for k in range(m)]
    W = hg
    u0 = richtung(winkel[0])
    u1 = richtung(winkel[-1])
    ext_x = [gx[0] - u0[0] * step * (W - k) for k in range(W)] + gx + [gx[-1] + u1[0] * step * (k + 1) for k in range(W)]
    ext_y = [gy[0] - u0[1] * step * (W - k) for k in range(W)] + gy + [gy[-1] + u1[1] * step * (k + 1) for k in range(W)]
    px, py = [0.0], [0.0]
    for a, b in zip(ext_x, ext_y):
        px.append(px[-1] + a)
        py.append(py[-1] + b)
    sx, sy = [], []
    for k in range(m):
        w = wk[k]
        lo, hi = k + W - w, k + W + w + 1
        sx.append((px[hi] - px[lo]) / (2 * w + 1))
        sy.append((py[hi] - py[lo]) / (2 * w + 1))
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


# Rechtsabbieger holen aus (Vorderachse aussen, Heck innen am Bordstein). Bei Linksabbiegern und
# Geradeausfahrern ist genug Platz, dort folgt die Vorderachse der Bahn.
RECHTS = {'WS', 'NW', 'EN', 'SE'}


def ausholen_fuer(vid):
    try:
        rel = vid.split('_')[1].split('.')[0][:2]
    except IndexError:
        return False
    return vid.split('_')[0] in AUSHOLEN and rel in RECHTS


def posen(typ, xs, ys, winkel, dt=0.2, ausholen=None):
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
    u0 = richtung(winkel[0])
    F0 = Fs[0]
    bahn = Bahn(F0, u0)
    out = []
    aushol = (typ in AUSHOLEN) if ausholen is None else (ausholen and typ in AUSHOLEN)
    if not g['art']:
        R = (F0[0] - u0[0] * g['wb'], F0[1] - u0[1] * g['wb'])
        h = u0
        for i, F in enumerate(Fs):
            if i:
                _unterteilt(bahn, F)
                for p in bahn_neu(bahn):
                    R, h = _nachziehen(p, R, g['wb'])
            P = bahn.pts[-1]
            if aushol:
                # Hinterachse auf der (geglaetteten) Bahn, Vorderachse tangential davor: in Kurven
                # faehrt die Vorderachse aussen, das Heck bleibt innen auf der Spur
                sR = bahn.s - g['wb']
                R = bahn.punkt(sR)
                h = _tangente(bahn, sR)
                P = (R[0] + h[0] * g['wb'], R[1] + h[1] * g['wb'])
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
                if aushol:
                    sA = bahn.s_teil - wb
                    A = bahn.punkt(sA)
                    u1 = _tangente(bahn, sA)
                else:
                    A, u1 = _nachziehen(p, A, wb)
                H = (A[0] + u1[0] * hitch, A[1] + u1[1] * hitch)
                T, u2 = _nachziehen(H, T, L)
                u2, gekappt = _begrenze(u1, u2, grenze)
                if gekappt:
                    T = (H[0] - u2[0] * L, H[1] - u2[1] * L)
        P = (A[0] + u1[0] * wb, A[1] + u1[1] * wb) if aushol else bahn.pts[-1]
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
