"""Seçilen adayların ayrıntısı: archive öğelerinin dosyaları ve Commons'ta ad/kategori araması."""
import json, re, urllib.parse, urllib.request
UA = {'User-Agent': 'EzanSaati/1.0 (ezansaatidestek@gmail.com)'}
def get(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))
out = {'archive': {}, 'commons': []}
for i in ['NeyzenTevfik', '78_krdili-hicazkar-taksim-ut-ile_udi-hrant_gbia0363097b', 'NishanSedefjianSabahiTaksimCa1946',
          'ney-taksim', '03.NihavendTaksim', 'ney_enst', 'lp_flutes-orientales-sacres-des-derviches-tou_flutes-orientales-sacres-des-derviches-tou']:
    try:
        m = get('https://archive.org/metadata/' + i)
        md = m.get('metadata', {})
        out['archive'][i] = {'baslik': md.get('title'), 'aciklama': re.sub('<[^>]+>', '', str(md.get('description', '')))[:400],
                             'lisans': md.get('licenseurl'), 'tarih': md.get('date'), 'yukleyen': md.get('uploader'),
                             'dosyalar': [(f['name'], f.get('length')) for f in m.get('files', []) if f['name'].lower().endswith(('.mp3', '.ogg', '.flac'))][:40]}
    except Exception as e:
        out['archive'][i] = str(e)
API = 'https://commons.wikimedia.org/w/api.php?'
ii = {'prop': 'imageinfo', 'iiprop': 'url|extmetadata|mediatype', 'iiextmetadatafilter': 'LicenseShortName|Artist|ImageDescription|DateTimeOriginal|Credit',
      'action': 'query', 'format': 'json'}
def ekle(r, q):
    for p in r.get('query', {}).get('pages', {}).values():
        x = p.get('imageinfo', [{}])[0]; m = x.get('extmetadata', {})
        if x.get('mediatype') not in ('AUDIO', 'VIDEO'): continue
        out['commons'].append({'ara': q, 'baslik': p['title'], 'lisans': m.get('LicenseShortName', {}).get('value'),
                               'sure': x.get('duration'), 'url': x.get('descriptionurl'),
                               'aciklama': re.sub('<[^>]+>', '', m.get('ImageDescription', {}).get('value', ''))[:200],
                               'sanatci': re.sub('<[^>]+>', '', m.get('Artist', {}).get('value', ''))[:80],
                               'tarih': re.sub('<[^>]+>', '', m.get('DateTimeOriginal', {}).get('value', ''))[:40]})
for q in ['Tanburi Cemil', 'Cemil Bey', 'Neyzen', 'Saz Semaisi', 'Husseyni', 'Peşrev', 'pesrev', 'taksim', 'Turkish 78 rpm',
          'Udi Hrant', 'Hafız Kemal', 'Hafiz Burhan', 'Tekke', 'Mevlevi ayini', 'Hüseyni', 'Uşşak', 'Rast taksim', 'Hicaz']:
    try:
        ekle(get(API + urllib.parse.urlencode({**ii, 'generator': 'search', 'gsrnamespace': 6, 'gsrlimit': 50, 'gsrsearch': q})), q)
    except Exception as e:
        print('hata', q, e)
# Kategori adlarını bul
for q in ['Tanburi Cemil', 'Ottoman music audio', 'Turkish classical music audio', 'Ney audio', 'Sufi music audio', 'Oud audio']:
    try:
        r = get(API + urllib.parse.urlencode({'action': 'query', 'format': 'json', 'list': 'search', 'srnamespace': 14, 'srsearch': q, 'srlimit': 15}))
        out.setdefault('kategoriler', {})[q] = [s['title'] for s in r['query']['search']]
    except Exception as e:
        print('hata', q, e)
json.dump(out, open('ses_detay.json', 'w'), ensure_ascii=False, indent=1)
