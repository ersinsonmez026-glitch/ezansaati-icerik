"""Onaylanan taslakları (ör. "1,3,5") videolar/ klasörüne taşır ve videolar.json'a ekler; gerisi atılır."""
import json, os, shutil, sys, time
secilen = {int(x) for x in sys.argv[1].replace(' ', '').split(',') if x}
liste = json.load(open('taslak/liste.json'))
onayli = json.load(open('videolar.json'))
for t in liste:
    if t['no'] not in secilen:
        continue
    vid = f"v{t['pixabay']}"
    shutil.copy(f"taslak/{t['no']:02d}.mp4", f'videolar/{vid}.mp4')
    shutil.copy(f"taslak/{t['no']:02d}.jpg", f'videolar/{vid}.jpg')
    onayli.insert(0, {'id': vid, 'video': f'videolar/{vid}.mp4', 'kapak': f'videolar/{vid}.jpg',
                      'tur': t['tur'], 'metin': t['metin'], 'kaynak': t['kaynak'],
                      'pixabay': t['pixabay'], 'lisans': t['sayfa'], 'eklendi': time.strftime('%Y-%m-%d')})
    print('onaylandı', vid, t['kaynak'])
json.dump(onayli, open('videolar.json', 'w'), ensure_ascii=False, indent=1)
