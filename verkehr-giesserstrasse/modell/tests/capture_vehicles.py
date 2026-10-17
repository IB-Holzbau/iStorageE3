import os
import asyncio,sys
from playwright.async_api import async_playwright
S=sys.argv[1]
async def snap(pg,name):
    await (await pg.query_selector('.mapbox')).screenshot(path=f'{S}/{name}.png')
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1200,'height':1300})
        errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
        html=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','dist','verkehrsmodell_giesserstrasse.html'),encoding='utf-8').read()
        await pg.set_content('<!doctype html><html><head><meta charset="utf-8"></head><body>'+html+'</body></html>')
        await pg.wait_for_timeout(500); await pg.click('#play')
        found={}
        for k in range(6000):
            await pg.evaluate('window.__t.run(8)')
            st=await pg.evaluate("""(()=>{const A=window.__t.agents();const o={};
              for(const a of A){if(a.t==='bus'&&a.r==='BSW'&&a.v<1&&a.s>200&&a.y>800)o.stop=1;
                if(a.t==='bus'&&a.r==='BSW'&&a.y<470&&a.y>300&&a.x<400)o.turnL=1;
                if(a.t==='bus'&&a.r==='BWS'&&a.y>380&&a.y<480)o.turnR=1;
                if(a.t==='semi'&&a.x>300&&a.x<450&&a.y>320&&a.y<460)o.semi=1;}
              return o;})()""")
            for key in st:
                if key not in found:
                    found[key]=1; await snap(pg,'b_'+key); print('got',key,k,flush=True)
            if len(found)==4: break
        print(errs)
        await b.close()
asyncio.run(main())
