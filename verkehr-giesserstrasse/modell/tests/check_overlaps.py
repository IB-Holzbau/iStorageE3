import os
import asyncio,sys,json
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page()
        html=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','dist','verkehrsmodell_giesserstrasse.html'),encoding='utf-8').read()
        await pg.set_content('<!doctype html><html><head><meta charset="utf-8"></head><body>'+html+'</body></html>')
        for lay in sys.argv[1:]:
            await pg.evaluate(f"window.__t.set({{layout:'{lay}'}})")
            pairs=set();samples=0;spd=[];stuck=0
            for k in range(400):
                await pg.evaluate('window.__t.run(20)')
                r=await pg.evaluate("""(()=>{const A=window.__t.agents().filter(a=>a.t!=='ped');const out=[];
                  function sd(ax,ay,bx,by,cx,cy,dx,dy){function pt(px,py,x1,y1,x2,y2){const vx=x2-x1,vy=y2-y1,l=vx*vx+vy*vy;let t=l?((px-x1)*vx+(py-y1)*vy)/l:0;t=Math.max(0,Math.min(1,t));return Math.hypot(x1+t*vx-px,y1+t*vy-py);}return Math.min(pt(ax,ay,cx,cy,dx,dy),pt(bx,by,cx,cy,dx,dy),pt(cx,cy,ax,ay,bx,by),pt(dx,dy,ax,ay,bx,by));}
                  function seg(a){if(a.art)return a.art;const hl=Math.max(0,(a.len-a.w)/2),c=Math.cos(a.h),s=Math.sin(a.h);return [[a.x-c*hl,a.y-s*hl,a.x+c*hl,a.y+s*hl]];}
                  for(let i=0;i<A.length;i++)for(let j=i+1;j<A.length;j++){const a=A[i],b=A[j];let m=1e9;for(const p of seg(a))for(const q of seg(b))m=Math.min(m,sd(...p,...q));if(m-a.w/2-b.w/2<-4)out.push(a.id+'-'+b.id);}
                  const sw=A.filter(a=>a.t==='car'&&a.r==='SW'&&a.y<520&&a.y>330&&a.x>250).map(a=>Math.round(a.v/15*3.6));
                  const st=A.filter(a=>a.stuckT>5).length;
                  return [out,sw,st];})()""")
                for x in r[0]: pairs.add(x)
                samples+=len(r[0]); spd+=r[1]; stuck+=r[2]
            spd.sort()
            print(lay,'Paare',len(pairs),'Proben',samples,'SW km/h Median',spd[len(spd)//2] if spd else None,'P80',spd[int(len(spd)*.8)] if spd else None,'stuck',stuck,flush=True)
        await b.close()
asyncio.run(main())
