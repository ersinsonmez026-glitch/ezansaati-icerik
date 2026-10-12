"""Profesyonel video düzeni: kısa metin (en çok 3 satır), satır satır yumuşak beliren yazı, sinematik renk tonu,
yavaş yakınlaşma, yazının arkasında parlaklığa göre koyulaşan bant, sabit 13 sn ve aynı açılış/kapanış.
Kullanım:
  python3 arac/pro.py ornek <video kimlikleri, virgülle>   -> taslak/NN.mp4 (önizleme, uygulamaya girmez)
  python3 arac/pro.py hepsi                                 -> onaylı videoları yerinde yeniden üretir"""
import json, os, random, subprocess, sys, urllib.parse, urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
from uret import UA, W, H, parlaklik

SURE, FPS_YAZI, ZOOM = 13.0, 15, 0.06
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
        hit = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))['hits'][0]['videos']
        url = (hit.get('large') or {}).get('url') or hit['medium']['url']
    open('/tmp/kaynak.mp4', 'wb').write(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300).read())


def sar(d, metin, font, genislik, rtl=False):
    satir, cur = [], []
    for w in metin.split():
        if cur and d.textlength(' '.join(cur + [w]), font=font, direction='rtl' if rtl else None) > genislik:
            satir.append(' '.join(cur)); cur = [w]
        else:
            cur.append(w)
    return satir + [' '.join(cur)]


def katman(metin, kaynak, cikti, arapca=''):
    d = ImageDraw.Draw(Image.new('RGBA', (W, H)))
    f = ImageFont.truetype(f'{KOK}/yazi/Lora-SemiBold.ttf', 44)
    fs = ImageFont.truetype(f'{KOK}/yazi/Lora-Bold.ttf', 26)
    fa = ImageFont.truetype(f'{KOK}/yazi/Amiri-Regular.ttf', 48)
    tr = sar(d, '“' + metin.strip('“”"') + '”', f, W - 120)
    ar = sar(d, arapca, fa, W - 110, rtl=True) if arapca else []
    if len(ar) > 2: ar = []                      # uzun Arapça videoyu kalabalıklaştırır
    LH, ALH = 62, 80
    blok = len(ar) * ALH + (24 if ar else 0) + len(tr) * LH + 50
    y = int(H * 0.60 - blok / 2)
    yer = []                                     # (başlangıç sn, y, metin, font, renk, rtl)
    t = 1.0
    for s in ar:
        yer.append((t, y, s, fa, ARAPCA, True)); y += ALH
    if ar: y += 24; t += 1.6
    for s in tr:
        yer.append((t, y, s, f, KREM, False)); y += LH; t += 0.75
    yer.append((t + 0.3, y + 14, kaynak, fs, ALTIN, False))
    son = t + 0.3 + 0.9
    sure = max(SURE, son + 4.0)
    ust, alt = yer[0][1] - 40, y + 70

    # Sabit katman: alt karartma, yazı bandı (parlaklığa göre), logo
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
    lg = Image.open(f'{KOK}/logo.webp').convert('RGBA'); lg.thumbnail((110, 110))
    ov.alpha_composite(lg, (W - lg.width - 34, H - 44 - lg.height))
    ov.save('/tmp/kar.png')

    # Yazı: her satır 0,9 sn'de yumuşakça ve 14 piksel yukarı kayarak belirir
    os.makedirs('/tmp/yz', exist_ok=True)
    for fn in os.listdir('/tmp/yz'): os.remove('/tmp/yz/' + fn)
    for n in range(int((son + 0.5) * FPS_YAZI) + 1):
        zaman = n / FPS_YAZI
        tl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(tl)
        for bas, yy, s, font, renk, rtl in yer:
            a = min(1, max(0, (zaman - bas) / 0.9))
            if a <= 0: continue
            e = 1 - (1 - a) ** 3                 # yumuşak yavaşlama
            al = int(255 * e); kay = int(14 * (1 - e))
            x = (W - dd.textlength(s, font=font, direction='rtl' if rtl else None)) / 2
            yon = 'rtl' if rtl else None
            if rtl:   # Amiri ince: koyu dış kontur, üstüne aynı renkle 1 px kalınlaştırma
                dd.text((x, yy + kay), s, font=font, fill=KOYU + (al,), direction=yon, stroke_width=3, stroke_fill=KOYU + (al,))
                dd.text((x, yy + kay), s, font=font, fill=renk + (al,), direction=yon, stroke_width=1, stroke_fill=renk + (al,))
            else:
                dd.text((x, yy + kay), s, font=font, fill=renk + (al,), direction=yon,
                        stroke_width=1 if font is fs else 2, stroke_fill=KOYU + (al,))
        golge = Image.new('RGBA', (W, H), (0, 0, 0, 255))
        golge.putalpha(tl.split()[3].filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * .8)))
        yazi = Image.new('RGBA', (W, H), (0, 0, 0, 0)); yazi.alpha_composite(golge, (0, 3)); yazi.alpha_composite(tl)
        yazi.save(f'/tmp/yz/{n:04d}.png')

    z = f'(1+{ZOOM}*t/{sure:.2f})'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-stream_loop', '-1', '-i', '/tmp/kaynak.mp4',
        '-loop', '1', '-i', '/tmp/kar.png', '-framerate', str(FPS_YAZI), '-i', '/tmp/yz/%04d.png', '-filter_complex',
        f'[0]scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},fps=30,'
        f"scale=w='2*trunc({W*2}*{z}/2)':h='2*trunc({H*2}*{z}/2)':eval=frame,crop={W*2}:{H*2},"
        f'scale={W}:{H}:flags=lanczos,{RENK},format=yuv420p[bg];'
        '[bg][1]overlay[b1];[2]format=rgba[t];[b1][t]overlay=eof_action=repeat,'
        f'fade=in:st=0:d=1,fade=out:st={sure-1:.2f}:d=1,format=yuv420p[v]',
        '-map', '[v]', '-an', '-t', f'{sure:.2f}', '-c:v', 'libx264', '-preset', 'slow', '-crf', '24',
        '-movflags', '+faststart', cikti + '.mp4'], check=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', f'{son + 1:.2f}', '-i', cikti + '.mp4',
        '-frames:v', '1', '-vf', 'scale=360:-2', '-q:v', '4', cikti + '.jpg'], check=True)


def kisa_metin(v, metinler, kullanilan):
    """Videonun metni uzunsa kullanılmamış kısa bir metinle değiştirilir (aynı tür önce)."""
    if len(v['metin']) <= MAKS_METIN:
        return next((m for m in metinler if m['kaynak'] == v['kaynak']), {'metin': v['metin'], 'kaynak': v['kaynak'], 'tur': v['tur'], 'arapca': ''})
    aday = [m for m in metinler if len(m['metin']) <= MAKS_METIN and m['kaynak'] not in kullanilan]
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
            indir(v); katman(m['metin'], m['kaynak'], f'taslak/{n:02d}', m.get('arapca', ''))
            liste.append({'no': n, 'id': i, **m}); print(n, i, m['kaynak'])
        json.dump(liste, open('taslak/liste.json', 'w'), ensure_ascii=False, indent=1)
    elif mod == 'hepsi':
        for v in onayli:
            m = kisa_metin(v, metinler, kullanilan); kullanilan.add(m['kaynak'])
            try:
                indir(v); katman(m['metin'], m['kaynak'], v['video'][:-4], m.get('arapca', ''))
            except Exception as e:
                print('yenilenemedi', v['id'], e); continue
            v.update(metin=m['metin'], kaynak=m['kaynak'], tur=m['tur']); print('yenilendi', v['id'], m['kaynak'])
        json.dump(onayli, open('videolar.json', 'w'), ensure_ascii=False, indent=1)
