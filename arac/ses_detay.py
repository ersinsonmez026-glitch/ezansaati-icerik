"""Internet Archive 'opensource_audio' koleksiyonunda ilahi araması: her öğenin lisansı, yükleyeni, açıklaması."""
import json, re, urllib.parse, urllib.request
UA = {'User-Agent': 'EzanSaati/1.0 (ezansaatidestek@gmail.com)'}
def get(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))
out = []
for q in ['ilahi', 'ilahiler', 'müziksiz ilahi', 'çalgısız ilahi', 'ney', 'tasavvuf']:
    u = 'https://archive.org/advancedsearch.php?' + urllib.parse.urlencode({
        'q': f'({q}) AND collection:opensource_audio', 'fl[]': ['identifier', 'title', 'creator', 'licenseurl', 'rights', 'uploader', 'description', 'downloads'],
        'rows': 500, 'output': 'json'}, doseq=True)
    for d in get(u)['response']['docs']:
        out.append({'ara': q, 'id': d['identifier'], 'baslik': d.get('title'), 'sanatci': d.get('creator'), 'lisans': d.get('licenseurl'),
                    'hak': d.get('rights'), 'yukleyen': d.get('uploader'), 'indirme': d.get('downloads'),
                    'aciklama': re.sub('<[^>]+>', '', str(d.get('description') or ''))[:300]})
gor = set(); tek = [x for x in out if not (x['id'] in gor or gor.add(x['id']))]
json.dump(tek, open('ses_detay.json', 'w'), ensure_ascii=False, indent=1)
print(len(tek), sum(1 for x in tek if x['lisans']))
