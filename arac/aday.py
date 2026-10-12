"""Video adayları bulur ve numaralı vitrin görselleri hazırlar; kullanıcı numara seçer, taslak.yml (kaynak=aday) üretir.
Kaynaklar: Pexels arama sayfası (anahtarsız) ve Pixabay API. Uygulamaya hiçbir şey girmez.
Kullanım: python3 arac/aday.py "arama 1, arama 2" [arama başına aday]"""
import io, json, os, re, sys, urllib.parse, urllib.request
from PIL import Image, ImageDraw, ImageFont

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
from uret import UA, YASAK

def ac(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={**UA, 'Accept-Language': 'en-US,en'}), timeout=60).read()

def pexels(q, n, kullanilan):
    try:
        html = ac(f'https://www.pexels.com/search/videos/{urllib.parse.quote(q)}/?orientation=portrait').decode('utf-8', 'ignore')
    except Exception as e:
        print('pexels arama açılmadı', q, e); return
    say = 0
    for i in dict.fromkeys(re.findall(r'/video/[a-z0-9-]*?-?(\d{6,})/', html)):
        if f'pexels-{i}' in kullanilan: continue
        m = re.search(rf'https://images\.pexels\.com/videos/{i}/[^"\'\s\\]+?\.jpe?g', html)
        kapak = m.group(0).split('?')[0] + '?auto=compress&w=360' if m else None
        if not kapak: continue
        kullanilan.add(f'pexels-{i}'); say += 1
        yield {'kaynak': 'pexels', 'id': f'pexels-{i}', 'url': f'https://www.pexels.com/download/video/{i}/',
               'sayfa': f'https://www.pexels.com/video/{i}/', 'kapak': kapak, 'arama': q}
        if say >= n: break

def pixabay(q, n, kullanilan):
    k = os.environ.get('PIXABAY_API_KEY')
    if not k: return
    u = 'https://pixabay.com/api/videos/?' + urllib.parse.urlencode({'key': k, 'q': q, 'safesearch': 'true', 'per_page': 50})
    say = 0
    for v in json.loads(ac(u)).get('hits', []):
        etiket = {t.strip().lower() for t in v.get('tags', '').split(',')}
        boy = v['videos'].get('large') or v['videos'].get('medium')
        if v['id'] in kullanilan or v['duration'] < 10 or etiket & YASAK or not boy or not boy.get('url'): continue
        kapak = boy.get('thumbnail') or v['videos'].get('medium', {}).get('thumbnail')
        if not kapak: continue
        kullanilan.add(v['id']); say += 1
        yield {'kaynak': 'pixabay', 'id': v['id'], 'url': boy['url'], 'sayfa': v['pageURL'], 'kapak': kapak, 'arama': q}
        if say >= n: break

if __name__ == '__main__':
    aramalar = [a.strip() for a in sys.argv[1].split(',') if a.strip()]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    onayli = json.load(open('videolar.json'))
    kullanilan = {v['pixabay'] for v in onayli}
    liste = []
    for q in aramalar:
        for fn in (pexels, pixabay):
            for a in fn(q, n, kullanilan):
                try:
                    im = Image.open(io.BytesIO(ac(a['kapak']))).convert('RGB')
                except Exception as e:
                    print('kapak yok', a['sayfa'], e); continue
                a['no'] = len(liste) + 1; a['_im'] = im; liste.append(a)
        print(q, 'toplam', len(liste))
    os.makedirs('aday', exist_ok=True)
    f = ImageFont.truetype(f'{KOK}/yazi/Lora-Bold.ttf', 30)
    tw, th, cols = 200, 300, 6
    for s in range(0, len(liste), 24):
        grup = liste[s:s + 24]
        rows = (len(grup) + cols - 1) // cols
        c = Image.new('RGB', (cols * (tw + 6), rows * (th + 6)), 'white')
        for k, a in enumerate(grup):
            im = a['_im']; r = max(tw / im.width, th / im.height)
            im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1))
            im = im.crop(((im.width - tw) // 2, (im.height - th) // 2, (im.width - tw) // 2 + tw, (im.height - th) // 2 + th))
            x, y = (k % cols) * (tw + 6), (k // cols) * (th + 6); c.paste(im, (x, y))
            d = ImageDraw.Draw(c); d.rectangle((x, y, x + 64, y + 40), fill=(180, 0, 0)); d.text((x + 6, y + 2), str(a['no']), font=f, fill='white')
        c.save(f'aday/vitrin{s // 24 + 1}.jpg', quality=82)
    for a in liste: a.pop('_im')
    json.dump(liste, open('aday/liste.json', 'w'), ensure_ascii=False, indent=1)
