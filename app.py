import os
from functools import wraps
import certifi
from flask import Flask, request, abort
from flask_limiter import Limiter
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator
from openai import OpenAI
from pymongo import MongoClient
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
# Trust the proxy's forwarded scheme/host (ngrok, Render, etc.) so request.url
# reports the real https URL Twilio signed. Without this, signature checks fail.
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
load_dotenv()


# Reject any request to /sms that isn't a genuine Twilio call. Twilio signs each
# webhook with the account auth token; we recompute the signature and compare.
# Without this, anyone who finds the URL can burn our LLM/DB quota.
# If TWILIO_AUTH_TOKEN is unset we skip the check (local dev / tests) rather than
# fail closed, so an unconfigured deploy is open by design — set the token in prod.
def validate_twilio_request(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = os.environ.get("TWILIO_AUTH_TOKEN")
        if token:
            validator = RequestValidator(token)
            signature = request.headers.get("X-Twilio-Signature", "")
            if not validator.validate(request.url, request.form, signature):
                abort(403)
        return f(*args, **kwargs)
    return wrapper

# Rate limit per sender phone number (all requests share Twilio's IPs, so
# keying on the "From" number throttles a spammer without throttling everyone).
# Set RATELIMIT_STORAGE_URI (e.g. redis://host:6379) to share limits across
# gunicorn workers/instances. Unset falls back to per-process in-memory, which
# is only correct for a single worker.
limiter = Limiter(
    key_func=lambda: request.form.get("From", request.remote_addr),
    app=app,
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
)

# --- CONFIGURATION ---
def get_ai_client():
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY"),
    )

# --- DATABASE CONNECTION (FORCED) ---
uri = os.environ.get("MONGO_URI")

try:
    # We use the 'uri' variable directly to bypass environment issues
    mongo_client = MongoClient(uri, tlsCAFile=certifi.where())
    db = mongo_client["CruzAidDB"]
    collection = db["resources"]
    print("✅ Connected to MongoDB Cloud!")
except Exception as e:
    print(f"❌ Database Error: {e}")
    collection = None


# Categories the triage router can emit. Every one MUST have a matching
# resource in setup_data.py, or users silently fall through to the default.
CATEGORIES = ["sexual", "mental", "dental", "emergency", "student"]


# --- AI FUNCTION ---
def ask_gemini(user_text):
    try:
        completion = get_ai_client().chat.completions.create(
            extra_headers={
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "CruzAid Hackathon",
            },
            model="google/gemini-2.5-flash-lite",
            messages=[
                {
                    "role": "user",
                    "content": f"""
                    You are a medical triage router. 
                    Classify the input into EXACTLY ONE of these categories:
                    {CATEGORIES}

                    RULES:
                    - "sexual": pregnancy, test, protection, condoms, std, birth control
                    - "mental": sad, depressed, suicide, anxiety, stress, unhappy, feelings
                    - "dental": tooth, gum, mouth, cavity, pain in jaw
                    - "emergency": broken, blood, dying, breathing, chest pain, car crash, accident
                    - "student": fever, flu, cold, headache, cough, sick, nausea, general checkup

                    Input: "{user_text}"

                    Return ONLY the category word. Do not add punctuation.
                    """
                }
            ]
        )
        return completion.choices[0].message.content.strip().lower()
    except Exception as e:
        print(f"AI Error: {e}")
        return "student"  # Default fallback


# --- THE SERVER ---
@app.route("/sms", methods=['POST'])
@limiter.limit("10 per minute")
@validate_twilio_request
def sms_reply():
    user_text = request.form.get('Body')

    # 1. Ask AI for Category
    category = ask_gemini(user_text)
    print(f"🧠 AI Category: {category}")

    # 2. Search MongoDB
    response_msg = ""

    if collection is not None:
        try:
            # 1. Find up to 3 matches
            cursor = collection.find({"tags": category}).limit(3)
            results = list(cursor)

            if results:
                response_msg = f"CruzAid: Found {len(results)} options for '{category}':\n"

                for place in results:
                    # Get the address safely
                    address_text = place.get('address', 'Santa Cruz, CA')

                    # Create the Map Link (SAFE VERSION)
                    # We use urllib to make sure spaces don't break the link
                    safe_address = address_text.replace(" ", "+")
                    map_url = f"https://www.google.com/maps/search/?api=1&query={safe_address}"

                    # Build the message
                    response_msg += f"\n🏥 *{place['name']}*\n📞 {place['phone']}\n📍 {address_text}\n🔗 {map_url}\n"
            else:
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
