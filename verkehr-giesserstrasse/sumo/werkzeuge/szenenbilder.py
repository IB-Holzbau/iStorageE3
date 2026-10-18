#!/usr/bin/env python3
"""Bilder der kritischen Szenen am kritischen Moment (Pruefhilfe).

Aufruf
    python3 werkzeuge/szenenbilder.py ausgabeordner [variante]
"""
import glob
import os
import sys

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1]
VAR = sys.argv[2] if len(sys.argv) > 2 else 'bestand'
exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
    pg = b.new_page(viewport={'width': 430, 'height': 1000}, device_scale_factor=2)
    fehler = []
    pg.on('pageerror', lambda e: fehler.append(str(e)))
    pg.goto('file://' + os.path.join(ROOT, 'grafik', 'abspieler.html'))
    pg.wait_for_timeout(700)
    pg.evaluate("window.__abspieler.setModus('sz')")
    for nr in range(1, 10):
        te = pg.evaluate(f"(()=>{{const c=window.__abspieler.daten().szenen.clips[{nr}];return c&&c['{VAR}']?c['{VAR}'].te:null}})()")
        if te is None:
            print('Szene', nr, 'fehlt in', VAR)
            continue
        pg.evaluate(f"window.__abspieler.ladeSzene({nr},'{VAR}');window.__abspieler.play(false);window.__abspieler.setT({te})")
        pg.wait_for_timeout(150)
        pg.locator('.mapbox').screenshot(path=os.path.join(OUT, f'szene{nr}_{VAR}.png'))
    print('Fehler', fehler)
    b.close()
