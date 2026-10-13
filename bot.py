import logging
import os
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

# Konfigurasi Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# 1. KONFIGURASI UTAMA
# ---------------------------------------------------------
TOKEN = "8943588149:AAHohrulaQgxX0iNmc5E7wMioSpTi2YkYek"
ADMIN_ID = 7090598735

# Katalog Produk (Dapat dikembangkan dengan mudah)
PRODUCTS = {
    "prod_1": {
        "name": "Paket VIP Bundle (Akses 4 Grup)",
        "price": "Rp 25.000",
        "link": (
            "1. Grup Archive: https://t.me/+sZ7BAvQu2aA3NzM1\n"
            "2. Grup Koleksi Ome tv: https://t.me/+HY7uowATHp45ZTA1\n"
            "3. Grup K0lpri Vc & Vc+: https://t.me/+bt6-NQTqu9RhN2M1\n"
            "4. Grup Koleksi Terupdate: https://t.me/+g_oaziW5aaM0OWM1"
        ),
        "qris_image": "qris.png",  # Pastikan file gambar qris.png ada di folder yang sama
    }
}

# Memori sesi pilihan produk pembeli
user_sessions = {}

bot = telebot.TeleBot(TOKEN)


# ---------------------------------------------------------
# 2. MENU UTAMA (/start, /produk, /bayar)
# ---------------------------------------------------------
@bot.message_handler(commands=["start", "produk", "bayar", "help"])
def show_catalog(message):
    chat_id = message.chat.id
    markup = InlineKeyboardMarkup()

    for prod_key, prod_info in PRODUCTS.items():
        btn_text = f"🛒 {prod_info['name']} — {prod_info['price']}"
        markup.add(
            InlineKeyboardButton(
                text=btn_text, callback_data=f"select_{prod_key}"
            )
        )

    text = (
        "👋 *Selamat datang di Bot Toko Otomatis!*\n\n"
        "Silakan pilih produk berkualitas yang ingin Anda beli di bawah ini:"
    )
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")


# ---------------------------------------------------------
# 3. MENANGANI PILIHAN PRODUK PEMBELI
# ---------------------------------------------------------
@bot.callback_query_handler(
    func=lambda call: call.data.startswith("select_")
)
def handle_product_selection(call):
    try:
        prod_key = call.data.split("select_")[1]
        user_id = call.from_user.id

        if prod_key not in PRODUCTS:
            bot.answer_callback_query(call.id, "Produk tidak ditemukan!")
            return

        user_sessions[user_id] = prod_key
        product = PRODUCTS[prod_key]

        text = (
            f"📦 *Produk Dipilih:* {product['name']}\n"
            f"💰 *Total Pembayaran:* `{product['price']}`\n\n"
            f"📌 *Cara Pembayaran:*\n"
            f"1. Silakan scan atau transfer ke QRIS di atas.\n"
            f"2. Setelah transfer berhasil, **kirimkan foto/screenshot bukti transfer** langsung ke chat ini.\n"
            f"3. Admin akan segera memverifikasi pesanan Anda."
        )

        if os.path.exists(product["qris_image"]):
            with open(product["qris_image"], "rb") as photo:
                bot.send_photo(
                    call.message.chat.id,
                    photo,
                    caption=text,
                    parse_mode="Markdown",
                )
        else:
            bot.send_message(
                call.message.chat.id,
                f"{text}\n\n⚠️ *Catatan:* File QRIS (`{product['qris_image']}`) belum diunggah ke server.",
                parse_mode="Markdown",
            )

        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"Error in selection: {e}")
        bot.answer_callback_query(
            call.id, "Terjadi kesalahan. Silakan coba lagi."
        )


# ---------------------------------------------------------
# 4. MENERIMA BUKTI PEMBAYARAN FOTO DARI PEMBELI
# ---------------------------------------------------------
@bot.message_handler(content_types=["photo"])
def handle_proof(message):
    try:
        user_id = message.from_user.id
        user_name = (
            message.from_user.first_name
            or message.from_user.username
            or "Buyer"
        )
        photo_id = message.photo[-1].file_id

        prod_key = user_sessions.get(user_id)
        if not prod_key or prod_key not in PRODUCTS:
            bot.reply_to(
                message,
                "⚠️ Anda belum memilih produk atau sesi telah kedaluwarsa.\n"
                "Silakan ketik /start untuk memilih produk terlebih dahulu.",
            )
            return

        product = PRODUCTS[prod_key]

        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton(
                "Setujui ✅", callback_data=f"app:{user_id}:{prod_key}"
            ),
            InlineKeyboardButton(
                "Tolak ❌", callback_data=f"rej:{user_id}:{prod_key}"
            ),
        )

        caption_admin = (
            f"📩 *BUKTI PEMBAYARAN BARU*\n\n"
            f"👤 Pembeli: {user_name} (`{user_id}`)\n"
            f"📦 Produk: {product['name']}\n"
            f"💰 Nominal: `{product['price']}`"
        )

        bot.send_photo(
            ADMIN_ID,
            photo_id,
            caption=caption_admin,
            reply_markup=markup,
            parse_mode="Markdown",
        )
        bot.reply_to(
            message,
            f"✅ Bukti transfer untuk *{product['name']}* berhasil dikirim! Mohon tunggu verifikasi Admin.",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Error handling proof: {e}")
        bot.reply_to(message, "Terjadi kesalahan saat mengirim bukti transfer.")


# ---------------------------------------------------------
# 5. VERIFIKASI ADMIN (APPROVE / REJECT)
# ---------------------------------------------------------
@bot.callback_query_handler(
    func=lambda call: call.data.startswith(("app:", "rej:"))
)
def callback_admin(call):
    try:
        action, user_id_str, prod_key = call.data.split(":")
        user_id = int(user_id_str)

        if prod_key not in PRODUCTS:
            bot.answer_callback_query(
                call.id, "Error: Data produk tidak ditemukan."
            )
            return

        product = PRODUCTS[prod_key]

        if action == "app":
            msg_text = (
                f"🎉 *PEMBAYARAN DISETUJUI!*\n\n"
                f"Terima kasih telah membeli *{product['name']}*.\n\n"
                f"🔗 *Tautan Akses Grup Anda:*\n{product['link']}"
            )
            bot.send_message(user_id, msg_text, parse_mode="Markdown")

            bot.edit_message_caption(
                caption=f"{call.message.caption}\n\n*Status:* DISETUJUI ✅",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="Markdown",
            )
            bot.answer_callback_query(
                call.id, "Pembayaran disetujui & link terkirim!"
            )

        elif action == "rej":
            msg_text = (
                f"❌ *PEMBAYARAN DITOLAK*\n\n"
                f"Mohon maaf, bukti transfer untuk *{product['name']}* tidak valid. "
                f"Silakan hubungi Admin jika ada kekeliruan."
            )
            bot.send_message(user_id, msg_text, parse_mode="Markdown")

            bot.edit_message_caption(
                caption=f"{call.message.caption}\n\n*Status:* DITOLAK ❌",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="Markdown",
            )
            bot.answer_callback_query(call.id, "Pembayaran ditolak.")
    except Exception as e:
        logger.error(f"Error admin callback: {e}")
        bot.answer_callback_query(call.id, "Terjadi kesalahan.")


# ---------------------------------------------------------
# 6. RUN BOT
# ---------------------------------------------------------
if __name__ == "__main__":
    logger.info("Bot Telegram siap dijalankan...")
    while True:
        try:
            bot.infinity_polling(
                timeout=60, long_polling_timeout=60, skip_pending=True
            )
        except Exception as e:
            logger.error(f"Polling error: {e}")
