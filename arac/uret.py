"""Taslak mesaj videoları üretir: Pixabay'den sakin dini videolar bulur, üstüne kaynaklı ayet/hadis ve logo
ekler (sessiz, 720x1280, 15 sn). Çıktı: taslak/NN.mp4, taslak/NN.jpg ve taslak/liste.json.
Uygulamaya girmez; yalnız onaylananlar onay.py ile videolar/ klasörüne ve videolar.json'a eklenir."""
import json, os, random, subprocess, sys, urllib.error, urllib.parse, urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, SURE = 720, 1280, 15
KOK = os.path.dirname(os.path.abspath(__file__))
ARAMALAR = ['kaaba', 'mecca', 'masjid al haram', 'medina mosque', 'mosque interior', 'mosque dome',
            'mosque chandelier', 'islamic calligraphy', 'arabic calligraphy', 'allah calligraphy', 'quran', 'mosque']
# Yakın çekim insan yüzü olan videolar alınmaz (etiketlere göre).
YASAK = {'woman', 'women', 'girl', 'man', 'men', 'boy', 'child', 'children', 'kid', 'portrait', 'face', 'model',
         'beauty', 'person', 'people', 'family', 'muslim woman', 'hijab', 'selfie', 'smile', 'couple', 'dance', 'music'}

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
        gorulen = set()
        for v in json_al(u).get('hits', []):
            if v['id'] in gorulen:
                continue
            gorulen.add(v['id'])
            etiket = {t.strip().lower() for t in v.get('tags', '').split(',')}
            if v['id'] in kullanilan or v['duration'] < 8 or etiket & YASAK:
                continue
            boy = v['videos'].get('large') or v['videos'].get('medium')
            if not boy or not boy.get('url'):
                continue
            yield {'id': v['id'], 'url': boy['url'], 'dikey': boy['height'] > boy['width'],
                   'sayfa': v['pageURL'], 'arama': q, 'etiket': v.get('tags', '')}

KELIME_SN = 0.38   # okuma hızı: kelime başına
BASLA = 1.0
FPS_YAZI = 10

def katman(metin, kaynak, cikti):
    """Zemin karartması ve logo sabit; yazı kelime kelime belirir (PNG dizisi, saniyede 10 kare)."""
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    g = Image.new('L', (1, H))
    for y in range(H):
        t = max(0, (y - H * 0.35) / (H * 0.65))
        g.putpixel((0, y), int(min(1, t * 1.3) * 200))
    kar = Image.new('RGBA', (W, H), (0, 0, 0, 255)); kar.putalpha(g.resize((W, H)))
    ov.alpha_composite(kar)
    lg = Image.open(f'{KOK}/logo.webp').convert('RGBA'); lg.thumbnail((120, 120))
    ov.alpha_composite(lg, (W - lg.width - 36, H - 46 - lg.height))   # logo sağ altta
    ov.save('/tmp/kar.png')

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
    # Her kelimenin yeri (satır ortalanmış)
    yerler = []
    for i, ks in enumerate(satir):
        x = (W - d.textlength(' '.join(ks), font=f)) / 2
        for k in ks:
            yerler.append((x, y0 + i * lh, k))
            x += d.textlength(k + ' ', font=f)
    kx = (W - d.textlength(kaynak, font=fs)) / 2; ky = y0 + len(satir) * lh + 16
    son = BASLA + len(yerler) * KELIME_SN
    sure = max(SURE, son + 4.5)
    os.makedirs('/tmp/yz', exist_ok=True)
    for fn in os.listdir('/tmp/yz'): os.remove('/tmp/yz/' + fn)
    kare_say = int((son + 1.2) * FPS_YAZI) + 1
    for n in range(kare_say):
        t = n / FPS_YAZI
        tl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(tl)
        for i, (x, y, k) in enumerate(yerler):
            a = (t - (BASLA + i * KELIME_SN)) / 0.35      # her kelime 0,35 sn'de belirir
            if a > 0:
                dd.text((x, y), k, font=f, fill=(255, 250, 235, int(255 * min(1, a))))
        a = (t - son - 0.2) / 0.6
        if a > 0:
            dd.text((kx, ky), kaynak, font=fs, fill=(232, 200, 138, int(255 * min(1, a))))
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

if __name__ == '__main__':
    adet = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    anahtar = os.environ['PIXABAY_API_KEY']
    onayli = json.load(open('videolar.json'))
    kullanilan = {v['pixabay'] for v in onayli}
    kullanilan_metin = {v['kaynak'] for v in onayli}
    metinler = [m for m in json.load(open(f'{KOK}/metinler.json')) if m['kaynak'] not in kullanilan_metin]
    random.shuffle(metinler)
    # Önce dikey videolar, aramalar karışık
    havuz = list(adaylar(anahtar, kullanilan))
    random.shuffle(havuz); havuz.sort(key=lambda v: not v['dikey'])
    os.makedirs('taslak', exist_ok=True)
    liste = []
    n = 0
    for v, m in zip(havuz, metinler):
        if n >= adet:
            break
        n += 1
        try:
            open('/tmp/kaynak.mp4', 'wb').write(ac(v['url']).read())
        except urllib.error.HTTPError as e:
            print('indirilemedi', v['sayfa'], e.code); n -= 1; continue
        ad = f'taslak/{n:02d}'
        katman(m['metin'], m['kaynak'], ad)
        liste.append({'no': n, 'pixabay': v['id'], 'sayfa': v['sayfa'], 'arama': v['arama'], 'dikey': v['dikey'], **m})
        print(n, v['sayfa'], m['kaynak'])
    json.dump(liste, open('taslak/liste.json', 'w'), ensure_ascii=False, indent=1)
