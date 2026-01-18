import certifi
from pymongo import MongoClient

uri = "mongodb+srv://nikhilarambothula_db_user:CruzAid2026@cluster0.4dsz38r.mongodb.net/?appName=Cluster0"
client = MongoClient(uri, tlsCAFile=certifi.where())

db = client["CruzAidDB"]
collection = db["resources"]

# We wipe the old data first so we don't get duplicates
collection.delete_many({})

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
        "tags": ["mental", "depressed", "sad", "anxiety", "stress", "suicide"]
    },
    {
        "name": "Planned Parenthood",
        "phone": "831-426-5550",
        "address": "1119 Pacific Ave, Santa Cruz",
        "tags": ["sexual", "pregnant", "test", "std", "protection"]
    }
]

collection.insert_many(data)
print("✅ SUCCESS: 5 resources uploaded to MongoDB Cloud!")