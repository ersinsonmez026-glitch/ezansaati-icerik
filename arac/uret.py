"""Taslak mesaj videoları üretir: Pixabay'den sakin dini videolar bulur, üstüne kaynaklı ayet/hadis ve logo
ekler (sessiz, 720x1280, 15 sn). Çıktı: taslak/NN.mp4, taslak/NN.jpg ve taslak/liste.json.
Uygulamaya girmez; yalnız onaylananlar onay.py ile videolar/ klasörüne ve videolar.json'a eklenir."""
import json, os, random, subprocess, sys, urllib.error, urllib.parse, urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, SURE = 720, 1280, 15
KOK = os.path.dirname(os.path.abspath(__file__))
ARAMALAR = ['kaaba', 'mecca', 'medina', 'mosque', 'minaret', 'quran', 'islamic', 'prayer beads', 'mosque sunset']

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
            if v['id'] in kullanilan or v['duration'] < 8:
                continue
            boy = v['videos'].get('large') or v['videos'].get('medium')
            if not boy or not boy.get('url'):
                continue
            yield {'id': v['id'], 'url': boy['url'], 'dikey': boy['height'] > boy['width'],
                   'sayfa': v['pageURL'], 'arama': q, 'etiket': v.get('tags', '')}

def katman(metin, kaynak, cikti):
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    g = Image.new('L', (1, H))
    for y in range(H):
        t = max(0, (y - H * 0.35) / (H * 0.65))
        g.putpixel((0, y), int(min(1, t * 1.3) * 200))
    kar = Image.new('RGBA', (W, H), (0, 0, 0, 255)); kar.putalpha(g.resize((W, H)))
    ov.alpha_composite(kar)
    tl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(tl)
    metin = '“' + metin.strip('“”"') + '”'
    for boyut in (40, 36, 32, 29, 26):
        f = ImageFont.truetype(f'{KOK}/yazi/Lora-SemiBold.ttf', boyut)
        satir, cur = [], ''
        for w in metin.split():
            t = (cur + ' ' + w).strip()
            if d.textlength(t, font=f) > W - 110: satir.append(cur); cur = w
            else: cur = t
        satir.append(cur)
        lh = int(boyut * 1.4)
        if len(satir) * lh < 420: break
    fs = ImageFont.truetype(f'{KOK}/yazi/Lora-Bold.ttf', 27)
    y0 = H - 260 - len(satir) * lh - 50
    for i, s in enumerate(satir):
        d.text(((W - d.textlength(s, font=f)) / 2, y0 + i * lh), s, font=f, fill=(255, 250, 235, 255))
    d.text(((W - d.textlength(kaynak, font=fs)) / 2, y0 + len(satir) * lh + 16), kaynak, font=fs, fill=(232, 200, 138, 255))
    golge = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    golge.putalpha(tl.split()[3].filter(ImageFilter.GaussianBlur(4)).point(lambda v: int(v * .85)))
    yazi = Image.new('RGBA', (W, H), (0, 0, 0, 0)); yazi.alpha_composite(golge, (2, 3)); yazi.alpha_composite(tl)
    lg = Image.open(f'{KOK}/logo.webp').convert('RGBA'); lg.thumbnail((150, 150))
    logo = Image.new('RGBA', (W, H), (0, 0, 0, 0)); logo.alpha_composite(lg, ((W - lg.width) // 2, H - 60 - lg.height))
    ov.save('/tmp/kar.png'); yazi.save('/tmp/yazi.png'); logo.save('/tmp/logo.png')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', '/tmp/kaynak.mp4', '-loop', '1', '-i', '/tmp/kar.png',
        '-loop', '1', '-i', '/tmp/yazi.png', '-loop', '1', '-i', '/tmp/logo.png', '-filter_complex',
        f'[0]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,format=yuv420p[bg];'
        '[bg][1]overlay[b1];[2]format=rgba,fade=in:st=1:d=1.5:alpha=1[t];[b1][t]overlay[b2];'
        f'[3]format=rgba,fade=in:st=2.5:d=1:alpha=1[l];[b2][l]overlay,fade=in:st=0:d=0.8,fade=out:st={SURE-0.8}:d=0.8,format=yuv420p[v]',
        '-map', '[v]', '-an', '-t', str(SURE), '-c:v', 'libx264', '-preset', 'slow', '-crf', '27',
        '-movflags', '+faststart', cikti + '.mp4'], check=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', '6', '-i', cikti + '.mp4', '-frames:v', '1',
        '-vf', 'scale=360:-2', '-q:v', '4', cikti + '.jpg'], check=True)

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
