import os
import asyncio,sys,json
from playwright.async_api import async_playwright
S=sys.argv[1]
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        html=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','dist','verkehrsmodell_giesserstrasse.html'),encoding='utf-8').read()
        pg=await b.new_page(viewport={'width':1200,'height':1100})
        errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.set_content('<!doctype html><html><head><meta charset="utf-8"></head><body>'+html+'</body></html>')
        await pg.wait_for_timeout(800)
        print('load errs',errs,flush=True)
        for name in sys.argv[2:]:
            await pg.click(f'[data-preset={name}]')
            r=await pg.evaluate('window.__t.run(36000)')  # 20 Minuten
            n=await pg.evaluate('window.__t.agents().length')
            st=await pg.evaluate("window.__t.agents().filter(a=>a.t!=='ped'&&a.v<1).map(a=>a.r).join(',')")
            await (await pg.query_selector('.mapbox')).screenshot(path=f'{S}/p_{name}.png')
            print(name,sum(r.values()),'/h',json.dumps(r),'agents',n,'stehend',st,errs[-1:],flush=True)
        await b.close()
asyncio.run(main())
