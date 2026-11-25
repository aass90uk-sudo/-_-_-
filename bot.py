import os
import time
import random
import schedule
import requests
from google import genai
from google.genai import types

# جلب المتغيرات من إعدادات Railway
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID") # ضع في Railway القيمة: @Athar_Dz_Islamicc
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# تهيئة عميل Gemini
client = genai.Client(api_key=GEMINI_API_KEY)

# قائمة أفكار متنوعة لضمان عدم تكرار المواضيع
TOPICS = [
    "الفتور الصامت بين الزوجين وكيفية كسره بذكاء",
    "الفرق بين احتياج الرجل للاحترام واحتياج المرأة للأمان العاطفي",
    "التفريغ العصبي وبكاء المرأة المفاجئ دون سبب واضح",
    "تأثير الضغوط اليومية والتوتر على التناغم الجسدي والنفسي",
    "خطورة المجاملة الزائدة والكتمان في بداية الحياة الزوجية",
    "كيف يقتل تدخل الأهل والمقارنات خصوصية العروسين",
    "لغة الجسد واللمسة الدافئة كبديل عن الصمت وقت الخلاف",
    "الاستعداد النفسي والجسدي وأهمية التمهيد العاطفي في العلاقة",
    "سوء الفهم في طريقة تعبير كل طرف عن حبه واهتمامه",
    "كيف نحمي العلاقة الزوجية من الروتين والملل بعد سنوات من الزواج"
]

recent_topics = []

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

الشروط:
- استخدم فقرات قصيرة ومريحة للعين.
- استخدم رموز تعبيرية هادئة مثل (🤍✨، ⚠️💔).
- تجنب تماماً اللغة الأكاديمية الجافة أو أي ألفاظ خادشة للحياء.
- لا تكتب أي مقدمات، ابدأ بالعنوان مباشرة.
"""

# الخاتمة الثابتة بالرابط الصحيح لقناتك قبل السؤال التفاعلي
CHANNEL_FOOTER = (
    '\n<a href="https://t.me/Athar_Dz_Islamicc">قناة ريحانة المغرب 💌</a>\n'
    'صدقة جارية لأم عقيدة وحمزة غ ـفر الله لها🖤\n'
)

def generate_post():
    available_topics = [t for t in TOPICS if t not in recent_topics]
    if not available_topics:
        recent_topics.clear()
        available_topics = TOPICS
        
    chosen_topic = random.choice(available_topics)
    recent_topics.append(chosen_topic)
    if len(recent_topics) > 5:
        recent_topics.pop(0)

    prompt = f"اكتب منشوراً عميقاً ومؤثراً حول الموضوع التالي: {chosen_topic}"
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.8,
        )
    )
    
    raw_text = response.text.strip()
    
    # استبدال العلامة بالخاتمة الثابتة قبل السؤال التفاعلي
    if "[FOOTER]" in raw_text:
        final_post = raw_text.replace("[FOOTER]", CHANNEL_FOOTER)
    else:
        final_post = f"{raw_text}\n{CHANNEL_FOOTER}"
        
    return final_post

def send_to_telegram(text):
    url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("✅ تم نشر المنشور بنجاح!")
    else:
        print(f"❌ خطأ في النشر: {response.text}")

def job():
    print("⏳ جاري توليد منشور جديد...")
    try:
        post_content = generate_post()
        send_to_telegram(post_content)
    except Exception as e:
        print(f"⚠️ حدث خطأ: {e}")

if __name__ == "__main__":
    print("🚀 البوت بدأ العمل بنجاح على Railway...")
    
    # نشر منشور تجريبي فوري عند تشغيل البوت
    job()
    
    # جدولة النشر اليومي (17:00 UTC تعادل الساعة 8:00 مساءً بتوقيت مكة المكرمة واليمن)
    schedule.every().day.at("17:00").do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(30)
