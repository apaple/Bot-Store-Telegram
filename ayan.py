import json  # Made With love by @govtrashit A.K.A RzkyO
import os  # DON'T CHANGE AUTHOR NAME!
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputFile, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, CallbackQuery
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, CallbackContext
)
from datetime import datetime

OWNER_ID = 5010807043
produk_file = "produk.json"
saldo_file = "saldo.json"
deposit_file = "pending_deposit.json"
riwayat_file = "riwayat.json"
statistik_file = "statistik.json"

# Context untuk menyimpan state user
user_context = {}

def load_json(file):
    if not os.path.exists(file):
        return {} if file.endswith(".json") else []
    with open(file, "r") as f:
        content = f.read().strip()
        if not content:
            return {} if file.endswith(".json") else []
        return json.loads(content)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

def update_statistik(uid, nominal):
    statistik = load_json(statistik_file)
    uid = str(uid)
    if uid not in statistik:
        statistik[uid] = {"jumlah": 0, "nominal": 0}
    statistik[uid]["jumlah"] += 1
    statistik[uid]["nominal"] += nominal
    save_json(statistik_file, statistik)

def add_riwayat(uid, tipe, keterangan, jumlah):
    riwayat = load_json(riwayat_file)
    if str(uid) not in riwayat:
        riwayat[str(uid)] = []
    riwayat[str(uid)].append({
        "tipe": tipe,
        "keterangan": keterangan,
        "jumlah": jumlah,
        "waktu": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    })
    save_json(riwayat_file, riwayat)
    if tipe == "BELI":
        update_statistik(uid, jumlah)

async def send_main_menu(context, chat_id, user):
    saldo = load_json(saldo_file)
    statistik = load_json(statistik_file)
    s = saldo.get(str(user.id), 0)
    jumlah = statistik.get(str(user.id), {}).get("jumlah", 0)
    total = statistik.get(str(user.id), {}).get("nominal", 0)

    text = (
        f"👋 Selamat datang di *YUKAISTORE*!\n\n"
        f"🧑 Nama: {user.full_name}\n"
        f"🆔 ID: {user.id}\n"
        f"💰 Total Saldo Kamu: Rp{s:,}\n"
        f"📦 Total Transaksi: {jumlah}\n"
        f"💸 Total Nominal Transaksi: Rp{total:,}"
    )

    keyboard = [
        [InlineKeyboardButton("📋 List Produk", callback_data="list_produk"),
         InlineKeyboardButton("🛒 Stock", callback_data="cek_stok")],
        [InlineKeyboardButton("💰 Deposit Saldo", callback_data="deposit")],
        [InlineKeyboardButton("📖 Informasi Bot", callback_data="info_bot")],
    ]
    if user.id == OWNER_ID:
        keyboard.append([InlineKeyboardButton("🛠 Admin Panel", callback_data="admin_panel")])

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def send_main_menu_safe(update, context):
    if update.message:
        await send_main_menu(context, update.effective_chat.id, update.effective_user)
    elif update.callback_query:
        await update.callback_query.message.delete()
        await send_main_menu(context, update.callback_query.from_user.id, update.callback_query.from_user)

async def handle_list_produk(update, context):  # HANDLE LIST PRODUK
    query = update.callback_query
    produk = load_json(produk_file)
    msg = "*LIST PRODUK*\n"
    keyboard = []
    row = []

    for i, (pid, item) in enumerate(produk.items(), start=1):
        msg += f"{pid} {item['nama']} - Rp{item.get('harga', 0):,}\n"
        if item["stok"] > 0:
            row.append(KeyboardButton(pid))
        else:
            row.append(KeyboardButton(f"{pid} SOLDOUT ❌"))
        if len(row) == 3:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    keyboard.append([KeyboardButton("🔙 Kembali")])

    reply_keyboard = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    await query.message.delete()
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text=msg + "\nSilahkan pilih Nomor produk yang ingin dibeli.",
        reply_markup=reply_keyboard,
        parse_mode="Markdown"
    )

async def handle_cek_stok(update, context):  # HANDLE CEK STOK
    query = update.callback_query
    produk = load_json(produk_file)
    now = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
    msg = f"*Informasi Stok*\n- {now}\n\n"
    keyboard = []
    row = []

    for pid, item in produk.items():
        msg += f"{pid}. {item['nama']} ➔ {item['stok']}x\n"
        if item["stok"] > 0:
            row.append(KeyboardButton(pid))
        else:
            row.append(KeyboardButton(f"{pid} SOLDOUT ❌"))
        if len(row) == 3:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    keyboard.append([KeyboardButton("🔙 Kembali")])

    reply_keyboard = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    await query.message.delete()
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text=msg,
        reply_markup=reply_keyboard,
        parse_mode="Markdown"
    )

async def handle_produk_detail(update, context):  # HANDLE PRODUK DETAIL
    query = update.callback_query
    data = query.data
    produk = load_json(produk_file)
    item = produk.get(data)

    if item["stok"] <= 0:
        await query.answer("Produk habis", show_alert=True)
        return

    harga = item["harga"]
    tipe = item["akun_list"][0]["tipe"] if item["akun_list"] else "-"
    stok = item["stok"]

    context.user_data["konfirmasi"] = {
        "produk_id": data,
        "jumlah": 1
    }

    text = (
        "KONFIRMASI PESANAN 🛒\n"
        "╭ - - - - - - - - - - - - - - - - - - - - - ╮\n"
        f"┊・Produk: {item['nama']}\n"
        f"┊・Variasi: {tipe}\n"
        f"┊・Harga satuan: Rp. {harga:,}\n"
        f"┊・Stok tersedia: {stok}\n"
        "┊ - - - - - - - - - - - - - - - - - - - - -\n"
        f"┊・Jumlah Pesanan: x1\n"
        f"┊・Total Pembayaran: Rp. {harga:,}\n"
        "╰ - - - - - - - - - - - - - - - - - - - - - ╯"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➖", callback_data="qty_minus"),
            InlineKeyboardButton("Jumlah: 1", callback_data="ignore"),
            InlineKeyboardButton("➕", callback_data="qty_plus")
        ],
        [InlineKeyboardButton("Konfirmasi Order ✅", callback_data="confirm_order")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="back_to_produk")]
    ])
    await query.message.delete()
    await context.bot.send_message(chat_id=query.from_user.id, text=text, reply_markup=keyboard)

async def handle_deposit(update, context):  # HANDLE DEPOSIT
    query = update.callback_query
    nominals = [10000, 15000, 20000, 25000]
    keyboard = [[InlineKeyboardButton(f"Rp{n:,}", callback_data=f"deposit_{n}") for n in nominals]]
    keyboard.append([InlineKeyboardButton("🔧 Custom Nominal", callback_data="deposit_custom")])
    keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu", callback_data="back_to_produk")])

    await query.edit_message_text(
        "💰 Pilih nominal deposit kamu:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_deposit_nominal(update, context):  # HANDLE DEPOSIT NOMINAL
    query = update.callback_query
    data = query.data
    if data == "deposit_custom":
        context.user_data["awaiting_custom"] = True
        reply_keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("❌ Batalkan Deposit")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await query.message.delete()
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="Ketik jumlah deposit yang kamu inginkan (angka saja):",
            reply_markup=reply_keyboard
        )
    else:
        nominal = int(data.split("_")[1])
        context.user_data["nominal_asli"] = nominal
        context.user_data["total_transfer"] = nominal + 23

        reply_keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("❌ Batalkan Deposit")]],
            resize_keyboard=True, one_time_keyboard=True
        )
        await query.message.delete()
        await context.bot.send_photo(
            chat_id=query.from_user.id,
            photo=InputFile("qr.png"),
            caption=f"💳 Transfer *Rp{nominal + 23:,}* ke:\n"
                 "YUKAISTORE`\nSetelah transfer, kirim bukti ke bot ini.",
            parse_mode="Markdown",
            reply_markup=reply_keyboard
        )

async def handle_cancel_deposit(update, context):
    query = update.callback_query
    uid = str(query.from_user.id)
    pending = load_json(deposit_file)
    pending = [p for p in pending if str(p["user_id"]) != uid]
    save_json(deposit_file, pending)
    await query.edit_message_text("✅ Deposit kamu telah dibatalkan.")
    await send_main_menu(context, query.from_user.id, query.from_user)

async def handle_admin_panel(update, context):  # HANDLE ADMIN PANEL (UPDATED)
    query = update.callback_query
    saldo = load_json(saldo_file)
    pending = load_json(deposit_file)
    produk = load_json(produk_file)
    
    text = "*📊 ADMIN PANEL*\n\n"
    text += "*💰 Data Saldo User:*\n"
    if saldo:
        for u, s in saldo.items():
            text += f"• ID {u}: Rp{s:,}\n"
    else:
        text += "Belum ada user.\n"
    
    text += "\n*⏳ Pending Deposit:*\n"
    if pending:
        for p in pending:
            text += f"- @{p['username']} ({p['user_id']}) Rp{p['nominal']:,}\n"
    else:
        text += "Tidak ada.\n"
    
    text += "\n*📦 Stok Produk:*\n"
    for pid, item in produk.items():
        text += f"{pid}. {item['nama']}: {item['stok']}x\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Tambah Stok", callback_data="tambah_stok"),
         InlineKeyboardButton("🔄 Ubah Saldo", callback_data="ubah_saldo")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="back_to_produk")]
    ])
    
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

async def handle_admin_confirm(update, context):  # HANDLE ADMIN CONFIRM
    query = update.callback_query
    user_id = int(query.data.split(":")[1])
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ YA", callback_data=f"final:{user_id}")],
        [InlineKeyboardButton("🔙 Batal", callback_data="back")]
    ])
    await query.edit_message_caption("Konfirmasi saldo ke user ini?", reply_markup=keyboard)

async def handle_admin_final(update, context):  # HANDLE ADMIN FINAL
    query = update.callback_query
    user_id = int(query.data.split(":")[1])
    pending = load_json(deposit_file)
    saldo = load_json(saldo_file)

    item = next((p for p in pending if p["user_id"] == user_id), None)
    if item:
        nominal = item["nominal"]
        saldo[str(user_id)] = saldo.get(str(user_id), 0) + nominal
        save_json(saldo_file, saldo)
        pending = [p for p in pending if p["user_id"] != user_id]
        save_json(deposit_file, pending)
        add_riwayat(user_id, "DEPOSIT", "Konfirmasi Admin", nominal)

        await query.edit_message_caption(
            f"✅ Saldo Rp{nominal:,} berhasil ditambahkan ke user:\n"
            f"👤 Username: @{item['username']}\n"
            f"🆔 User ID: {user_id}"
        )
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Saldo Rp{nominal:,} berhasil ditambahkan ke akunmu!",
            reply_markup=ReplyKeyboardRemove()
        )
        await send_main_menu(context, user_id, await context.bot.get_chat(user_id))

    else:
        await query.edit_message_caption("❌ Data deposit tidak ditemukan.")

async def handle_admin_reject(update, context):  # HANDLE ADMIN REJECT
    query = update.callback_query
    user_id = int(query.data.split(":")[1])
    await query.edit_message_caption("❌ Deposit ditolak.")
    await context.bot.send_message(
        chat_id=user_id,
        text="❌ Deposit kamu ditolak oleh admin.",
        reply_markup=ReplyKeyboardRemove()
    )

async def handle_qty_plus(update, context):  # HANDLE QTY PLUS
    query = update.callback_query
    produk = load_json(produk_file)
    info = context.user_data.get("konfirmasi")
    if not info:
        await query.answer("Data tidak tersedia")
        return

    produk_id = info["produk_id"]
    item = produk.get(produk_id)
    if not item:
        await query.answer("Produk tidak ditemukan")
        return

    jumlah = info["jumlah"]
    if jumlah < item["stok"]:
        jumlah += 1
    context.user_data["konfirmasi"]["jumlah"] = jumlah

    total = jumlah * item["harga"]
    tipe = item["akun_list"][0]["tipe"] if item["akun_list"] else "-"

    text = (
        "KONFIRMASI PESANAN 🛒\n"
        "╭ - - - - - - - - - - - - - - - - - - - - - ╮\n"
        f"┊・Produk: {item['nama']}\n"
        f"┊・Variasi: {tipe}\n"
        f"┊・Harga satuan: Rp. {item['harga']:,}\n"
        f"┊・Stok tersedia: {item['stok']}\n"
        "┊ - - - - - - - - - - - - - - - - - - - - -\n"
        f"┊・Jumlah Pesanan: x{jumlah}\n"
        f"┊・Total Pembayaran: Rp. {total:,}\n"
        "╰ - - - - - - - - - - - - - - - - - - - - - ╯"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➖", callback_data="qty_minus"),
            InlineKeyboardButton(f"Jumlah: {jumlah}", callback_data="ignore"),
            InlineKeyboardButton("➕", callback_data="qty_plus")
        ],
        [InlineKeyboardButton("Konfirmasi Order ✅", callback_data="confirm_order")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="back_to_produk")]
    ])

    await query.edit_message_text(text, reply_markup=keyboard)

async def handle_qty_minus(update, context):  # HANDLE QTY MINUS
    query = update.callback_query
    produk = load_json(produk_file)
    info = context.user_data.get("konfirmasi")
    if not info:
        await query.answer("Data tidak tersedia")
        return

    produk_id = info["produk_id"]
    item = produk.get(produk_id)
    if not item:
        await query.answer("Produk tidak ditemukan")
        return

    jumlah = info["jumlah"]
    if jumlah > 1:
        jumlah -= 1
    context.user_data["konfirmasi"]["jumlah"] = jumlah

    total = jumlah * item["harga"]
    tipe = item["akun_list"][0]["tipe"] if item["akun_list"] else "-"

    text = (
        "KONFIRMASI PESANAN 🛒\n"
        "╭ - - - - - - - - - - - - - - - - - - - - - ╮\n"
        f"┊・Produk: {item['nama']}\n"
        f"┊・Variasi: {tipe}\n"
        f"┊・Harga satuan: Rp. {item['harga']:,}\n"
        f"┊・Stok tersedia: {item['stok']}\n"
        "┊ - - - - - - - - - - - - - - - - - - - - -\n"
        f"┊・Jumlah Pesanan: x{jumlah}\n"
        f"┊・Total Pembayaran: Rp. {total:,}\n"
        "╰ - - - - - - - - - - - - - - - - - - - - - ╯"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➖", callback_data="qty_minus"),
            InlineKeyboardButton(f"Jumlah: {jumlah}", callback_data="ignore"),
            InlineKeyboardButton("➕", callback_data="qty_plus")
        ],
        [InlineKeyboardButton("Konfirmasi Order ✅", callback_data="confirm_order")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="back_to_produk")]
    ])

    await query.edit_message_text(text, reply_markup=keyboard)

async def handle_confirm_order(update, context):  # HANDLE CONFIRM ORDER
    query = update.callback_query
    uid = str(query.from_user.id)
    produk = load_json(produk_file)
    saldo = load_json(saldo_file)
    info = context.user_data.get("konfirmasi")
    if not info:
        await query.answer("❌ Data pesanan tidak ditemukan", show_alert=True)
        return

    produk_id = info["produk_id"]
    jumlah = info["jumlah"]
    item = produk.get(produk_id)
    if not item:
        await query.edit_message_text("❌ Produk tidak ditemukan.")
        return

    total = jumlah * item["harga"]

    if saldo.get(uid, 0) < total:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Deposit Saldo", callback_data="deposit")],
            [InlineKeyboardButton("🔙 Kembali ke Menu", callback_data="back_to_produk")]
        ])
        await query.edit_message_text(
            "❌ *Saldo kamu tidak cukup untuk menyelesaikan pesanan.*\n"
            "Silakan deposit saldo terlebih dahulu atau kembali ke menu utama.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        return

    if item["stok"] < jumlah or len(item["akun_list"]) < jumlah:
        await query.edit_message_text("❌ Stok atau akun tidak mencukupi.")
        return

    saldo[uid] -= total
    item["stok"] -= jumlah
    akun_terpakai = [item["akun_list"].pop(0) for _ in range(jumlah)]
    save_json(saldo_file, saldo)
    save_json(produk_file, produk)
    add_riwayat(uid, "BELI", f"{item['nama']} x{jumlah}", total)

    os.makedirs("akun_dikirim", exist_ok=True)
    file_path = f"akun_dikirim/{uid}_{produk_id}_x{jumlah}.txt"
    with open(file_path, "w") as f:
        for i, akun in enumerate(akun_terpakai, start=1):
            f.write(
                f"Akun #{i}\n"
                f"Username: {akun['username']}\n"
                f"Password: {akun['password']}\n"
                f"Tipe: {akun['tipe']}\n"
                "---------------------------\n"
            )

    with open(file_path, "rb") as f:
        await context.bot.send_document(
            chat_id=query.from_user.id,
            document=InputFile(f, filename=os.path.basename(file_path)),
            caption=f"📦 Pembelian *{item['nama']}* x{jumlah} berhasil!\nSisa saldo: Rp{saldo[uid]:,}",
            parse_mode="Markdown"
        )

    context.user_data.pop("konfirmasi", None)
    await send_main_menu(context, query.from_user.id, query.from_user)

async def handle_back(update, context):  # HANDLE BACK
    query = update.callback_query
    await query.edit_message_caption("✅ Dibatalkan.")

async def handle_back_to_produk(update, context):  # HANDLE BACK TO PRODUK
    query = update.callback_query
    await query.message.delete()
    await send_main_menu(context, query.from_user.id, query.from_user)

async def handle_info_bot(update, context):  # HANDLE INFO BOT
    query = update.callback_query
    text = (
        "📖 *INFORMASI BOT*\n"
        "╽─────────────────────────────╮\n"
        "├  *Nama Bot*: `YUKAISTORE`\n"
        "├  *Author*: [@MYOTAKKU](https://t.me/MYOTAKKU)\n"
        "├  *Fungsi*: Penjualan akun digital otomatis\n"
        "├  *Fitur*: Deposit, Pengiriman Akun, Statistik\n"
        "├  *Update*: TERBARU\n"
        "╰─────────────────────────────╯\n\n"
        "💬 *Saran / kritik?* Hubungi [@MYOTAKKU](https://t.me/MYOTAKKU)"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Kembali ke Menu", callback_data="back_to_produk")]
    ])

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=keyboard
    )

async def handle_ignore(update, context):  # HANDLE IGNORE
    query = update.callback_query
    await query.answer()

# ============= FITUR TAMBAH STOK (BARU) =============

async def handle_tambah_stok_menu(update, context):
    """Menu untuk memilih produk yang akan ditambah stoknya"""
    query = update.callback_query
    produk = load_json(produk_file)
    
    text = "*📦 TAMBAH STOK PRODUK*\n\nPilih produk yang ingin ditambahkan stoknya:\n\n"
    keyboard = []
    
    for pid, item in produk.items():
        text += f"{pid}. {item['nama']} (Stok: {item['stok']})\n"
        keyboard.append([InlineKeyboardButton(
            f"{pid}. {item['nama']}", 
            callback_data=f"addstock_{pid}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="back_to_produk")])
    
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def process_add_stock(update, context):
    """Memproses data akun yang dikirim admin"""
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()
    
    if text == "❌ Batalkan":
        if user_id in user_context:
            del user_context[user_id]
        await update.message.reply_text(
            "✅ Proses dibatalkan.",
            reply_markup=ReplyKeyboardRemove()
        )
        await send_main_menu_safe(update, context)
        return True
    
    if user_id not in user_context:
        return False
    
    ctx = user_context[user_id]
    if ctx.get("action") != "add_stock":
        return False
    
    produk = load_json(produk_file)
    produk_id = ctx["produk_id"]
    
    if produk_id not in produk:
        await update.message.reply_text("❌ Produk tidak ditemukan!")
        del user_context[user_id]
        return True
    
    item = produk[produk_id]
    
    # Parse data akun
    lines = text.split('\n')
    added_accounts = []
    failed_lines = []
    
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
            
        parts = line.split('|')
        
        if len(parts) != 3:
            failed_lines.append(f"Baris {i}: Format salah (harus 3 bagian)")
            continue
        
        username, password, tipe = [p.strip() for p in parts]
        
        if not username or not password or not tipe:
            failed_lines.append(f"Baris {i}: Ada field yang kosong")
            continue
        
        # Tambahkan ke akun_list
        item["akun_list"].append({
            "username": username,
            "password": password,
            "tipe": tipe
        })
        added_accounts.append(username)
    
    # Update stok
    if added_accounts:
        item["stok"] += len(added_accounts)
        save_json(produk_file, produk)
    
    # Buat response
    response = f"*✅ STOK BERHASIL DITAMBAHKAN*\n\n"
    response += f"📦 Produk: {item['nama']}\n"
    response += f"➕ Akun ditambahkan: {len(added_accounts)}\n"
    response += f"📊 Stok sekarang: {item['stok']}\n\n"
    
    if added_accounts:
        response += "*Akun yang ditambahkan:*\n"
        for acc in added_accounts[:5]:  # Tampilkan max 5
            response += f"• {acc}\n"
        if len(added_accounts) > 5:
            response += f"• ... dan {len(added_accounts) - 5} lainnya\n"
    
    if failed_lines:
        response += f"\n⚠️ *Gagal diproses ({len(failed_lines)}):*\n"
        for fail in failed_lines[:3]:  # Tampilkan max 3
            response += f"• {fail}\n"
        if len(failed_lines) > 3:
            response += f"• ... dan {len(failed_lines) - 3} lainnya\n"
    
    await update.message.reply_text(
        response,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Bersihkan context
    del user_context[user_id]
    
    await send_main_menu_safe(update, context)
    return True

async def handle_command_addstock(update, context):
    """Command /addstock untuk admin"""
    user = update.effective_user
    
    if user.id != OWNER_ID:
        await update.message.reply_text("❌ Command ini hanya untuk admin!")
        return
    
    produk = load_json(produk_file)
    
    text = "*📦 TAMBAH STOK PRODUK*\n\nPilih produk yang ingin ditambahkan stoknya:\n\n"
    keyboard = []
    
    for pid, item in produk.items():
        text += f"{pid}. {item['nama']} (Stok saat ini: {item['stok']})\n"
        keyboard.append([InlineKeyboardButton(
            f"{pid}. {item['nama']}", 
            callback_data=f"addstock_{pid}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="admin_panel")])
    
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_pilih_produk_stok(update, context):
    """Ketika admin memilih produk untuk ditambah stok"""
    query = update.callback_query
    produk_id = query.data.split("_")[1]
    produk = load_json(produk_file)
    
    if produk_id not in produk:
        await query.answer("❌ Produk tidak ditemukan", show_alert=True)
        return
    
    item = produk[produk_id]
    
    # Simpan context user
    user_context[str(query.from_user.id)] = {
        "action": "add_stock",
        "produk_id": produk_id,
        "step": "username"
    }
    
    reply_keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("❌ Batalkan")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await query.message.delete()
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text=f"*📦 TAMBAH STOK: {item['nama']}*\n\n"
             f"Stok saat ini: {item['stok']}\n\n"
             f"Silakan kirim data akun dengan format:\n"
             f"```\n"
             f"username1@mail.com|password1|tipe1\n"
             f"username2@mail.com|password2|tipe2\n"
             f"username3@mail.com|password3|tipe3\n"
             f"```\n\n"
             f"*Contoh:*\n"
             f"```\n"
             f"spotify10@mail.com|pass123|1 Bulan Student\n"
             f"spotify11@mail.com|pass456|1 Bulan Student\n"
             f"```\n\n"
             f"Pisahkan dengan "|" (pipe) dan setiap akun di baris baru.\n"
             f"Atau kirim satu per satu.",
        parse_mode="Markdown",
        reply_markup=reply_keyboard
    )

# ============= FITUR UBAH SALDO (BARU) =============

async def handle_ubah_saldo(update, context):
    query = update.callback_query
    if query.from_user.id != OWNER_ID:
        await query.answer("Hanya admin yang bisa mengakses ini.", show_alert=True)
        return

    await query.message.delete()
    reply_keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("❌ Batalkan")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text="Kirim ID user yang saldo-nya ingin diubah:",
        reply_markup=reply_keyboard
    )
    user_context[str(query.from_user.id)] = {
        "action": "ubah_saldo",
        "step": "id"
    }

async def process_ubah_saldo(update, context):
    user_id = str(update.effective_user.id)
    if int(user_id) != OWNER_ID:
        return False
    text = update.message.text.strip()
    
    if text == "❌ Batalkan":
        if user_id in user_context:
            del user_context[user_id]
        await update.message.reply_text(
            "✅ Proses dibatalkan.",
            reply_markup=ReplyKeyboardRemove()
        )
        await send_main_menu_safe(update, context)
        return True
    
    if user_id not in user_context:
        return False
    
    ctx = user_context[user_id]
    if ctx.get("action") != "ubah_saldo":
        return False
    
    if ctx["step"] == "id":
        try:
            target_id = int(text)
            saldo = load_json(saldo_file)
            if str(target_id) not in saldo:
                await update.message.reply_text("❌ User tidak ditemukan.")
                return True
            ctx["target_id"] = target_id
            ctx["step"] = "nominal"
            await update.message.reply_text(
                f"Saldo saat ini: Rp{saldo[str(target_id)]:,}\n\n"
                "Kirim nominal perubahan (positif untuk tambah, negatif untuk kurang):"
            )
            return True
        except ValueError:
            await update.message.reply_text("❌ ID invalid, harus angka.")
            return True
    
    elif ctx["step"] == "nominal":
        try:
            nominal = int(text)
            saldo = load_json(saldo_file)
            target_str = str(ctx["target_id"])
            old_saldo = saldo.get(target_str, 0)
            saldo[target_str] = old_saldo + nominal
            save_json(saldo_file, saldo)
            add_riwayat(ctx["target_id"], "ADMIN_UBAH", f"Perubahan saldo oleh admin: {nominal}", abs(nominal))
            await update.message.reply_text(
                f"✅ Saldo user {ctx['target_id']} diubah dari Rp{old_saldo:,} menjadi Rp{saldo[target_str]:,}",
                reply_markup=ReplyKeyboardRemove()
            )
            del user_context[user_id]
            await send_main_menu_safe(update, context)
            return True
        except ValueError:
            await update.message.reply_text("❌ Nominal invalid, harus angka.")
            return True

# ============= CALLBACK HANDLERS =============

callback_handlers = {
    "list_produk": handle_list_produk,
    "cek_stok": handle_cek_stok,
    "info_bot": handle_info_bot,
    "deposit": handle_deposit,
    "deposit_custom": handle_deposit_nominal,
    "cancel_deposit": handle_cancel_deposit,
    "admin_panel": handle_admin_panel,
    "tambah_stok": handle_tambah_stok_menu,  # TAMBAHAN BARU
    "ubah_saldo": handle_ubah_saldo,  # TAMBAHAN BARU
    "qty_plus": handle_qty_plus,
    "qty_minus": handle_qty_minus,
    "confirm_order": handle_confirm_order,
    "back": handle_back,
    "back_to_produk": handle_back_to_produk,
    "ignore": handle_ignore,
}

async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data in load_json(produk_file):
        await handle_produk_detail(update, context)
    elif data.startswith("addstock_"):  # TAMBAHAN BARU
        await handle_pilih_produk_stok(update, context)
    elif data.startswith("deposit_"):
        await handle_deposit_nominal(update, context)
    elif data.startswith("confirm:"):
        await handle_admin_confirm(update, context)
    elif data.startswith("final:"):
        await handle_admin_final(update, context)
    elif data.startswith("reject:"):
        await handle_admin_reject(update, context)
    elif data in callback_handlers:
        await callback_handlers[data](update, context)
    else:
        await query.edit_message_text("❌ Aksi tidak dikenali.")

async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    saldo = load_json(saldo_file)
    uid = str(user.id)
    if uid not in saldo:
        saldo[uid] = 0
        save_json(saldo_file, saldo)
    await send_main_menu(context, update.effective_chat.id, user)

async def handle_text(update: Update, context: CallbackContext):
    text = update.message.text.strip()

    if "SOLDOUT" in text:
        text = text.split()[0]

    uid = str(update.effective_user.id)

    # CEK UNTUK PROSES TAMBAH STOK (ADMIN)
    if await process_add_stock(update, context):
        return

    # CEK UNTUK PROSES UBAH SALDO (ADMIN)
    if await process_ubah_saldo(update, context):
        return

    if text == "❌ Batalkan Deposit":
        pending = load_json(deposit_file)
        pending = [p for p in pending if str(p["user_id"]) != uid]
        save_json(deposit_file, pending)
        await update.message.reply_text("✅ Deposit kamu telah dibatalkan.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu_safe(update, context)
        return

    if context.user_data.get("awaiting_custom"):
        try:
            nominal = int(text)
            context.user_data["awaiting_custom"] = False
            context.user_data["nominal_asli"] = nominal
            context.user_data["total_transfer"] = nominal + 23
            reply_keyboard = ReplyKeyboardMarkup(
                [[KeyboardButton("❌ Batalkan Deposit")]],
                resize_keyboard=True, one_time_keyboard=True
            )
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=InputFile("qr.jpg"),
                caption=f"💳 Transfer *Rp{nominal + 23:,}* ke:\n"
                        "`SESUAI NOMINAL`\nSetelah transfer, kirim bukti foto transfer ke bot ini.",
                parse_mode="Markdown",
                reply_markup=reply_keyboard
            )
        except:
            await update.message.reply_text("❌ Format salah, hanya bisa mengirim angka.")
        return

    produk = load_json(produk_file)
    if text in produk:
        item = produk[text]
        if item["stok"] <= 0:
            await update.message.reply_text("❌ Produk ini tidak bisa dibeli karena stok habis.")
            await send_main_menu_safe(update, context)
            return

        harga = item["harga"]
        tipe = item["akun_list"][0]["tipe"] if item["akun_list"] else "-"
        stok = item["stok"]

        context.user_data["konfirmasi"] = {
            "produk_id": text,
            "jumlah": 1
        }

        konfirmasi_text = (
            "KONFIRMASI PESANAN 🛒\n"
            "╭ - - - - - - - - - - - - - - - - - - - - - ╮\n"
            f"┊・Produk: {item['nama']}\n"
            f"┊・Variasi: {tipe}\n"
            f"┊・Harga satuan: Rp. {harga:,}\n"
            f"┊・Stok tersedia: {stok}\n"
            "┊ - - - - - - - - - - - - - - - - - - - - -\n"
            f"┊・Jumlah Pesanan: x1\n"
            f"┊・Total Pembayaran: Rp. {harga:,}\n"
            "╰ - - - - - - - - - - - - - - - - - - - - - ╯"
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➖", callback_data="qty_minus"),
                InlineKeyboardButton("Jumlah: 1", callback_data="ignore"),
                InlineKeyboardButton("➕", callback_data="qty_plus")
            ],
            [InlineKeyboardButton("Konfirmasi Order ✅", callback_data="confirm_order")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="back_to_produk")]
        ])
        await update.message.reply_text(konfirmasi_text, reply_markup=keyboard)
        return

    if text == "🔙 Kembali":
        await send_main_menu_safe(update, context)
        return

    await send_main_menu_safe(update, context)

async def handle_photo(update: Update, context: CallbackContext):
    user = update.effective_user
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    os.makedirs("bukti", exist_ok=True)
    path = f"bukti/{user.id}.jpg"
    await file.download_to_drive(path)

    nominal = context.user_data.get("nominal_asli", 0)
    total = context.user_data.get("total_transfer", nominal)

    pending = load_json(deposit_file)
    pending.append({
        "user_id": user.id,
        "username": user.username,
        "bukti_path": path,
        "nominal": nominal,
        "total_transfer": total
    })
    save_json(deposit_file, pending)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Konfirmasi", callback_data=f"confirm:{user.id}")],
        [InlineKeyboardButton("❌ Tolak", callback_data=f"reject:{user.id}")]
    ])
    with open(path, "rb") as f:
        await context.bot.send_photo(
            chat_id=OWNER_ID,
            photo=InputFile(f),
            caption=f"📥 Deposit dari @{user.username or user.id}\n"
                    f"Transfer: Rp{total:,}\nMasuk: Rp{nominal:,}",
            reply_markup=keyboard
        )
    await update.message.reply_text("✅ Bukti dikirim! Tunggu konfirmasi admin.")

def main():  # Made With love by @govtrashit A.K.A RzkyO
    app = Application.builder().token("8130810030:AAEG6UmjONPbLsXkUpAcCKQwCDImHEtRieM").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addstock", handle_command_addstock))  # TAMBAHAN BARU
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

if __name__ == "__main__":
    main()
