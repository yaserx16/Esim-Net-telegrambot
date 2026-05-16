# 🌐 eSIM Net Telegram Bot

بوت تليقرام لبيع باقات eSIM عبر واجهة eSIM Net API.

## 🚀 النشر على Render (مجاني)

### 1. ارفع الكود على GitHub
```bash
git init
git add .
git commit -m "init esim bot"
git remote add origin https://github.com/YOUR_USERNAME/esim-bot.git
git push -u origin main
```

### 2. أنشئ Background Worker على Render
1. اذهب إلى [render.com](https://render.com) وسجّل دخول
2. اضغط **New → Background Worker**
3. اربط مستودع GitHub
4. اضبط الإعدادات:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
5. أضف Environment Variables:
   - `BOT_TOKEN` = توكن البوت
   - `API_KEY` = مفتاح API

## 🚀 النشر على Railway (مجاني)

1. اذهب إلى [railway.app](https://railway.app)
2. اضغط **New Project → Deploy from GitHub repo**
3. اربط المستودع
4. في **Variables** أضف:
   - `BOT_TOKEN`
   - `API_KEY`
5. في **Settings → Deploy** تأكد من أن الأمر هو `python bot.py`

## ✨ مميزات البوت

- 🌍 تصفح باقات eSIM لأكثر من 150 دولة
- 💰 عرض رصيد المحفظة وآخر المعاملات
- 🛒 شراء باقات مع تسليم فوري
- 📋 متابعة قائمة الطلبات
- 🔑 ICCID وكود التفعيل يظهر مباشرة في المحادثة
