import os
import certifi
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI
from pymongo import MongoClient
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

# --- CONFIGURATION ---
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)

# --- DATABASE CONNECTION (FORCED) ---
# ⚠️ ACTION REQUIRED: Paste your teammate's long link inside the quotes below!
uri = "mongodb+srv://nikhilarambothula_db_user:CruzAid2026@cluster0.4dsz38r.mongodb.net/?appName=Cluster0"

try:
    # We use the 'uri' variable directly to bypass environment issues
    mongo_client = MongoClient(uri, tlsCAFile=certifi.where())
    db = mongo_client["CruzAidDB"]
    collection = db["resources"]
    print("✅ Connected to MongoDB Cloud!")
except Exception as e:
    print(f"❌ Database Error: {e}")
    collection = None


# --- AI FUNCTION ---
def ask_gemini(user_text):
    try:
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "CruzAid Hackathon",
            },
            model="google/gemini-2.5-flash-lite",
            messages=[
                {
                    "role": "user",
                    "content": f"""
                    You are a medical triage sorter.
                    Input: "{user_text}"

                    Rules:
                    - If mentions tooth, gum, mouth -> return 'dental'
                    - If mentions fever, flu, cold, headache -> return 'student'
                    - If mentions blood, broken, dying, breathing -> return 'emergency'

                    Return ONLY the single category word.
                    """
                }
            ]
        )
        return completion.choices[0].message.content.strip().lower()
    except Exception as e:
        print(f"AI Error: {e}")
        return "general"


# --- THE SERVER ---
@app.route("/sms", methods=['POST'])
def sms_reply():
    user_text = request.form.get('Body')

    # 1. Ask AI for Category
    category = ask_gemini(user_text)
    print(f"🧠 AI Category: {category}")

    # 2. Search MongoDB
    response_msg = ""

    if collection is not None:
        try:
            # Look for a document where 'tags' includes the category
            result = collection.find_one({"tags": category})

            if result:
                response_msg = f"CruzAid: Based on '{category}', we recommend: {result['name']}. Call: {result['phone']} ({result.get('address', 'Santa Cruz')})"
            else:
                # Database connected, but no match found
                response_msg = f"CruzAid: Based on '{category}', please contact UCSC Student Health at 831-459-2211."
        except Exception as e:
            print(f"⚠️ Search Error: {e}")
            response_msg = f"CruzAid: Based on '{category}', please contact UCSC Student Health at 831-459-2211."
    else:
        # Database failed to connect
        response_msg = "CruzAid (Offline Mode): Please call 911 for emergencies or 831-459-2211 for Student Health."

    # 3. Send Reply
    resp = MessagingResponse()
    resp.message(response_msg)
    return str(resp)


if __name__ == "__main__":
    app.run(debug=True, port=5000)