import os
import json
import time
import schedule
import requests
from groq import Groq

# جلب المتغيرات من إعدادات Railway
TELEGRAM_TOKEN = str(os.environ.get("TELEGRAM_TOKEN", "")).strip()
CHANNEL_ID = str(os.environ.get("CHANNEL_ID", "")).strip()
GROQ_API_KEY = str(os.environ.get("GROQ_API_KEY", "")).strip()

client = Groq(api_key=GROQ_API_KEY)

# مسار ملف الذاكرة الدائمة المربوط بـ Volume
DATA_DIR = "/data" if os.path.exists("/data") else "."
HISTORY_FILE = os.path.join(DATA_DIR, "published_history.json")

# النماذج القوية والمناسبة للنصوص العربية الطويلة بالترتيب
MODELS_TO_USE = [
    "openai/gpt-oss-120b",
    "allam-2-7b",
    "openai/gpt-oss-20b"
]

SYSTEM_PROMPT = """
أنت كاتب محتوى متخصص في (الوعي الزوجي، الصحة النفسية والجسدية في الزواج، والعلاقات الأسرية) بأسلوب راقٍ، محافظ، علمي، ودافئ.
اكتب منشوراً لقناة تيليجرام باللهجة السعودية/الخليجية البيضاء القريبة من القلب.

التزم بالهيكل التالي بدقة شديدة:
1. عنوان جذاب ومباشر يلامس مشكلة حقيقية بين الزوجين (اجعله عريضاً هكذا: <b>العنوان</b>).
2. كسر مفهوم خاطئ شائع بين الأزواج بأسلوب لطيف.
3. التفسير النفسي أو العلمي المبسط للمشكلة بلغة محترمة وواضحة.
4. الحل الذهبي في سطرين بأسلوب دافئ وحنون.

ثم ضع الرمز التالي في سطر منفصل تماماً:
[FOOTER]

5. بعد الرمز مباشرة، اكتب سؤالاً تفاعلياً قصيراً في النهاية يفتح باب التفكير أو النقاش مع رمز تعبيري مناسب مثل (👇💬).

الشروط الصارمة:
- يجب أن يكون الموضوع والفكرة والزاوية جديدة ومبتكرة كلياً ومختلفة تماماً عن أي عنوان سابق.
- استخدم فقرات قصيرة ومريحة للعين، ورموز تعبيرية هادئة مثل (🤍✨، ⚠️💔).
- تجنب تماماً اللغة الأكاديمية الجافة أو أي ألفاظ خادشة للحياء.
- لا تكتب أي مقدمات، ابدأ بالعنوان مباشرة.
"""

CHANNEL_FOOTER = (
    '\n<a href="https://t.me">قناة ريحانة المغرب 💌</a>\n'
    'صدقة جارية لأم عقيدة وحمزة غ ـفر الله لها🖤\n'
)

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_to_history(title):
    history = load_history()
    history.append(title)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def extract_title(post_text):
    lines = post_text.split("\n")
    first_line = next(iter(lines), "بدون عنوان")
    clean_title = first_line.replace("<b>", "").replace("</b>", "").strip()
    return clean_title

def generate_unique_post():
    history = load_history()
    
    if history:
        past_titles_text = "\n".join([f"- {t}" for t in history])
        prompt = (
            "ابتكر موضوعاً نفسياً أو زوجياً جديداً كلياً، عميقاً، ومختلفاً تماماً عن المواضيع السابقة.\n"
            "قائمة العناوين والمواضيع التي تم نشرها سابقاً (ممنوع تكرارها أو الاقتراب من نفس فكرتها نهائياً):\n"
            f"{past_titles_text}\n\n"
            "اكتب الآن المنشور الجديد كلياً:"
        )
    else:
        prompt = "ابتكر موضوعاً نفسياً أو زوجياً عميقاً ومؤثراً لأول منشور في القناة، واكتبه الآن:"

    last_error = None
    for model_name in MODELS_TO_USE:
        try:
            print(f"🔄 جاري التوليد باستخدام {model_name}...")
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                model=model_name,
                temperature=0.9,
            )
            first_choice = next(iter(chat_completion.choices))
            raw_text = first_choice.message.content.strip()
            new_title = extract_title(raw_text)
            
            if "[FOOTER]" in raw_text:
                final_post = raw_text.replace("[FOOTER]", CHANNEL_FOOTER)
            else:
                final_post = f"{raw_text}\n{CHANNEL_FOOTER}"
                
            return final_post, new_title
        except Exception as e:
            last_error = e
            print(f"⚠️ تخطي {model_name}: {str(e)[:100]}")
            continue

    raise Exception(f"فشلت جميع النماذج: {last_error}")

def send_to_telegram(text):
    url = "https://telegram.org" + TELEGRAM_TOKEN + "/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    response = requests.post(url, json=payload)
    return response.status_code == 200, response.text

def job():
    print("⏳ جاري ابتكار منشور جديد غير مكرر عبر Groq...")
    try:
        post_content, new_title = generate_unique_post()
        success, response_info = send_to_telegram(post_content)
        if success:
            save_to_history(new_title)
            print(f"✅ تم النشر بنجاح وحفظ العنوان في الذاكرة الدائمة: {new_title}")
        else:
            print(f"❌ فشل النشر في تيليجرام: {response_info}")
    except Exception as e:
        print(f"⚠️ حدث خطأ: {e}")

if __name__ == "__main__":
    print("🚀 البوت بدأ العمل بذاكرة دائمة ومواضيع متجددة...")
    
    # نشر منشور تجريبي فوري عند التشغيل
    job()
    
    # جدولة النشر اليومي (17:00 UTC تعادل 8:00 مساءً بتوقيت مكة المكرمة واليمن)
    schedule.every().day.at("17:00").do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(30)
