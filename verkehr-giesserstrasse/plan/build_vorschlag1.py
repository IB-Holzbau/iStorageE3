"""Zeichnet Vorschlag 1 der Initiative sauber in den Eintragsplan.

Aufruf: python3 build_vorschlag1.py
Ergebnis: plan_vorschlag1.pdf und PNG je Seite. Grundlage ist der Bestand aus dem Abspieler,
darüber eine Zeichenebene in Modellmetern (x Ost, y Süd, Ursprung Knotenmitte).
Lagen sind aus den Spuren des SUMO-Netzes abgeleitet und auf etwa 0,5 m genau.
"""
import asyncio, math
import build_plan as bp

ROT = '#c8402c'
ASPHALT = '#999ca0'


def bez(p0, p1, p2, p3, n=40):
    out = []
    for i in range(n + 1):
        t = i / n
        a = (1 - t) ** 3; b = 3 * (1 - t) ** 2 * t; c = 3 * (1 - t) * t ** 2; d = t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def bogen(p_start, d_in, p_end, d_out, R, n=36):
    """Gerade, Kreisbogen mit Radius R, Gerade (tangential), wie eine echte Markierung"""
    import math
    def norm(v):
        l = math.hypot(*v); return (v[0] / l, v[1] / l)
    a, b = norm(d_in), norm(d_out)
    # Schnittpunkt der Geraden p_start + s*a und p_end - t*b
    det = a[0] * (-b[1]) - a[1] * (-b[0])
    rx, ry = p_end[0] - p_start[0], p_end[1] - p_start[1]
    s_ = (rx * (-b[1]) - ry * (-b[0])) / det
    S = (p_start[0] + a[0] * s_, p_start[1] + a[1] * s_)
    th = math.acos(max(-1, min(1, a[0] * b[0] + a[1] * b[1])))
    T = R * math.tan(th / 2)
    A = (S[0] - a[0] * T, S[1] - a[1] * T)
    B = (S[0] + b[0] * T, S[1] + b[1] * T)
    cross = a[0] * b[1] - a[1] * b[0]
    sg = 1 if cross > 0 else -1
    C = (A[0] - a[1] * R * sg, A[1] + a[0] * R * sg)
    a0 = math.atan2(A[1] - C[1], A[0] - C[0])
    pts = [p_start, A]
    for i in range(1, n):
        ang = a0 + sg * th * i / n
        pts.append((C[0] + R * math.cos(ang), C[1] + R * math.sin(ang)))
    pts += [B, p_end]
    return pts


def d(pts):
    return 'M' + ' L'.join(f'{x:.2f} {y:.2f}' for x, y in pts)


def offset(pts, o):
    """seitlicher Versatz, positiv = rechts in Fahrtrichtung (y nach Süden)"""
    out = []
    for i, (x, y) in enumerate(pts):
        a = pts[max(i - 1, 0)]; b = pts[min(i + 1, len(pts) - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]; n = math.hypot(dx, dy) or 1
        out.append((x - dy / n * o, y + dx / n * o))
    return out


def band(pts, w, fill, op=1.0):
    return f'<path d="{d(pts)}" fill="none" stroke="{fill}" stroke-width="{w}" stroke-opacity="{op}" stroke-linejoin="round"/>'


def linie(pts, w=0.15, dash=None, col='#fff'):
    da = f' stroke-dasharray="{dash}"' if dash else ''
    return f'<path d="{d(pts)}" fill="none" stroke="{col}" stroke-width="{w}"{da}/>'


def furt(pts, w=1.85):
    """rote Radfurt mit unterbrochenen Rändern und Fahrradsymbolen"""
    s = band(pts, w, ROT, 0.75)
    s += linie(offset(pts, w / 2), 0.18, '0.5 0.5') + linie(offset(pts, -w / 2), 0.18, '0.5 0.5')
    for i in range(6, len(pts) - 3, 12):
        x, y = pts[i]
        s += f'<circle cx="{x:.2f}" cy="{y:.2f}" r="0.28" fill="none" stroke="#fff" stroke-width="0.09"/>'
    return s


def nummer(x, y, n):
    return (f'<circle cx="{x}" cy="{y}" r="1.7" fill="#fff" stroke="{ROT}" stroke-width="0.35"/>'
            f'<text x="{x}" y="{y + 0.75}" font-size="2.2" font-weight="700" text-anchor="middle" fill="{ROT}" font-family="Arial">{n}</text>')


def pfeil_kombi(x, y, ang):
    """Fahrbahnpfeil links, geradeaus, rechts; ang = Fahrtrichtung in Grad (0 = Norden, im Uhrzeigersinn)"""
    w = 0.28
    p = (f'<g transform="translate({x} {y}) rotate({ang})" fill="#fff" stroke="#fff" stroke-linecap="round">'
         f'<path d="M0 3.2 L0 -1.6" stroke-width="{w}" fill="none"/>'
         '<path d="M0 -2.6 L-0.55 -1.5 L0.55 -1.5 Z" stroke="none"/>'
         f'<path d="M0 1.4 C0 0.6 -0.4 0.2 -1.3 0.2" stroke-width="{w}" fill="none"/>'
         '<path d="M-2.2 0.2 L-1.2 -0.35 L-1.2 0.75 Z" stroke="none"/>'
         f'<path d="M0 1.4 C0 0.6 0.4 0.2 1.3 0.2" stroke-width="{w}" fill="none"/>'
         '<path d="M2.2 0.2 L1.2 -0.35 L1.2 0.75 Z" stroke="none"/></g>')
    return p


def rad(x, y, ang, links=False):
    s = (f'<g transform="translate({x} {y}) rotate({ang})" fill="none" stroke="#fff" stroke-width="0.12">'
         '<circle cx="-0.55" cy="0.35" r="0.38"/><circle cx="0.55" cy="0.35" r="0.38"/>'
         '<path d="M-0.55 0.35 L-0.1 -0.25 L0.55 0.35 M-0.1 -0.25 L0.35 -0.25 L0.55 0.35"/>')
    if links:
        s += '<path d="M0 -0.9 L0 -1.6 L-0.9 -1.6 M-0.9 -1.6 L-0.55 -1.9 M-0.9 -1.6 L-0.55 -1.3" stroke-width="0.16"/>'
    return s + '</g>'


def overlay():
    s = []
    # Fahrspur Süd nach Norden, bisherige rechte Spur (Mitte) und linke Spur
    rechts = [(-3.0, 39.2), (-1.4, 31.3), (0.9, 19.6), (2.4, 11.9), (2.7, 10.3)]
    links = [(-6.5, 38.5), (-5.0, 30.6), (-2.6, 18.9), (-1.1, 11.2), (-0.8, 9.6)]
    # alte Pfeile und Spurlinie im Knotenzulauf überdecken
    s.append(band([p for p in rechts if p[1] < 20.5] , 3.5, ASPHALT))
    s.append(band([p for p in links if p[1] < 20.5], 3.5, ASPHALT))
    s.append(pfeil_kombi(-1.9, 15.0, 11))
    # 4 Sperrfläche zwischen Radweg und östlichem Bordstein
    def auf(pts, y):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            if min(y1, y2) <= y <= max(y1, y2):
                return (x1 + (x2 - x1) * (y - y1) / (y2 - y1), y)
    teil = [auf(rechts, 25.0), auf(rechts, 19.6), auf(rechts, 10.6)]
    sp_a = offset(teil, 0.05)
    sp_b = offset(teil, 1.75)
    s.append(f'<path d="{d(sp_a + sp_b[::-1])} Z" fill="{ASPHALT}" stroke="#fff" stroke-width="0.18"/>')
    s.append('<clipPath id="spclip"><path d="' + d(sp_a + sp_b[::-1]) + ' Z"/></clipPath><g clip-path="url(#spclip)">')
    for k in range(0, 18):
        y = 10.0 + k
        x = auf(rechts, min(max(y, 10.6), 25.0))[0]
        s.append(linie([(x - 1, y + 0.6), (x + 3, y - 1.4)], 0.2))
    s.append('</g>')
    # 5 zwei Parkplätze am östlichen Bordstein
    for yc in (29.0, 35.0):
        xc = -1.25 + (35 - yc) * 0.2
        s.append(f'<rect x="{xc - 1.0:.2f}" y="{yc - 2.6:.2f}" width="2.0" height="5.2" fill="none" stroke="#fff" stroke-width="0.15" transform="rotate(11 {xc:.2f} {yc:.2f})"/>')
        s.append(f'<text x="{xc:.2f}" y="{yc + 0.6:.2f}" font-size="1.6" text-anchor="middle" fill="#fff" font-family="Arial" font-weight="700">P</text>')
    # 2 Radfahrstreifen nach Norden links in der bisherigen rechten Spur
    rw = offset(rechts, -0.875)
    s.append(band(rw, 1.85, ROT))
    s.append(linie(offset(rw, -0.95), 0.25))
    s.append(rad(*rw[1], 11 - 90))
    # 2a Furt geradeaus in den Nordarm
    nord = [(1.84, 10.1), (3.7, -8.8)]
    s.append(furt([(nord[0][0] + (nord[1][0] - nord[0][0]) * t / 30, nord[0][1] + (nord[1][1] - nord[0][1]) * t / 30) for t in range(31)]))
    # Schutzstreifen Nordarm nordwärts
    s.append(band([(3.7, -8.8), (5.6, -24.0)], 1.5, ROT, 0.85))
    s.append(linie(offset([(3.7, -8.8), (5.6, -24.0)], -0.8), 0.15, '1 1'))
    # 2b Furt Süd nach West im Außenbogen, vor der Stopplinie Nord vorbei
    s.append(furt(bogen((1.84, 10.1), (0.19, -0.98), (-10.4, -5.4), (-0.99, -0.141), 11.0)))
    # Schutzstreifen Naumburger West Nordseite, westwärts
    wn = [(-10.4, -5.4), (-44.8, -10.3)]
    s.append(band(wn, 1.5, ROT, 0.85))
    s.append(linie(offset(wn, 0.8), 0.15, '1 1'))
    s.append(rad(-28, -7.9, -98))
    # 1 Schutzstreifen Naumburger West Südseite ostwärts, dann um die Kiosk-Ecke
    ws = [(-46.0, -2.6), (-11.4, 2.2)]
    s.append(band(ws, 1.6, ROT, 0.85))
    s.append(linie(offset(ws, -0.85), 0.15, '1 1'))
    s.append(rad(-30, 0.1, 82))
    s.append(band([(-6.9, 7.6), (-7.3, 10.0), (-8.8, 17.6), (-11.3, 29.4), (-12.6, 35.5)], 3.1, ASPHALT))
    s.append(furt(bogen((-13.0, 1.98), (0.99, 0.138), (-7.3, 10.0), (-0.195, 0.98), 4.5), 1.6))
    sued_w = [(-6.9, 8.2), (-7.3, 10.0), (-8.8, 17.6), (-11.3, 29.4), (-12.6, 35.5)]
    s.append(band(sued_w, 1.85, ROT))
    s.append(linie(offset(sued_w, -0.95), 0.25))
    s.append(rad(-10.0, 23.0, 169))
    # 6 neu: Schutzstreifen Rad links abbiegen West nach Nord (Aufstellstreifen links der Kfz-Spur)
    wl = [(-30.0, -4.4), (-11.6, -1.9)]
    s.append(band(wl, 1.4, '#e8a33d', 0.95))
    s.append(linie(offset(wl, -0.75), 0.15, '0.8 0.8'))
    s.append(linie(offset(wl, 0.75), 0.15, '0.8 0.8'))
    s.append(rad(-17, -2.75, 82, links=True))
    s.append(f'<path d="{d(bogen((-11.6, -1.9), (0.99, 0.135), (3.8, -9.0), (0.124, -0.992), 7.0))}" fill="none" stroke="#e8a33d" stroke-width="1.3" stroke-opacity="0.8" stroke-dasharray="0.8 0.6"/>')
    # Nummern
    for (x, y, n) in [(-36, 3.4, 1), (-6.5, -9.5, 2), (-6.3, 21.5, 3), (6.0, 18.0, 4), (3.6, 32.0, 5), (-24, -0.9, 6)]:
        s.append(nummer(x, y, n))
    return '\n'.join(s)


NOTIZ = ('<div style="background:#fff;padding:1mm"><b>Vorschlag 1</b> (Zeichnung aus der Skizze der Initiative, Lage ca. ±0,5 m)<br>'
         '<span style="color:#c8402c">■</span> 1 Schutzstreifen West ostwärts, rote Furt um die Kiosk-Ecke, Radfahrstreifen Süd südwärts bis Ende Halteverbot<br>'
         '<span style="color:#c8402c">■</span> 2 Radfahrstreifen Süd nordwärts, Furt geradeaus nach Nord und im Außenbogen nach West, Schutzstreifen Nord und West<br>'
         '3 eine Kfz-Spur nach Norden (Pfeil links, geradeaus, rechts) · 4 Sperrfläche · 5 zwei Parkplätze<br>'
         '<span style="color:#e8a33d">■</span> 6 neu: Aufstellstreifen für Rad links abbiegen West nach Nord mit Furt</div>')


async def main():
    bp.OPT.update(name='vorschlag1', titel='Vorschlag 1 der Initiative', overlay=overlay(), meta=False,
                  hinweis='Radführung entlang der abknickenden Vorfahrt, eine Kfz-Spur nach Norden. Rot = Radverkehr, orange = Rad links abbiegen West nach Nord. Ergänzungen bitte farbig einzeichnen.',
                  notizen=NOTIZ)
    await bp.main()

if __name__ == '__main__':
    asyncio.run(main())
