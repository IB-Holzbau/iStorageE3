"""Baut die Seite dist/verkehrsmodell_giesserstrasse.html aus den Quellen in src/.
Aufruf: python3 build.py
"""
import os,re
ROOT=os.path.dirname(os.path.abspath(__file__))
SRC=os.path.join(ROOT,'src')
svg=[]; A=svg.append
code=open(os.path.join(SRC,'map_static.py.txt'),encoding='utf-8').read()
code=code.split('# Nummern')[0]
code=code.replace('svg=[]','').replace('A=svg.append','')
exec(code)
s='\n'.join(svg)
s=s.replace('viewBox="0 0 800 1470"','viewBox="0 0 800 1170" id="map" role="img" aria-label="Verkehrsmodell der Einmündung Gießerstraße und Naumburger Straße"')
s=s.replace('<rect width="800" height="1470" fill="#f4f1ea"/>','<rect width="800" height="1170" fill="#f4f1ea"/>')
s=s.replace('stroke="#f2b705" stroke-width="26" stroke-opacity="0.4"','stroke="#f2b705" stroke-width="22" stroke-opacity="0.28"')
# Buslinien entfernen (Modell zeigt echte Busse)
s=re.sub(r'<g fill="none" stroke="#1f6fb2" stroke-width="3" stroke-dasharray="2 8".*?</g>','',s,flags=re.S)
extra='''
<!-- Kiosk an der Südwestecke -->
<g transform="translate(150 452)">
  <rect x="0" y="0" width="100" height="58" rx="4" fill="#f2b705" stroke="#8a6500" stroke-width="2"/>
  <path d="M0 14 L100 14" stroke="#8a6500" stroke-width="2"/>
  <path d="M0 0 L12 14 L24 0 L36 14 L48 0 L60 14 L72 0 L84 14 L100 0" fill="#ffffff" fill-opacity="0.6" stroke="#8a6500" stroke-width="1.5"/>
  <text x="50" y="44" font-size="17" font-weight="700" fill="#3a2a00" text-anchor="middle">Kiosk</text>
</g>
<!-- parkende Autos am Beginn der Ostseite -->
<g id="parkOst">
''' 
for x in [530,630,676,722,768]:
    extra+=f'<rect x="{x-19}" y="302" width="38" height="20" rx="5" fill="#8c919a" stroke="#fff" stroke-width="1.5"/>\n'
for x in [530,630,676,722,768]:
    extra+=f'<rect x="{x-19}" y="398" width="38" height="20" rx="5" fill="#8c919a" stroke="#fff" stroke-width="1.5"/>\n'
extra+='</g>\n'+open(os.path.join(SRC,'overlays.svg'),encoding='utf-8').read()+'\n<g id="dyn"></g><g id="heat"></g><g id="agents"></g><g id="fx"></g>\n'
s=s.replace('</svg>','')+extra+'</svg>'
s=s.replace('<rect x="280" y="420" width="210" height="750"/></g>','<rect x="280" y="420" width="210" height="750"/></g><g fill=\"#5b5f66\"><path d=\"M310 276 A24 24 0 0 1 286 300 L310 300 Z\"/><path d=\"M469 300 A24 24 0 0 1 445 276 L445 300 Z\"/><path d=\"M256 420 A24 24 0 0 1 280 444 L280 420 Z\"/><path d=\"M490 444 A24 24 0 0 1 514 420 L490 420 Z\"/></g>',1)
s=s.replace('<line x1="500" y1="300" x2="500" y2="360" stroke-width="7" stroke-dasharray="9 7"/>','<line id="warteOst" x1="500" y1="300" x2="500" y2="360" stroke-width="7" stroke-dasharray="9 7"/>',1)
s=s.replace('<g fill="#ffffff" fill-opacity="0.35">','<g id="pfeileAlt" fill="#ffffff" fill-opacity="0.35">',1)
s=s.replace('<g transform="translate(548 940)">','<g id="schild50" transform="translate(548 940)">',1)
s=s.replace('<g transform="translate(530 250)">','<g id="vorfahrtOst" transform="translate(530 250)">',1)

T=[('<rect x="310" y="260" width="135" height="40" fill="#d62828" fill-opacity="0.28" stroke="#d62828" stroke-width="4" stroke-dasharray="11 6"/>',''),
 ('<rect x="560" y="300" width="42" height="120" fill="#f28c28" fill-opacity="0.2" stroke="#f28c28" stroke-width="3" stroke-dasharray="10 6"/>',''),
 ('<path d="M400 1170 L400 790 C400 700 381 700 381 610 L381 530 A200 200 0 0 0 181 330 L40 330"','<g id="vorfahrtBand"><path d="M400 1170 L400 790 C400 700 381 700 381 610 L381 530 A200 200 0 0 0 181 330 L40 330"'),
 ('<path d="M28 330 L60 310 L60 350 Z" fill="#c99400"/>','<path d="M28 330 L60 310 L60 350 Z" fill="#c99400"/></g>'),
 ('<g transform="translate(548 600)">','<g id="schildVorfahrt" transform="translate(548 600)">'),
 ('<g transform="translate(262 238)">','<g id="stopNord" transform="translate(262 238)">'),
 ('<line x1="310" y1="252" x2="378" y2="252" stroke-width="9"/>','<line id="haltNord" x1="310" y1="252" x2="378" y2="252" stroke-width="9"/>'),
 ('<line x1="345" y1="440"','<line id="mitteSued" x1="345" y1="440"'),
 ('<line x1="417" y1="440"','<line id="spurTrenn" x1="417" y1="440"'),
 ('<polyline points="470,762','<polyline id="zickzack" points="470,762'),
 ('<g transform="translate(503 790)">','<g id="hSchild" transform="translate(503 790)">')]
for a,b in T:
    assert a in s, a[:60]
    s=s.replace(a,b,1)

MAP=s

head=open(os.path.join(SRC,'head.html'),encoding='utf-8').read()
body=open(os.path.join(SRC,'body.html'),encoding='utf-8').read().replace('{{MAP}}',MAP)
js=open(os.path.join(SRC,'sim.js'),encoding='utf-8').read()
os.makedirs(os.path.join(ROOT,'dist'),exist_ok=True)
out=os.path.join(ROOT,'dist','verkehrsmodell_giesserstrasse.html')
open(out,'w',encoding='utf-8').write(head+body+'\n<script>\n'+js+'</script>\n')
print('geschrieben:',out)
