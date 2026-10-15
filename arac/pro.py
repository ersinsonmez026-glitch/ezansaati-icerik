"""Profesyonel video düzeni: kısa metin (en çok 3 satır), satır satır yumuşak beliren yazı, sinematik renk tonu,
yavaş yakınlaşma, yazının arkasında parlaklığa göre koyulaşan bant, sabit 13 sn ve aynı açılış/kapanış.
Kullanım:
  python3 arac/pro.py ornek <video kimlikleri, virgülle>   -> taslak/NN.mp4 (önizleme, uygulamaya girmez)
  python3 arac/pro.py hepsi                                 -> onaylı videoları yerinde yeniden üretir
  python3 arac/pro.py ses                                   -> metinleri değiştirmeden sesli yeniden üretir
  python3 arac/pro.py meal                                  -> tilavetin ardından Türkçe sesli meal (Diyanet Vakfı)
  python3 arac/pro.py mealornek <kimlikler>                 -> sesli meal önizlemesi (taslak dalı)
Ses: ayet videolarında o ayetin tilaveti (Mâhir el-Muaykılî, Islamic Network CDN); hadis videolarında arac/ses/
klasöründeki izinli ezgi/vokal kayıtlarından biri (kaynak ve lisans arac/ses/kaynak.json'da). Klasör boşsa sessiz."""
import json, os, random, subprocess, sys, urllib.parse, urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter

KOK = os.path.dirname(os.path.abspath(__file__))
# Bağlamından koparılınca uygun düşmeyen metinler (savaş, yöneticiler, cenaze, kişiye hitap vb.) kullanılmaz
HARIC = set(json.load(open(os.path.join(KOK, 'haric.json'))))
sys.path.insert(0, KOK)
from uret import UA, W, H, parlaklik

SURE, FPS_YAZI, ZOOM = 13.0, 30, 0.06
HIZ = 34          # Türkçe meal harf harf: saniyede harf
MAKS_METIN = 110          # videoda yalnız kısa metinler (uzunlar kartlarda)
RENK = ('eq=contrast=1.06:saturation=0.92:brightness=-0.015,'
        'colorbalance=rs=0.04:gs=0.01:bs=-0.04:rh=0.03:bh=-0.03,vignette=angle=PI/5')
KREM, ALTIN, KOYU = (255, 250, 235), (236, 204, 140), (20, 15, 5)
ARAPCA = (255, 238, 185)   # Arapça: açık altın, kalınlaştırılmış


def indir(v):
    """Onaylı videonun kaynak dosyası: Pexels indirme adresi ya da Pixabay API'den (kimlikle) dosya adresi."""
    k = str(v['pixabay'])
    if k.startswith('pexels-'):
        url = f"https://www.pexels.com/download/video/{k.removeprefix('pexels-')}/"
    else:
        u = 'https://pixabay.com/api/videos/?' + urllib.parse.urlencode({'key': os.environ['PIXABAY_API_KEY'], 'id': k})
        h = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))['hits'][0]
        v['_etiket'] = h.get('tags', '')
        hit = h['videos']
        url = (hit.get('large') or {}).get('url') or hit['medium']['url']
    open('/tmp/kaynak.mp4', 'wb').write(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300).read())


def sar(d, metin, font, genislik, rtl=False):
    satir, cur = [], []
    for w in metin.split():
        if cur and d.textlength(' '.join(cur + [w]), font=font, direction='rtl' if rtl else None) > genislik:
            satir.append(' '.join(cur)); cur = [w]
        else:
            cur.append(w)
    satir += [' '.join(cur)]
    # Dengeli satırlar: aynı satır sayısını veren en dar genişlik seçilir (son satırda tek kelime kalmasın)
    if len(satir) > 1 and genislik > 200:
        dar = sar(d, metin, font, genislik - 20, rtl)
        if len(dar) == len(satir): return dar
    return satir


SELAM_H = 100                 # uygulamadaki selam yazısının yüksekliği (720x1280'de)
SELAM_ALAN = 68 + SELAM_H - 50


def bos_yer(yukseklik):
    """Yazı ve selam bloğu için görüntünün en sakin (en az ayrıntılı) dikey yeri; üst sınır bloğun başı."""
    for fn in os.listdir('/tmp'):
        if fn.startswith('by_'): os.remove('/tmp/' + fn)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', '/tmp/kaynak.mp4', '-vf',
                    f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=1/2', '-frames:v', '6',
                    '/tmp/by_%d.png'], check=True)
    satir = [0.0] * H
    kareler = [fn for fn in os.listdir('/tmp') if fn.startswith('by_')]
    for fn in kareler:
        e = Image.open('/tmp/' + fn).convert('L').filter(ImageFilter.FIND_EDGES).resize((90, H))
        px = e.load()
        for yy in range(H):
            satir[yy] += sum(px[x, yy] for x in range(90))
    ust_sinir, alt_sinir = 150, H - 170 - yukseklik          # üstte boşluk, altta logo
    en, en_y = None, int(H * 0.55 - yukseklik / 2)
    toplam = [0.0]
    for v in satir: toplam.append(toplam[-1] + v)
    for yy in range(ust_sinir, max(ust_sinir, alt_sinir) + 1, 10):
        yogun = (toplam[yy + yukseklik] - toplam[yy]) / yukseklik
        yogun *= 1 + 0.35 * abs((yy + yukseklik / 2) / H - 0.58)   # ortaya yakın yerler hafif tercih edilir
        if en is None or yogun < en: en, en_y = yogun, yy
    return en_y



def _ses_filtre(ses, sure):
    """Ses zinciri (girdi 4): tilavet ayetin Arapçası belirirken başlar; ezgi baştan, kısık. İkisi de sonda kısılır."""
    if not ses:
        return ''
    yol, bas, uz, tur = ses
    if tur == 'tilavet':
        ms = int(bas * 1000)
        return (f';[4]aresample=44100,adelay={ms}|{ms},afade=t=in:st={bas:.2f}:d=0.2,'
                f'afade=t=out:st={sure - 1.2:.2f}:d=1.2,apad,atrim=0:{sure:.2f}[a]')
    return (f';[4]aresample=44100,atrim=0:{sure:.2f},volume=0.55,afade=t=in:d=1.2,'
            f'afade=t=out:st={sure - 1.8:.2f}:d=1.8,apad,atrim=0:{sure:.2f}[a]')


SURELER = json.load(open(os.path.join(KOK, 'sureler.json')))   # [ad, ayet sayısı] (Hafs, Tanzil)
KARI = 'ar.mahermuaiqly'
# Sesli meal: Diyanet Vakfı meali (Islamic Network, tr.vakfi-audio). Metni (tr.vakfi, Tanzil) yalnız tam cümle ve
# kısa olan ayetlerde; videoda yazan meal okunanla aynı olsun diye bu videolarda yazı da Diyanet Vakfı mealidir.
VAKFI = json.load(open(os.path.join(KOK, 'vakfi.json')))


def _sure_ayet(kaynak):
    """"Bakara, 152" -> (2, 152); bulunamazsa None."""
    try:
        ad, no = [x.strip() for x in kaynak.split(',', 1)]
        s = next(i for i, x in enumerate(SURELER, 1) if x[0] == ad)
        a = int(no.split('-')[0])
        return (s, a) if 1 <= a <= SURELER[s - 1][1] else None
    except (StopIteration, ValueError):
        return None


def _sure_uzunlugu(yol):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', yol],
                                capture_output=True, text=True, check=True).stdout.strip())


def ses_sec(v):
    """Videonun sesi: ayette tilavet (Kur'an genelindeki ayet numarasıyla tek dosya), hadiste ezgi. Yoksa None."""
    if v.get('tur') == 'ayet':
        sa = _sure_ayet(v['kaynak'])
        if not sa:
            return None
        g = sum(x[1] for x in SURELER[:sa[0] - 1]) + sa[1]
        yol = f'/tmp/tilavet-{g}.mp3'
        if not os.path.exists(yol):
            url = f'https://cdn.islamic.network/quran/audio/128/{KARI}/{g}.mp3'
            open(yol, 'wb').write(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read())
        if v['kaynak'] in VAKFI and os.environ.get('SESLI_MEAL'):
            meal = f'/tmp/meal-{g}.mp3'
            if not os.path.exists(meal):
                url = f'https://cdn.islamic.network/quran/audio/192/tr.vakfi-audio/{g}.mp3'
                open(meal, 'wb').write(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read())
            ikisi = f'/tmp/tilavet-meal-{g}.m4a'   # tilavet, 0,8 sn ara, Türkçe meal
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', yol, '-i', meal, '-filter_complex',
                            '[0]aresample=44100,aformat=channel_layouts=stereo[a];[1]aresample=44100,aformat=channel_layouts=stereo,'
                            'adelay=800|800[b];[a][b]concat=n=2:v=0:a=1[o]', '-map', '[o]', '-c:a', 'aac', '-b:a', '128k', ikisi],
                           check=True)
            return (ikisi, 1.8, _sure_uzunlugu(ikisi), 'tilavet')
        return (yol, 1.8, _sure_uzunlugu(yol), 'tilavet')   # Arapça yazı tam belirince
    klasor = os.path.join(KOK, 'ses')
    parcalar = sorted(f for f in os.listdir(klasor) if f.endswith(('.mp3', '.m4a', '.ogg'))) if os.path.isdir(klasor) else []
    if not parcalar:
        return None
    yol = os.path.join(klasor, parcalar[sum(map(ord, v['id'])) % len(parcalar)])
    return (yol, 0.0, _sure_uzunlugu(yol), 'ezgi')

def katman(metin, kaynak, cikti, arapca='', hat=False, ses=None):
    """ses: (dosya, başlangıç sn, süre sn, tür 'tilavet'|'ezgi') ya da None (sessiz)."""
    d = ImageDraw.Draw(Image.new('RGBA', (W, H)))
    f = ImageFont.truetype(f'{KOK}/yazi/Lora-Medium.ttf', 44)
    fs = ImageFont.truetype(f'{KOK}/yazi/Lora-Bold.ttf', 26)
    fa = ImageFont.truetype(f'{KOK}/yazi/AmiriQuran-Regular.ttf', 46)
    tr = sar(d, '“' + metin.strip('“”"') + '”', f, W - 120)
    ar = sar(d, arapca, fa, W - 110, rtl=True) if arapca else []
    if len(ar) > 2 or hat: ar = []               # uzun Arapça ya da görüntüde hat varsa Arapça satır konmaz
    LH, ALH = 62, 96   # Amiri Quran harekeleri uzun: satır arası geniş
    blok = len(ar) * ALH + (34 if ar else 0) + len(tr) * LH + 50
    y = bos_yer(blok + SELAM_ALAN)
    yer = []                                     # (başlangıç sn, y, metin, font, renk, rtl, harf harf mi)
    t = 1.0
    for s in ar:
        yer.append((t, y, s, fa, ARAPCA, True, False)); y += ALH
    if ar: y += 34; t += 1.3
    for s in tr:
        yer.append((t, y, s, f, KREM, False, True)); y += LH; t += len(s) / HIZ
    yer.append((t + 0.3, y + 14, kaynak, fs, ALTIN, False, False))
    son = t + 0.3 + 0.9
    sure = max(SURE, son + 4.0)
    if ses and ses[3] == 'tilavet':
        sure = max(sure, ses[1] + ses[2] + 1.6)   # tilavet yarıda kesilmez: video gerektiği kadar uzar
    selam_y = y + 68                             # uygulama selam yazısını buraya çizer (ayetin hemen altı)
    ust, alt = yer[0][1] - 40, selam_y + SELAM_H + 30   # bant selam yazısını da kapsar

    # Karartma katmanı (alt degrade + yazı bandı): yazıyla birlikte yavaş yavaş belirir. Logo ayrı ve sabit.
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    g = Image.new('L', (1, H))
    for yy in range(H):
        g.putpixel((0, yy), int(min(1, max(0, (yy - H * 0.45) / (H * 0.55)) * 1.2) * 170))
    kar = Image.new('RGBA', (W, H), (0, 0, 0, 255)); kar.putalpha(g.resize((W, H))); ov.alpha_composite(kar)
    isik = parlaklik(ust, alt)
    koyu = int(60 + 130 * min(1, max(0, (isik - 60) / 110)))
    m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).rounded_rectangle((10, ust, W - 10, alt), 50, fill=koyu)
    bant = Image.new('RGBA', (W, H), (0, 0, 0, 255)); bant.putalpha(m.filter(ImageFilter.GaussianBlur(50)))
    ov.alpha_composite(bant)
    ov.save('/tmp/bant.png')
    logo = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    lg = Image.open(f'{KOK}/logo.webp').convert('RGBA'); lg.thumbnail((132, 132))   # %20 büyük
    logo.alpha_composite(lg, (W - lg.width - 30, H - 40 - lg.height))
    logo.save('/tmp/kar.png')
    bant_bas = max(0.0, yer[0][0] - 0.4); bant_sure = max(1.2, son - 0.6 - bant_bas)

    # Yazı: her satır 0,9 sn'de yumuşakça ve 14 piksel yukarı kayarak belirir
    os.makedirs('/tmp/yz', exist_ok=True)
    for fn in os.listdir('/tmp/yz'): os.remove('/tmp/yz/' + fn)
    for n in range(int((son + 0.5) * FPS_YAZI) + 1):
        zaman = n / FPS_YAZI
        tl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(tl)
        for bas, yy, s, font, renk, rtl, harf in yer:
            if harf:   # daktilo: harfler sırayla, her biri çok kısa bir geçişle
                if zaman < bas: continue
                x0 = (W - dd.textlength(s, font=font)) / 2
                k = (zaman - bas) * HIZ
                tam = min(len(s), int(k))
                if tam:
                    dd.text((x0, yy), s[:tam], font=font, fill=renk + (255,), stroke_width=1, stroke_fill=KOYU + (255,))
                if tam < len(s):
                    al = int(255 * (k - tam))
                    if al:
                        dd.text((x0 + dd.textlength(s[:tam], font=font), yy), s[tam], font=font, fill=renk + (al,),
                                stroke_width=1, stroke_fill=KOYU + (al,))
                continue
            a = min(1, max(0, (zaman - bas) / 0.9))
            if a <= 0: continue
            e = 1 - (1 - a) ** 3                 # yumuşak yavaşlama
            al = int(255 * e); kay = int(14 * (1 - e))
            x = (W - dd.textlength(s, font=font, direction='rtl' if rtl else None)) / 2
            yon = 'rtl' if rtl else None
            # İnce koyu kenar; okunurluğu asıl alttaki yumuşak gölge sağlar
            dd.text((x, yy + kay), s, font=font, fill=renk + (al,), direction=yon, stroke_width=1, stroke_fill=KOYU + (al,))
        golge = Image.new('RGBA', (W, H), (0, 0, 0, 255))
        golge.putalpha(tl.split()[3].filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * .8)))
        yazi = Image.new('RGBA', (W, H), (0, 0, 0, 0)); yazi.alpha_composite(golge, (0, 3)); yazi.alpha_composite(tl)
        yazi.save(f'/tmp/yz/{n:04d}.png')

    z = f'(1+{ZOOM}*t/{sure:.2f})'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-stream_loop', '-1', '-i', '/tmp/kaynak.mp4',
        '-loop', '1', '-i', '/tmp/kar.png', '-framerate', str(FPS_YAZI), '-i', '/tmp/yz/%04d.png',
        '-loop', '1', '-i', '/tmp/bant.png', *(['-i', ses[0]] if ses else []), '-filter_complex',
        f'[0]scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},fps=30,'
        f"scale=w='2*trunc({W*2}*{z}/2)':h='2*trunc({H*2}*{z}/2)':eval=frame,crop={W*2}:{H*2},"
        f'scale={W}:{H}:flags=lanczos,{RENK},format=yuv420p[bg];'
        f'[3]format=rgba,fade=in:st={bant_bas:.2f}:d={bant_sure:.2f}:alpha=1[bt];[bg][bt]overlay=shortest=1[b0];'
        '[b0][1]overlay[b1];[2]format=rgba[t];[b1][t]overlay=eof_action=repeat,'
        f'fade=in:st=0:d=1,fade=out:st={sure-1:.2f}:d=1,format=yuv420p[v]' + _ses_filtre(ses, sure),
        '-map', '[v]', *(['-map', '[a]', '-c:a', 'aac', '-b:a', '96k'] if ses else ['-an']), '-t', f'{sure:.2f}', '-c:v', 'libx264', '-preset', 'slow', '-crf', '24', '-maxrate', '1400k', '-bufsize', '2800k',
        '-movflags', '+faststart', cikti + '.mp4'], check=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', f'{son + 1:.2f}', '-i', cikti + '.mp4',
        '-frames:v', '1', '-vf', 'scale=360:-2', '-q:v', '4', cikti + '.jpg'], check=True)
    katman.selam_t = round(son + 0.4, 2)          # selam yazısı yazı bitince görünür (sn)
    return round(selam_y / H, 4)


def kisa_metin(v, metinler, kullanilan):
    """Videonun metni uzunsa kullanılmamış kısa bir metinle değiştirilir (aynı tür önce)."""
    if len(v['metin']) <= MAKS_METIN:
        return next((m for m in metinler if m['kaynak'] == v['kaynak']), {'metin': v['metin'], 'kaynak': v['kaynak'], 'tur': v['tur'], 'arapca': ''})
    aday = [m for m in metinler if len(m['metin']) <= MAKS_METIN and m['kaynak'] not in kullanilan and m['kaynak'] not in HARIC]
    aday.sort(key=lambda m: m['tur'] != v['tur'])
    return aday[0]


if __name__ == '__main__':
    mod = sys.argv[1]
    onayli = json.load(open('videolar.json'))
    metinler = json.load(open(f'{KOK}/metinler.json'))
    random.seed(7); random.shuffle(metinler)
    kullanilan = {v['kaynak'] for v in onayli if len(v['metin']) <= MAKS_METIN}
    if mod == 'ornek':
        ids = sys.argv[2].replace(' ', '').split(',')
        os.makedirs('taslak', exist_ok=True)
        liste = []
        for n, i in enumerate(ids, 1):
            v = next(x for x in onayli if x['id'] == i)
            m = kisa_metin(v, metinler, kullanilan); kullanilan.add(m['kaynak'])
            ses = ses_sec({'id': v['id'], **m}); indir(v); sy = katman(m['metin'], m['kaynak'], f'taslak/{n:02d}', m.get('arapca', ''), ses=ses)
            liste.append({'no': n, 'id': i, 'selam_y': sy, 'selam_t': katman.selam_t, **m}); print(n, i, m['kaynak'], sy)
        json.dump(liste, open('taslak/liste.json', 'w'), ensure_ascii=False, indent=1)
    elif mod == 'eslestir':
        # Konu eşleşmesi: her videonun konusu (Pexels: elle, Pixabay: etiket), metinler konuya göre yeniden dağıtılır
        import konu
        tum = json.load(open(f'{KOK}/metinler.json'))
        kisa = [m for m in tum if len(m['metin']) <= MAKS_METIN and m['kaynak'] not in HARIC]
        for v in onayli:
            k = str(v['pixabay'])
            if k.startswith('pexels-'):
                v['konu'] = konu.PEXELS.get(k.removeprefix('pexels-'), v.get('konu', 'cami_dis'))
            else:
                u = 'https://pixabay.com/api/videos/?' + urllib.parse.urlencode({'key': os.environ['PIXABAY_API_KEY'], 'id': k})
                try:
                    h = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))['hits'][0]
                    v['konu'] = konu.medya_konu(h.get('tags', ''))
                except Exception as e:
                    print('etiket yok', k, e); v['konu'] = v.get('konu', 'doga')
        for v, m in konu.dagit(onayli, kisa):
            try:
                ses = ses_sec({'id': v['id'], **m}); indir(v); sy = katman(m['metin'], m['kaynak'], v['video'][:-4], m.get('arapca', ''), hat=v['konu'] == 'hat', ses=ses)
            except Exception as e:
                print('yenilenemedi', v['id'], e); continue
            v.update(metin=m['metin'], kaynak=m['kaynak'], tur=m['tur'], selam_y=sy, selam_t=katman.selam_t, ses=(ses[3] if ses else ''))
            print('eşleşti', v['id'], v['konu'], m['kaynak'])
            json.dump(onayli, open('videolar.json', 'w'), ensure_ascii=False, indent=1)
        onayli.sort(key=lambda x: konu.SIRA.get(x.get('konu'), 9))
        json.dump(onayli, open('videolar.json', 'w'), ensure_ascii=False, indent=1)
    elif mod == 'ses':
        arapca = {m['kaynak']: m.get('arapca', '') for m in metinler}
        for v in onayli:
            try:
                ses = ses_sec(v)
                indir(v)
                sy = katman(v['metin'], v['kaynak'], v['video'][:-4], arapca.get(v['kaynak'], ''),
                            hat=v.get('konu') == 'hat', ses=ses)
            except Exception as e:
                print('yenilenemedi', v['id'], e); continue
            v.update(selam_y=sy, selam_t=katman.selam_t, ses=(ses[3] if ses else ''),
                     ses_dosya=(os.path.basename(ses[0]) if ses and ses[3] == 'ezgi' else ''))
            print('sesli', v['id'], v['kaynak'], v['ses'])
            json.dump(onayli, open('videolar.json', 'w'), ensure_ascii=False, indent=1)
    elif mod in ('meal', 'mealornek'):
        # Sesli meal: tilavetin ardından Türkçe meal okunur; videodaki meal yazısı okunanla aynı (Diyanet Vakfı)
        os.environ['SESLI_MEAL'] = '1'
        arapca = {m['kaynak']: m.get('arapca', '') for m in metinler}
        secili = sys.argv[2].replace(' ', '').split(',') if mod == 'mealornek' else None
        if secili: os.makedirs('taslak', exist_ok=True)
        for n, v in enumerate([x for x in onayli if not secili or x['id'] in secili], 1):
            try:
                metin = VAKFI.get(v['kaynak'], v['metin'])
                ses = ses_sec(v)
                indir(v)
                cikti = f'taslak/{n:02d}' if secili else v['video'][:-4]
                sy = katman(metin, v['kaynak'], cikti, arapca.get(v['kaynak'], ''), hat=v.get('konu') == 'hat', ses=ses)
            except Exception as e:
                print('yenilenemedi', v['id'], e); continue
            if secili: print(n, v['id'], v['kaynak'], metin); continue
            v.update(metin=metin, selam_y=sy, selam_t=katman.selam_t, ses='meal' if v['kaynak'] in VAKFI else 'tilavet',
                     meal='Diyanet Vakfı' if v['kaynak'] in VAKFI else '')
            print('sesli meal', v['id'], v['kaynak'], v['ses'])
            json.dump(onayli, open('videolar.json', 'w'), ensure_ascii=False, indent=1)
    elif mod == 'hepsi':
        for v in onayli:
            m = kisa_metin(v, metinler, kullanilan); kullanilan.add(m['kaynak'])
            try:
                ses = ses_sec({'id': v['id'], **m}); indir(v); sy = katman(m['metin'], m['kaynak'], v['video'][:-4], m.get('arapca', ''), ses=ses)
            except Exception as e:
                print('yenilenemedi', v['id'], e); continue
            v.update(metin=m['metin'], kaynak=m['kaynak'], tur=m['tur'], selam_y=sy, selam_t=katman.selam_t, ses=(ses[3] if ses else '')); print('yenilendi', v['id'], m['kaynak'])
        json.dump(onayli, open('videolar.json', 'w'), ensure_ascii=False, indent=1)
