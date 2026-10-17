#!/usr/bin/env python3
"""Zeigt fuer einen Knoten, wer wem Vorfahrt gewaehren muss.
Aufruf  python3 werkzeuge/vorfahrt.py netze/bestand.net.xml J
"""
import sys
import xml.etree.ElementTree as ET

net, jid = sys.argv[1], sys.argv[2]
r = ET.parse(net).getroot()
name = {}
for c in r.findall('connection'):
    v = c.get('via') or ''
    if c.get('from').startswith(':') or not v.startswith(f':{jid}_'):
        continue
    idx = v[len(jid) + 2:].rsplit('_', 1)[0]
    if idx.isdigit():
        name[int(idx)] = f"{c.get('from').split('_')[0]}>{c.get('to').split('_')[0]}"
quer = [e for e in r.findall('edge') if e.get('function') == 'crossing' and e.get('id').startswith(f':{jid}_c')]
for i, e in enumerate(quer):
    name[len(name)] = 'Fuss ' + e.get('crossingEdges', '').split('_')[0]
j = [x for x in r.findall('junction') if x.get('id') == jid][0]
n = len(j.findall('request'))
for q in j.findall('request'):
    k = int(q.get('index'))
    resp = q.get('response')
    wem = [name.get(i, f'Querung{i}') for i in range(n) if resp[n - 1 - i] == '1']
    print(f"{name.get(k, f'Querung{k}'):10s} wartet auf {', '.join(wem) or '-'}")
