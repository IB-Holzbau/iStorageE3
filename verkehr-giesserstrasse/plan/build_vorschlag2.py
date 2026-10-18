"""Zeichnet Vorschlag 2 (Weiterentwicklung von Vorschlag 1 nach der Simulation).

Aufruf: python3 build_vorschlag2.py
Ergebnis: plan_vorschlag2.pdf und PNG je Seite.

Kernidee: zwei Kfz-Spuren nach Norden bleiben, Räder nach West fahren in einem
Radstreifen in Mittellage zwischen Linksabbieger und Geradeausspur. So kreuzen sie
den Geradeausverkehr nicht mehr im Knoten, sondern einmal früh an einer markierten Stelle.
"""
import asyncio
import build_plan as bp
from build_vorschlag1 import (ROT, ASPHALT, bogen, d, offset, band, linie, furt, nummer, rad)

ORANGE = '#e8a33d'

# Achse Südarm wie im Abspieler (gerade, Mittellinie zwischen Spur Süd und Spur Nord), Fahrtrichtung Nord.
# Bordsteine: West 5,8 m links der Achse, Ost 7,2 m rechts. Punkte in Plankoordinaten (y Süd).
def _achse_s(s):
    return (-0.69 - 0.195 * s, -0.14 + 0.981 * s)
C = [_achse_s(s) for s in (40, 34, 28, 22, 16, 12, 9.8)]


def quer(o):
    """Linie im Abstand o (m) rechts (östlich) der Achse"""
    return offset(C, o)


def pfeil(x, y, ang, art):
    w = 0.28
    s = f'<g transform="translate({x} {y}) rotate({ang})" fill="#fff" stroke="#fff" stroke-linecap="round">'
    if art == 'links':
        s += (f'<path d="M0.3 3.0 L0.3 0.2 C0.3 -0.7 -0.2 -1.0 -1.0 -1.0" stroke-width="{w}" fill="none"/>'
              '<path d="M-1.9 -1.0 L-0.9 -1.55 L-0.9 -0.45 Z" stroke="none"/>')
    else:  # geradeaus und rechts
        s += (f'<path d="M0 3.2 L0 -1.6" stroke-width="{w}" fill="none"/>'
              '<path d="M0 -2.6 L-0.55 -1.5 L0.55 -1.5 Z" stroke="none"/>'
              f'<path d="M0 1.4 C0 0.6 0.4 0.2 1.3 0.2" stroke-width="{w}" fill="none"/>'
              '<path d="M2.2 0.2 L1.2 -0.35 L1.2 0.75 Z" stroke="none"/>')
    return s + '</g>'


def overlay():
    s = []
    # ganzen Zulauf Süd neu markieren: alte Markierung, Falschparker und Pfeile überdecken
    s.append(band(quer(0.7), 13.0, ASPHALT))
    # Querschnitt (Abstand zur Achse in m): Rad Süd -5,8..-3,95 | Kfz Süd -3,95..-1,0 | Leitlinie -1,0
    # | Linksabbieger -1,0..1,75 | Rad Mittellage 1,75..3,15 | Geradeaus 3,15..5,9 | Schutzstreifen 5,9..7,2
    s.append(linie(quer(-1.0), 0.15, '3 3'))                    # Mittellinie
    s.append(linie(quer(-3.95), 0.25))                          # Rand Radfahrstreifen Süd
    s.append(band(quer(-4.875), 1.85, ROT))                     # 1 Radfahrstreifen südwärts
    s.append(rad(*quer(-4.875)[2], 169))
    # Radstreifen in Mittellage für Rad Süd nach West, ab der Einfädelung (y < 30)
    mitte = [p for p in quer(2.45) if p[1] < 31]
    s.append(band(mitte, 1.4, ROT))
    s.append(linie([p for p in quer(1.75) if p[1] < 31], 0.25))
    s.append(linie([p for p in quer(3.15) if p[1] < 31], 0.25))
    s.append(rad(*mitte[1], 11 - 90))
    # Pfeil links (Linksabbieger) und geradeaus/rechts
    l = quer(0.375)[4]; g = quer(4.3)[4]
    s.append(pfeil(l[0] + 0.3, l[1] + 3.0, 14, 'links'))
    s.append(pfeil(g[0] + 0.3, g[1] + 3.0, 14, 'gerade'))
    s.append(linie(quer(3.15)[:2], 0.15, '3 3'))                # Spurlinie südlich der Einfädelung
    # Schutzstreifen rechts für Rad Süd nach Nord
    s.append(band(quer(6.55), 1.3, ROT, 0.85))
    s.append(linie(quer(5.9), 0.15, '1 1'))
    s.append(rad(*quer(6.55)[1], 11 - 90))
    # 3 Einfädelung: Rad nach West wechselt früh vom rechten Rand in die Mittellage
    a = quer(6.55)[1]; b = quer(2.45)[1]
    p0 = (a[0] + (a[0] - b[0]) * 0, a[1] + 6.0)
    s.append(furt([(p0[0] + (mitte[0][0] - p0[0]) * t / 20, p0[1] + (mitte[0][1] - p0[1]) * t / 20) for t in range(21)], 1.4))
    # 2a Furt Rad geradeaus in den Nordarm, Schutzstreifen Nordarm
    e = quer(6.55)[-1]
    s.append(furt([(e[0] + (4.6 - e[0]) * t / 30, e[1] + (-9.0 - e[1]) * t / 30) for t in range(31)], 1.3))
    s.append(band([(4.6, -9.0), (6.5, -24.0)], 1.3, ROT, 0.85))
    s.append(linie(offset([(4.6, -9.0), (6.5, -24.0)], -0.7), 0.15, '1 1'))
    # 2b Furt Rad Süd nach West aus der Mittellage, rechts neben den abbiegenden Kfz
    m_end = mitte[-1]
    s.append(furt(bogen(m_end, (0.25, -0.97), (-12.0, -5.2), (-0.99, -0.141), 10.0), 1.4))
    s.append(rad(-16.5, -5.85, -98))
    # Mittellinie der abknickenden Vorfahrt durch den Knoten
    st = quer(-1.0)[3]
    s.append(linie(bogen(st, (0.19, -0.98), (-24.0, -4.4), (-0.99, -0.138), 8.0), 0.16, '1.5 1.5'))
    # 1 Schutzstreifen West ostwärts, Furt um die Kiosk-Ecke
    def aw(t, q):  # Westarm: t = Abstand vom Knoten, q = Abstand südlich der Achse
        return (0.14 - 0.99 * t - 0.138 * q, -0.99 - 0.138 * t + 0.99 * q)
    ws = [aw(46, 5.08), aw(11.2, 5.08)]
    s.append(band(ws, 1.35, ROT, 0.85))
    s.append(linie(offset(ws, -0.8), 0.15, '1 1'))
    s.append(rad(-30, 0.1, 82))
    k_end = quer(-4.875)[3]
    s.append(furt(bogen(aw(12.5, 5.08), (0.99, 0.138), k_end, (-0.19, 0.98), 4.5), 1.6))
    # 4 Aufstellstreifen Rad links abbiegen West nach Nord
    wl = [aw(30, 0.7), aw(11.6, 0.7)]
    s.append(band(wl, 1.4, ORANGE, 0.95))
    s.append(linie(offset(wl, -0.75), 0.15, '0.8 0.8'))
    s.append(linie(offset(wl, 0.75), 0.15, '0.8 0.8'))
    s.append(rad(-17, -2.75, 82, links=True))
    s.append(f'<path d="{d(bogen(aw(11.6, 0.7), (0.99, 0.138), (4.0, -9.0), (0.124, -0.992), 7.0))}" fill="none" stroke="{ORANGE}" stroke-width="1.3" stroke-opacity="0.8" stroke-dasharray="0.8 0.6"/>')
    # Nummern
    for (x, y, n) in [(-36, 3.4, 1), (-6.5, -9.5, 2), (9.5, 30.0, 3), (-24, -0.9, 4), (9.0, 18.0, 5)]:
        s.append(nummer(x, y, n))
    return '\n'.join(s)


NOTIZ = ('<div style="background:#fff;padding:1mm"><b>Vorschlag 2</b> (Weiterentwicklung von Vorschlag 1 nach der Simulation, Lage ca. ±0,5 m)<br>'
         '1 wie Vorschlag 1: Schutzstreifen West ostwärts, Furt um die Kiosk-Ecke, Radfahrstreifen Süd südwärts<br>'
         '2 Rad Süd nach West im Radstreifen in Mittellage, im Bogen rechts neben den abbiegenden Kfz, danach Mischverkehr Tempo 30 · Rad Süd nach Nord rechts, Furt geradeaus<br>'
         '3 Einfädelung: Rad nach West wechselt früh und markiert in die Mittellage · 4 Aufstellstreifen Rad West nach Nord<br>'
         '5 zwei Kfz-Spuren nach Norden bleiben (links / geradeaus und rechts), schmaler: 2,75 m, Mittellage 1,4 m, Schutzstreifen 1,3 m</div>')


async def main():
    bp.OPT.update(entfernen=['path[stroke-dasharray="3 3"][stroke-width="0.13"]'], name='vorschlag2',
                  titel='Vorschlag 2', overlay=overlay(), meta=False,
                  hinweis='Zwei Kfz-Spuren nach Norden, Rad nach West in Mittellage. Rot = Radverkehr, orange = Rad links abbiegen West nach Nord. Ergänzungen bitte farbig einzeichnen.',
                  notizen=NOTIZ)
    await bp.main()

if __name__ == '__main__':
    asyncio.run(main())
