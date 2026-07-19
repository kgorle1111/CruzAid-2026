import os

import certifi
from dotenv import load_dotenv
from pymongo import MongoClient

data = [
    {
        "name": "UCSC Student Health Center",
        "phone": "831-459-2211",
        "address": "1156 High St, Santa Cruz",
        "tags": ["student", "fever", "flu", "cold", "sick", "headache"]
    },
    {
        "name": "Dominican Hospital ER",
        "phone": "831-462-7700",
        "address": "1555 Soquel Dr, Santa Cruz",
        "tags": ["emergency", "broken", "dying", "blood", "critical", "accident"]
    },
    {
        "name": "Dientes Community Dental",
        "phone": "831-464-5409",
        "address": "1830 Commercial Way, Santa Cruz",
        "tags": ["dental", "tooth", "mouth", "gum", "cavity"]
    },
    {
        "name": "CAPS (Counseling)",
        "phone": "831-459-2628",
        "address": "Cowell College, UCSC",
        "tags": ["mental", "depressed", "sad", "anxiety", "stress"]
    },
    {
        "name": "Planned Parenthood",
        "phone": "831-426-5550",
        "address": "1119 Pacific Ave, Santa Cruz",
        "tags": ["sexual", "pregnant", "test", "std", "protection"]
    },
    {
        "name": "Sutter Health Urgent Care",
        "phone": "831-458-6310",
        "address": "1301 Mission St 1st Floor, Santa Cruz, CA 95060",
        # Added "emergency" and "student" so it appears for injuries
        "tags": ["emergency", "student", "urgent care", "walk-in", "minor injury", "sprain", "burn", "stitches", "x-ray"]
    },
    {
        "name": "Kaiser Permanente Santa Cruz",
        "phone": "831-425-4100",
        "address": "110 Cooper St #500, Santa Cruz, CA 95060",
        # Added "student" so it appears for general sickness
        "tags": ["student", "primary care", "doctor", "appointment", "referral", "checkup", "insurance-based"]
    },
    {
        "name": "Santa Cruz Women’s Health Clinic",
        "phone": "831-427-3500",
        "address": "250 Locust St, Santa Cruz, CA 95060",
        # Added "sexual" and "student"
        "tags": ["sexual", "student", "womens health", "gynecology", "obgyn", "reproductive care", "birth control", "periods"]
    },
    {
        "name": "Coastside Family Medicine",
        "phone": "831-287-5169",
        "address": "250 Locust St, Santa Cruz, CA 95060",
        # Added "student"
        "tags": ["student", "family medicine", "vaccinations", "children", "routine care"]
    },
    {
        "name": "Poison Control (California)",
        "phone": "1-800-222-1222",
        "address": "UCSF School of Pharmacy, 490 Illinois St, San Francisco",
        # Added "emergency" so the bot triggers it for danger
        "tags": ["emergency", "poison", "overdose", "toxic", "chemical", "bite", "sting"]
    },
    {
        "name": "988 Suicide & Crisis Lifeline",
        "phone": "988",
        "address": "104 Walnut Ave, Santa Cruz, CA 95060",
        # Added "mental" and "emergency"
        "tags": ["mental", "emergency", "suicide", "self-harm", "panic", "hopeless"]
    }
]


def seed():
    load_dotenv()
    uri = os.environ.get("MONGO_URI")
    client = MongoClient(uri, tlsCAFile=certifi.where())
    collection = client["CruzAidDB"]["resources"]
    collection.delete_many({})  # wipe first so we don't get duplicates
    collection.insert_many(data)
    print(f"✅ SUCCESS: {len(data)} resources uploaded to MongoDB Cloud!")


if __name__ == "__main__":
    seed()
