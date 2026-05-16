import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)

# ── Config ──────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "8568124430:AAH1biC-kDuknRxnsCox6Oaw0jBXWCyw2fA")
API_KEY   = os.getenv("API_KEY",   "rk_live_a5eefd9db7685c6d6181d8ad4595f50a")
BASE_URL  = "https://esimnet.org/api/v1/reseller"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── Conversation states ──────────────────────────────────────────────────────
ENTER_MANUAL_COUNTRY, ENTER_EMAIL, CONFIRM_ORDER = range(3)

# ── Popular countries ────────────────────────────────────────────────────────
COUNTRIES = [
    ("🇺🇸 USA",          "US"), ("🇬🇧 UK",          "GB"),
    ("🇫🇷 France",       "FR"), ("🇩🇪 Germany",      "DE"),
    ("🇯🇵 Japan",        "JP"), ("🇦🇺 Australia",    "AU"),
    ("🇨🇦 Canada",       "CA"), ("🇮🇹 Italy",        "IT"),
    ("🇪🇸 Spain",        "ES"), ("🇹🇷 Turkey",       "TR"),
    ("🇦🇪 UAE",          "AE"), ("🇸🇦 Saudi Arabia", "SA"),
    ("🇩🇿 Algeria",      "DZ"), ("🇲🇦 Morocco",      "MA"),
    ("🇪🇬 Egypt",        "EG"), ("🇹🇳 Tunisia",      "TN"),
    ("🌍 دولة أخرى",    "MANUAL"),
]

# ── API helpers ──────────────────────────────────────────────────────────────
def api_get(path, params=None):
    try:
        r = requests.get(f"{BASE_URL}{path}", headers=HEADERS, params=params, timeout=15)
        return r.json()
    except Exception as e:
        logger.error(f"GET {path} failed: {e}")
        return {"success": False, "error": str(e)}

def api_post(path, payload):
    try:
        r = requests.post(f"{BASE_URL}{path}", headers=HEADERS, json=payload, timeout=30)
        return r.json()
    except Exception as e:
        logger.error(f"POST {path} failed: {e}")
        return {"success": False, "error": str(e)}

# ── Keyboards ────────────────────────────────────────────────────────────────
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 تصفح الباقات",  callback_data="browse"),
         InlineKeyboardButton("💰 رصيدي",          callback_data="balance")],
        [InlineKeyboardButton("📋 طلباتي",         callback_data="orders"),
         InlineKeyboardButton("ℹ️ مساعدة",         callback_data="help")],
    ])

def back_keyboard(dest="main_menu"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=dest)]])

# ── /start ───────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🌐 *مرحباً بك في بوت eSIM Net!* 👋\n\n"
        "من هنا يمكنك:\n"
        "• 📶 تصفح وشراء باقات eSIM لأي دولة\n"
        "• 💰 عرض رصيد محفظتك\n"
        "• 📋 متابعة جميع طلباتك\n\n"
        "اختر من القائمة أدناه 👇"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

# ── Balance ──────────────────────────────────────────────────────────────────
async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("⏳ جاري تحميل رصيدك...")

    data = api_get("/balance")

    if data.get("success"):
        bal  = data["balance"]
        cur  = data["currency"]
        txns = data.get("transactions", [])[:5]

        text = f"💰 *رصيد محفظتك:* `{bal} {cur}`\n\n"

        if txns:
            text += "📊 *آخر 5 معاملات:*\n"
            for t in txns:
                icon = "➖" if t["type"] == "DEBIT" else "➕"
                desc = t.get("description", "")[:45]
                text += f"{icon} `{t['amount']} {cur}` — {desc}\n"
    else:
        text = f"❌ *خطأ:* {data.get('error', 'فشل تحميل الرصيد')}"

    await q.edit_message_text(text, reply_markup=back_keyboard(), parse_mode="Markdown")

# ── Browse ───────────────────────────────────────────────────────────────────
async def browse_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    buttons = []
    row = []
    for name, code in COUNTRIES:
        row.append(InlineKeyboardButton(name, callback_data=f"country_{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")])

    await q.edit_message_text(
        "🌍 *اختر الدولة:*",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )

async def handle_country_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    code = q.data.replace("country_", "")

    if code == "MANUAL":
        await q.edit_message_text("✏️ *أدخل كود الدولة* (مثال: US, FR, DZ, JP):", parse_mode="Markdown")
        return ENTER_MANUAL_COUNTRY

    await _load_plans(q, context, code)
    return ConversationHandler.END

async def receive_manual_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().upper()
    await update.message.reply_text(f"⏳ جاري تحميل باقات {code}...")
    await _load_plans(update, context, code, via_message=True)
    return ConversationHandler.END

async def _load_plans(q_or_update, context, country_code, via_message=False):
    data = api_get("/products", params={"country": country_code})

    if not data.get("success") or not data.get("plans"):
        err_text = f"❌ {data.get('error', 'لا توجد باقات لهذه الدولة')}"
        kb = back_keyboard("browse")
        if via_message:
            await q_or_update.message.reply_text(err_text, reply_markup=kb)
        else:
            await q_or_update.edit_message_text(err_text, reply_markup=kb)
        return

    plans = data["plans"]
    context.user_data["plans"]   = {p["id"]: p for p in plans}
    context.user_data["country"] = country_code

    text = f"📦 *باقات متاحة في {country_code}* ({len(plans)} باقة):\n\n"
    buttons = []

    for p in plans:
        data_lbl = "♾️ لا محدود" if p.get("is_unlimited") else p.get("data_amount", "—")
        days     = p.get("duration_days", "?")
        price    = p.get("reseller_price", "?")
        cur      = p.get("currency", "USD")
        extras   = ("📞" if p.get("withCall") else "") + ("💬" if p.get("withSMS") else "")
        label    = f"📶 {data_lbl} | {days}د | {price}{cur} {extras}".strip()
        buttons.append([InlineKeyboardButton(label, callback_data=f"plan_{p['id']}")])

    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="browse")])

    if via_message:
        await q_or_update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
    else:
        await q_or_update.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

# ── Plan selection ────────────────────────────────────────────────────────────
async def handle_plan_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    plan_id = q.data.replace("plan_", "")

    plan = context.user_data.get("plans", {}).get(plan_id)
    if not plan:
        await q.edit_message_text("❌ الباقة غير موجودة، ابدأ من جديد /start")
        return ConversationHandler.END

    context.user_data["selected_plan"] = plan
    data_lbl = "♾️ لا محدود" if plan.get("is_unlimited") else plan.get("data_amount", "—")

    text = (
        f"📦 *تفاصيل الباقة المختارة:*\n\n"
        f"📛 الاسم: {plan['name']}\n"
        f"📶 البيانات: {data_lbl}\n"
        f"📅 المدة: {plan.get('duration_days', '?')} يوم\n"
        f"💵 السعر: {plan['reseller_price']} {plan['currency']}\n"
        f"📞 مكالمات: {'✅' if plan.get('withCall') else '❌'}\n"
        f"💬 رسائل: {'✅' if plan.get('withSMS') else '❌'}\n\n"
        f"✉️ *أدخل البريد الإلكتروني للعميل:*"
    )
    await q.edit_message_text(text, parse_mode="Markdown")
    return ENTER_EMAIL

async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()

    if "@" not in email or "." not in email.split("@")[-1]:
        await update.message.reply_text("❌ البريد غير صحيح، أعد المحاولة:")
        return ENTER_EMAIL

    context.user_data["email"] = email
    plan    = context.user_data["selected_plan"]
    country = context.user_data["country"]

    text = (
        f"✅ *تأكيد الطلب:*\n\n"
        f"📦 الباقة: {plan['name']}\n"
        f"🌍 الدولة: {country}\n"
        f"✉️ البريد: `{email}`\n"
        f"💵 السعر: {plan['reseller_price']} {plan['currency']}\n\n"
        f"هل تريد المتابعة؟"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأكيد الطلب", callback_data="confirm_order"),
         InlineKeyboardButton("❌ إلغاء",       callback_data="main_menu")]
    ])
    await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")
    return CONFIRM_ORDER

async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("⏳ جاري معالجة الطلب... لا تغلق المحادثة")

    plan    = context.user_data["selected_plan"]
    country = context.user_data["country"]
    email   = context.user_data["email"]

    result = api_post("/order", {
        "planId":         plan["id"],
        "country":        country,
        "customerEmail":  email,
    })

    if result.get("success"):
        order  = result["order"]
        esim   = result["esim"]
        wallet = result.get("wallet", {})

        text = (
            f"🎉 *تم الطلب بنجاح!*\n\n"
            f"📋 رقم الطلب:\n`{order['reference']}`\n\n"
            f"📦 الباقة: {order['planName']}\n"
            f"🌍 الدولة: {order['country']}\n"
            f"✅ الحالة: {order['status']}\n"
            f"💵 المبلغ: {order['price']} {order['currency']}\n"
            f"💰 الرصيد المتبقي: {wallet.get('balanceAfter', '?')} {order['currency']}\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📱 *بيانات eSIM:*\n\n"
            f"🔢 ICCID:\n`{esim['iccid']}`\n\n"
            f"🔑 كود التفعيل:\n`{esim['activationCode']}`\n\n"
            f"📩 تم إرسال QR Code إلى البريد الإلكتروني."
        )
    else:
        error = result.get("error", "خطأ غير معروف")
        text  = f"❌ *فشل الطلب:*\n\n{error}"

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]])
    await q.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    return ConversationHandler.END

# ── Orders ───────────────────────────────────────────────────────────────────
async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("⏳ جاري تحميل طلباتك...")

    data = api_get("/orders", params={"limit": 10})

    if not data.get("success"):
        text = f"❌ {data.get('error', 'فشل تحميل الطلبات')}"
    else:
        orders = data.get("orders", [])
        if not orders:
            text = "📋 لا توجد طلبات بعد.\n\nابدأ بشراء أول باقة! 🚀"
        else:
            text = "📋 *آخر 10 طلبات:*\n\n"
            for o in orders:
                icon = "✅" if o["status"] == "DELIVERED" else "⏳"
                text += (
                    f"{icon} `{o['reference']}`\n"
                    f"   🌍 {o['country']} | 📦 {o['planId']} | "
                    f"💵 {o['amount']} {o['currency']}\n\n"
                )

    await q.edit_message_text(text, reply_markup=back_keyboard(), parse_mode="Markdown")

# ── Help ─────────────────────────────────────────────────────────────────────
async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    text = (
        "ℹ️ *دليل الاستخدام:*\n\n"
        "1️⃣ اضغط *تصفح الباقات*\n"
        "2️⃣ اختر الدولة\n"
        "3️⃣ اختر الباقة المناسبة\n"
        "4️⃣ أدخل البريد الإلكتروني للعميل\n"
        "5️⃣ أكّد الطلب ← ستصل بيانات eSIM فوراً ✅\n\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 *ملاحظات:*\n"
        "• QR Code يُرسل على بريد العميل\n"
        "• رصيدك يُخصم تلقائياً عند نجاح الطلب\n"
        "• في حال فشل الطلب يُعاد الرصيد تلقائياً\n\n"
        "📌 اكتب /start للعودة للقائمة الرئيسية"
    )
    await q.edit_message_text(text, reply_markup=back_keyboard(), parse_mode="Markdown")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Conversation: browse → select plan → email → confirm
    browse_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_country_button, pattern=r"^country_"),
            CallbackQueryHandler(handle_plan_button,    pattern=r"^plan_"),
        ],
        states={
            ENTER_MANUAL_COUNTRY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_manual_country)
            ],
            ENTER_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email)
            ],
            CONFIRM_ORDER: [
                CallbackQueryHandler(confirm_order, pattern="^confirm_order$")
            ],
        },
        fallbacks=[
            CommandHandler("start", cmd_start),
            CallbackQueryHandler(cmd_start, pattern="^main_menu$"),
        ],
        per_message=False,
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(browse_conv)
    app.add_handler(CallbackQueryHandler(cmd_start,       pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(show_balance,    pattern="^balance$"))
    app.add_handler(CallbackQueryHandler(browse_products, pattern="^browse$"))
    app.add_handler(CallbackQueryHandler(show_orders,     pattern="^orders$"))
    app.add_handler(CallbackQueryHandler(show_help,       pattern="^help$"))

    logger.info("✅ البوت يعمل الآن...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
