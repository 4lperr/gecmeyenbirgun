from PIL import Image, ImageDraw, ImageFont, ImageFilter
import json
import os
import math
import random

# ==== AYARLAR ====
GENISLIK = 680
YUKSEKLIK = 680
YAZI_RENGI = (250, 250, 250)
IMZA_RENGI = (150, 150, 150)
CIZGI_RENGI = (130, 130, 130)
KUS_RENGI = (210, 210, 210)
NOKTA_RENGI = (170, 170, 170)
FONT_BOYUT = 54
SATIR_ARASI = 1.55
YAZI_DIKEY_KONUM = 0.42
YAZI_MARGIN_ORAN = 0.12
LOGO_BOYUT = 50
IMZA = "@gecmeyenbirgun"

FONT_YOLU = "font.ttf"
LOGO_YOLU = "logo.png"
JSON_YOLU = "yazilar.json"
CIKTI_KLASORU = "cikti"


# ==== ARKA PLAN ====
def arka_plan_olustur():
    img = Image.new("RGB", (GENISLIK, YUKSEKLIK), (5, 5, 5))
    pixels = img.load()
    cx, cy = GENISLIK // 2, int(YUKSEKLIK * 0.42)
    max_dist = math.sqrt(cx**2 + cy**2)
    for y in range(YUKSEKLIK):
        for x in range(GENISLIK):
            dist = math.sqrt((x - cx)**2 + (y - cy)**2)
            oran = min(dist / max_dist, 1.0)
            v = int(30 * (1 - oran) + 5 * oran)
            if v < 5:
                v = 5
            pixels[x, y] = (v, v, v)

    vignette = Image.new("L", (GENISLIK, YUKSEKLIK), 0)
    vp = vignette.load()
    for y in range(YUKSEKLIK):
        for x in range(GENISLIK):
            dx = (x - GENISLIK / 2) / (GENISLIK / 2)
            dy = (y - YUKSEKLIK / 2) / (YUKSEKLIK / 2)
            d = math.sqrt(dx**2 + dy**2)
            if d > 0.75:
                vp[x, y] = int(min(255, (d - 0.75) * 400))
    black = Image.new("RGB", (GENISLIK, YUKSEKLIK), (0, 0, 0))
    img = Image.composite(black, img, vignette)

    grain = Image.new("RGB", (GENISLIK, YUKSEKLIK), (0, 0, 0))
    gp = grain.load()
    for _ in range(25000):
        gx = random.randint(0, GENISLIK - 1)
        gy = random.randint(0, YUKSEKLIK - 1)
        v = random.randint(0, 40)
        gp[gx, gy] = (v, v, v)
    img = Image.blend(img, grain, 0.05)
    return img


# ==== ELLE ÇİZİLMİŞ İTALİK ÇİZGİ ====
def el_cizgisi(draw, x1, x2, y_base, egim=4, genlik=1.8, dalga=2.5, renk=CIZGI_RENGI):
    """Hafif italik + hafif dalgalı, elle çizilmiş hissi veren çizgi"""
    n = int(x2 - x1)
    noktalar = []
    for i in range(n + 1):
        x = x1 + i
        t = i / n
        y_egim = y_base - t * egim                         # italik eğim
        y_dalga = math.sin(t * dalga * math.pi * 2) * genlik  # ana dalga
        y_dalga += math.sin(t * 7 * math.pi) * 0.7         # organik bozulma
        noktalar.append((x, y_egim + y_dalga))
    draw.line(noktalar, fill=renk, width=1)
    return noktalar[-1]


# ==== MİNİK KUŞ (sağa bakan, çizgiye oturmuş) ====
def kus_ciz(draw, x, y, boyut=9, renk=KUS_RENGI):
    s = boyut
    # Kuyruk (sola, hafif aşağı)
    draw.polygon([
        (x - s*0.4, y - s*0.15),
        (x - s*1.25, y - s*0.35),
        (x - s*1.05, y + s*0.15),
    ], fill=renk)
    # Gövde (hafif oval)
    draw.ellipse([x - s*0.55, y - s*0.7, x + s*0.45, y + s*0.15], fill=renk)
    # Kafa
    draw.ellipse([x + s*0.1, y - s*1.15, x + s*0.75, y - s*0.5], fill=renk)
    # Gaga
    draw.polygon([
        (x + s*0.7, y - s*0.95),
        (x + s*1.05, y - s*0.85),
        (x + s*0.7, y - s*0.7),
    ], fill=renk)


# ==== KUŞUN ETRAFINDA DÜŞÜNCE NOKTALARI ====
def noktalar(draw, x, y, adet=4, min_r=10, max_r=26, renk=NOKTA_RENGI):
    for _ in range(adet):
        aci = random.uniform(-math.pi, 0)  # üst yarım daire
        mesafe = random.uniform(min_r, max_r)
        nx = x + math.cos(aci) * mesafe
        ny = y + math.sin(aci) * mesafe
        r = random.uniform(0.8, 1.5)
        draw.ellipse([nx - r, ny - r, nx + r, ny + r], fill=renk)


# ==== GLOW ====
def glow_efekti(img, satirlar, font):
    glow = Image.new("RGB", (GENISLIK, YUKSEKLIK), (0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    satir_yukseklikleri = []
    for satir in satirlar:
        bbox = gdraw.textbbox((0, 0), satir, font=font)
        satir_yukseklikleri.append(bbox[3] - bbox[1])
    toplam = sum(satir_yukseklikleri) + int(FONT_BOYUT * (SATIR_ARASI - 1) * (len(satirlar) - 1))
    baslangic_y = int(YUKSEKLIK * YAZI_DIKEY_KONUM - toplam / 2)
    y = baslangic_y
    for i, satir in enumerate(satirlar):
        bbox = gdraw.textbbox((0, 0), satir, font=font)
        gen = bbox[2] - bbox[0]
        x = (GENISLIK - gen) // 2
        gdraw.text((x, y), satir, font=font, fill=(180, 180, 180))
        y += satir_yukseklikleri[i] + int(FONT_BOYUT * (SATIR_ARASI - 1))
    glow = glow.filter(ImageFilter.GaussianBlur(18))
    img = Image.blend(img, glow, 0.35)
    return img


# ==== YÜKLE ====
with open(JSON_YOLU, "r", encoding="utf-8") as f:
    yazilar = json.load(f)

os.makedirs(CIKTI_KLASORU, exist_ok=True)

logo = None
if os.path.exists(LOGO_YOLU):
    logo = Image.open(LOGO_YOLU).convert("RGBA")
    logo = logo.resize((LOGO_BOYUT, LOGO_BOYUT), Image.LANCZOS)

font_yazi = ImageFont.truetype(FONT_YOLU, FONT_BOYUT)
font_imza = ImageFont.truetype(FONT_YOLU, 18)

MAX_GENISLIK = int(GENISLIK * (1 - 2 * YAZI_MARGIN_ORAN))


# ==== HER YAZI İÇİN ====
for yazi in yazilar:
    img = arka_plan_olustur()
    satirlar = yazi["metin"].split("\n")

    # Otomatik satır kaydırma
    yeni_satirlar = []
    for satir in satirlar:
        kelimeler = satir.split(" ")
        gecici = ""
        for k in kelimeler:
            test = (gecici + " " + k).strip()
            bbox = ImageDraw.Draw(img).textbbox((0, 0), test, font=font_yazi)
            if bbox[2] - bbox[0] <= MAX_GENISLIK:
                gecici = test
            else:
                if gecici:
                    yeni_satirlar.append(gecici)
                gecici = k
        if gecici:
            yeni_satirlar.append(gecici)
    satirlar = yeni_satirlar

    # Glow
    img = glow_efekti(img, satirlar, font_yazi)

    draw = ImageDraw.Draw(img)

    # ============ ÜST: ELLE ÇİZİLMİŞ ÇİZGİ + KUŞ ============
    ust_y = 85
    ust_x1 = int(GENISLIK * 0.26)
    ust_x2 = int(GENISLIK * 0.60)
    random.seed(yazi["id"])  # her yazıda tutarlı rastgelelik
    son = el_cizgisi(draw, ust_x1, ust_x2, ust_y, egim=5, genlik=1.8, dalga=2.2)
    # Kuş çizginin sağ ucuna oturuyor
    kus_ciz(draw, son[0] + 4, son[1] + 1, boyut=9)
    # Kuşun üstüne doğru "düşünce" noktaları
    noktalar(draw, son[0] + 4, son[1] - 6, adet=4, min_r=12, max_r=26)

    # ============ ANA YAZI ============
    satir_yukseklikleri = []
    for satir in satirlar:
        bbox = draw.textbbox((0, 0), satir, font=font_yazi)
        satir_yukseklikleri.append(bbox[3] - bbox[1])
    toplam = sum(satir_yukseklikleri) + int(FONT_BOYUT * (SATIR_ARASI - 1) * (len(satirlar) - 1))
    baslangic_y = int(YUKSEKLIK * YAZI_DIKEY_KONUM - toplam / 2)
    y = baslangic_y
    for i, satir in enumerate(satirlar):
        bbox = draw.textbbox((0, 0), satir, font=font_yazi)
        gen = bbox[2] - bbox[0]
        x = (GENISLIK - gen) // 2
        draw.text((x, y), satir, font=font_yazi, fill=YAZI_RENGI)
        y += satir_yukseklikleri[i] + int(FONT_BOYUT * (SATIR_ARASI - 1))

    # ============ ALT: İNCE ÇİZGİ + ORTADA NOKTA ============
    alt_y = YUKSEKLIK - 100
    draw.line([(GENISLIK * 0.36, alt_y), (GENISLIK * 0.64, alt_y)], fill=CIZGI_RENGI, width=1)
    draw.ellipse([GENISLIK * 0.5 - 1.3, alt_y - 1.3, GENISLIK * 0.5 + 1.3, alt_y + 1.3], fill=CIZGI_RENGI)

    # ============ LOGO sağ alt ============
    if logo:
        logo_x = GENISLIK - LOGO_BOYUT - 40
        logo_y = YUKSEKLIK - LOGO_BOYUT - 40
        img.paste(logo, (logo_x, logo_y), logo)

    # ============ İMZA sol alt ============
    draw.text((45, YUKSEKLIK - 50), IMZA, font=font_imza, fill=IMZA_RENGI)

    dosya = f"{CIKTI_KLASORU}/post_{yazi['id']:02d}.png"
    img.save(dosya, "PNG")
    print(f"✓ {dosya}")

print(f"\nToplam {len(yazilar)} görsel üretildi.")