#!/usr/bin/env python3
"""Screenshots des Abspielers je Variante nach Zeit t (Sekunden).

Aufruf
    python3 werkzeuge/screenshots.py [t] [ausgabeordner] [varianten...]
Chromium unter /opt/pw-browsers wird genutzt, wenn vorhanden.
"""
import glob
import os
import sys

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = float(sys.argv[1]) if len(sys.argv) > 1 else 60
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'grafik')
VAR = sys.argv[3:]

exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
    pg = b.new_page(viewport={'width': 800, 'height': 1400}, device_scale_factor=1)
    fehler = []
    pg.on('pageerror', lambda e: fehler.append(str(e)))
    pg.goto('file://' + os.path.join(ROOT, 'grafik', 'abspieler.html'))
    pg.wait_for_timeout(800)
    tabs = VAR or pg.eval_on_selector_all('#tabs button:not([disabled])', 'bs=>bs.map(b=>b.dataset.v)')
    for v in tabs:
        pg.evaluate(f"window.__abspieler.play(false);window.__abspieler.setVariante('{v}');window.__abspieler.setT({T})")
        pg.wait_for_timeout(300)
        pg.locator('.mapbox').screenshot(path=os.path.join(OUT, f'abspieler_{v}.png'))
        print('Screenshot', v)
    print('Fehler', fehler)
    b.close()
