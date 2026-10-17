"""Fussgaenger, die diagonal ueber den Knoten gehen (NO-Ecke <-> SW-Ecke mit dem Kiosk).

Ortsbeobachtung der Initiative: Ein Teil des Kioskstroms quert nicht erst den Nord- und dann den
Westarm, sondern geht schraeg durch den Knoten. SUMO kann eine solche Querung nicht sauber
abbilden (eine Querung muss genau einen Arm ueberspannen). Diese Personen werden deshalb hier
neben SUMO gefuehrt. Laut Initiative gehen sie nur, wenn wirklich frei ist: kein Fahrzeug im
Knoten und keines, das in den naechsten 7 s ankommt. Ist es nach 15 s nicht frei, nehmen sie die
normalen Querungen (hier: sie verschwinden aus dieser Rechnung). Sie bleiben nicht stehen. Die Fahrzeuge in SUMO reagieren nicht auf sie. Gezaehlt wird, wie oft ein
Fahrzeug ueber 15 km/h staerker als 3 m/s² bremsen muesste, um vor ihnen zu halten (wie bei den
uebrigen Fussgaengerkonflikten). Das ist eine Abschaetzung der Gefaehrdung, kein Unfallmodell.
"""
import math
import random

KNOTEN_R = 14.0        # m um die Knotenmitte, dort darf kein Fahrzeug sein
ANKUNFT_S = 7.0        # s, kein Fahrzeug darf frueher am Knotenrand ankommen
AUFGEBEN_S = 15.0      # s, danach normale Querungen


def ecken(build):
    """Startpunkte auf dem Gehweg an der Nordost- und der Suedwestecke (Kiosk)."""
    arme = build.achsen()
    R = {a: build.Rahmen(a, arme[a]) for a in arme}
    park = {(a, s): sum(w for k, w in build.querschnitt(a, s, 'm') if k == 'park') for a in 'SNWE' for s in ('in', 'out')}
    ne = build.schnitt(R['E'].kante('in', park[('E', 'in')] + 1.6), R['N'].kante('out', park[('N', 'out')] + 1.6))
    sw = build.schnitt(R['W'].kante('in', park[('W', 'in')] + 1.6), R['S'].kante('out', park[('S', 'out')] + 1.6))
    return ne, sw


class Diagonal:
    def __init__(self, seed, je_stunde, beginn, ende, ne, sw):
        rng = random.Random(10007 * seed + 31)
        self.rng = rng
        self.ne, self.sw = ne, sw
        self.leute = []
        t = beginn
        i = 0
        while True:
            t += rng.expovariate(je_stunde / 3600.0)
            if t >= ende:
                break
            hin = rng.random() < 0.5
            a, b = (ne, sw) if hin else (sw, ne)
            d = math.hypot(b[0] - a[0], b[1] - a[1])
            v = rng.uniform(1.1, 1.5)
            self.leute.append(dict(id=f'diag{"SW" if hin else "NE"}.{i}', t0=t, a=a, b=b, ux=(b[0] - a[0]) / d,
                                   uy=(b[1] - a[1]) / d, laenge=d, v=v, zustand='weg', warte=0.0, s=0.0))
            i += 1

    def schritt(self, t, dt, fahrzeuge):
        """fahrzeuge: Liste (x, y, tempo). Gibt die Personen zurueck, die gerade sichtbar sind:
        (id, x, y, vx, vy, geht)."""
        out = []
        for p in self.leute:
            if p['zustand'] == 'weg':
                if t >= p['t0']:
                    p['zustand'] = 'wartet'
                else:
                    continue
            if p['zustand'] in ('fertig', 'normal'):
                continue
            if p['zustand'] == 'wartet':
                p['warte'] += dt
                frei = True
                for x, y, v in fahrzeuge:
                    d = math.hypot(x, y)
                    if d < KNOTEN_R or (v > 1.0 and (d - KNOTEN_R) / v < ANKUNFT_S):
                        frei = False
                        break
                if frei:
                    p['zustand'] = 'geht'
                elif p['warte'] > AUFGEBEN_S:
                    p['zustand'] = 'normal'
                    continue
            elif p['zustand'] == 'geht':
                p['s'] += p['v'] * dt
                if p['s'] >= p['laenge']:
                    p['zustand'] = 'fertig'
                    continue
            x = p['a'][0] + p['ux'] * p['s']
            y = p['a'][1] + p['uy'] * p['s']
            geht = p['zustand'] == 'geht'
            out.append((p['id'], x, y, p['ux'] * p['v'] if geht else 0.0, p['uy'] * p['v'] if geht else 0.0, geht))
        return out

    def wartezeiten(self, beginn, ende):
        return [p['warte'] for p in self.leute if beginn <= p['t0'] < ende and p['zustand'] in ('geht', 'fertig')]
