"""Kullanıcının ürettirdiği Bayram görselleri (arac/bayram/bNN.jpg, yazısız, 1080x1920) -> Bayram bölümü kartları.
Yazı yeri ve rengi kartyeni.py'deki planla seçilir (alttan ilk okunur yer); ELLE ile yer/renk elle verilebilir.
Metinler yalnız arac/metinler.json'dan (kaynaklı).

  python3 arac/bayram_yerel.py ciz      -> foto-yeni/bayram/ (önizleme, vitrin.jpg)
  python3 arac/bayram_yerel.py onayla   -> fotolar/ob_NN_y.jpg + ozel.json'a (bolum: bayram)"""
import json, os, sys, time
from PIL import Image, ImageDraw, ImageFont
KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
from kartyeni import ciz, SINIR

# görsel no -> kaynak (arac/metinler.json'daki 'kaynak' alanı)
SECIM = {
    1: 'Hadis-i Şerif · Tirmizî, Birr, 15',        # büyüğün elinden çocuğa şeker
    2: "Zümer, 66",                                 # gün doğarken camiye yürüyenler
    3: 'Hadis-i Şerif · Müslim, Îmân, 147',         # bayramlık elbise
    4: 'Hadis-i Şerif · Tirmizî, Birr, 3',          # el öpme
    5: 'Hadis-i Şerif · Buhârî, Edeb, 33',          # kapıda hediye/sepet
    6: 'Hadis-i Şerif · Müslim, Vasiyye, 14',       # kabir ziyareti
    7: 'Hadis-i Şerif · Ebû Dâvûd, Et’ıme, 14',     # bayram sofrası
    8: 'Duhâ, 11',                                  # kahve, baklava, lokum
    9: 'Hadis-i Şerif · Müslim, Birr, 20',          # misafir odası, şekerlik
    10: 'Hadis-i Şerif · Tirmizî, Menâkıb, 63',     # aile kahvaltısı
    11: 'Hadis-i Şerif · Müslim, Îmân, 77',         # komşu evi oturma odası
    12: 'Hucurât, 10',                              # kapı önünde misafir ayakkabıları
    13: 'Hadis-i Şerif · Müslim, Birr, 144',        # şeker toplayan çocuklar
    14: 'Yâsîn, 58',                                # süslü kapı
    16: 'Rûm, 17',                                  # bayram sabahı kasaba
}
ELLE = {8: {'y': 440}, 9: {'y': 370}, 10: {'y': 260}}   # no -> {'y': bloğun üstü (px, 1920 ölçeği), 'renk': '#rrggbb'}
# Elle ayar sayfasından gelenler (arac/ozel_elle.json, "bayram" bölümü): yer/renk değişir, "cikar" olan kart çıkar
if os.path.exists(f'{KOK}/ozel_elle.json'):
    for _no, _a in json.load(open(f'{KOK}/ozel_elle.json')).get('bayram', {}).items():
        if _a.get('cikar'): SECIM.pop(int(_no), None)
        else: ELLE[int(_no)] = {**ELLE.get(int(_no), {}), **{k: _a[k] for k in ('y', 'renk') if k in _a}}
CIK = 'foto-yeni/bayram'


def ciz_hepsi():
    metin = {m['kaynak']: m for m in json.load(open(f'{KOK}/metinler.json'))}
    os.makedirs(CIK, exist_ok=True)
    liste = []
    for no, k in SECIM.items():
        m = metin[k]
        img = Image.open(f'{KOK}/bayram/b{no:02d}.jpg').convert('RGB')
        r = ciz(img, m['metin'], m['kaynak'], m.get('arapca', ''), True, f'{CIK}/{no:02d}', elle=ELLE.get(no))
        liste.append({'no': no, 'tur': m['tur'], 'metin': m['metin'], 'kaynak': m['kaynak'], **r})
        print(no, r)
    json.dump(liste, open(f'{CIK}/liste.json', 'w'), ensure_ascii=False, indent=1)
    f = ImageFont.truetype(f'{KOK}/yazi/Lora-Bold.ttf', 26)
    tw, th, cols = 270, 480, 5
    c = Image.new('RGB', (cols * (tw + 8), ((len(liste) + cols - 1) // cols) * (th + 8)), 'white')
    for i, t in enumerate(liste):
        x, y = (i % cols) * (tw + 8) + 4, (i // cols) * (th + 8) + 4
        c.paste(Image.open(f"{CIK}/{t['no']:02d}_k.jpg").resize((tw, th)), (x, y))
        d = ImageDraw.Draw(c); d.rectangle((x, y, x + 120, y + 34), fill=(180, 0, 0) if t['elendi'] else (0, 90, 40))
        d.text((x + 5, y + 2), f"{t['no']} · {t['puan']:.2f}", font=f, fill='white')
    c.save(f'{CIK}/vitrin.jpg', quality=82)


def onayla():
    tarih = time.strftime('%Y-%m-%d')
    oz = json.load(open('ozel.json'))
    oz = [o for o in oz if not o['id'].startswith('ob_')]
    for t in json.load(open(f'{CIK}/liste.json')):
        fid = f"ob_{t['no']:02d}"
        e = {'id': fid, 'lisans': 'Ezan Saati için üretildi (yapay zekâ görseli)', 'bolum': 'bayram',
             'resim': f'fotolar/{fid}_y.jpg', 'kapak': f'fotolar/{fid}_y_k.jpg',
             'tur': t['tur'], 'metin': t['metin'], 'kaynak': t['kaynak'], 'selam_y': t['selam_y'], 'eklendi': tarih}
        os.replace(f"{CIK}/{t['no']:02d}.jpg", e['resim'])
        os.replace(f"{CIK}/{t['no']:02d}_k.jpg", e['kapak'])
        oz.append(e)
    # Bayram kartları bölümde önce görünsün: yeni yerel kartlar eski bayram kartlarının önüne
    yeni = [o for o in oz if o['id'].startswith('ob_')]
    oz = [o for o in oz if not o['id'].startswith('ob_')]
    i = next((n for n, o in enumerate(oz) if o.get('bolum') == 'bayram'), len(oz))
    oz[i:i] = yeni
    json.dump(oz, open('ozel.json', 'w'), ensure_ascii=False, indent=1)
    print('ozel', len(oz), 'bayram', sum(o.get('bolum') == 'bayram' for o in oz))


if __name__ == '__main__':
    {'ciz': ciz_hepsi, 'onayla': onayla}[sys.argv[1]]()
