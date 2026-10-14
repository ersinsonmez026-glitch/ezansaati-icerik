"""Lisansı açık (CC0 / kamu malı / CC BY) ney, ud, kanun, enstrümantal tasavvuf kayıtları: Internet Archive + Wikimedia Commons."""
import json, re, urllib.parse, urllib.request
UA = {'User-Agent': 'EzanSaati/1.0 (ezansaatidestek@gmail.com)'}
def get(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))
sonuc = []
# Internet Archive
lis = '(licenseurl:*publicdomain* OR licenseurl:*licenses/by/* OR licenseurl:*licenses/by-sa/*)'
for q in ['ney', 'ney taksim', 'ud taksim', 'oud improvisation', 'kanun taksim', 'sufi instrumental', 'tasavvuf musikisi', 'nay flute']:
    u = 'https://archive.org/advancedsearch.php?' + urllib.parse.urlencode({
        'q': f'({q}) AND mediatype:audio AND {lis}', 'fl[]': ['identifier', 'title', 'creator', 'licenseurl', 'downloads'],
        'rows': 40, 'output': 'json', 'sort[]': 'downloads desc'}, doseq=True)
    try:
        for d in get(u)['response']['docs']:
            sonuc.append({'kaynak': 'archive', 'ara': q, 'id': d['identifier'], 'baslik': d.get('title'), 'sanatci': d.get('creator'),
                          'lisans': d.get('licenseurl'), 'indirme': d.get('downloads'), 'url': 'https://archive.org/details/' + d['identifier']})
    except Exception as e:
        print('archive hata', q, e)
# Wikimedia Commons
for q in ['ney', 'nay flute', 'oud', 'taksim', 'kanun instrument', 'sufi music', 'makam']:
    u = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode({
        'action': 'query', 'format': 'json', 'generator': 'search', 'gsrnamespace': 6, 'gsrlimit': 50,
        'gsrsearch': f'{q} filetype:audio', 'prop': 'imageinfo', 'iiprop': 'url|extmetadata|size|mediatype'})
    try:
        for p in get(u).get('query', {}).get('pages', {}).values():
            ii = p['imageinfo'][0]; m = ii.get('extmetadata', {})
            sonuc.append({'kaynak': 'commons', 'ara': q, 'baslik': p['title'], 'lisans': m.get('LicenseShortName', {}).get('value'),
                          'sanatci': re.sub('<[^>]+>', '', m.get('Artist', {}).get('value', ''))[:80],
                          'sure': ii.get('duration'), 'url': ii.get('descriptionurl'), 'dosya': ii.get('url')})
    except Exception as e:
        print('commons hata', q, e)
gor = set(); tek = []
for s in sonuc:
    k = s.get('id') or s['baslik']
    if k not in gor: gor.add(k); tek.append(s)
json.dump(tek, open('ses_adaylar.json', 'w'), ensure_ascii=False, indent=1)
print(len(tek))
