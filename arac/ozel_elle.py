"""Bayram / Ramazan / Kandil yerel kartları için elle ayar sayfasının zeminleri ve satır düzenleri.
Kart numarası: Bayram 100+n, Ramazan 200+n, Kandil 300+n (n = görsel no). "oto" yayındaki hâldir (ELLE dahil).

  python3 arac/ozel_elle.py hazirla CIKTI_KLASORU   -> CIKTI/z/NNN.jpg (540x960, logolu, yazısız) + CIKTI/kartlar.json
  python3 arac/ozel_elle.py yaz SECIM.json           -> arac/ozel_elle.json (sayfanın kaydı: {no: {y, renk, cikar}})"""
import importlib, json, os, sys
from PIL import Image
KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
from kartyeni import ciz, duzen, W, H, O, SELAM_H

GRUP = [(100, 'bayram', 'b'), (200, 'ramazan', 'r'), (300, 'kandil', 'k')]


def hazirla(cik):
    os.makedirs(f'{cik}/z', exist_ok=True)
    metin = {m['kaynak']: m for m in json.load(open(f'{KOK}/metinler.json'))}
    lg = Image.open(f'{KOK}/logo.webp').convert('RGBA'); lg.thumbnail((int(132 * O), int(132 * O)))
    liste = []
    for taban, bolum, h in GRUP:
        mod = importlib.import_module(f'{bolum}_yerel')
        for n, kay in mod.SECIM.items():
            m = metin[kay]
            img = Image.open(f'{KOK}/{bolum}/{h}{n:02d}.jpg').convert('RGB')
            el = mod.ELLE.get(n)
            r = ciz(img, m['metin'], m['kaynak'], m.get('arapca', ''), True, f'/tmp/ozel_elle_{taban + n}', elle=el)
            z = img.convert('RGBA'); z.alpha_composite(lg, (W - lg.width - int(34 * O), H - int(44 * O) - lg.height))
            z.convert('RGB').resize((540, 960), Image.LANCZOS).save(f'{cik}/z/{taban + n:03d}.jpg', quality=80, optimize=True)
            sat, son_y, fs = duzen(m['metin'], m['kaynak'], m.get('arapca', ''))
            tur = lambda font, rtl: 'ar' if rtl else ('k' if font is fs else 'tr')
            oto = {'y': r['ypx'], 'koyu': r['koyu'], 'puan': r['puan'], 'elendi': False}
            if el and el.get('renk'): oto['renk'] = el['renk']
            liste.append({'no': taban + n, 'gorsel': n, 'bolum': bolum, 'selam': True,
                          'satir': [{'t': s_, 'f': tur(font, rtl), 'px': font.size, 'y': oy} for oy, s_, font, _, rtl in sat],
                          'son_y': son_y, 'blok': sat[-1][0] + int(50 * O), 'oto': oto})
            print(taban + n, r)
    json.dump({'W': W, 'H': H, 'O': O, 'selam_h': SELAM_H, 'kartlar': liste}, open(f'{cik}/kartlar.json', 'w'),
              ensure_ascii=False, separators=(',', ':'))


def yaz(yol):
    """Sayfanın kaydı ({no: {y, renk, cikar}}) -> arac/ozel_elle.json ({bolum: {gorsel_no: {...}}})."""
    secim = json.load(open(yol))
    out = {b: {} for _, b, _ in GRUP}
    for no, a in secim.items():
        no = int(no)
        taban, bolum, _ = next(g for g in GRUP if g[0] <= no < g[0] + 100)
        a = {k: a[k] for k in ('y', 'renk', 'cikar') if a.get(k) not in (None, False)}
        if a: out[bolum][str(no - taban)] = a
    json.dump(out, open(f'{KOK}/ozel_elle.json', 'w'), ensure_ascii=False, indent=1, sort_keys=True)
    print({b: len(v) for b, v in out.items()})


if __name__ == '__main__':
    {'hazirla': hazirla, 'yaz': yaz}[sys.argv[1]](sys.argv[2])
