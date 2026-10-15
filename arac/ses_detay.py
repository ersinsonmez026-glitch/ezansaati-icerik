"""Overpass sunucuları testi: uygulamanın cami sorgusu (Elazığ), her sunucuda durum kodu, süre, sonuç sayısı."""
import json, time, urllib.parse, urllib.request
eps = ['https://overpass-api.de/api/interpreter', 'https://overpass.private.coffee/api/interpreter',
       'https://maps.mail.ru/osm/tools/overpass/api/interpreter', 'https://overpass.kumi.systems/api/interpreter',
       'https://lz4.overpass-api.de/api/interpreter', 'https://z.overpass-api.de/api/interpreter']
out = []
for r in (1500, 4000):
    q = f'[out:json][timeout:20];nwr["amenity"="place_of_worship"]["religion"="muslim"](around:{r},38.67,39.22);out center 60;'
    for ep in eps:
        for ua in ('EzanSaati/1.0', 'Dart/3.9 (dart:io)'):
            t = time.time()
            try:
                req = urllib.request.Request(ep, data=('data=' + urllib.parse.quote(q)).encode(), method='POST',
                                             headers={'User-Agent': ua, 'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'})
                res = urllib.request.urlopen(req, timeout=30)
                n = len(json.load(res).get('elements', []))
                out.append([r, ep, ua, res.status, round(time.time() - t, 1), n])
            except Exception as e:
                out.append([r, ep, ua, str(e)[:80], round(time.time() - t, 1), None])
json.dump(out, open('ses_detay.json', 'w'), indent=0)
