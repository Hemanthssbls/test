from pymongo import MongoClient

# MongoDB connection details
MONGO_URI = "mongodb+srv://michealachayan2:Micheal,12@cluster0.4dicebk.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "Cluster0"
COLLECTION_NAME = "Telegram_collection"

def delete_duplicates():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    # Step 1: Aggregate to find duplicate file_hash values
    pipeline = [
        {"$group": {
            "_id": "$file_hash",
            "count": {"$sum": 1},
            "ids": {"$push": "$_id"}
        }},
        {"$match": {"count": {"$gt": 1}}}
    ]

    duplicates = list(collection.aggregate(pipeline))
    print(f"Found {len(duplicates)} duplicate file hashes.")

    deleted_count = 0
    for doc in duplicates:
        # Keep one, delete rest
        ids_to_delete = doc["ids"][1:]  # skip first
        result = collection.delete_many({"_id": {"$in": ids_to_delete}})
        deleted_count += result.deleted_count
        print(f"Deleted {result.deleted_count} duplicates for hash {doc['_id']}")

    print(f"Total duplicates deleted: {deleted_count}")

if __name__ == "__main__":
    delete_duplicates()
