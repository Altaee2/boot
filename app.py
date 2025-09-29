# =========================
# --- الأدوات اللازمة ---
# =========================
import telebot
import requests
import gdshortener
import re
import zipfile
from io import BytesIO
import json
import os
import threading
import time
from telebot import types
# استيراد الأدوات اللازمة لإنشاء الأزرار المضمنة (Inline Keyboard)
from telebot.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Mak
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from pytz import timezone # 🆕 استيراد مكتبة pytz للمنطقة الزمنية

# =========================
# --- الإعدادات الثابتة والمدمجة ---
# =========================
TOKEN = "7631796128:AAFOUcS1aolCyUUZp-ndLYlH4-U4uxTlFgU" 
DEVELOPER_ID = 6454550864 
CHANNEL_ID = "@xx28z"   
CHANNEL_URL = "my00002.t.me"
DATE_FORMAT = '%Y %m %d'
LOG_FILE = 'user_ids.txt'

# إعدادات قائمة المهام (TODO List)
DATA_FILE = "tasks_data.json"
LOCK = threading.Lock() 

# 🆕 إعدادات المنطقة الزمنية لبغداد
BAGHDAD_TIMEZONE = timezone('Asia/Baghdad') 

# --- تهيئة البوت وقواعد البيانات المؤقتة ---
bot = telebot.TeleBot(TOKEN, parse_mode='HTML')
user_data = {}
user_ratings = {}
channel_keyboard = Mak().add(Btn("قناتي", url=CHANNEL_URL))

# قاموس لحفظ حالة المستخدم لإضافة مهمة
# {user_id: True/False}
adding_task_state = {} 

# =========================
# 1. دوال مساعدة للتسجيل
# =========================
def log_new_user(message):
    """تسجيل المستخدم الجديد وإرسال إشعار للمطور."""
    user_id = message.from_user.id
    first_name = message.from_user.first_name

    if not os.path.exists(LOG_FILE) or str(user_id) not in open(LOG_FILE).read():
        user_data[user_id] = None
        notification_message = (
            f"مستخدم جديد بدأ البوت: "
            f"[{first_name}](tg://user?id={user_id})، المعرّف: `{user_id}`"
        )
        bot.send_message(
            DEVELOPER_ID,
            notification_message,
            parse_mode="Markdown"
        )
        with open(LOG_FILE, 'a') as file:
            file.write(f'{user_id}\n')


# =========================
# 2. دوال جلب معلومات الوقت والتاريخ (جديد)
# =========================
def get_hijri_date():
    """يجلب التاريخ الهجري من موقع السيد السيستاني."""
    url = "https://www.sistani.org"
    headers = {
      'User-Agent': "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Mobile Safari/537.36",
    }
    try:
        # تحديد مهلة زمنية للطلب لمنع توقف البوت
        response = requests.get(url, headers=headers, timeout=5) 
        response.raise_for_status() 
        
        # البحث عن التاريخ الهجري باستخدام التعبير النظامي
        res = re.search(r'style="margin-left:9px;">([^<]+)</span>', response.text)
        if res:
            # تنظيف وإرجاع التاريخ الهجري
            return res.group(1).strip()
        else:
            return "غير متوفر"
    except Exception:
        # إرجاع رسالة خطأ في حالة فشل الجلب
        return "غير متوفر"

def get_current_info():
    """تنسيق رسالة الترحيب بمعلومات الوقت والتاريخ (بغداد)."""
    # جلب الوقت الحالي بتوقيت بغداد
    now = datetime.now(BAGHDAD_TIMEZONE)
    
    # تنسيق التاريخ الميلادي واليوم والساعة
    date_gregorian = now.strftime('%Y/%m/%d')
    time_now = now.strftime('%I:%M %p') # تنسيق الساعة 12
    day_name = now.strftime('%A')
    
    # تعريب أسماء الأيام
    day_names_ar = {
        'Sunday': 'الأحد', 'Monday': 'الإثنين', 'Tuesday': 'الثلاثاء', 
        'Wednesday': 'الأربعاء', 'Thursday': 'الخميس', 'Friday': 'الجمعة', 'Saturday': 'السبت'
    }
    day_name_ar = day_names_ar.get(day_name, day_name)
    
    # جلب التاريخ الهجري
    hijri_date = get_hijri_date()
    
    # بناء رسالة الترحيب والمعلومات
    info_message = (
        f"<b>أهلاً بك عزيزي المستخدم!</b> 👋\n"
        f"أنا هنا لمساعدتك في مجموعة من الخدمات المميزة.\n\n"
        f"<b>🗓️ معلومات الوقت والتاريخ (بغداد):</b>\n"
        f"• <b>اليوم:</b> {day_name_ar}\n"
        f"• <b>التاريخ الهجري:</b> {hijri_date}\n"
        f"• <b>التاريخ الميلادي:</b> {date_gregorian}\n"
        f"• <b>الوقت الحالي:</b> {time_now}\n\n"
        f"<b>اختر الخدمة التي تريدها من القائمة بالأسفل:</b>"
    )
    return info_message


# =========================
# 3. أوامر البداية والقائمة الرئيسية
# =========================
@bot.message_handler(commands=['start'])
def main_menu(message):
    log_new_user(message)
    
    # 🆕 جلب رسالة الترحيب والمعلومات الجديدة
    welcome_message = get_current_info()
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📖 القرآن الكريم", "✖ جدول الضرب", "📂 فك ضغط ZIP") 
    markup.add("🔗 اختصار رابط", "🎬 تحميل تيك توك", "📋 قائمة المهام")
    markup.add("🤖 اسأل ChatGPT", "📅 الفرق بين تاريخين", "🚗 التعرف على سيارة")
    markup.add("ℹ️ معلومات / ترحيب") # 🆕 إضافة زر المعلومات
    
    bot.send_message(
        message.chat.id,
        welcome_message,
        reply_markup=markup,
        parse_mode='HTML'
    )


# =========================
# 4. خدمة القرآن الكريم
# =========================
def send_quran_page(chat_id, num):
    """إرسال صورة لصفحة معينة من القرآن."""
    try:
        num = int(num)
        if not (1 <= num <= 604): 
            bot.send_message(chat_id, "❌ رقم الصفحة يجب أن يكون بين 1 و 604.")
            return

        url = f"https://quran.ksu.edu.sa/png_big/{num}.png"
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(
            types.InlineKeyboardButton(text=f"• صفحة {num} •", callback_data="couu"),
        )
        keyboard.row(
            types.InlineKeyboardButton(text="◀ صفحة السابقة", callback_data=f"quran|{num - 1}"),
            types.InlineKeyboardButton(text="صفحة التالية ▶", callback_data=f"quran|{num + 1}"),
        )
        bot.send_photo(chat_id, url, reply_markup=keyboard)
    except ValueError:
        bot.send_message(chat_id, "❌ يرجى إرسال رقم صفحة صحيح.")
    except Exception as e:
        bot.send_message(chat_id, f"حدث خطأ أثناء تحميل الصفحة: {e}")


# =========================
# 5. خدمة جدول الضرب
# =========================
def multiplication_table(n):
    """حساب جدول الضرب لرقم معين."""
    return "\n".join([f"{n} × {i} = {n*i}" for i in range(1, 11)])

# =========================
# 6. خدمة اختصار الروابط وتقييم البوت
# =========================
def shorten_link(url):
    """استخدام gdshortener لاختصار رابط."""
    s = gdshortener.ISGDShortener()
    return s.shorten(url)[0]

def handle_shortener(message):
    """معالج الخطوة الثانية لاختصار الرابط."""
    url = message.text.strip()
    if re.search(r"https?://[^\s]+", url):
        try:
            short = shorten_link(url)
            bot.reply_to(message, f"✅ تم اختصار الرابط:\n`{short}`\n\n⭐ قيّم البوت بإرسال رقم من 1 إلى 5", parse_mode="MARKDOWN")
            bot.register_next_step_handler(message, rate_bot)
        except Exception:
             bot.reply_to(message, "❌ حدث خطأ أثناء محاولة الاختصار. تأكد أن الرابط صحيح.")
    else:
        bot.reply_to(message, "❌ هذا ليس رابط صالح.")

def rate_bot(message):
    """معالج لتقييم البوت."""
    try:
        rating = int(message.text)
        if 1 <= rating <= 5:
            user_ratings[message.from_user.id] = rating
            username = message.from_user.username or message.from_user.first_name
            
            bot.send_message(
                CHANNEL_ID,
                f"⭐ تقييم جديد!\n- المستخدم: @{username} (ID: `{message.from_user.id}`)\n- التقييم: {rating}/5",
                parse_mode="HTML"
            )
            bot.reply_to(message, f"✅ شكراً لتقييمك {rating}⭐")
        else:
            bot.reply_to(message, "❌ أرسل رقم من 1 إلى 5 فقط.")
    except ValueError:
        bot.reply_to(message, "❌ أرسل رقم صالح.")


# =========================
# 7. خدمة تحميل تيك توك
# =========================
def download_tiktok(url):
    """جلب رابط تحميل فيديو تيك توك."""
    headers = {
        "referer": "https://lovetik.com/sa/video/",
        "origin": "https://lovetik.com",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    payload = {"query": url}
    r = requests.post("https://lovetik.com/api/ajax/search", headers=headers, data=payload).json()
    return r["links"][2]["a"]

def handle_tiktok(message):
    """معالج الخطوة الثانية لتحميل تيك توك."""
    try:
        vurl = download_tiktok(message.text.strip())
        caption = "✅ تم تحميل الفيديو بنجاح.\n\n🤍 حقوق البوت: @altaee_z\n🌐 موقعي: www.ali-Altaee.free.nf"
        bot.send_video(message.chat.id, vurl, caption=caption)
    except Exception:
        bot.reply_to(message, "- عذراً الرابط غير صالح أو لا يمكن تحميل الفيديو!")


# =========================
# 8. خدمة ChatGPT API
# =========================
def ask_gpt(question):
    """إرسال سؤال إلى ChatGPT."""
    r = requests.get(
        f"https://chatgpt.apinepdev.workers.dev/?question={requests.utils.quote(question)}"
    ).json()
    ans = r["answer"]
    ans = ans.replace("🔗 Join our community: [t.me/nepdevsz](https://t.me/nepdevsz)", "")
    return ans + "\n\n🤍 تلجرام :- @altaee_z\n🌐 موقعي : www.ali-Altaee.free.nf"

def handle_gpt(message):
    """معالج الخطوة الثانية لـ ChatGPT."""
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        answer = ask_gpt(message.text.strip())
        bot.reply_to(message, answer)
    except Exception:
        bot.reply_to(message, "❌ عذراً، لم أتمكن من الحصول على إجابة الآن. يرجى المحاولة لاحقاً.")

# =========================
# 9. خدمة التعرف على سيارة
# =========================
def recognize_car(info_url: str):
    """إرسال رابط الصورة إلى موقع carnet.ai والتعرّف على بيانات السيارة"""
    url = "https://carnet.ai/recognize-url"
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://carnet.ai',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/105.0.0.0 Mobile Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
    }
    r = requests.post(url, headers=headers, data=info_url)
    return r.json()
def handle_car_photo(message):
    """استقبال صورة المستخدم وإرسال معلومات السيارة"""
    if not message.photo:
        bot.reply_to(message, "❌ يرجى إرسال صورة وليس نصاً.")
        return

    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"

    result = recognize_car(file_url)
    if 'error' in result:
        bot.reply_to(message, "❌ لم أستطع التعرف على السيارة!")
        return

    carname = result['car']['make']
    carmodel = result['car']['model']
    years = result['car']['years']
    angle = result['angle']['name']
    color = result['color']['name']

    reply = (
        "✅ تم التعرف على السيارة:\n"
        f"• الشركة المصنعة: {carname}\n"
        f"• الموديل: {carmodel}\n"
        f"• سنة الإصدار: {years}\n"
        f"• اللون: {color}\n"
        f"• زاوية التصوير: {angle}\n\n"
        "🤍 حقوق التطوير: @altaee_z\n"
        "🌐 موقعي: www.ali-Altaee.free.nf"
    )
    bot.reply_to(message, reply)    


# =========================
# 10. دوال الفرق بين تاريخين
# =========================
def get_date_one(message):
    """يستلم التاريخ الأول ويطلب التاريخ الثاني."""
    try:
        date_one = datetime.strptime(message.text.strip(), DATE_FORMAT)
        user_data[message.from_user.id] = date_one
        
        response_message = (
            f"حسناً، تم استلام التاريخ الأول: `{message.text.strip()}` ✅\n"
            f"الآن أرسل **التاريخ الثاني** بنفس الصيغة."
        )
        bot.reply_to(message, response_message, parse_mode="Markdown")
        bot.register_next_step_handler(message, calculate_difference)
        
    except ValueError:
        error_message = (
            "عذراً! يبدو أن صيغة التاريخ غير صحيحة ❌. \n"
            "الرجاء إرسال التاريخ بالصيغة المطلوبة: `السنة الشهر اليوم`."
        )
        bot.reply_to(message, error_message)
        bot.register_next_step_handler(message, get_date_one)


def calculate_difference(message):
    """يستلم التاريخ الثاني ويحسب الفرق بين التاريخين."""
    user_id = message.from_user.id
    
    if user_id not in user_data or user_data[user_id] is None:
        bot.reply_to(message, "عذراً، لم أجد التاريخ الأول. يرجى بدء العملية مجدداً من القائمة الرئيسية.")
        return

    date_one = user_data[user_id]
    
    try:
        date_two = datetime.strptime(message.text.strip(), DATE_FORMAT)
        
        date_delta = date_two - date_one
        
        total_days = abs(date_delta.days)
        
        days = total_days
        weeks = days // 7
        
        months = abs((date_two.year - date_one.year) * 12 + (date_two.month - date_one.month))
        
        years = abs(date_two.year - date_one.year)

        result_message = f'''*📊 الفرق بين التاريخين المرسَلين: 📅*
---
*🗓️ مرّ على هذا التاريخ بـ:*
*▫️ الأيام:* `{days}` يوم
*▫️ الأسابيع:* `{weeks}` أسبوع
*▫️ الأشهر (تقريبي):* `{months}` شهر
*▫️ السنوات:* `{years}` سنة
'''
        
        bot.reply_to(message, result_message, parse_mode="Markdown")
        
        if user_id in user_data:
            del user_data[user_id]
        
    except ValueError:
        error_message = (
            "عذراً! يبدو أن صيغة التاريخ الثاني غير صحيحة ❌. \n"
            "الرجاء إرسال التاريخ بالصيغة المطلوبة: `السنة الشهر اليوم`."
        )
        bot.reply_to(message, error_message)
        bot.register_next_step_handler(message, calculate_difference)


# =========================
# 11. خدمة فك ضغط ملفات ZIP
# =========================

def send_zip_welcome(message):
    """يرسل رسالة ترحيبية خاصة بخدمة ZIP."""
    welcome_message = (
        'مرحبا عزيزي، أنا هنا لمساعدتك في فك ضغط ملفات **ZIP**.\n'
        'فقط قم بإرسال ملف **.zip** وسأقوم بفك ضغطه وإرسال محتوياته إليك.'
    )
    bot.reply_to(message, welcome_message, reply_markup=channel_keyboard, parse_mode='Markdown')

@bot.message_handler(content_types=['document'])
def handle_document(message):
    """معالجة المستندات المرسلة والتحقق مما إذا كانت ملفات ZIP لفك ضغطها."""
    # تأكد أن الرسالة ليست جزءاً من عملية إضافة مهمة جارية
    if message.from_user.id in adding_task_state and adding_task_state[message.from_user.id]:
        return # تجاهل الملف إذا كان المستخدم في وضع إضافة مهمة

    if message.document.file_name and message.document.file_name.lower().endswith('.zip'):
        msg_waiting = bot.reply_to(message, "جاري فحص الملف وفك الضغط...")
        
        try:
            file_info = bot.get_file(message.document.file_id)
            dow = bot.download_file(file_info.file_path)
            
            with zipfile.ZipFile(BytesIO(dow)) as zip_ref:
                file_names = [f for f in zip_ref.namelist() if not f.endswith('/')]
                
                if not file_names:
                    bot.edit_message_text("❌ الملف لا يحتوي على ملفات قابلة للإرسال (قد يكون مجلدات فارغة).", message.chat.id, msg_waiting.message_id)
                    return
                
                for file_name in file_names:
                    with zip_ref.open(file_name) as file_in_zip:
                        bot.send_document(
                            message.chat.id,
                            file_in_zip,
                            visible_file_name=file_name
                        )
            
            bot.edit_message_text("✅ تم فك ضغط وإرسال جميع الملفات بنجاح.", message.chat.id, msg_waiting.message_id)

        except zipfile.BadZipFile:
            bot.edit_message_text("❌ حدث خطأ: الملف المُرسَل ليس ملف ZIP صالح أو تالف.", message.chat.id, msg_waiting.message_id)
        except Exception as e:
            print(f"حدث خطأ غير متوقع: {e}")
            bot.edit_message_text("❌ حدث خطأ أثناء المعالجة. يرجى المحاولة مرة أخرى.", message.chat.id, msg_waiting.message_id)
            
    else:
        pass


# =========================
# 12. دوال وإعدادات قائمة المهام (TODO List)
# =========================

# --- مساعدات لحفظ/قراءة البيانات ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with LOCK:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}

def save_data(data):
    tmp = DATA_FILE + ".tmp"
    with LOCK:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DATA_FILE)

def get_user_tasks(user_id):
    data = load_data()
    return data.get(str(user_id), [])

def set_user_tasks(user_id, tasks):
    data = load_data()
    data[str(user_id)] = tasks
    save_data(data)

# --- أدوات مساعدة لواجهة المستخدم ---
def tasks_to_message(tasks):
    if not tasks:
        return "قائمة المهام فارغة."
    lines = ["<b>📋 قائمة مهامك:</b>\n"]
    for i, t in enumerate(tasks, start=1):
        status = "✅" if t.get("done") else "◻️"
        text = t.get("text", "")
        lines.append(f"<code>{i}</code>. {status} {text}")
    return "\n".join(lines)

def make_task_list_markup(user_id):
    """ينشئ الأزرار المضمنة للمهام الفردية."""
    tasks = get_user_tasks(user_id)
    markup = InlineKeyboardMarkup()
    for idx, task in enumerate(tasks):
        # زر واحد لكل مهمة يجمع بين التبديل والحذف
        done_text = "✅ مكتمل" if task.get("done") else "✔️ إنجاز"
        markup.row(
            InlineKeyboardButton(done_text, callback_data=f"toggle|{idx}"),
            InlineKeyboardButton("🗑️ حذف", callback_data=f"delete|{idx}")
        )
    return markup

def make_todo_main_markup(user_id):
    """ينشئ الأزرار الرئيسية لخدمة المهام (إضافة، مسح الكل)."""
    markup = InlineKeyboardMarkup()
    tasks = get_user_tasks(user_id)
    
    # دائماً زر إضافة
    markup.row(InlineKeyboardButton("➕ إضافة مهمة جديدة", callback_data="add_new_task"))
    
    # زر مسح الكل يظهر فقط إذا كانت هناك مهام
    if tasks:
        markup.row(InlineKeyboardButton("❌ مسح كل المهام", callback_data="clear_all"))
    
    # إضافة زر لعرض القائمة بشكل منفصل (إذا كان المستخدم يضغط على الزر الرئيسي)
    if tasks:
        markup.row(InlineKeyboardButton("عرض قائمة المهام الحالية", callback_data="view_list"))
        
    return markup

def send_task_menu(chat_id, user_id, message_id=None, text=None):
    """يرسل رسالة قائمة المهام الرئيسية مع الأزرار."""
    tasks = get_user_tasks(user_id)
    
    if text is None:
        text = tasks_to_message(tasks) + "\n\n<b>ماذا تريد أن تفعل الآن؟</b>"
        
    markup = make_todo_main_markup(user_id)

    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode='HTML')
        except Exception:
            # إذا فشل التحرير (لأن الرسالة قديمة مثلاً)، أرسل رسالة جديدة
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')


def handle_new_task_input(message):
    """يتعامل مع النص المرسل لإضافة مهمة."""
    user_id = message.from_user.id
    task_text = message.text.strip()
    
    # إيقاف حالة الإضافة
    adding_task_state[user_id] = False

    if not task_text:
        bot.reply_to(message, "❌ لم يتم إدخال نص للمهمة. يرجى البدء من جديد عبر القائمة الرئيسية.")
        return

    tasks = get_user_tasks(user_id)
    tasks.append({"text": task_text, "done": False, "created_at": int(time.time())})
    set_user_tasks(user_id, tasks)
    
    # إرسال قائمة المهام المحدثة
    text = f"✅ تم إضافة المهمة: <b>{task_text}</b>\n\n"
    text += tasks_to_message(tasks) + "\n\n<b>ماذا تريد أن تفعل الآن؟</b>"

    # نرسل القائمة المحدثة (كمحادثة جديدة)
    send_task_menu(message.chat.id, user_id, text=text)

# =========================
# 13. معالج جميع الرسائل النصية
# =========================
@bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'))
def handle_all(message):
    text = message.text.strip()
    user_id = message.from_user.id
    
    # --- معالج خاص لمدخل مهمة جديدة ---
    if user_id in adding_task_state and adding_task_state[user_id]:
        handle_new_task_input(message)
        return

    # --- معالجات الخدمات الرئيسية ---
    if text == "📖 القرآن الكريم":
        bot.reply_to(message, "أرسل رقم الصفحة:")
        bot.register_next_step_handler(message, lambda m: send_quran_page(m.chat.id, m.text)) 
        return
        
    # 🆕 معالج زر المعلومات/الترحيب
    if text == "ℹ️ معلومات / ترحيب":
        info_message = get_current_info()
        bot.reply_to(message, info_message, parse_mode='HTML')
        return

    if text == "📂 فك ضغط ZIP":
        send_zip_welcome(message)
        return

    if text == "📅 الفرق بين تاريخين":
        welcome_message = (
            "مرحباً بك! أنا بوت لحساب **الفرق بين تاريخين** 📅.\n"
            "أرسل **التاريخ الأول** بالصيغة التالية:\n"
            "`السنة الشهر اليوم`\n"
            "مثال: `2023 1 1`"
        )
        bot.reply_to(message, welcome_message, parse_mode="Markdown")
        bot.register_next_step_handler(message, get_date_one)
        return

    if text == "✖ جدول الضرب":
        bot.reply_to(message, "أرسل الرقم لعرض جدول ضربه:")
        def handle_multiplication(m):
            try:
                n = int(m.text.strip())
                bot.reply_to(m, multiplication_table(n))
            except ValueError:
                bot.reply_to(m, "❌ يرجى إرسال رقم صالح فقط.")
        
        bot.register_next_step_handler(message, handle_multiplication)
        return

    if text == "🔗 اختصار رابط":
        bot.reply_to(message, "أرسل الرابط لاختصاره:")
        bot.register_next_step_handler(message, handle_shortener)
        return

    if text == "🎬 تحميل تيك توك":
        bot.reply_to(message, "أرسل رابط فيديو تيك توك:")
        bot.register_next_step_handler(message, handle_tiktok)
        return

    if text == "🚗 التعرف على سيارة":
    	bot.reply_to(message, "📷 أرسل صورة السيارة المراد التعرف عليها:")
    	bot.register_next_step_handler(message, handle_car_photo)
    	return
    
    if text == "🤖 اسأل ChatGPT":
        bot.reply_to(message, "أرسل سؤالك:")
        bot.register_next_step_handler(message, handle_gpt)
        return

    # --- معالج قائمة المهام (TODO List) من الزر الرئيسي ---
    if text == "📋 قائمة المهام":
        send_task_menu(message.chat.id, user_id)
        return

    # --- ردود ثابتة ---
    if text in ["منو مطورك", "مطورك", "منو المطور"]:
        bot.reply_to(message, "🤍 تلجرام :- @altaee_z\n🌐 موقعي : www.ali-Altaee.free.nf")
        return

    # --- رسالة افتراضية ---
    bot.reply_to(message, "عذراً، لم أفهم طلبك. يرجى اختيار خدمة من القائمة الرئيسية.")


# =========================
# 14. معالج الـ CallbackQuery الموحد
# =========================
@bot.callback_query_handler(func=lambda call: True)
def unified_callback_handler(call):
    data = call.data
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    # ------------------
    # معالج القرآن الكريم
    # ------------------
    if data == 'couu':
        bot.answer_callback_query(call.id, text='هذا زر يعرض فيه العدد فقط')
        return
    elif data.startswith('quran|'):
        try:
            num = int(data.split('|')[1])
            if not (1 <= num <= 604):
                bot.answer_callback_query(call.id, text='وصلت إلى بداية أو نهاية المصحف.')
                return

            url = f"https://quran.ksu.edu.sa/png_big/{num}.png"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton(text=f"• صفحة {num} •", callback_data="couu"))
            keyboard.row(
                types.InlineKeyboardButton(text="◀ صفحة السابقة", callback_data=f"quran|{num - 1}"),
                types.InlineKeyboardButton(text="صفحة التالية ▶", callback_data=f"quran|{num + 1}"),
            )
            bot.edit_message_media(
                types.InputMediaPhoto(url),
                chat_id,
                message_id,
                reply_markup=keyboard
            )
        except Exception:
            bot.answer_callback_query(call.id, text='لا يمكن التبديل لهذه الصفحة.')
            
    # -----------------------
    # معالج قائمة المهام (TODO)
    # -----------------------
    elif data == "add_new_task":
        # تعيين حالة المستخدم للإضافة
        adding_task_state[user_id] = True
        
        # إزالة الأزرار وإرسال رسالة تطلب نص المهمة
        text = "📝 أرسل الآن **نص المهمة** التي تريد إضافتها (مثلاً: شراء الخبز)."
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=None, parse_mode='Markdown')
            bot.answer_callback_query(call.id, "أرسل نص المهمة الآن.")
        except Exception:
            bot.send_message(chat_id, text, reply_markup=None, parse_mode='Markdown')
            bot.answer_callback_query(call.id, "أرسل نص المهمة الآن.")

    elif data == "view_list":
        # عرض قائمة المهام مع أزرار التحكم الفردية
        tasks = get_user_tasks(user_id)
        if not tasks:
            bot.answer_callback_query(call.id, "القائمة فارغة، استخدم 'إضافة مهمة'.")
            send_task_menu(chat_id, user_id, message_id)
            return

        text = "<b>إدارة المهام الفردية:</b>"
        text += tasks_to_message(tasks)
        markup = make_task_list_markup(user_id)
        
        # إضافة زر للعودة للقائمة الرئيسية للمهام
        markup.row(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="todo_main_menu"))
        
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode='HTML')
            bot.answer_callback_query(call.id, "تم عرض المهام")
        except Exception:
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')
            bot.answer_callback_query(call.id, "تم عرض المهام")
            
    elif data == "todo_main_menu":
        # العودة للقائمة الرئيسية للمهام
        send_task_menu(chat_id, user_id, message_id)
        bot.answer_callback_query(call.id, "تم العودة للقائمة الرئيسية")

    elif data.startswith("toggle|"):
        idx = int(data.split("|",1)[1])
        tasks = get_user_tasks(user_id)
        if 0 <= idx < len(tasks):
            tasks[idx]['done'] = not tasks[idx].get('done', False)
            set_user_tasks(user_id, tasks)
            bot.answer_callback_query(call.id, "تم تحديث حالة المهمة")
            
            # تحديث عرض المهام الفردية
            text = "<b>إدارة المهام الفردية:</b>"
            text += tasks_to_message(tasks)
            markup = make_task_list_markup(user_id)
            markup.row(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="todo_main_menu"))

            try:
                bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode='HTML')
            except Exception:
                 # في حالة التبديل من قائمة المهام الرئيسية (قد يحدث خطأ تحرير)
                send_task_menu(chat_id, user_id, text="✅ تم تحديث حالة المهمة بنجاح.")
        else:
            bot.answer_callback_query(call.id, "المهمة غير موجودة")
            
    elif data.startswith("delete|"):
        idx = int(data.split("|",1)[1])
        tasks = get_user_tasks(user_id)
        if 0 <= idx < len(tasks):
            removed_task = tasks.pop(idx).get('text')
            set_user_tasks(user_id, tasks)
            bot.answer_callback_query(call.id, "تم حذف المهمة")
            
            # تحديث عرض المهام الفردية
            text = "<b>إدارة المهام الفردية:</b>"
            text += tasks_to_message(tasks)
            markup = make_task_list_markup(user_id)
            markup.row(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="todo_main_menu"))
            
            if not tasks:
                 # إذا أصبحت القائمة فارغة، نرجع للقائمة الرئيسية
                send_task_menu(chat_id, user_id, message_id)
            else:
                try:
                    bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode='HTML')
                except Exception:
                     # في حالة الحذف من قائمة المهام الرئيسية
                    send_task_menu(chat_id, user_id, text=f"🗑️ تم حذف: <b>{removed_task}</b>")
        else:
            bot.answer_callback_query(call.id, "المهمة غير موجودة")
            
    elif data == "clear_all":
        set_user_tasks(user_id, [])
        bot.answer_callback_query(call.id, "تم مسح كل المهام")
        send_task_menu(chat_id, user_id, message_id, text="تم مسح كل المهام. 🎉\n\n<b>ماذا تريد أن تفعل الآن؟</b>")


# =========================
# 15. تشغيل البوت
# =========================
if __name__ == '__main__':
    print("البوت بدأ العمل...")
    bot.infinity_polling()
