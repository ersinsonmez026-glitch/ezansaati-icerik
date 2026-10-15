"""Türkçe sesli meal kaynakları: alquran.cloud ses sürümleri, everyayah listesi, Piper Türkçe ses lisansları."""
import json, urllib.request
UA = {'User-Agent': 'EzanSaati/1.0 (ezansaatidestek@gmail.com)'}
def oku(u):
    try:
        return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode('utf-8', 'replace')
    except Exception as e:
        return f'HATA {e}'
out = {}
d = oku('https://api.alquran.cloud/v1/edition?format=audio')
try:
    out['alquran_ses'] = [e for e in json.loads(d)['data'] if e['language'] != 'ar']
except Exception:
    out['alquran_ses'] = d[:500]
out['everyayah'] = [l for l in oku('https://everyayah.com/data/recitations.js').splitlines() if 'urk' in l or 'Turk' in l or 'tr' in l.lower()[:40]][:40]
out['everyayah_ham'] = oku('https://everyayah.com/data/recitations.js')[:200]
for v in ['dfki/medium', 'fahrettin/medium', 'fettah/medium']:
    out['piper_' + v] = oku(f'https://huggingface.co/rhasspy/piper-voices/raw/main/tr/tr_TR/{v}/MODEL_CARD')[:1500]
out['qurancom'] = oku('https://api.quran.com/api/v4/resources/recitations?language=tr')[:3000]
json.dump(out, open('ses_detay.json', 'w'), ensure_ascii=False, indent=1)
