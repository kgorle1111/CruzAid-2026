import os
import certifi
from dotenv import load_dotenv
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI
from pymongo import MongoClient

app = Flask(__name__)
load_dotenv()

# --- CONFIGURATION ---
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)

# --- DATABASE CONNECTION (NEW) ---
# This connects to the cloud database using the link in your .env file
try:
    mongo_client = MongoClient(os.environ.get("MONGO_URI"), tlsCAFile=certifi.where())
    db = mongo_client["CruzAidDB"]  # Make sure your teammate named the DB 'CruzAidDB'
    collection = db["resources"]  # Make sure the collection is named 'resources'
    print("✅ Connected to MongoDB!")
except Exception as e:
    print(f"❌ Database Error: {e}")
    collection = None


# --- AI FUNCTION (UNCHANGED) ---
def ask_gemini(user_text):
    try:
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "CruzAid Hackathon",
            },
            model="google/gemini-2.5-flash-lite",  # Your working model
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

    # 2. Search MongoDB (NEW)
    response_msg = ""

    if collection is not None:
        # Look for a document where 'tags' includes the category
        # Example Data in DB: {"name": "UCSC Health", "phone": "555-5555", "tags": ["student", "fever"]}
        result = collection.find_one({"tags": category})

        if result:
            response_msg = f"CruzAid: Based on '{category}', we recommend: {result['name']}. Call: {result['phone']} ({result.get('address', 'Santa Cruz')})"
        else:
            # Database works, but no match found
            response_msg = f"CruzAid: Based on '{category}', please contact UCSC Student Health at 831-459-2211."
    else:
        # Database failed to connect, use backup
        response_msg = "CruzAid (Offline Mode): Please call 911 for emergencies or 831-459-2211 for Student Health."

    # 3. Send Reply
    resp = MessagingResponse()
    resp.message(response_msg)
    return str(resp)


if __name__ == "__main__":
    app.run(debug=True, port=5000)