from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import json
import os
import math
import random
import datetime
import asyncio

from ayarlar import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

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
ARSIV_KLASORU = "arsiv"

# Bekleyen görsel: {mesaj_id: yazi_id}
BEKLEYEN = {}


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


def el_cizgisi(draw, x1, x2, y_base, egim=4, genlik=1.8, dalga=2.5, renk=CIZGI_RENGI):
    n = int(x2 - x1)
    noktalar = []
    for i in range(n + 1):
        x = x1 + i
        t = i / n
        y_egim = y_base - t * egim
        y_dalga = math.sin(t * dalga * math.pi * 2) * genlik
        y_dalga += math.sin(t * 7 * math.pi) * 0.7
        noktalar.append((x, y_egim + y_dalga))
    draw.line(noktalar, fill=renk, width=1)
    return noktalar[-1]


def kus_ciz(draw, x, y, boyut=9, renk=KUS_RENGI):
    s = boyut
    draw.polygon([
        (x - s*0.4, y - s*0.15),
        (x - s*1.25, y - s*0.35),
        (x - s*1.05, y + s*0.15),
    ], fill=renk)
    draw.ellipse([x - s*0.55, y - s*0.7, x + s*0.45, y + s*0.15], fill=renk)
    draw.ellipse([x + s*0.1, y - s*1.15, x + s*0.75, y - s*0.5], fill=renk)
    draw.polygon([
        (x + s*0.7, y - s*0.95),
        (x + s*1.05, y - s*0.85),
        (x + s*0.7, y - s*0.7),
    ], fill=renk)


def noktalar(draw, x, y, adet=4, min_r=10, max_r=26, renk=NOKTA_RENGI):
    for _ in range(adet):
        aci = random.uniform(-math.pi, 0)
        mesafe = random.uniform(min_r, max_r)
        nx = x + math.cos(aci) * mesafe
        ny = y + math.sin(aci) * mesafe
        r = random.uniform(0.8, 1.5)
        draw.ellipse([nx - r, ny - r, nx + r, ny + r], fill=renk)


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


def gorsel_uret(yazi, cikti_yolu):
    logo = None
    if os.path.exists(LOGO_YOLU):
        logo = Image.open(LOGO_YOLU).convert("RGBA")
        logo = logo.resize((LOGO_BOYUT, LOGO_BOYUT), Image.LANCZOS)

    font_yazi = ImageFont.truetype(FONT_YOLU, FONT_BOYUT)
    font_imza = ImageFont.truetype(FONT_YOLU, 18)
    max_genislik = int(GENISLIK * (1 - 2 * YAZI_MARGIN_ORAN))

    img = arka_plan_olustur()
    satirlar = yazi["metin"].split("\n")

    yeni_satirlar = []
    for satir in satirlar:
        kelimeler = satir.split(" ")
        gecici = ""
        for k in kelimeler:
            test = (gecici + " " + k).strip()
            bbox = ImageDraw.Draw(img).textbbox((0, 0), test, font=font_yazi)
            if bbox[2] - bbox[0] <= max_genislik:
                gecici = test
            else:
                if gecici:
                    yeni_satirlar.append(gecici)
                gecici = k
        if gecici:
            yeni_satirlar.append(gecici)
    satirlar = yeni_satirlar

    img = glow_efekti(img, satirlar, font_yazi)
    draw = ImageDraw.Draw(img)

    ust_y = 85
    ust_x1 = int(GENISLIK * 0.26)
    ust_x2 = int(GENISLIK * 0.60)
    random.seed(yazi["id"])
    son = el_cizgisi(draw, ust_x1, ust_x2, ust_y, egim=5, genlik=1.8, dalga=2.2)
    kus_ciz(draw, son[0] + 4, son[1] + 1, boyut=9)
    noktalar(draw, son[0] + 4, son[1] - 6, adet=4, min_r=12, max_r=26)

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

    alt_y = YUKSEKLIK - 100
    draw.line([(GENISLIK * 0.36, alt_y), (GENISLIK * 0.64, alt_y)], fill=CIZGI_RENGI, width=1)
    draw.ellipse([GENISLIK * 0.5 - 1.3, alt_y - 1.3, GENISLIK * 0.5 + 1.3, alt_y + 1.3], fill=CIZGI_RENGI)

    if logo:
        logo_x = GENISLIK - LOGO_BOYUT - 40
        logo_y = YUKSEKLIK - LOGO_BOYUT - 40
        img.paste(logo, (logo_x, logo_y), logo)

    draw.text((45, YUKSEKLIK - 50), IMZA, font=font_imza, fill=IMZA_RENGI)

    img.save(cikti_yolu, "PNG")


# ==== JSON OKU/YAZ ====
def yazilari_oku():
    with open(JSON_YOLU, "r", encoding="utf-8") as f:
        return json.load(f)


def yazilari_yaz(yazilar):
    with open(JSON_YOLU, "w", encoding="utf-8") as f:
        json.dump(yazilar, f, ensure_ascii=False, indent=2)


# ==== BOT KOMUTLARI ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Geçmeyen Bir Gün botu çalışıyor.\n\n"
        "/uret → 1 görsel üret ve gönder\n"
        "/bekleyen → şu an bekleyen görseller\n"
        "/durum → kaç yazı kaldı"
    )


async def durum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    yazilar = yazilari_oku()
    kalan = len([y for y in yazilar if not y.get("kullanildi", False)])
    kullanilan = len(yazilar) - kalan
    await update.message.reply_text(
        f"📊 Durum:\n"
        f"Toplam yazı: {len(yazilar)}\n"
        f"Kullanılan: {kullanilan}\n"
        f"Kalan: {kalan}"
    )


async def bekleyen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not BEKLEYEN:
        await update.message.reply_text("Bekleyen görsel yok.")
        return
    metin = "⏳ Bekleyen görseller:\n\n"
    for mesaj_id, yazi_id in BEKLEYEN.items():
        metin += f"• Yazı ID: {yazi_id}\n"
    await update.message.reply_text(metin)


async def uret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await tek_gorsel_uret_ve_gonder(context.application)


async def tek_gorsel_uret_ve_gonder(app):
    yazilar = yazilari_oku()
    kullanilmamis = [y for y in yazilar if not y.get("kullanildi", False)]

    if not kullanilmamis:
        await app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text="⚠️ Havuz boş. Yeni yazı ekleyin."
        )
        return

    yazi = random.choice(kullanilmamis)

    os.makedirs("gecici", exist_ok=True)
    gecici_yol = f"gecici/onizleme_{yazi['id']}.png"
    gorsel_uret(yazi, gecici_yol)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Beğendim", callback_data=f"ok_{yazi['id']}"),
            InlineKeyboardButton("❌ Atla", callback_data=f"skip_{yazi['id']}")
        ]
    ])

    with open(gecici_yol, "rb") as f:
        mesaj = await app.bot.send_photo(
            chat_id=TELEGRAM_CHAT_ID,
            photo=f,
            caption=f"📝 Yazı ID: {yazi['id']}\n\nBeğendin mi?",
            reply_markup=keyboard
        )

    BEKLEYEN[mesaj.message_id] = yazi["id"]


async def buton_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    mesaj_id = query.message.message_id

    if mesaj_id not in BEKLEYEN:
        await query.edit_message_caption("⚠️ Bu görsel artık beklemede değil.")
        return

    yazi_id = BEKLEYEN[mesaj_id]
    yazilar = yazilari_oku()
    yazi = next((y for y in yazilar if y["id"] == yazi_id), None)

    if not yazi:
        await query.edit_message_caption("⚠️ Yazı bulunamadı.")
        del BEKLEYEN[mesaj_id]
        return

    if data.startswith("ok_"):
        yazi["kullanildi"] = True
        yazilari_yaz(yazilar)

        bugun = datetime.datetime.now().strftime("%Y-%m-%d")
        klasor = os.path.join(ARSIV_KLASORU, bugun)
        os.makedirs(klasor, exist_ok=True)

        gecici = f"gecici/onizleme_{yazi_id}.png"
        arsiv = os.path.join(klasor, f"post_{yazi_id:03d}.png")
        if os.path.exists(gecici):
            os.replace(gecici, arsiv)

        kalan = len([y for y in yazilar if not y.get("kullanildi", False)])
        await query.edit_message_caption(
            f"✅ Kaydedildi.\nYazı ID: {yazi_id}\nArşivde: {arsiv}\nKalan yazı: {kalan}"
        )
    else:
        await query.edit_message_caption(
            f"❌ Atladın. Yazı ID: {yazi_id} havuzda kaldı."
        )

    del BEKLEYEN[mesaj_id]


# ==== ZAMANLAYICI (12, 15, 17, 20, 00) ====
async def zamanlayici(app):
    hedefler = [(12, 0), (15, 0), (17, 0), (20, 0), (0, 0)]
    gonderildi = set()

    while True:
        simdi = datetime.datetime.now()
        bugun = simdi.date()
        for saat, dakika in hedefler:
            anahtar = (bugun, saat, dakika)
            if simdi.hour == saat and simdi.minute == dakika and anahtar not in gonderildi:
                gonderildi.add(anahtar)
                try:
                    await tek_gorsel_uret_ve_gonder(app)
                except Exception as e:
                    print(f"Hata: {e}")
        await asyncio.sleep(30)


# ==== BAŞLAT ====
async def main_async():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("uret", uret))
    app.add_handler(CommandHandler("durum", durum))
    app.add_handler(CommandHandler("bekleyen", bekleyen))
    app.add_handler(CallbackQueryHandler(buton_handler))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    print("🤖 Bot çalışıyor. Durdurmak için Ctrl+C.")

    asyncio.create_task(zamanlayici(app))

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main_async())