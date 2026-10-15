"""Sesli meal hata ayıklama: üç ayette tilavet, meal ve birleşik ses süreleri."""
import json, os, subprocess, sys
sys.path.insert(0, 'arac')
os.environ['SESLI_MEAL'] = '1'
import pro
def uz(p):
    return subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_name,channels,sample_rate', '-of', 'compact', p], capture_output=True, text=True).stdout
out = []
for k in ['Hûd, 115', 'İhlâs, 1', 'Enbiyâ, 19']:
    r = pro.ses_sec({'tur': 'ayet', 'kaynak': k, 'id': 'x'})
    sa = pro._sure_ayet(k); g = sum(x[1] for x in pro.SURELER[:sa[0] - 1]) + sa[1]
    sil = subprocess.run(['ffmpeg', '-nostdin', '-i', r[0], '-af', 'silencedetect=n=-35dB:d=0.25', '-f', 'null', '-'], capture_output=True, text=True).stderr
    out.append({'k': k, 'g': g, 'r': list(r), 'tilavet': uz(f'/tmp/tilavet-{g}.mp3'), 'meal': uz(f'/tmp/meal-{g}.mp3'), 'ikisi': uz(r[0]),
                'sessiz': [l.split('] ')[-1] for l in sil.splitlines() if 'silence_' in l]})
json.dump(out, open('ses_detay.json', 'w'), ensure_ascii=False, indent=1)
