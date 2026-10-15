"""Her video için: Diyanet Vakfı meal metni (tr.vakfi), sesli meal ve tilavet süreleri."""
import json, os, subprocess, urllib.request
UA = {'User-Agent': 'EzanSaati/1.0 (ezansaatidestek@gmail.com)'}
KOK = 'arac'
SURELER = json.load(open('arac/sureler.json'))
def sa(k):
    try:
        ad, no = [x.strip() for x in k.split(',', 1)]
        s = next(i for i, x in enumerate(SURELER, 1) if x[0] == ad)
        return s, int(no.split('-')[0])
    except Exception:
        return None
def sure(url):
    try:
        open('/tmp/a.mp3', 'wb').write(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read())
        return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', '/tmp/a.mp3'],
                                    capture_output=True, text=True).stdout.strip())
    except Exception as e:
        return str(e)
out = []
for v in json.load(open('videolar.json')):
    x = sa(v['kaynak'])
    if not x: out.append({'id': v['id'], 'kaynak': v['kaynak'], 'hata': 'kaynak'}); continue
    g = sum(y[1] for y in SURELER[:x[0] - 1]) + x[1]
    try:
        t = json.load(urllib.request.urlopen(urllib.request.Request(f'https://api.alquran.cloud/v1/ayah/{g}/tr.vakfi', headers=UA), timeout=60))['data']['text']
    except Exception as e:
        t = str(e)
    out.append({'id': v['id'], 'kaynak': v['kaynak'], 'g': g, 'bizim': v['metin'], 'vakfi': t,
                'tilavet': sure(f'https://cdn.islamic.network/quran/audio/128/ar.mahermuaiqly/{g}.mp3'),
                'meal_ses': sure(f'https://cdn.islamic.network/quran/audio/64/tr.vakfi-audio/{g}.mp3')})
json.dump(out, open('ses_detay.json', 'w'), ensure_ascii=False, indent=1)
