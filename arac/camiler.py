"""Türkiye camileri (OpenStreetMap, ODbL): osmium ile süzülmüş GeoJSON'dan 0,5°'lik bölge dosyaları.
camiler/<enlem>_<boylam>.json -> [[ad, enlem, boylam], ...]  (ad yoksa "")  ve camiler/dizin.json (dosya listesi)."""
import json, math, os, sys
from collections import defaultdict
geo = json.load(open(sys.argv[1]))
kova = defaultdict(list)
for f in geo['features']:
    g = f['geometry']; p = f.get('properties') or {}
    if g['type'] == 'Point':
        lng, lat = g['coordinates']
    else:  # alan (bina): köşelerin ortalaması
        pts = []
        def topla(c):
            if isinstance(c[0], (int, float)): pts.append(c)
            else:
                for x in c: topla(x)
        topla(g['coordinates'])
        lng = sum(x[0] for x in pts) / len(pts); lat = sum(x[1] for x in pts) / len(pts)
    ad = (p.get('name:tr') or p.get('name') or '').strip()
    kova[(math.floor(lat * 2) / 2, math.floor(lng * 2) / 2)].append([ad, round(lat, 5), round(lng, 5)])
os.makedirs('camiler', exist_ok=True)
for f in os.listdir('camiler'): os.remove(os.path.join('camiler', f))
toplam = 0
for (la, lo), l in kova.items():
    json.dump(l, open(f'camiler/{la:g}_{lo:g}.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    toplam += len(l)
json.dump(sorted(f'{la:g}_{lo:g}' for la, lo in kova), open('camiler/dizin.json', 'w'), separators=(',', ':'))
print(toplam, 'cami,', len(kova), 'dosya')
