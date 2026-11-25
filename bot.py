import json
import os
import time

import requests
import schedule
from groq import Groq

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
CHANNEL_ID = os.environ.get("CHANNEL_ID", "").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()

if not TELEGRAM_TOKEN:
    raise ValueError("المتغير TELEGRAM_TOKEN غير موجود")
if not CHANNEL_ID:
    raise ValueError("المتغير CHANNEL_ID غير موجود")
if not GROQ_API_KEY:
    raise ValueError("المتغير GROQ_API_KEY غير موجود")

if not CHANNEL_ID.startswith("@") and not CHANNEL_ID.startswith("-100"):
    CHANNEL_ID = f"@{CHANNEL_ID}"

client = Groq(api_key=GROQ_API_KEY)

DATA_DIR = "/data" if os.path.exists("/data") else "."
HISTORY_FILE = os.path.join(DATA_DIR, "published_history.json")

MODELS_TO_USE = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]

# مواعيد النشر اليومية (أربعة منشورات)
POST_TIMES = [
    "09:00",
    "13:00",
    "17:00",
    "21:00",
]

SYSTEM_PROMPT = """
أنت كاتب محتوى متخصص في الوعي الزوجي، الصحة النفسية والجسدية في الزواج، والعلاقات الأسرية.
اكتب منشوراً لقناة تيليجرام باللهجة السعودية أو الخليجية البيضاء، بأسلوب راقٍ ومحافظ وعلمي ودافئ.
التزم بهذا الهيكل:
1. عنوان جذاب ومباشر يلامس مشكلة حقيقية بين الزوجين.
اجعل العنوان عريضاً بهذا الشكل:
**العنوان**
2. اكسر مفهوماً خاطئاً شائعاً بين الأزواج بأسلوب لطيف.
3. قدم تفسيراً نفسياً أو علمياً مبسطاً بلغة محترمة وواضحة.
4. اكتب الحل الذهبي في سطرين بأسلوب دافئ وحنون.
ثم اكتب هذا الرمز في سطر منفصل تماماً:
[FOOTER]
5. بعد الرمز مباشرة، اكتب سؤالاً تفاعلياً قصيراً يفتح باب التفكير أو النقاش.
الشروط:
- لا تكتب أي مقدمة قبل العنوان.
- اجعل الموضوع والفكرة والزاوية مختلفة عن العناوين السابقة.
- استخدم فقرات قصيرة ومريحة للعين.
- تجنب اللغة الأكاديمية الجافة.
- تجنب أي ألفاظ خادشة للحياء.
- لا تكرر نفس الفكرة أو العنوان السابق.
"""

CHANNEL_FOOTER = """
[قناة ريحانة المغرب](https://t.me/Athar_Dz_Islamicc)
صدقة جارية لأم عقيدة وحمزة، غفر الله لها
"""


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except Exception as error:
        print(f"تعذر تحميل الذاكرة السابقة: {error}")
        return []


def save_to_history(title):
    history = load_history()
    history.append(title)
    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=2)


def extract_title(post_text):
    first_line = post_text.splitlines()[0] if post_text.splitlines() else "بدون عنوان"
    return (
        first_line
        .replace("**", "")
        .replace("**", "")
        .strip()
    )


def generate_unique_post():
    history = load_history()
    if history:
        past_titles = "\n".join(f"- {title}" for title in history)
        prompt = f"""
ابتكر منشوراً نفسياً أو زوجياً جديداً كلياً، عميقاً ومختلفاً تماماً عن المواضيع السابقة.
هذه قائمة بالعناوين التي تم نشرها سابقاً:
{past_titles}
ممنوع تكرار هذه العناوين أو الاقتراب من نفس أفكارها.
اكتب المنشور الجديد الآن.
"""
    else:
        prompt = """
ابتكر أول منشور نفسي أو زوجي عميق ومؤثر للقناة، واكتبه الآن.
"""

    last_error = None
    for model_name in MODELS_TO_USE:
        try:
            print(f"جاري التوليد باستخدام النموذج: {model_name}")
            completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                model=model_name,
                temperature=0.9,
            )

            if not completion.choices:
                raise ValueError("لم يعُد النموذج أي نص")

            generated_text = completion.choices[0].message.content
            if not generated_text:
                raise ValueError("النص الناتج فارغ")

            generated_text = generated_text.strip()
            title = extract_title(generated_text)

            if "[FOOTER]" in generated_text:
                final_post = generated_text.replace(
                    "[FOOTER]",
                    CHANNEL_FOOTER.strip(),
                    1,
                )
            else:
                final_post = f"{generated_text}\n\n{CHANNEL_FOOTER.strip()}"

            return final_post, title
        except Exception as error:
            last_error = error
            print(f"تعذر استخدام {model_name}: {str(error)[:200]}")

    raise RuntimeError(f"فشلت جميع نماذج Groq: {last_error}")


def call_telegram(method, payload):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    try:
        response = requests.post(
            url,
            json=payload,
            timeout=30,
        )
        try:
            response_data = response.json()
        except ValueError:
            response_data = {
                "ok": False,
                "description": response.text,
            }
        if response.status_code == 200 and response_data.get("ok") is True:
            return True, response_data
        return False, response_data
    except requests.RequestException as error:
        return False, {
            "ok": False,
            "description": f"خطأ في الاتصال بتيليجرام: {error}",
        }


def send_to_telegram(text):
    return call_telegram(
        "sendMessage",
        {
            "chat_id": CHANNEL_ID,
            "text": text,
            "disable_web_page_preview": True,
        },
    )


def pin_message(message_id):
    return call_telegram(
        "pinChatMessage",
        {
            "chat_id": CHANNEL_ID,
            "message_id": message_id,
            "disable_notification": True,
        },
    )


def build_schedule_message():
    times_lines = "\n".join(
        f"‏{index}. 🕰 {post_time}" for index, post_time in enumerate(POST_TIMES, start=1)
    )
    return (
        "﴿ وَمِنْ آيَاتِهِ أَنْ خَلَقَ لَكُم مِّنْ أَنفُسِكُمْ أَزْوَاجًا لِّتَسْكُنُوا إِلَيْهَا "
        "وَجَعَلَ بَيْنَكُم مَّوَدَّةً وَرَحْمَةً ﴾\n\n"
        "🌷أهلاً بكم في قناة رَيْحَانَةُ المَغْرِبِ الأَوْسَطِ 🌿\n\n"
        "هنا نزرع بذور الطمأنينة في بيوتكم...\n"
        "مساحة هادئة نتحدّث فيها عن الوعي الزوجي، وعن النفس التي تسكن بينكم، وعن القلوب التي تتعب "
        "حتى يبقى بيتكم هادئاً دافئاً.\n\n"
        "حكاياتنا كلها عن شيء واحد: كيف تبقى المودة حيّة، وكيف يبقى البيت آواةً للقلب، "
        "بلغة بيضاء راقية، وقلبٍ يفهمكم دون أن يحاكمكم.\n\n"
        " ننشر لكم كل يوم في هذه التواقيت:\n"
        f"{times_lines}\n\n"
        "اجعلوا لنا من قلوبكم نصباً وشاركونا في التعليقات، فلربما كانت كلمتكم عوناً لبيتٍ آخر.\n\n"
        "صدقة جارية لأم عقيدة وحمزة، غفر الله لها وأسكنها فسيح جناته 🤍"
    )


def send_schedule_and_pin():
    print("جاري إرسال رسالة الجدولة والتثبيت")
    success, response_info = send_to_telegram(build_schedule_message())
    if not success:
        print(f"فشل إرسال رسالة الجدولة: {response_info}")
        return
    message_id = response_info.get("result", {}).get("message_id")
    if message_id is None:
        print("تعذر الحصول على رقم الرسالة لتثبيتها")
        return
    pin_success, pin_info = pin_message(message_id)
    if pin_success:
        print("تم تثبيت رسالة الجدولة بنجاح")
    else:
        print(f"فشل تثبيت الرسالة: {pin_info}")


def job():
    print("جاري إنشاء منشور جديد")
    try:
        post_content, new_title = generate_unique_post()
        success, response_info = send_to_telegram(post_content)
        if success:
            save_to_history(new_title)
            print(f"تم النشر بنجاح: {new_title}")
        else:
            print(f"فشل النشر في تيليجرام: {response_info}")
    except Exception as error:
        print(f"حدث خطأ أثناء تنفيذ المهمة: {error}")


if __name__ == "__main__":
    print("البوت بدأ العمل")
    send_schedule_and_pin()
    for post_time in POST_TIMES:
        schedule.every().day.at(post_time).do(job)
    while True:
        schedule.run_pending()
        time.sleep(30)
