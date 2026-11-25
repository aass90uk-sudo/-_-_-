import os
import json
import time
import schedule
import requests
from google import genai
from google.genai import types

# جلب المتغيرات من إعدادات Railway
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID") # @Athar_Dz_Islamicc
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

# مسار ملف الذاكرة الدائمة المربوط بـ Volume
DATA_DIR = "/data" if os.path.exists("/data") else "."
HISTORY_FILE = os.path.join(DATA_DIR, "published_history.json")

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
    first_line = post_text.split("\n")
    clean_title = first_line.replace("<b>", "").replace("</b>", "").strip()
    return clean_title

def get_available_flash_models():
    """جلب قائمة نماذج Flash المتاحة فعلياً في مفتاح API الخاص بك"""
    models = []
    try:
        for m in client.models.list():
            name = m.name.replace("models/", "")
            if "flash" in name.lower() and "image" not in name.lower() and "audio" not in name.lower():
                models.append(name)
    except Exception as e:
        print(f"⚠️ تعذر جلب قائمة النماذج: {e}")
    
    # ترتيب النماذج بحيث يجرب الأحدث أولاً
    models.sort(reverse=True)
    return models if models else ["gemini-3.8-flash"]

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

    available_models = get_available_flash_models()
    print(f"📋 النماذج المتاحة في حسابك: {available_models}")

    last_error = None
    for attempt in range(4):
        for model_name in available_models:
            try:
                print(f"🔄 محاولة التوليد باستخدام {model_name}...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.95,
                    )
                )
                raw_text = response.text.strip()
                new_title = extract_title(raw_text)
                
                if "[FOOTER]" in raw_text:
                    final_post = raw_text.replace("[FOOTER]", CHANNEL_FOOTER)
                else:
                    final_post = f"{raw_text}\n{CHANNEL_FOOTER}"
                    
                return final_post, new_title
                
            except Exception as e:
                last_error = e
                print(f"⚠️ خطأ مع {model_name}: {str(e)[:120]}")
                time.sleep(2)
                
        print("⏳ سننتظر 20 ثانية ونعيد المحاولة...")
        time.sleep(20)
        
    raise Exception(f"فشلت جميع المحاولات: {last_error}")

def send_to_telegram(text):
    url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    response = requests.post(url, json=payload)
    return response.status_code == 200, response.text

def job():
    print("⏳ جاري ابتكار منشور جديد غير مكرر...")
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
    
    # نشر منشور تجريبي عند التشغيل
    job()
    
    # جدولة النشر اليومي (17:00 UTC تعادل 8:00 مساءً بتوقيت مكة المكرمة واليمن)
    schedule.every().day.at("17:00").do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(30)
