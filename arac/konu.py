"""Konu eşleşmesi: her görüntünün ve her ayet/hadisin konusu; metin, konusuna uyan görüntüye verilir.
Görüntü konusu Pixabay etiketlerinden (ya da elle) bulunur; metin konusu metindeki kelimelerden."""
import re

# Görüntü konuları ve kütüphanedeki sırası (küçük önce): Kâbe ve camiler başta, sade görüntüler sonda
SIRA = {'kabe': 0, 'medine': 0, 'cami_ic': 1, 'namaz': 1, 'cami_dis': 2, 'hat': 2, 'kuran': 2,
        'gece': 3, 'fener': 3, 'gul': 3, 'mum': 4, 'doga': 4, 'cicek': 4, 'gazze': 5}

ETIKET = [  # (konu, etiketlerde aranan kelimeler) — ilk eşleşen
    ('kabe', ['kaaba', 'mecca', 'makkah', 'haram', 'hajj', 'umrah', 'tawaf', 'kabah']),
    ('medine', ['medina', 'madinah', 'nabawi', 'green dome', 'prophet']),
    ('namaz', ['praying', 'prayer rug', 'prayer mat', 'salah', 'sujood', 'prostrat', 'worship', 'dua']),
    ('hat', ['calligraphy', 'arabic', 'allah', 'muhammad', 'islamic art', 'pattern', 'ornament']),
    ('kuran', ['quran', 'koran', 'holy book', 'tasbih', 'rosary', 'beads', 'misbaha']),
    ('cami_ic', ['interior', 'inside', 'chandelier', 'dome interior', 'ceiling', 'mihrab', 'carpet']),
    ('cami_dis', ['mosque', 'minaret', 'masjid', 'dome', 'cami', 'istanbul', 'sultan', 'hagia']),
    ('fener', ['lantern', 'ramadan', 'ramazan', 'lamp', 'iftar', 'dates']),
    ('mum', ['candle', 'flame', 'fire']),
    ('gul', ['rose']),
    ('gece', ['moon', 'crescent', 'night', 'star', 'galaxy', 'milky']),
    ('cicek', ['flower', 'tulip', 'blossom', 'petal', 'bloom', 'lily']),
]


def medya_konu(etiketler):
    t = etiketler.lower()
    for k, kelimeler in ETIKET:
        if any(w in t for w in kelimeler):
            return k
    return 'doga'


METIN = [  # (konu, desen, uygun görüntü konuları)
    ('hac', r'kâbe|kabe|hac\b|hacc|umre|arefe|mescid-i haram', ['kabe']),
    ('peygamber', r'peygamber|resûl|resul|muhammed|nebi|salat ederler|sünnet', ['gul', 'medine', 'hat']),
    ('namaz', r'namaz|cemaat|mescit|mescid|secde|rükû|ruku|saf(lar)?ı|ezan|abdest|cuma', ['cami_ic', 'namaz', 'cami_dis']),
    ('kuran', r"kur[’']?an|kitab|ayet|zikr|zikir|tesbih|hamd|hamt|elhamdülillah", ['hat', 'kuran', 'cami_ic']),
    ('oruc', r'oruç|ramazan|iftar|sahur', ['fener', 'gece']),
    ('dua', r'dua|allah[’\']?ım|sığınırım|bağışla|tevbe|af\b|affet|mağfiret|tevekkül|sabr|sabır|vekil', ['gece', 'mum', 'kabe', 'namaz']),
    ('kudret', r'gökler|yer(?:de|i|in)\b|yeryüzü|yarat|gece ile gündüz|geceyi|kudret|mülk|her şeye gücü', ['doga', 'gece', 'cicek']),
    ('ahiret', r'cennet|ahiret|âhiret|kıyamet|hesap', ['doga', 'gece']),
    ('rahmet', r'rahmet|merhamet|rahim|rahîm|rahman', ['doga', 'cicek', 'gul']),
]


def metin_konu(metin):
    t = metin.lower()
    for k, desen, _ in METIN:
        if re.search(desen, t):
            return k
    return 'genel'


def uygun(metin_k, medya_k):
    for k, _, medya in METIN:
        if k == metin_k:
            return medya_k in medya
    return medya_k in ('doga', 'cicek', 'gece', 'cami_dis', 'mum', 'fener')   # genel ahlak metinleri


def dagit(medyalar, metinler, kullanilan=()):
    """Her görüntüye (konusuna göre) bir metin verir; her metin bir kez. medyalar: [{'konu':...}]"""
    kalan = [m for m in metinler if m['kaynak'] not in kullanilan]
    for m in kalan:
        m['_k'] = metin_konu(m['metin'])
    sonuc = []
    # önce özel konulu görüntüler (Kâbe, cami içi, hat…), en son doğa: uygun metni ilk onlar alsın
    for med in sorted(medyalar, key=lambda x: SIRA.get(x['konu'], 9)):
        sec = next((m for m in kalan if uygun(m['_k'], med['konu']) and m['_k'] != 'genel'), None) \
            or next((m for m in kalan if uygun(m['_k'], med['konu'])), None) \
            or (kalan[0] if kalan else None)
        if sec is None:
            break
        kalan.remove(sec)
        sonuc.append((med, sec))
    return sonuc


# Pexels görüntülerinin etiketi yok; gözle verilen konular
PEXELS = {
    '36443276': 'cami_ic', '36885067': 'cami_ic', '34637327': 'cami_ic', '29693438': 'cami_dis', '34127022': 'cami_dis',
    '27467293': 'cami_dis', '34005010': 'cami_dis', '34005008': 'cami_dis', '34005039': 'cami_dis',
    '35170561': 'kabe', '35170552': 'kabe', '35155718': 'kabe', '35282058': 'kabe', '34872085': 'kabe',
    '35349323': 'kabe', '35155731': 'kabe', '35189255': 'kabe', '39902982': 'cami_dis', '28217912': 'cami_dis',
    '34753278': 'cami_dis', '31135693': 'cami_dis', '31802396': 'cami_dis', '34017709': 'cami_dis', '32110800': 'cami_dis',
}
