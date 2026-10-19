"""Kullanıcının ürettirdiği Ramazan görselleri (arac/ramazan/rNN.jpg, yazısız, 1080x1920) -> Ramazan bölümü kartları.
Yazı yeri ve rengi kartyeni.py'deki planla seçilir (alttan ilk okunur yer); ELLE ile yer/renk elle verilebilir.
Metinler yalnız arac/metinler.json'dan (kaynaklı).

  python3 arac/ramazan_yerel.py ciz      -> foto-yeni/ramazan/ (önizleme, vitrin.jpg)
  python3 arac/ramazan_yerel.py onayla   -> fotolar/or_NN_y.jpg + ozel.json'a (bolum: ramazan)"""
import json, os, sys, time
from PIL import Image, ImageDraw, ImageFont
KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
from kartyeni import ciz, SINIR

# görsel no -> kaynak (arac/metinler.json'daki 'kaynak' alanı)
SECIM = {
    1: 'Hadis-i Şerif · Tirmizî, Sıfatü’l-kıyâme, 43',  # iftar sofrası, uzanan eller
    2: "Şûrâ, 19",                                       # fırından çıkan Ramazan pidesi
    3: 'Hadis-i Şerif · İbn Mâce, Sıyâm, 44',            # sahur davulcusu
    4: 'Hadis-i Şerif · Buhârî, Îmân, 28',               # sahur sofrası
    5: 'Hadis-i Şerif · Buhârî, Ezân, 30',               # teravihe giden cemaat
    6: 'Hadis-i Şerif · Tirmizî, Zühd, 2',               # komşuya iftar yemeği
    7: 'Hadis-i Şerif · Buhârî, Savm, 45',               # iftar sofrası, saat
    8: 'Kadir, 3',                                       # camide teravih
    9: 'Hadis-i Şerif · Müslim, Birr, 69',               # fitre/zekât
    10: "Mâide, 88",                                     # güllaç
    11: 'Bakara, 152',                                   # pencerede hurma ve su, gün batımı
}
ELLE = {2: {'y': 940}, 7: {'y': 130}, 9: {'y': 1330, 'renk': '#2B1A0C'}}   # no -> {'y': bloğun üstü (px, 1920 ölçeği), 'renk': '#rrggbb'}
CIK = 'foto-yeni/ramazan'


def ciz_hepsi():
    metin = {m['kaynak']: m for m in json.load(open(f'{KOK}/metinler.json'))}
    os.makedirs(CIK, exist_ok=True)
    liste = []
    for no, k in SECIM.items():
        m = metin[k]
        img = Image.open(f'{KOK}/ramazan/r{no:02d}.jpg').convert('RGB')
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
    oz = [o for o in oz if not o['id'].startswith('or_')]
    for t in json.load(open(f'{CIK}/liste.json')):
        fid = f"or_{t['no']:02d}"
        e = {'id': fid, 'lisans': 'Ezan Saati için üretildi (yapay zekâ görseli)', 'bolum': 'ramazan',
             'resim': f'fotolar/{fid}_y.jpg', 'kapak': f'fotolar/{fid}_y_k.jpg',
             'tur': t['tur'], 'metin': t['metin'], 'kaynak': t['kaynak'], 'selam_y': t['selam_y'], 'eklendi': tarih}
        os.replace(f"{CIK}/{t['no']:02d}.jpg", e['resim'])
        os.replace(f"{CIK}/{t['no']:02d}_k.jpg", e['kapak'])
        oz.append(e)
    # Ramazan kartları bölümde önce görünsün: yeni yerel kartlar eski bayram kartlarının önüne
    yeni = [o for o in oz if o['id'].startswith('or_')]
    oz = [o for o in oz if not o['id'].startswith('or_')]
    i = next((n for n, o in enumerate(oz) if o.get('bolum') == 'ramazan'), len(oz))
    oz[i:i] = yeni
    json.dump(oz, open('ozel.json', 'w'), ensure_ascii=False, indent=1)
    print('ozel', len(oz), 'ramazan', sum(o.get('bolum') == 'ramazan' for o in oz))


if __name__ == '__main__':
    {'ciz': ciz_hepsi, 'onayla': onayla}[sys.argv[1]]()
