import os
import asyncio,sys,json
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        html=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','dist','verkehrsmodell_giesserstrasse.html'),encoding='utf-8').read()
        pg=await b.new_page()
        await pg.set_content('<!doctype html><html><head><meta charset="utf-8"></head><body>'+html+'</body></html>')
        for cfg in sys.argv[1:]:
            d={}
            for kv in cfg.split(','):
                if '=' in kv: k,v=kv.split('='); d[k]=v
                else: d[kv]=True
            d.setdefault('layout','bestand')
            await pg.evaluate(f"window.__t.set({json.dumps(d)})")
            r=await pg.evaluate('window.__t.run(12000)')
            st=await pg.evaluate("window.__t.agents().filter(a=>a.t!=='ped'&&a.v<1).map(a=>a.r+'@'+Math.round(a.x)+','+Math.round(a.y)+(a.released?'R':'')).join(' ')")
            print(cfg,sum(r.values()),'|',st[:300],flush=True)
        await b.close()
asyncio.run(main())
