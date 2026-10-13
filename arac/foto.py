"""Fotoğraflı mesaj kartları (videolarla aynı düzen): görüntünün en sakin yerine Arapça + meal + kaynak,
parlaklığa göre koyulaşan bant, sıcak renk tonu, logo; selam yazısının yeri (selam_y) kaydedilir.
Kullanım:
  python3 arac/foto.py aday "arama 1, arama 2" [adet]   -> foto-aday/vitrinN.jpg + liste.json
  python3 arac/foto.py taslak "3 5 8"                  -> foto-taslak/NN.jpg + liste.json (uygulamaya girmez)
  python3 arac/foto.py onay "1,2,4"                    -> fotolar/ + fotolar.json"""
import io, json, os, random, re, shutil, sys, time, urllib.parse, urllib.request
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageStat

KOK = os.path.dirname(os.path.abspath(__file__))
# Bağlamından koparılınca uygun düşmeyen metinler (savaş, yöneticiler, cenaze, kişiye hitap vb.) kullanılmaz
HARIC = set(json.load(open(os.path.join(KOK, 'haric.json'))))
sys.path.insert(0, KOK)
from uret import UA, YASAK
from pro import sar, MAKS_METIN, KREM, ALTIN, KOYU, ARAPCA, SELAM_H

W, H = 1080, 1920
O = W / 720                       # videolardaki ölçülerin bu boyuta oranı
MAKS_KART = 170                   # kartta biraz daha uzun metin olabilir
PEY = re.compile(r'Peygamber|Resûl|Muhammed|Nebi', re.I)
PEY_HARIC = {'Hadis-i Şerif · Buhârî, Şurût, 15', 'Hadis-i Şerif · İbn Hanbel, VI, 157'}


def ac(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()


def aday(aramalar, n):
    onayli = json.load(open('fotolar.json')) if os.path.exists('fotolar.json') else []
    kullanilan = {f['pixabay'] for f in onayli}
    liste = []
    for q in aramalar:
        u = 'https://pixabay.com/api/?' + urllib.parse.urlencode({'key': os.environ['PIXABAY_API_KEY'], 'q': q,
            'image_type': 'photo', 'orientation': 'vertical', 'safesearch': 'true', 'min_height': 1600, 'per_page': 60})
        say = 0
        for h in json.loads(ac(u)).get('hits', []):
            etiket = {t.strip().lower() for t in h.get('tags', '').split(',')}
            if h['id'] in kullanilan or etiket & YASAK: continue
            try:
                im = Image.open(io.BytesIO(ac(h['webformatURL']))).convert('RGB')
            except Exception as e:
                print('kapak yok', h['id'], e); continue
            kullanilan.add(h['id']); say += 1
            liste.append({'no': len(liste) + 1, 'id': h['id'], 'url': h['largeImageURL'], 'sayfa': h['pageURL'],
                          'arama': q, '_im': im})
            if say >= n: break
        print(q, len(liste))
    os.makedirs('foto-aday', exist_ok=True)
    f = ImageFont.truetype(f'{KOK}/yazi/Lora-Bold.ttf', 30)
    tw, th, cols = 200, 300, 6
    for s in range(0, len(liste), 24):
        grup = liste[s:s + 24]
        c = Image.new('RGB', (cols * (tw + 6), ((len(grup) + cols - 1) // cols) * (th + 6)), 'white')
        for k, a in enumerate(grup):
            im = a['_im']; r = max(tw / im.width, th / im.height)
            im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1))
            im = im.crop(((im.width - tw) // 2, (im.height - th) // 2, (im.width - tw) // 2 + tw, (im.height - th) // 2 + th))
            x, y = (k % cols) * (tw + 6), (k // cols) * (th + 6); c.paste(im, (x, y))
            d = ImageDraw.Draw(c); d.rectangle((x, y, x + 64, y + 40), fill=(180, 0, 0)); d.text((x + 6, y + 2), str(a['no']), font=f, fill='white')
        c.save(f'foto-aday/vitrin{s // 24 + 1}.jpg', quality=82)
    for a in liste: a.pop('_im')
    json.dump(liste, open('foto-aday/liste.json', 'w'), ensure_ascii=False, indent=1)


def sakin_yer(img, yukseklik):
    """Görüntünün en az ayrıntılı dikey bölgesi (bloğun üst kenarı)."""
    e = img.convert('L').filter(ImageFilter.FIND_EDGES).resize((90, H))
    px = e.load(); top = [0]
    for yy in range(H):
        top.append(top[-1] + sum(px[x, yy] for x in range(90)))
    en, en_y = None, int(H * 0.55 - yukseklik / 2)
    for yy in range(int(150 * O), max(int(150 * O), int(H - 170 * O - yukseklik)) + 1, 10):
        yogun = (top[yy + yukseklik] - top[yy]) / yukseklik * (1 + 0.35 * abs((yy + yukseklik / 2) / H - 0.58))
        if en is None or yogun < en: en, en_y = yogun, yy
    return en_y


def kart(img, metin, kaynak, cikti, arapca='', hat=False, selam=True, odak=0.5, yer=None):
    """hat: görüntüde hat yazısı var, Arapça satır konmaz. selam: altta selam yazısına yer bırak. odak: yatay kesim merkezi (0-1).
    yer: yazı bloğunun ortası, yüksekliğe oranla (0-1); verilirse en sakin yer aranmaz (kişinin üstüne gelmesin diye elle)."""
    if hat: arapca = ''
    r = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * r) + 1, int(img.height * r) + 1), Image.LANCZOS)
    ox = int(min(max(0, img.width * odak - W / 2), img.width - W))
    img = img.crop((ox, (img.height - H) // 2, ox + W, (img.height - H) // 2 + H))
    # Sıcak, sinematik ton (videolarla aynı his) ve hafif kenar kararması
    img = ImageEnhance.Contrast(ImageEnhance.Color(img).enhance(0.92)).enhance(1.06)
    rr, gg, bb = img.split()
    img = Image.merge('RGB', (rr.point(lambda v: min(255, v * 1.04)), gg, bb.point(lambda v: v * 0.95)))
    d = ImageDraw.Draw(Image.new('RGB', (W, H)))
    uzun = len(metin) > MAKS_METIN
    f = ImageFont.truetype(f'{KOK}/yazi/Lora-SemiBold.ttf', int((38 if uzun else 44) * O))
    fs = ImageFont.truetype(f'{KOK}/yazi/Lora-Bold.ttf', int(26 * O))
    fa = ImageFont.truetype(f'{KOK}/yazi/Amiri-Regular.ttf', int(48 * O))
    tr = sar(d, '“' + metin.strip('“”"') + '”', f, W - 120 * O)
    ar = sar(d, arapca, fa, W - 110 * O, rtl=True) if arapca else []
    if len(ar) > 2: ar = []
    LH, ALH = int((54 if uzun else 62) * O), int(80 * O)
    blok = len(ar) * ALH + (int(24 * O) if ar else 0) + len(tr) * LH + int(50 * O)
    yuk = blok + (int((68 + SELAM_H - 50) * O) if selam else 0)
    y = sakin_yer(img, yuk) if yer is None else int(min(max(H * yer - yuk / 2, 90 * O), H - 170 * O - yuk))
    satirlar = []
    for s in ar: satirlar.append((y, s, fa, ARAPCA, True)); y += ALH
    if ar: y += int(24 * O)
    for s in tr: satirlar.append((y, s, f, KREM, False)); y += LH
    satirlar.append((y + int(14 * O), kaynak, fs, ALTIN, False))
    selam_y = y + int(68 * O)
    ust, alt = satirlar[0][0] - int(40 * O), (selam_y + int((SELAM_H + 30) * O)) if selam else y + int(80 * O)
    isik = ImageStat.Stat(img.convert('L').crop((60, max(0, ust), W - 60, min(H, alt)))).mean[0]
    koyu = int(60 + 130 * min(1, max(0, (isik - 60) / 110)))
    if yer is not None: koyu = max(koyu, 150)   # elle yerleştirilen yazı karmaşık görüntü üstünde: koyu bant
    c = img.convert('RGBA')
    g = Image.new('L', (1, H))
    for yy in range(H):
        g.putpixel((0, yy), int(min(1, max(0, (yy - H * 0.45) / (H * 0.55)) * 1.2) * 170))
    k = Image.new('RGBA', (W, H), (0, 0, 0, 255)); k.putalpha(g.resize((W, H))); c.alpha_composite(k)
    m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).rounded_rectangle((15, ust, W - 15, alt), int(50 * O), fill=koyu)
    k = Image.new('RGBA', (W, H), (0, 0, 0, 255)); k.putalpha(m.filter(ImageFilter.GaussianBlur(int(50 * O)))); c.alpha_composite(k)
    tl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(tl)
    for yy, s, font, renk, rtl in satirlar:
        yon = 'rtl' if rtl else None
        x = (W - dd.textlength(s, font=font, direction=yon)) / 2
        if rtl:
            dd.text((x, yy), s, font=font, fill=KOYU, direction=yon, stroke_width=4, stroke_fill=KOYU)
            dd.text((x, yy), s, font=font, fill=renk, direction=yon, stroke_width=1, stroke_fill=renk)
        else:
            dd.text((x, yy), s, font=font, fill=renk, stroke_width=1 if font is fs else 3, stroke_fill=KOYU)
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    sh.putalpha(tl.split()[3].filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * .8)))
    c.alpha_composite(sh, (0, 4)); c.alpha_composite(tl)
    lg = Image.open(f'{KOK}/logo.webp').convert('RGBA'); lg.thumbnail((int(132 * O), int(132 * O)))
    c.alpha_composite(lg, (W - lg.width - int(34 * O), H - int(44 * O) - lg.height))
    c.convert('RGB').save(cikti + '.jpg', quality=86, optimize=True, progressive=True)
    c.convert('RGB').resize((360, 640), Image.LANCZOS).save(cikti + '_k.jpg', quality=80)
    return round(selam_y / H, 4)


def taslak(numaralar, pey_no):
    secim = {int(x) for x in numaralar.replace(',', ' ').split()}
    pey_no = {int(x) for x in pey_no.replace(',', ' ').split()}
    onayli = json.load(open('fotolar.json')) if os.path.exists('fotolar.json') else []
    kullanilan = {f['kaynak'] for f in onayli}
    metinler = [m for m in json.load(open(f'{KOK}/metinler.json')) if m['kaynak'] not in kullanilan and m['kaynak'] not in HARIC and len(m['metin']) <= MAKS_KART]
    random.seed(int(time.time())); random.shuffle(metinler)
    pey = [m for m in metinler if PEY.search(m['metin']) and m['kaynak'] not in PEY_HARIC]
    diger = [m for m in metinler if m not in pey]
    os.makedirs('foto-taslak', exist_ok=True)
    liste = []
    for a in json.load(open('foto-aday/liste.json')):
        if a['no'] not in secim: continue
        m = pey.pop(0) if a['no'] in pey_no and pey else diger.pop(0)
        n = len(liste) + 1
        try:
            img = Image.open(io.BytesIO(ac(a['url']))).convert('RGB')
        except Exception as e:
            print('indirilemedi', a['sayfa'], e); continue
        sy = kart(img, m['metin'], m['kaynak'], f'foto-taslak/{n:02d}', m.get('arapca', ''))
        liste.append({'no': n, 'pixabay': a['id'], 'sayfa': a['sayfa'], 'arama': a['arama'], 'selam_y': sy, **m})
        print(n, a['sayfa'], m['kaynak'])
    json.dump(liste, open('foto-taslak/liste.json', 'w'), ensure_ascii=False, indent=1)


# Mazlumlar (Gazze) bölümü: kullanıcının gönderdiği fotoğraflar (arac/gazze/NN.jpg) ve Pixabay'den seçilenler
# ("px:kimlik"), her birinde gazze.json'dan tek bir kaynaklı metin. Selam yazısı konmaz (bolum: gazze).
# yer: yazının ortası (yüksekliğe oranla); kişinin üstüne gelmesin diye elle verilir, None ise en sakin yer.
GAZZE = [  # (fotoğraf, yatay odak, yer, gazze.json'daki kaynak)
    ('27', 0.48, 0.17, 'Hadis-i Şerif · Buhârî, Zekât, 63'),
    ('28', 0.5, None, 'Âl-i İmrân, 150'),
    ('29', 0.5, None, 'Hadis-i Şerif · Buhârî, Talâk, 25'),
    ('30', 0.6, 0.14, 'Meâric, 5'),
    ('31', 0.55, None, 'Yûnus, 44'),
    ('px:1233827', 0.5, None, 'Rûm, 5'),
    ('px:2093372', 0.5, None, 'Âl-i İmrân, 126'),
    ('px:1756826', 0.5, None, 'Neml, 79'),
    ('px:4853197', 0.5, None, 'Âl-i İmrân, 160'),
    ('px:1439887', 0.5, None, 'Hadis-i Şerif · Tirmizî, Sıfatü’l-kıyâme, 8'),
    ('px:7554178', 0.5, None, 'Ahzâb, 3'),
    ('px:380754', 0.5, None, 'Hadis-i Şerif · Tirmizî, Sıfatü’l-kıyâme, 59'),
    ('px:2578323', 0.5, None, 'İbrâhîm, 27'),
    ('px:4661296', 0.5, None, 'Hadis-i Şerif · Ebû Dâvûd, Kadâ’ (akdiye), 14'),
    ('px:7092311', 0.5, None, 'Fussilet, 46'),
    ('px:1512181', 0.5, None, 'Zümer, 69'),
    ('px:202047', 0.5, None, 'Nisâ, 45'),
    ('px:3870862', 0.5, None, 'İnşirâh, 5'),
    ('px:5666549', 0.5, None, 'Hadis-i Şerif · Müslim, Cenâiz, 14'),
    ('px:1641753', 0.5, 0.18, 'Bakara, 153'),
    ('px:1665871', 0.5, None, 'Hadis-i Şerif · Müslim, Birr, 62'),
    ('px:112790', 0.5, None, 'Hadis-i Şerif · Ebû Dâvûd, Vitr, 29'),
]


def gazze():
    metin = {m['kaynak']: m for m in json.load(open(f'{KOK}/gazze.json'))}
    tum = json.load(open('fotolar.json')) if os.path.exists('fotolar.json') else []
    for f in tum:   # eski Mazlumlar kartlarının dosyaları silinir, yenileri yazılır
        if f.get('bolum') == 'gazze':
            for y in (f['resim'], f['kapak']):
                if os.path.exists(y): os.remove(y)
    onayli = [f for f in tum if f.get('bolum') != 'gazze']
    os.makedirs('fotolar', exist_ok=True)
    yeni = []
    for foto, odak, yer, k in GAZZE:
        m = metin[k]
        if foto.startswith('px:'):
            pid = foto[3:]
            u = 'https://pixabay.com/api/?' + urllib.parse.urlencode({'key': os.environ['PIXABAY_API_KEY'], 'id': pid})
            h = json.loads(ac(u))['hits'][0]
            img = Image.open(io.BytesIO(ac(h['largeImageURL']))).convert('RGB')
            fid, lisans, px = f'gp{pid}', h['pageURL'], int(pid)
        else:
            img = Image.open(f'{KOK}/gazze/{foto}.jpg').convert('RGB')
            fid, lisans, px = f'g{foto}', 'Pexels', 0
        kart(img, m['metin'], m['kaynak'], f'fotolar/{fid}', m.get('arapca', ''), selam=False, odak=odak, yer=yer)
        yeni.append({'id': fid, 'resim': f'fotolar/{fid}.jpg', 'kapak': f'fotolar/{fid}_k.jpg', 'tur': m['tur'],
                     'metin': m['metin'], 'kaynak': m['kaynak'], 'pixabay': px, 'lisans': lisans, 'selam_y': 0,
                     'bolum': 'gazze', 'konu': 'gazze', 'eklendi': time.strftime('%Y-%m-%d')})
        print(fid, k)
    json.dump(onayli + yeni, open('fotolar.json', 'w'), ensure_ascii=False, indent=1)


def eslestir():
    """Onaylı kartları yeniden çizer: görüntünün konusu Pixabay etiketlerinden, metin konusuna göre dağıtılır
    (cemaat hadisi cami içine, kudret ayeti doğaya …); logo büyük, hat görüntüsünde Arapça satır yok."""
    import konu
    tum = json.load(open('fotolar.json'))
    gazze_k = [f for f in tum if f.get('bolum') == 'gazze']
    onayli = [f for f in tum if f.get('bolum') != 'gazze']
    metinler = [m for m in json.load(open(f'{KOK}/metinler.json')) if m['kaynak'] not in HARIC and len(m['metin']) <= MAKS_KART]
    random.seed(11); random.shuffle(metinler)
    for f in onayli:
        u = 'https://pixabay.com/api/?' + urllib.parse.urlencode({'key': os.environ['PIXABAY_API_KEY'], 'id': f['pixabay']})
        try:
            h = json.loads(ac(u))['hits'][0]
            f['konu'], f['_url'] = konu.medya_konu(h.get('tags', '')), h['largeImageURL']
        except Exception as e:
            print('etiket yok', f['id'], e); f['konu'] = f.get('konu', 'doga')
    for f, m in konu.dagit([f for f in onayli if f.get('_url')], metinler):
        try:
            img = Image.open(io.BytesIO(ac(f['_url']))).convert('RGB')
            sy = kart(img, m['metin'], m['kaynak'], f['resim'][:-4], m.get('arapca', ''), hat=f['konu'] == 'hat')
        except Exception as e:
            print('yenilenemedi', f['id'], e); continue
        f.update(metin=m['metin'], kaynak=m['kaynak'], tur=m['tur'], selam_y=sy)
        print('eşleşti', f['id'], f['konu'], m['kaynak'])
    for f in onayli: f.pop('_url', None)
    onayli.sort(key=lambda x: konu.SIRA.get(x.get('konu'), 9))
    json.dump(onayli + gazze_k, open('fotolar.json', 'w'), ensure_ascii=False, indent=1)


def onay(numaralar):
    secim = {int(x) for x in numaralar.replace(' ', '').split(',') if x}
    onayli = json.load(open('fotolar.json')) if os.path.exists('fotolar.json') else []
    os.makedirs('fotolar', exist_ok=True)
    for t in json.load(open('foto-taslak/liste.json')):
        if t['no'] not in secim: continue
        fid = f"f{t['pixabay']}"
        shutil.copy(f"foto-taslak/{t['no']:02d}.jpg", f'fotolar/{fid}.jpg')
        shutil.copy(f"foto-taslak/{t['no']:02d}_k.jpg", f'fotolar/{fid}_k.jpg')
        onayli.insert(0, {'id': fid, 'resim': f'fotolar/{fid}.jpg', 'kapak': f'fotolar/{fid}_k.jpg', 'tur': t['tur'],
                          'metin': t['metin'], 'kaynak': t['kaynak'], 'pixabay': t['pixabay'], 'lisans': t['sayfa'],
                          'selam_y': t['selam_y'], 'eklendi': time.strftime('%Y-%m-%d')})
    json.dump(onayli, open('fotolar.json', 'w'), ensure_ascii=False, indent=1)
    print('onaylı foto', len(onayli))


if __name__ == '__main__':
    mod = sys.argv[1]
    if mod == 'aday':
        aday([a.strip() for a in sys.argv[2].split(',') if a.strip()], int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] else 7)
    elif mod == 'taslak':
        taslak(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else '')
    elif mod == 'onay':
        onay(sys.argv[2])
    elif mod == 'gazze':
        gazze()
    elif mod == 'eslestir':
        eslestir()
