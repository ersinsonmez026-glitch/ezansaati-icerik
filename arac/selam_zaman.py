"""Mevcut videolara 'selam_t' (selam yazısının görüneceği saniye: ayet/hadis yazısı bitince) ekler.
pro.katman'daki zamanlamanın aynısı, video yeniden üretilmeden hesaplanır."""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont
KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
from pro import sar, HIZ, W

ar = {m['kaynak']: m.get('arapca', '') for m in json.load(open(f'{KOK}/metinler.json'))}
ar.update({m['kaynak']: m.get('arapca', '') for m in json.load(open(f'{KOK}/gazze.json'))})
d = ImageDraw.Draw(Image.new('RGB', (W, 100)))
videolar = json.load(open('videolar.json'))
for v in videolar:
    f = ImageFont.truetype(f'{KOK}/yazi/Lora-SemiBold.ttf', 44)
    fa = ImageFont.truetype(f'{KOK}/yazi/Amiri-Regular.ttf', 48)
    tr = sar(d, '“' + v['metin'].strip('“”"') + '”', f, W - 120)
    a = ar.get(v['kaynak'], '')
    sa = sar(d, a, fa, W - 110, rtl=True) if a else []
    if len(sa) > 2 or v.get('konu') == 'hat': sa = []
    t = 1.0 + (1.3 if sa else 0)
    for s in tr: t += len(s) / HIZ
    v['selam_t'] = round(t + 0.3 + 0.9 + 0.4, 2)
json.dump(videolar, open('videolar.json', 'w'), ensure_ascii=False, indent=1)
print(len(videolar), 'video; selam_t', min(v['selam_t'] for v in videolar), '-', max(v['selam_t'] for v in videolar))
