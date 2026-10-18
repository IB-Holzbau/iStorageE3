"""Erzeugt den Eintragsplan der Kreuzung (Bestand) als PDF und PNG.

Aufruf: python3 build_plan.py [pfad/zu/abspieler.html]
Ergebnis: plan_bestand.pdf, plan_bestand_s1.png, plan_bestand_s2.png, plan_meta.json

Die Karte wird aus dem Abspieler übernommen (Variante Bestand, ohne Fahrzeuge).
Modellkoordinaten sind Meter, Ursprung Knotenmitte, x nach Osten, y nach Süden.
plan_meta.json hält fest, wie Seiten-Millimeter auf Modellmeter abgebildet werden,
damit eingetragene Pläne später per Passmarken zurückgerechnet werden können.
"""
import asyncio, json, os, sys, subprocess, glob, datetime
from playwright.async_api import async_playwright

HIER = os.path.dirname(os.path.abspath(__file__))
QUELLE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HIER, '..', 'sumo', 'grafik', 'abspieler.html')
EXE = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]

# Seiten: A3 hoch, 297 x 420 mm. Kartenfeld mit festem Maßstab.
SEITEN = [
    dict(name='Gesamtplan', massstab=400, x0=-46, x1=46, y0=-40, y1=90, raster=10),
    dict(name='Knoten im Detail', massstab=200, x0=-27, x1=27, y0=-28, y1=36, raster=5),
]
PAGE_W, PAGE_H = 297.0, 420.0
RAND = 14.0
KOPF = 30.0  # Platz für Titel


def spalten(n):
    s = ''
    while True:
        s = chr(65 + n % 26) + s
        n = n // 26 - 1
        if n < 0:
            return s


async def karte_holen():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=EXE) if EXE else await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 1200, 'height': 1400})
        await pg.goto('file://' + os.path.abspath(QUELLE))
        await pg.wait_for_timeout(1500)
        svg = await pg.evaluate('''() => {
            const A = window.__abspieler;
            try { A.setModus && A.setModus('frei'); } catch(e) {}
            try { A.setVariante('bestand'); } catch(e) {}
            try { A.setT(0); } catch(e) {}
            const s = document.getElementById('map').cloneNode(true);
            for (const id of ['agents','sicht','fx']) { const g = s.querySelector('#'+id); if (g) g.remove(); }
            return s.innerHTML;
        }''')
        await b.close()
        return svg


def seite_html(nr, cfg, inhalt, gesamt):
    m = cfg['massstab']
    w_m, h_m = cfg['x1'] - cfg['x0'], cfg['y1'] - cfg['y0']
    w_mm, h_mm = w_m * 1000 / m, h_m * 1000 / m
    left = (PAGE_W - w_mm) / 2
    top = RAND + KOPF
    assert top + h_mm < PAGE_H - RAND - 22, (cfg['name'], h_mm)
    # Raster
    r = cfg['raster']
    grid = []
    gx0 = int((cfg['x0'] // r) * r)
    xs = [x for x in range(gx0, int(cfg['x1']) + 1, r) if cfg['x0'] <= x <= cfg['x1']]
    gy0 = int((cfg['y0'] // r) * r)
    ys = [y for y in range(gy0, int(cfg['y1']) + 1, r) if cfg['y0'] <= y <= cfg['y1']]
    for x in xs:
        grid.append(f'<line x1="{x}" y1="{cfg["y0"]}" x2="{x}" y2="{cfg["y1"]}"/>')
    for y in ys:
        grid.append(f'<line x1="{cfg["x0"]}" y1="{y}" x2="{cfg["x1"]}" y2="{y}"/>')
    # Feldbezeichnungen außen
    lab = []
    for i in range(len(xs) - 1):
        cx = (xs[i] + xs[i + 1]) / 2
        px = left + (cx - cfg['x0']) * 1000 / m
        lab.append(f'<div class="gl" style="left:{px:.2f}mm;top:{top-5:.2f}mm">{spalten(i)}</div>')
        lab.append(f'<div class="gl" style="left:{px:.2f}mm;top:{top+h_mm+1.2:.2f}mm">{spalten(i)}</div>')
    for j in range(len(ys) - 1):
        cy = (ys[j] + ys[j + 1]) / 2
        py = top + (cy - cfg['y0']) * 1000 / m
        lab.append(f'<div class="gl" style="left:{left-4:.2f}mm;top:{py-1.6:.2f}mm">{j+1}</div>')
        lab.append(f'<div class="gl" style="left:{left+w_mm+4:.2f}mm;top:{py-1.6:.2f}mm">{j+1}</div>')
    # Passmarken an den Ecken des Kartenfelds (außerhalb)
    marken = []
    pm = []
    for (mx, my) in [(left - 7, top - 7), (left + w_mm + 7, top - 7), (left - 7, top + h_mm + 7), (left + w_mm + 7, top + h_mm + 7)]:
        marken.append(f'<svg class="pm" style="left:{mx-4:.2f}mm;top:{my-4:.2f}mm" viewBox="-4 -4 8 8"><circle r="3" fill="none" stroke="#000" stroke-width=".35"/><circle r="1.1" fill="#000"/><line x1="-4" y1="0" x2="4" y2="0" stroke="#000" stroke-width=".25"/><line x1="0" y1="-4" x2="0" y2="4" stroke="#000" stroke-width=".25"/></svg>')
        pm.append([round(mx, 2), round(my, 2)])
    # Maßstabsleiste
    sb_m = 20 if m >= 400 else 10
    sb_mm = sb_m * 1000 / m
    seg = ''.join(f'<rect x="{i*sb_mm/4:.2f}" y="0" width="{sb_mm/4:.2f}" height="1.6" fill="{"#000" if i%2==0 else "#fff"}" stroke="#000" stroke-width=".2"/>' for i in range(4))
    massst = f'''<svg class="sb" style="left:{left:.2f}mm;top:{top+h_mm+8:.2f}mm;width:{sb_mm+12:.2f}mm;height:7mm" viewBox="0 -1 {sb_mm+12:.2f} 7">{seg}
      <text x="0" y="4.6" font-size="2.4">0</text><text x="{sb_mm/2:.2f}" y="4.6" font-size="2.4" text-anchor="middle">{sb_m//2}</text><text x="{sb_mm:.2f}" y="4.6" font-size="2.4" text-anchor="middle">{sb_m} m</text></svg>'''
    nordpfeil = f'''<svg class="np" style="left:{left+w_mm-12:.2f}mm;top:{top+3:.2f}mm" viewBox="-6 -8 12 16"><circle r="5.5" fill="#fff" fill-opacity=".85" stroke="#000" stroke-width=".3"/><path d="M0 -5 L2.2 2 L0 0.8 L-2.2 2 Z" fill="#000"/><text y="6.9" font-size="3" text-anchor="middle" font-weight="700">N</text></svg>'''
    karte = f'''<svg class="karte" style="left:{left:.2f}mm;top:{top:.2f}mm;width:{w_mm:.2f}mm;height:{h_mm:.2f}mm"
        viewBox="{cfg['x0']} {cfg['y0']} {w_m} {h_m}" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
        <g opacity="0.62">{inhalt}</g>
        <g stroke="#2f6fb5" stroke-width="0.06" stroke-opacity="0.55" fill="none">{''.join(grid)}</g>
        <rect x="{cfg['x0']}" y="{cfg['y0']}" width="{w_m}" height="{h_m}" fill="none" stroke="#000" stroke-width="0.15"/>
      </svg>'''
    stand = datetime.date.today().strftime('%d.%m.%Y')
    html = f'''<section class="seite">
      <div class="kopf" style="left:{RAND}mm;top:{RAND}mm;width:{PAGE_W-2*RAND}mm">
        <div class="t1">Kreuzung Gießerstraße / Naumburger Straße, Leipzig-Plagwitz</div>
        <div class="t2">Eintragsplan Bestand · {cfg['name']} · Maßstab 1:{m} bei Druck auf A3 · Raster {r} m · Stand {stand} · Seite {nr} von {gesamt}</div>
        <div class="t3">Verbesserungen bitte farbig einzeichnen (rot oder grün), jede Idee mit einer Nummer im Kreis, darunter kurz beschreiben. Passmarken in den Ecken nicht abdecken. Foto möglichst gerade von oben.</div>
      </div>
      {karte}{''.join(lab)}{''.join(marken)}{massst}{nordpfeil}
      <div class="notiz" style="left:{left+sb_mm+20:.2f}mm;top:{top+h_mm+13:.2f}mm;width:{left+w_mm-(left+sb_mm+20):.2f}mm;height:{PAGE_H-RAND+6-(top+h_mm+13):.2f}mm">
        <b>Notizen</b> (Nr. · Maßnahme)
      </div>
    </section>'''
    meta = dict(seite=nr, name=cfg['name'], massstab=m, modell_bbox=[cfg['x0'], cfg['y0'], cfg['x1'], cfg['y1']],
                kartenfeld_mm=[round(left, 2), round(top, 2), round(w_mm, 2), round(h_mm, 2)], raster_m=r,
                passmarken_mm=pm, raster_spalten=[spalten(i) for i in range(len(xs) - 1)], raster_x=xs, raster_y=ys)
    return html, meta


async def main():
    inhalt = await karte_holen()
    teile, metas = [], []
    for i, cfg in enumerate(SEITEN, 1):
        h, mt = seite_html(i, cfg, inhalt, len(SEITEN))
        teile.append(h); metas.append(mt)
    doc = f'''<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Eintragsplan Kreuzung Gießerstraße</title>
    <style>
      @page {{ size: {PAGE_W}mm {PAGE_H}mm; margin: 0 }}
      html,body {{ margin:0; padding:0; background:#fff; font-family: Arial, Helvetica, sans-serif; color:#111 }}
      .seite {{ position:relative; width:{PAGE_W}mm; height:{PAGE_H}mm; page-break-after:always; overflow:hidden }}
      .seite:last-child {{ page-break-after:auto }}
      .seite > * {{ position:absolute }}
      .t1 {{ font-size:15pt; font-weight:700 }}
      .t2 {{ font-size:9pt; margin-top:1.5mm }}
      .t3 {{ font-size:8.5pt; margin-top:1.5mm; color:#333 }}
      .gl {{ font-size:7pt; color:#2f6fb5; transform:translateX(-50%); font-weight:700 }}
      .pm {{ width:8mm; height:8mm }}
      .np {{ width:12mm; height:16mm }}
      .notiz {{ border:0.3mm solid #999; font-size:8pt; padding:2mm; box-sizing:border-box;
               background: repeating-linear-gradient(#fff 0, #fff 6.6mm, #bbb 6.6mm, #bbb 6.8mm) }}
    </style></head><body>{''.join(teile)}</body></html>'''
    out_html = os.path.join(HIER, 'plan_bestand.html')
    with open(out_html, 'w', encoding='utf-8') as f:
        f.write(doc)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=EXE) if EXE else await p.chromium.launch()
        pg = await b.new_page()
        await pg.goto('file://' + out_html)
        await pg.wait_for_timeout(800)
        await pg.pdf(path=os.path.join(HIER, 'plan_bestand.pdf'), width=f'{PAGE_W}mm', height=f'{PAGE_H}mm', print_background=True)
        # Referenzbilder je Seite, 150 dpi
        px_mm = 150 / 25.4
        pg2 = await b.new_page(viewport={'width': int(PAGE_W * 96 / 25.4), 'height': int(PAGE_H * 96 / 25.4)}, device_scale_factor=150 / 96)
        await pg2.goto('file://' + out_html)
        await pg2.wait_for_timeout(800)
        for i in range(len(SEITEN)):
            el = (await pg2.query_selector_all('section.seite'))[i]
            await el.screenshot(path=os.path.join(HIER, f'plan_bestand_s{i+1}.png'))
        await b.close()
    try:
        commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=HIER, text=True).strip()
    except Exception:
        commit = None
    meta = dict(erstellt=datetime.datetime.now().isoformat(timespec='seconds'), quelle=os.path.relpath(QUELLE, HIER),
                git_commit=commit, seite_mm=[PAGE_W, PAGE_H], referenz_dpi=150,
                koordinaten='Modellmeter, Ursprung Knotenmitte, x Ost, y Süd (wie SUMO-Abspieler)', seiten=metas)
    with open(os.path.join(HIER, 'plan_meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print('fertig', [m['name'] for m in metas])

asyncio.run(main())
