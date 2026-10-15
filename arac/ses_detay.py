"""Video adayı ayetlerin (kısa meal) Abdülbasit okuyuş süreleri (baş/son sessizlik kırpılmış)."""
import json, os, subprocess, sys
sys.path.insert(0, 'arac')
os.environ['KARI'] = 'ar.abdulsamad'
import pro
m = json.load(open('arac/metinler.json')); h = set(json.load(open('arac/haric.json')))
out = {}
for x in m:
    if x['tur'] != 'ayet' or len(x['metin']) > pro.MAKS_METIN or x['kaynak'] in h or x['kaynak'] in out:
        continue
    try:
        r = pro.ses_sec({'tur': 'ayet', 'kaynak': x['kaynak'], 'id': 'x'})
        out[x['kaynak']] = round(r[2], 2) if r else None
    except Exception as e:
        out[x['kaynak']] = str(e)
json.dump(out, open('ses_detay.json', 'w'), ensure_ascii=False, indent=1)
