"""Lisansı açık ney, ud, kanun, tanbur, taksim kayıtları: Internet Archive + Wikimedia Commons (kategori ve arama)."""
import json, re, urllib.parse, urllib.request
UA = {'User-Agent': 'EzanSaati/1.0 (ezansaatidestek@gmail.com)'}
def get(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))
sonuc = []
# Internet Archive: lisans süzmesi sorguda değil burada (licenseurl joker sorgusu boş dönüyor)
for q in ['ney', 'neyzen', 'ney taksim', 'taksim', 'ud taksim', 'oud', 'kanun', 'tanburi cemil', 'neyzen tevfik',
          'turkish classical music', 'ottoman music', 'sufi', 'mevlevi', 'tasavvuf', 'ilahi', 'nay', 'makam']:
    u = 'https://archive.org/advancedsearch.php?' + urllib.parse.urlencode({
        'q': f'({q}) AND mediatype:audio', 'fl[]': ['identifier', 'title', 'creator', 'licenseurl', 'downloads', 'year', 'collection'],
        'rows': 60, 'output': 'json', 'sort[]': 'downloads desc'}, doseq=True)
    try:
        docs = get(u)['response']['docs']
        print('archive', q, len(docs))
        for d in docs:
            sonuc.append({'kaynak': 'archive', 'ara': q, 'id': d['identifier'], 'baslik': d.get('title'), 'sanatci': d.get('creator'),
                          'lisans': d.get('licenseurl'), 'indirme': d.get('downloads'), 'yil': d.get('year'),
                          'koleksiyon': d.get('collection'), 'url': 'https://archive.org/details/' + d['identifier']})
    except Exception as e:
        print('archive hata', q, e)
def commons(sayfalar, q):
    for p in sayfalar:
        ii = p.get('imageinfo', [{}])[0]; m = ii.get('extmetadata', {})
        sonuc.append({'kaynak': 'commons', 'ara': q, 'baslik': p['title'], 'lisans': m.get('LicenseShortName', {}).get('value'),
                      'sanatci': re.sub('<[^>]+>', '', m.get('Artist', {}).get('value', ''))[:80],
                      'aciklama': re.sub('<[^>]+>', '', m.get('ImageDescription', {}).get('value', ''))[:160],
                      'sure': ii.get('duration'), 'url': ii.get('descriptionurl'), 'dosya': ii.get('url')})
API = 'https://commons.wikimedia.org/w/api.php?'
ii = {'prop': 'imageinfo', 'iiprop': 'url|extmetadata|size|mediatype', 'action': 'query', 'format': 'json'}
for k in ['Audio files of Turkish music', 'Audio files of Ottoman classical music', 'Ney (instrument)', 'Audio files of ney',
          'Audio files of oud', 'Oud music', 'Audio files of qanun', 'Audio files of tanbur', 'Taksim (music)',
          'Audio files of Sufi music', 'Mevlevi music', 'Audio files of Arabic music', 'Audio files of Persian music',
          'Turkish makam music', 'Audio files of kemenche']:
    try:
        r = get(API + urllib.parse.urlencode({**ii, 'generator': 'categorymembers', 'gcmtitle': 'Category:' + k,
                                              'gcmtype': 'file', 'gcmlimit': 200}))
        s = list(r.get('query', {}).get('pages', {}).values()); print('kategori', k, len(s)); commons(s, 'kat:' + k)
    except Exception as e:
        print('commons hata', k, e)
for q in ['ney taksim', 'ney improvisation', 'oud taqsim', 'oud improvisation', 'tanbur taksim', 'Tanburi Cemil',
          'Neyzen Tevfik', 'Turkish classical music', 'peşrev', 'semai instrumental', 'kanun taksim', 'sufi ney']:
    try:
        r = get(API + urllib.parse.urlencode({**ii, 'generator': 'search', 'gsrnamespace': 6, 'gsrlimit': 50,
                                              'gsrsearch': f'{q} filetype:audio'}))
        s = list(r.get('query', {}).get('pages', {}).values()); print('ara', q, len(s)); commons(s, q)
    except Exception as e:
        print('commons hata', q, e)
gor = set(); tek = []
for s in sonuc:
    k = s.get('id') or s['baslik']
    if k not in gor: gor.add(k); tek.append(s)
json.dump(tek, open('ses_adaylar.json', 'w'), ensure_ascii=False, indent=1)
print(len(tek))
