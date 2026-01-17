import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
app = Flask(__name__)

# --- AI SETUP (OpenRouter/Gemini) ---
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# --- DUMMY DATABASE ---
LOCAL_RESOURCES = [
    {"name": "Dientes Community Dental", "tags": ["dental", "tooth", "pain"], "phone": "831-464-5409",
     "address": "1830 Commercial Way"},
    {"name": "UCSC Student Health", "tags": ["sick", "doctor", "fever", "student"], "phone": "831-459-2211",
     "address": "UC Santa Cruz"},
    {"name": "Dominican Hospital ER", "tags": ["emergency", "dying", "broken", "blood"], "phone": "831-462-7700",
     "address": "1555 Soquel Dr"},
    {"name": "Planned Parenthood", "tags": ["sexual", "pregnancy", "testing"], "phone": "831-426-5550",
     "address": "1119 Pacific Ave"}
]


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
                    "content": f""" You are a medical sorter. Input text: "{user_text}"
        
        Rules:
        - If it mentions 'tooth', 'gum', 'mouth' -> return 'dental'
        - If it mentions 'fever', 'headache', 'cold', 'flu' -> return 'student'
        - If it mentions 'blood', 'broken', 'emergency' -> return 'emergency'
        
        Return ONLY the single word. Do not write a sentence.
        """
                }
            ]
        )
        return completion.choices[0].message.content.strip().lower()
    except Exception as e:
        print(f"AI Error: {e}")
        return "general"


@app.route('/sms', methods=['POST'])
def bot():
    # 1. Get the message (Twilio uses 'Body', not 'Text')
    incoming_msg = request.values.get('Body', '').lower()
    sender = request.values.get('From', '')
    print(f"📩 Received from {sender}: {incoming_msg}")

    # 2. Ask AI
    category = ask_gemini(incoming_msg)
    print(f"🧠 AI Category: {category}")

    # 3. Database Lookup
    match = next((r for r in LOCAL_RESOURCES if category in r['tags']), LOCAL_RESOURCES[1])

    # 4. Create the Reply
    response_text = f"CruzAid: Based on '{category}', we recommend: {match['name']}. Call: {match['phone']} ({match['address']})"

    # 5. Send back TwiML (Twilio's XML format)
    resp = MessagingResponse()
    resp.message(response_text)

    return str(resp)


if __name__ == '__main__':
    app.run(port=5000, debug=True)