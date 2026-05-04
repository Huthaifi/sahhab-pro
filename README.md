# ⚡ سحّاب Pro — Sahhab Pro

> محمّل الوسائط الاحترافي | Professional Media Downloader

تطبيق ويب كامل لتحميل الفيديوهات من يوتيوب، تيك توك، إنستغرام، سناب شات، وأكثر من ألف موقع آخر — مع دعم قائمة الانتظار، وجلب حسابات كاملة، وإرسال مباشر لتيليجرام.

---

## ✨ الميزات

| الميزة | الوصف |
|--------|--------|
| ⚡ تحميل سريع | أضف رابط وحدد الجودة، يبدأ التحميل فوراً |
| 📋 روابط متعددة | ضع حتى 50 رابط دفعة واحدة |
| 👤 جلب حساب كامل | أدخل رابط قناة أو حساب ويعرض لك كل الفيديوهات |
| ⏳ قائمة الانتظار | تحميل متسلسل مع شريط تقدم لكل مهمة |
| ✈️ إرسال لتيليجرام | السيرفر يحمّل ويرسل مباشرة لقناتك بدون استهلاك إنترنتك |
| 🌐 1000+ موقع | YouTube, TikTok, Instagram, Snapchat, Twitter/X, Facebook وأكثر |
| 🎵 صوت فقط | استخرج الصوت MP3/M4A من أي فيديو |
| 📱 واجهة عربية | RTL عربي كامل، متجاوب مع الجوال |

---

## 🏗️ بنية المشروع

```
sahhab-pro/
├── backend/
│   ├── main.py            ← FastAPI — نقاط API والـ WebSocket
│   ├── downloader.py      ← مُغلِّف yt-dlp (تحميل + جلب الحسابات)
│   ├── queue_manager.py   ← إدارة قائمة الانتظار + بث WebSocket
│   ├── telegram_sender.py ← إرسال مباشر لتيليجرام
│   └── requirements.txt
├── frontend/
│   └── index.html         ← واجهة SPA عربية كاملة (HTML+CSS+JS)
├── render.yaml            ← إعداد النشر على Render.com
└── README.md
```

---

## 🚀 تشغيل محلي (Local Development)

### متطلبات
- Python 3.10+
- pip

### خطوات التشغيل

```bash
# 1. انسخ المشروع
git clone <repo-url>
cd sahhab-pro

# 2. ثبّت المتطلبات
cd backend
pip install -r requirements.txt

# 3. شغّل السيرفر
python main.py
# أو:
uvicorn main:app --reload --port 8000

# 4. افتح الواجهة
# افتح ملف frontend/index.html في المتصفح مباشرة
# أو شغّل سيرفر بسيط:
cd ../frontend
python -m http.server 3000
# ثم افتح: http://localhost:3000
```

### تغيير عنوان الـ API في الواجهة

في `frontend/index.html`، السطر:
```javascript
const API_BASE = localStorage.getItem('sahhab_api') || 'http://localhost:8000';
```

يمكنك تغيير `http://localhost:8000` لعنوان السيرفر بعد النشر.

أو من المتصفح مباشرة:
```javascript
localStorage.setItem('sahhab_api', 'https://your-backend.onrender.com')
```

---

## ☁️ النشر المجاني (بدون بطاقة ائتمان)

### الخيار 1: Render.com (Backend) + Cloudflare Pages (Frontend)

#### Backend على Render.com

1. ارفع المشروع على GitHub
2. اذهب إلى [render.com](https://render.com) وأنشئ حساباً
3. اختر **New Web Service** → اربط مستودع GitHub
4. استخدم الإعدادات التالية:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
   - **Runtime:** Python 3
5. انشر — ستحصل على رابط مثل: `https://sahhab-pro.onrender.com`

> ⚠️ الخطة المجانية تُوقف السيرفر بعد 15 دقيقة من عدم الاستخدام.
> للحل: استخدم [UptimeRobot](https://uptimerobot.com) لإبقاء السيرفر يقظاً.

#### Frontend على Cloudflare Pages

1. اذهب إلى [pages.cloudflare.com](https://pages.cloudflare.com)
2. **New Project** → ارفع مجلد `frontend` مباشرة
3. أو اربطه بـ GitHub وحدد `frontend` كـ root directory
4. الموقع سينشر فوراً على رابط مجاني

#### تحديث رابط API في الواجهة
افتح `frontend/index.html` وغيّر:
```javascript
const API_BASE = 'https://your-backend-name.onrender.com';
```

---

### الخيار 2: Railway.app (أسهل)

1. اذهب إلى [railway.app](https://railway.app)
2. **New Project** → **Deploy from GitHub**
3. حدد مجلد `backend`
4. Railway يكتشف Python ويعمل تلقائياً
5. احصل على $5 رصيد مجاني شهرياً (يكفي للاستخدام الخفيف)

---

### الخيار 3: Koyeb (بديل مجاني)

1. [koyeb.com](https://koyeb.com) → خطة مجانية حقيقية
2. ارفع المشروع كـ Docker أو Git
3. Dockerfile مقترح:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

---

## ✈️ إعداد بوت تيليجرام

1. افتح تيليجرام وابحث عن **@BotFather**
2. أرسل `/newbot` وأتبع الخطوات
3. انسخ الـ **Bot Token** الذي يظهر
4. أضف البوت لقناتك كـ **مسؤول** مع صلاحية "نشر الرسائل"
5. افتح تبويب **تيليجرام** في الموقع والصق التوكن وحدد Chat ID
6. اضغط **تحقق** ثم **حفظ**

### كيف أعرف Chat ID القناة؟
- للقنوات العامة: اكتب `@اسم_القناة` مباشرة
- للمجموعات والقنوات الخاصة: استخدم [@RawDataBot](https://t.me/RawDataBot)

---

## 🔧 API Reference

| Method | Path | الوصف |
|--------|------|--------|
| `POST` | `/api/download` | إضافة رابط للقائمة |
| `POST` | `/api/download/bulk` | إضافة عدة روابط دفعة |
| `GET`  | `/api/status/{id}` | حالة مهمة معينة |
| `GET`  | `/api/queue` | جميع المهام |
| `DELETE` | `/api/queue/{id}` | إلغاء مهمة |
| `DELETE` | `/api/queue` | حذف المكتملة |
| `POST` | `/api/profile` | جلب فيديوهات حساب |
| `GET`  | `/api/download/{id}/file` | تحميل الملف |
| `POST` | `/api/telegram/send` | إرسال لتيليجرام |
| `POST` | `/api/telegram/verify` | التحقق من توكن البوت |
| `WS`   | `/ws/{client_id}` | WebSocket للتحديثات اللحظية |

---

## 📊 جودة التحميل المدعومة

| الخيار | الوصف |
|--------|--------|
| `best` | أفضل جودة متاحة (افتراضي) |
| `1080p` | Full HD |
| `720p` | HD |
| `480p` | SD |
| `360p` | منخفضة |
| `audio` | صوت فقط (M4A) |

---

## ⚠️ ملاحظات هامة

- **الحد الأقصى لتيليجرام:** 50 MB لبوتات تيليجرام — الملفات الأكبر لن تُرسل
- **yt-dlp:** يجب تحديثه بانتظام لدعم المنصات: `pip install -U yt-dlp`
- **Instagram/TikTok:** قد يتطلب تسجيل الدخول للمحتوى الخاص — يمكن إضافة Cookies
- **الملفات المحملة:** تُحفظ مؤقتاً على السيرفر — يُنصح بتنظيف دوري
- **القانون:** هذا الأداة للاستخدام الشخصي فقط، احترم حقوق المحتوى

---

## 📦 التقنيات المستخدمة

| | التقنية | الاستخدام |
|-|---------|-----------|
| 🐍 | FastAPI | Backend API |
| 📥 | yt-dlp | تحميل الوسائط |
| 🔌 | WebSocket | تحديثات لحظية |
| ✈️ | Telegram Bot API | الإرسال المباشر |
| 🌐 | Vanilla HTML/CSS/JS | الواجهة (بدون frameworks) |
| ☁️ | Render.com | استضافة مجانية للـ Backend |
| 📄 | Cloudflare Pages | استضافة مجانية للـ Frontend |

---

## 📝 License

للاستخدام الشخصي فقط.
