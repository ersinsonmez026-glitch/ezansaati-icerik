"""Taslak mesaj videoları üretir: Pixabay'den sakin dini videolar bulur, üstüne kaynaklı ayet/hadis ve logo
ekler (sessiz, 720x1280, 15 sn). Çıktı: taslak/NN.mp4, taslak/NN.jpg ve taslak/liste.json.
Uygulamaya girmez; yalnız onaylananlar onay.py ile videolar/ klasörüne ve videolar.json'a eklenir."""
import json, os, random, subprocess, sys, urllib.error, urllib.parse, urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageStat

W, H, SURE = 720, 1280, 15
KOK = os.path.dirname(os.path.abspath(__file__))
# Öncelik sırası: Kâbe ve Mescid-i Haram, cami içleri, hat (Allah, Muhammed), Kur'an; en son genel cami.
ARAMALAR = ['kaaba', 'mecca', 'masjid al haram', 'mosque interior', 'mosque dome inside', 'mosque chandelier',
            'islamic calligraphy', 'arabic calligraphy', 'allah', 'quran', 'medina mosque', 'mosque']
# Yakın çekim insan yüzü olan videolar alınmaz (etiketlere göre).
YASAK = {'woman', 'women', 'girl', 'man', 'men', 'boy', 'child', 'children', 'kid', 'portrait', 'face', 'model',
         'beauty', 'person', 'people', 'family', 'muslim woman', 'hijab', 'selfie', 'smile', 'couple', 'dance', 'music',
         'mother', 'baby', 'son', 'daughter', 'muslim girl', 'niqab', 'burqa', 'student', 'kids', 'lady', 'female', 'male',
         'city', 'cityscape', 'skyline', 'traffic', 'street'}

UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36'}

def ac(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120)

def json_al(url):
    try:
        return json.load(ac(url))
    except urllib.error.HTTPError as e:
        raise SystemExit(f'Pixabay arama hatası {e.code} (anahtar doğru mu?)')

def adaylar(anahtar, kullanilan):
    for q in ARAMALAR:
        u = 'https://pixabay.com/api/videos/?' + urllib.parse.urlencode(
            {'key': anahtar, 'q': q, 'safesearch': 'true', 'per_page': 50, 'video_type': 'film'})
        for v in json_al(u).get('hits', []):
            etiket = {t.strip().lower() for t in v.get('tags', '').split(',')}
            if v['id'] in kullanilan or v['duration'] < 8 or etiket & YASAK:
                continue
            boy = v['videos'].get('large') or v['videos'].get('medium')
            if not boy or not boy.get('url'):
                continue
            kullanilan.add(v['id'])   # aynı video iki aramada çıkarsa bir kez alınır
            yield {'sira': ARAMALAR.index(q), 'id': v['id'], 'url': boy['url'], 'dikey': boy['height'] > boy['width'],
                   'sayfa': v['pageURL'], 'arama': q, 'etiket': v.get('tags', '')}

KELIME_SN = 0.38   # okuma hızı: kelime başına
BASLA = 1.0
FPS_YAZI = 10

COMMONS_ARAMA = ['Kaaba', 'Masjid al-Haram', 'Kaaba tawaf', 'Mosque interior', 'Prophet\'s Mosque Medina',
                 'Sultan Ahmed Mosque interior', 'Islamic calligraphy', 'Mosque dome interior']
COMMONS_LISANS = ('cc0', 'public domain', 'cc by', 'cc-by')   # CC BY / BY-SA: görüntü sahibinin adı videoya yazılır
CUA = {'User-Agent': 'EzanSaatiVideo/1.0 (https://ezansaati-premium-2026.web.app; ezansaatidestek@gmail.com)'}

def commons_adaylar(kullanilan):
    import re
    for q in COMMONS_ARAMA:
        u = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode({
            'action': 'query', 'format': 'json', 'generator': 'search', 'gsrnamespace': 6,
            'gsrsearch': f'{q} filetype:video', 'gsrlimit': 40, 'prop': 'imageinfo',
            'iiprop': 'url|size|mime|extmetadata'})
        try:
            veri = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=CUA), timeout=60))
        except Exception as e:
            print('commons arama olmadı', q, e); continue
        for sayfa in (veri.get('query', {}).get('pages', {}) or {}).values():
            ii = (sayfa.get('imageinfo') or [{}])[0]
            em = ii.get('extmetadata', {})
            lis = (em.get('LicenseShortName', {}).get('value') or '').lower()
            sure = float(ii.get('duration') or 0)
            vid = 'c' + str(sayfa['pageid'])
            if vid in kullanilan or not any(l in lis for l in COMMONS_LISANS) or 'nc' in lis or 'nd' in lis:
                continue
            if sure and sure < 8:
                continue
            url = ii.get('url', '')
            m = re.match(r'(https://upload\.wikimedia\.org/wikipedia/commons)/(\w/\w\w)/(.+)$', url)
            if not m:
                continue
            ad = m.group(3)
            # Wikimedia'nın küçültülmüş (720p) kopyası; yoksa özgün dosya (çok büyük değilse)
            adaylar_url = [f'{m.group(1)}/transcoded/{m.group(2)}/{ad}/{ad}.720p.vp9.webm',
                           f'{m.group(1)}/transcoded/{m.group(2)}/{ad}/{ad}.480p.vp9.webm']
            if (ii.get('size') or 0) < 150e6:
                adaylar_url.append(url)
            sahip = re.sub(r'<[^>]+>', '', em.get('Artist', {}).get('value') or '').strip()[:40]
            kullanilan.add(vid)
            yield {'sira': -1, 'id': vid, 'urls': adaylar_url, 'url': adaylar_url[0], 'dikey': (ii.get('height') or 0) > (ii.get('width') or 1),
                   'sayfa': sayfa.get('fullurl') or 'https://commons.wikimedia.org/wiki/' + urllib.parse.quote(sayfa['title']),
                   'arama': 'commons:' + q, 'etiket': sayfa['title'],
                   'kredi': f"Görüntü: {sahip} · {em.get('LicenseShortName', {}).get('value', '')} · Wikimedia Commons"}

def pexels_adaylar(baglantilar, kullanilan):
    """Kullanıcının seçtiği Pexels videoları (sayfa ya da indirme adresi). Pexels lisansı kaynak göstermeyi zorunlu tutmaz."""
    import re
    for b in baglantilar:
        m = re.search(r'pexels\.com/.*?(\d{5,})/?$', b.strip())
        if not m or f'pexels-{m.group(1)}' in kullanilan:
            continue
        i = m.group(1)
        yield {'id': f'pexels-{i}', 'url': f'https://www.pexels.com/download/video/{i}/',
               'sayfa': f'https://www.pexels.com/video/{i}/', 'arama': 'pexels', 'dikey': True, 'sira': -2}

def parlaklik(ust, alt):
    """Kaynak videonun (kırpılmış hâli) yazı bölgesindeki ortalama parlaklığı (0-255), birkaç kareden."""
    for fn in os.listdir('/tmp'):
        if fn.startswith('pk_'): os.remove('/tmp/' + fn)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', '/tmp/kaynak.mp4', '-vf',
                    f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=1/2', '-frames:v', '6',
                    '/tmp/pk_%d.png'], check=True)
    d = [ImageStat.Stat(Image.open('/tmp/' + fn).convert('L').crop((60, max(0, ust), W - 60, min(H, alt)))).mean[0]
         for fn in os.listdir('/tmp') if fn.startswith('pk_')]
    return max(d) if d else 120

def katman(metin, kaynak, cikti, kredi='', arapca=''):
    """Zemin karartması ve logo sabit; yazı kelime kelime belirir (PNG dizisi, saniyede 10 kare)."""
    d = ImageDraw.Draw(Image.new('RGBA', (W, H)))
    metin = '“' + metin.strip('“”"') + '”'
    for boyut in (42, 38, 34, 30, 27):
        f = ImageFont.truetype(f'{KOK}/yazi/Lora-SemiBold.ttf', boyut)
        satir, cur = [], []
        for w in metin.split():
            if d.textlength(' '.join(cur + [w]), font=f) > W - 110 and cur: satir.append(cur); cur = [w]
            else: cur.append(w)
        satir.append(cur)
        lh = int(boyut * 1.42)
        if len(satir) * lh < 440: break
    fs = ImageFont.truetype(f'{KOK}/yazi/Lora-Bold.ttf', 27)
    y0 = H - 250 - len(satir) * lh - 40
    # Arapça (kısa ayetlerde): Türkçe mealin üstünde, en başta belirir
    ar_satir, fa = [], None
    if arapca:
        fa = ImageFont.truetype(f'{KOK}/yazi/Amiri-Regular.ttf', 40)
        cur = []
        for w in arapca.split():
            if d.textlength(' '.join(cur + [w]), font=fa, direction='rtl') > W - 100 and cur:
                ar_satir.append(' '.join(cur)); cur = [w]
            else:
                cur.append(w)
        ar_satir.append(' '.join(cur))
        y0 += 0
        ar_lh = 64
        y_ar = y0 - len(ar_satir) * ar_lh - 24
    # Her kelimenin yeri (satır ortalanmış)
    yerler = []
    for i, ks in enumerate(satir):
        x = (W - d.textlength(' '.join(ks), font=f)) / 2
        for k in ks:
            yerler.append((x, y0 + i * lh, k))
            x += d.textlength(k + ' ', font=f)
    kx = (W - d.textlength(kaynak, font=fs)) / 2; ky = y0 + len(satir) * lh + 16
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    g = Image.new('L', (1, H))
    for y in range(H):
        t = max(0, (y - H * 0.35) / (H * 0.65))
        g.putpixel((0, y), int(min(1, t * 1.3) * 200))
    kar = Image.new('RGBA', (W, H), (0, 0, 0, 255)); kar.putalpha(g.resize((W, H)))
    ov.alpha_composite(kar)
    # Yazının arkasına kenarları silik koyu bant; koyuluğu o bölgedeki görüntünün parlaklığına göre (açık sahnede koyu)
    ust = (y_ar if ar_satir else y0) - 40; alt = ky + 60
    isik = parlaklik(ust, alt)
    koyu = int(70 + 120 * min(1, max(0, (isik - 60) / 110)))
    m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).rounded_rectangle((20, ust, W - 20, alt), 40, fill=koyu)
    bant = Image.new('RGBA', (W, H), (0, 0, 0, 255)); bant.putalpha(m.filter(ImageFilter.GaussianBlur(45)))
    ov.alpha_composite(bant)
    print('parlaklık', int(isik), 'bant', koyu)
    lg = Image.open(f'{KOK}/logo.webp').convert('RGBA'); lg.thumbnail((120, 120))
    ov.alpha_composite(lg, (W - lg.width - 36, H - 46 - lg.height))   # logo sağ altta
    if kredi:   # CC BY lisansı: görüntü sahibinin adı
        ImageDraw.Draw(ov).text((24, H - 34), kredi, font=ImageFont.truetype(f'{KOK}/yazi/Lora-SemiBold.ttf', 15),
                                fill=(255, 255, 255, 150))
    ov.save('/tmp/kar.png')
    ar_sure = 2.2 if ar_satir else 0      # Arapça önce belirir
    son = BASLA + ar_sure + len(yerler) * KELIME_SN
    sure = max(SURE, son + 4.5)
    os.makedirs('/tmp/yz', exist_ok=True)
    for fn in os.listdir('/tmp/yz'): os.remove('/tmp/yz/' + fn)
    kare_say = int((son + 1.2) * FPS_YAZI) + 1
    for n in range(kare_say):
        t = n / FPS_YAZI
        tl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(tl)
        if ar_satir:
            a = (t - BASLA) / 1.2
            if a > 0:
                for j, sa in enumerate(ar_satir):
                    dd.text(((W - dd.textlength(sa, font=fa, direction='rtl')) / 2, y_ar + j * ar_lh), sa, font=fa,
                            fill=(240, 214, 150, int(255 * min(1, a))), direction='rtl',
                            stroke_width=2, stroke_fill=(20, 15, 5, int(255 * min(1, a))))
        for i, (x, y, k) in enumerate(yerler):
            a = (t - (BASLA + ar_sure + i * KELIME_SN)) / 0.35      # her kelime 0,35 sn'de belirir
            if a > 0:
                dd.text((x, y), k, font=f, fill=(255, 250, 235, int(255 * min(1, a))), stroke_width=2,
                        stroke_fill=(20, 15, 5, int(255 * min(1, a))))
        a = (t - son - 0.2) / 0.6
        if a > 0:
            dd.text((kx, ky), kaynak, font=fs, fill=(232, 200, 138, int(255 * min(1, a))), stroke_width=1,
                    stroke_fill=(20, 15, 5, int(255 * min(1, a))))
        golge = Image.new('RGBA', (W, H), (0, 0, 0, 255))
        golge.putalpha(tl.split()[3].filter(ImageFilter.GaussianBlur(4)).point(lambda v: int(v * .85)))
        yazi = Image.new('RGBA', (W, H), (0, 0, 0, 0)); yazi.alpha_composite(golge, (2, 3)); yazi.alpha_composite(tl)
        yazi.save(f'/tmp/yz/{n:04d}.png')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-stream_loop', '-1', '-i', '/tmp/kaynak.mp4',
        '-loop', '1', '-i', '/tmp/kar.png', '-framerate', str(FPS_YAZI), '-i', '/tmp/yz/%04d.png', '-filter_complex',
        f'[0]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,format=yuv420p[bg];'
        '[bg][1]overlay[b1];[2]format=rgba[t];[b1][t]overlay=eof_action=repeat,'
        f'fade=in:st=0:d=0.8,fade=out:st={sure-0.8:.2f}:d=0.8,format=yuv420p[v]',
        '-map', '[v]', '-an', '-t', f'{sure:.2f}', '-c:v', 'libx264', '-preset', 'slow', '-crf', '27',
        '-movflags', '+faststart', cikti + '.mp4'], check=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', f'{min(son + 1.5, sure - 1):.2f}', '-i', cikti + '.mp4',
        '-frames:v', '1', '-vf', 'scale=360:-2', '-q:v', '4', cikti + '.jpg'], check=True)

# Bağlamından koparılınca anlamı bozulan metinler Peygamber videolarına konmaz
PEY_HARIC = {'Hadis-i Şerif · Buhârî, Şurût, 15', 'Hadis-i Şerif · İbn Hanbel, VI, 157'}

def yenile():
    """Onaylı videoları (videolar.json) güncel yazı düzeniyle aynı metin ve kaynakla yeniden üretir."""
    ar = {m['kaynak']: m.get('arapca', '') for m in json.load(open(f'{KOK}/metinler.json'))}
    for v in json.load(open('videolar.json')):
        i = v['pixabay'].removeprefix('pexels-')
        url = f'https://www.pexels.com/download/video/{i}/' if v['pixabay'].startswith('pexels-') else v.get('kaynak_url')
        if not url:
            print('atlandı', v['id']); continue
        open('/tmp/kaynak.mp4', 'wb').write(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300).read())
        katman(v['metin'], v['kaynak'], v['video'][:-4], v.get('kredi', ''), ar.get(v['kaynak'], ''))
        print('yenilendi', v['id'])

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'yenile':
        yenile(); sys.exit()
    adet = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    anahtar = os.environ['PIXABAY_API_KEY']
    onayli = json.load(open('videolar.json'))
    kullanilan = {v['pixabay'] for v in onayli}
    kullanilan_metin = {v['kaynak'] for v in onayli}
    import re
    import pro   # profesyonel düzen (kısa metin, harf harf yazı, sakin yer)
    metinler = [m for m in json.load(open(f'{KOK}/metinler.json'))
                if m['kaynak'] not in kullanilan_metin and len(m['metin']) <= pro.MAKS_METIN]
    # Hz. Peygamber'le ilgili metinler gül/hat videolarına (PEYGAMBER = aday numaraları)
    PEY = re.compile(r'Peygamber|Resûl|Muhammed|Nebi', re.I)
    pey_no = {int(x) for x in os.environ.get('PEYGAMBER', '').replace(',', ' ').split()}
    pey_metin = [m for m in metinler if PEY.search(m['metin']) and m['kaynak'] not in PEY_HARIC]
    metinler = [m for m in metinler if m not in pey_metin]
    random.shuffle(metinler)
    # Önce dikey videolar, aramalar karışık
    kaynak = sys.argv[2] if len(sys.argv) > 2 else 'hepsi'
    havuz = []
    if kaynak == 'aday':   # aday.yml vitrininden seçilen numaralar
        sec = {int(x) for x in os.environ.get('BAGLANTILAR', '').replace(',', ' ').split()}
        for a in json.load(open('aday/liste.json')):
            if a['no'] in sec and a['id'] not in kullanilan:
                havuz.append({'id': a['id'], 'url': a['url'], 'sayfa': a['sayfa'], 'arama': 'pexels', 'dikey': True, 'sira': -2,
                              'peygamber': a['no'] in pey_no})
    if kaynak == 'pexels':
        havuz += list(pexels_adaylar(os.environ.get('BAGLANTILAR', '').split(), kullanilan))
    if kaynak in ('commons', 'hepsi'):
        havuz += list(commons_adaylar(kullanilan))
    if kaynak in ('pixabay', 'hepsi'):
        havuz += list(adaylar(anahtar, kullanilan))
    print('aday sayısı', len(havuz))
    if kaynak not in ('pexels', 'aday'):
        random.shuffle(havuz)
    # Önce öncelikli aramalardan; her aramadan en çok 2 video (çeşitlilik), dikeyler önde
    havuz.sort(key=lambda v: (v['sira'], not v['dikey']))  # Commons (sira -1) önce
    say, secim = {}, []
    for v in havuz:
        if v['arama'] == 'pexels' or say.get(v['arama'], 0) < 2:
            secim.append(v); say[v['arama']] = say.get(v['arama'], 0) + 1
    havuz = secim + [v for v in havuz if v not in secim]
    os.makedirs('taslak', exist_ok=True)
    liste = []
    n = 0
    sira = iter(metinler)
    for v in havuz:
        if n >= adet:
            break
        m = pey_metin.pop(0) if v.get('peygamber') and pey_metin else next(sira)
        n += 1
        tamam = False
        for url in v.get('urls', [v['url']]):
            try:
                req = urllib.request.Request(url, headers=CUA if 'wikimedia' in url else UA)
                open('/tmp/kaynak.mp4', 'wb').write(urllib.request.urlopen(req, timeout=300).read())
                tamam = True; break
            except Exception as e:
                print('indirilemedi', url, e)
        if not tamam:
            n -= 1; continue
        ad = f'taslak/{n:02d}'
        try:
            sy = pro.katman(m['metin'], m['kaynak'], ad, m.get('arapca', ''))
        except subprocess.CalledProcessError as e:
            print('işlenemedi', v['sayfa'], e); n -= 1; continue
        liste.append({'no': n, 'pixabay': v['id'], 'sayfa': v['sayfa'], 'arama': v['arama'], 'dikey': v['dikey'],
                      'kredi': v.get('kredi', ''), 'selam_y': sy, **m})
        print(n, v['sayfa'], m['kaynak'])
    json.dump(liste, open('taslak/liste.json', 'w'), ensure_ascii=False, indent=1)
