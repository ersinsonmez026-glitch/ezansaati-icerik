"""Bütün foto kartlarını (fotolar.json: genel + Mazlumlar, arac/ozel_secim.json: bölüm kartları) tek planla çizer:
görsel hiç koyulaştırılmaz; yazı her kartta tek renk (açık zeminde koyu, koyu zeminde krem); yer alttan yukarı
aranır ve okunur olan ilk (en alttaki) yer seçilir. Her satırın (Arapça, meal, kaynak) okunurluğu ölçülür;
hiçbir yerde okunmayan kart elenir.

  python3 arac/kartyeni.py hazirla           -> foto-yeni/NNN.jpg, vitrinN.jpg, liste.json (uygulamaya girmez)
  python3 arac/kartyeni.py onayla "12 40"    -> elenmeyenler (ve ek çıkarılacak numaralar hariç) fotolar.json,
                                                ozel.json ve fotolar/ klasörüne; eski dosyalar silinir"""
import io, json, os, sys, time, urllib.parse
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
from foto import ac, GAZZE, W, H, O, _yumusak_yaz
from pro import sar, MAKS_METIN, KREM, ALTIN, ARAPCA, SELAM_H

HAM = 'ham'          # ham görüntü önbelleği (yalnız Actions önbelleğinde; depoya girmez)
CIK = 'foto-yeni'
ALT_SINIR = 0.25     # yazı bloğunun üstü bundan yukarı çıkmaz (yüksekliğe oranla)
IYI = 0.12           # bu puanın altı rahat okunur: alttan ilk böyle yer seçilir
SINIR = 0.22         # en iyi yer bile bunun üstündeyse kart elenir


def _pixabay(pid):
    u = 'https://pixabay.com/api/?' + urllib.parse.urlencode({'key': os.environ['PIXABAY_API_KEY'], 'id': pid})
    time.sleep(0.8)   # dakikada 100 istek sınırı
    h = json.loads(ac(u))['hits'][0]
    return ac(h['largeImageURL'])


def ham(anahtar, getir, odak=0.5):
    """W x H'ye kırpılmış, sıcak tonlu görüntü (yazısız). Bir kez indirilir."""
    yol = f'{HAM}/{anahtar}_{int(odak * 100)}.jpg'
    if os.path.exists(yol):
        return Image.open(yol).convert('RGB')
    img = Image.open(io.BytesIO(getir())).convert('RGB')
    r = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * r) + 1, int(img.height * r) + 1), Image.LANCZOS)
    ox = int(min(max(0, img.width * odak - W / 2), img.width - W))
    img = img.crop((ox, (img.height - H) // 2, ox + W, (img.height - H) // 2 + H))
    img = ImageEnhance.Contrast(ImageEnhance.Color(img).enhance(0.92)).enhance(1.06)
    rr, gg, bb = img.split()
    img = Image.merge('RGB', (rr.point(lambda v: min(255, v * 1.04)), gg, bb.point(lambda v: v * 0.95)))
    os.makedirs(HAM, exist_ok=True)
    img.save(yol, quality=95)
    return img


def duzen(metin, kaynak, arapca):
    """Satırlar (bloğun üstüne göre konum), blok yüksekliği ve yazı tipleri."""
    d = ImageDraw.Draw(Image.new('RGB', (W, H)))
    uzun = len(metin) > MAKS_METIN
    b = 0.92
    f = ImageFont.truetype(f'{KOK}/yazi/Lora-SemiBold.ttf', int((38 if uzun else 44) * O * b))
    fs = ImageFont.truetype(f'{KOK}/yazi/Lora-Bold.ttf', int(26 * O))
    fa = ImageFont.truetype(f'{KOK}/yazi/AmiriQuran-Regular.ttf', int(46 * O * 1.08))
    tr = sar(d, '“' + metin.strip('“”"') + '”', f, W - 120 * O)
    ar = sar(d, arapca, fa, W - 110 * O, rtl=True) if arapca else []
    if len(ar) > 2: ar = []
    LH, ALH = int((54 if uzun else 62) * O * b), int(96 * O * b)
    sat, y = [], 0
    for s in ar: sat.append((y, s, fa, ARAPCA, True)); y += ALH
    if ar: y += int(34 * O)
    for s in tr: sat.append((y, s, f, KREM, False)); y += LH
    sat.append((y + int(14 * O), kaynak, fs, ALTIN, False))
    return sat, y, fs


def maskeler(sat):
    """Her satırın harf maskesi (biraz genişletilmiş: harfin çevresindeki zemin de sayılır), satır kutusuna göre."""
    out = []
    for oy, s, font, _, rtl in sat:
        yon = 'rtl' if rtl else None
        m = Image.new('L', (W, int(font.size * 2.2)), 0); dd = ImageDraw.Draw(m)
        x = (W - dd.textlength(s, font=font, direction=yon)) / 2
        dd.text((x, int(font.size * 0.4)), s, font=font, fill=255, direction=yon)
        m = m.filter(ImageFilter.MaxFilter(9))
        out.append((oy - int(font.size * 0.4), np.asarray(m) > 0))
    return out


def puan(L, E, mk, y, koyu):
    """Bloğun üstü y'deyken en kötü satırın puanı (0 iyi). Krem yazıda açık zemin, koyu yazıda koyu zemin ve
    her ikisinde zemindeki ayrıntı (kenar yoğunluğu) okunurluğu düşürür."""
    en = 0.0
    for oy, m in mk:
        y0 = y + oy
        a, e = L[y0:y0 + m.shape[0]][m[:H - y0]], E[y0:y0 + m.shape[0]][m[:H - y0]]
        if a.size == 0: continue
        kotu = (a < 105).mean() if koyu else (a > 165).mean()
        en = max(en, kotu + 3 * e.mean() / 255)
    return en


def ciz(img, metin, kaynak, arapca, selam, cikti):
    sat, son_y, fs = duzen(metin, kaynak, arapca)
    blok = sat[-1][0] + int(50 * O)
    yuk = blok + (int((68 + SELAM_H - 50) * O) if selam else 0)
    L = np.asarray(img.convert('L'), dtype=np.float32)
    Lb = np.asarray(img.convert('L').filter(ImageFilter.GaussianBlur(2)), dtype=np.float32)
    E = np.zeros_like(Lb)
    E[1:-1, 1:-1] = np.hypot(Lb[1:-1, 2:] - Lb[1:-1, :-2], Lb[2:, 1:-1] - Lb[:-2, 1:-1])
    E = np.minimum(E, 60)   # tek bir keskin kenar bütün satırı batırmasın
    mk = maskeler(sat)
    hi = int(H - 170 * O - yuk); lo = min(hi, max(int(90 * O), int(H * ALT_SINIR)))
    secim, enb = None, None
    for y in range(hi, lo - 1, -10):   # alttan yukarı
        for koyu in (False, True):
            p = puan(L, E, mk, y, koyu)
            if enb is None or p < enb[0]: enb = (p, y, koyu)
            if secim is None and p <= IYI: secim = (p, y, koyu)
    p, y, koyu = secim or enb
    satirlar = [(y + oy, s, font, renk, rtl) for oy, s, font, renk, rtl in sat]
    selam_y = y + son_y + int(68 * O)
    _yumusak_yaz(img.convert('RGBA'), satirlar, fs, cikti, selam_y, koyu=koyu)
    return {'puan': round(float(p), 3), 'koyu': koyu, 'yer': round(y / H, 3), 'selam_y': round(selam_y / H, 4),
            'elendi': bool(p > SINIR)}


def isler():
    """(anahtar, getir, odak, metin kaydı, selam, hedef liste, eski kayıt) — tüm kartlar."""
    metin = {m['kaynak']: m for m in json.load(open(f'{KOK}/metinler.json'))}
    gmetin = {m['kaynak']: m for m in json.load(open(f'{KOK}/gazze.json'))}
    godak = {k: (foto, odak) for foto, odak, _, k in GAZZE}
    for f in json.load(open('fotolar.json')):
        if f.get('bolum') == 'gazze':
            foto, odak = godak[f['kaynak']]
            m = gmetin[f['kaynak']]
            if foto.startswith('px:'):
                yield f'px{foto[3:]}', (lambda p=foto[3:]: _pixabay(p)), odak, m, False, 'fotolar', f
            else:
                yield f'g{foto}', (lambda p=foto: open(f'{KOK}/gazze/{p}.jpg', 'rb').read()), odak, m, False, 'fotolar', f
        else:
            m = dict(metin[f['kaynak']])
            if f.get('konu') == 'hat': m['arapca'] = ''   # hat görselinde Arapça satır konmaz
            yield f"px{f['pixabay']}", (lambda p=f['pixabay']: _pixabay(p)), 0.5, m, True, 'fotolar', f
    aday = {a['no']: a for a in json.load(open('foto-aday/liste.json'))}
    aday.update({f"P{a['no']}": a for a in json.load(open('foto-pexels/liste.json'))})
    for no, bolum, k in json.load(open(f'{KOK}/ozel_secim.json')):
        a, m = aday[no], metin[k]
        eski = {'id': f"o{a['id']}", 'pixabay': a['id'], 'lisans': a['sayfa'], 'bolum': bolum}
        if str(a['id']).startswith('pexels-'):
            yield a['id'], (lambda u=a['url']: ac(u + '?auto=compress&cs=tinysrgb&w=1800')), 0.5, m, True, 'ozel', eski
        else:
            yield f"px{a['id']}", (lambda p=a['id']: _pixabay(p)), 0.5, m, True, 'ozel', eski


def vitrin(liste):
    f = ImageFont.truetype(f'{KOK}/yazi/Lora-Bold.ttf', 26)
    tw, th, cols = 240, 427, 6
    for s in range(0, len(liste), 24):
        grup = liste[s:s + 24]
        c = Image.new('RGB', (cols * (tw + 8), ((len(grup) + cols - 1) // cols) * (th + 8)), 'white')
        for k, t in enumerate(grup):
            im = Image.open(f"{CIK}/{t['no']:03d}_k.jpg").resize((tw, th))
            x, y = (k % cols) * (tw + 8) + 4, (k // cols) * (th + 8) + 4
            c.paste(im, (x, y)); d = ImageDraw.Draw(c)
            if t['elendi']: d.rectangle((x - 4, y - 4, x + tw + 3, y + th + 3), outline=(220, 0, 0), width=6)
            d.rectangle((x, y, x + 150, y + 34), fill=(180, 0, 0) if t['elendi'] else (0, 90, 40))
            d.text((x + 5, y + 2), f"{t['no']} · {t['puan']:.2f}", font=f, fill='white')
        c.save(f'{CIK}/vitrin{s // 24 + 1}.jpg', quality=80)


def hazirla():
    os.makedirs(CIK, exist_ok=True)
    liste = []
    for n, (anahtar, getir, odak, m, selam, hedef, eski) in enumerate(isler(), 1):
        try:
            img = ham(anahtar, getir, odak)
        except Exception as e:
            print('indirilemedi', anahtar, e); continue
        r = ciz(img, m['metin'], m['kaynak'], m.get('arapca', ''), selam, f'{CIK}/{n:03d}')
        liste.append({'no': n, 'hedef': hedef, 'eski': eski, 'tur': m['tur'], 'metin': m['metin'],
                      'kaynak': m['kaynak'], **r})
        print(n, hedef, eski['id'], r)
    json.dump(liste, open(f'{CIK}/liste.json', 'w'), ensure_ascii=False, indent=1)
    vitrin(liste)
    print('elenen', [t['no'] for t in liste if t['elendi']])


def onayla(cikar):
    cikar = {int(x) for x in cikar.replace(',', ' ').split()}
    tarih = time.strftime('%Y-%m-%d')
    eski_dosya = {x for f in json.load(open('fotolar.json')) for x in (f['resim'], f['kapak'])}
    if os.path.exists('ozel.json'):
        eski_dosya |= {x for f in json.load(open('ozel.json')) for x in (f['resim'], f['kapak'])}
    out = {'fotolar': [], 'ozel': []}
    for t in json.load(open(f'{CIK}/liste.json')):
        if t['elendi'] or t['no'] in cikar: continue
        e = dict(t['eski']); fid = e['id']
        # Yeni dosya adı: telefonlardaki ve jsDelivr'daki eski kopya kullanılmaz
        e['resim'], e['kapak'] = f'fotolar/{fid}_y.jpg', f'fotolar/{fid}_y_k.jpg'
        os.replace(f"{CIK}/{t['no']:03d}.jpg", e['resim'])
        os.replace(f"{CIK}/{t['no']:03d}_k.jpg", e['kapak'])
        sy = t['selam_y']
        if round(sy * 10000) == round(e.get('selam_y', -1) * 10000): sy = round(sy + 0.0001, 4)   # sürüm değişsin
        if e.get('bolum') == 'gazze': sy = 0.0002 if e.get('selam_y') == 0.0001 else 0.0001   # selam yok; sürüm işareti
        e.update(tur=t['tur'], metin=t['metin'], kaynak=t['kaynak'], selam_y=sy)
        e.setdefault('eklendi', tarih)
        out[t['hedef']].append(e)
    yeni = {x for l in out.values() for f in l for x in (f['resim'], f['kapak'])}
    for y in eski_dosya - yeni:
        if os.path.exists(y): os.remove(y)
    json.dump(out['fotolar'], open('fotolar.json', 'w'), ensure_ascii=False, indent=1)
    json.dump(out['ozel'], open('ozel.json', 'w'), ensure_ascii=False, indent=1)
    print('fotolar', len(out['fotolar']), 'ozel', len(out['ozel']))


if __name__ == '__main__':
    {'hazirla': lambda: hazirla(), 'onayla': lambda: onayla(sys.argv[2] if len(sys.argv) > 2 else '')}[sys.argv[1]]()
