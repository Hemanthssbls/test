from pymongo import MongoClient
import re

# MongoDB connection details
MONGO_URI = "mongodb+srv://michealachayan2:Micheal,12@cluster0.4dicebk.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "Cluster0"
COLLECTION_NAME = "Telegram_collection"

# Step 0: Connect to MongoDB and get the collection
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# Step 1: Group movies by size
pipeline = [
    {
        "$group": {
            "_id": "$size",
            "ids": {"$push": "$_id"},
            "names": {"$push": "$name"},
            "count": {"$sum": 1}
        }
    },
    {
        "$match": {
            "count": {"$gt": 1}
        }
    }
]

duplicates = list(collection.aggregate(pipeline))

# Step 2: Delete duplicates, keep one per group
preferred_order = ["1080p", "720p", "BluRay", "DVDRip", "PreDVD", "CAM"]

def quality_rank(name):
    for i, tag in enumerate(preferred_order):
        if re.search(tag, name, re.IGNORECASE):
            return i
    return len(preferred_order)

for group in duplicates:
    ids = group['ids']
    names = group['names']

    sorted_ids = sorted(zip(names, ids), key=lambda x: quality_rank(x[0]))

    keep_id = sorted_ids[0][1]
    delete_ids = [doc_id for _, doc_id in sorted_ids[1:]]

    if delete_ids:
        result = collection.delete_many({"_id": {"$in": delete_ids}})
        print(f"Deleted {result.deleted_count} duplicate(s) for size {group['_id']}")

print("Duplicate cleanup complete.")
