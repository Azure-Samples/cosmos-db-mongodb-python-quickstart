import os
import sys
from flask import Flask, render_template
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from random import randint
import pymongo
from dotenv import load_dotenv

app = Flask(__name__)


@app.route("/")
def hello_world():
    load_dotenv()
    print("CS:")

    credential = DefaultAzureCredential()

    KEYVAULT_ENDPOINT = os.environ.get("KEYVAULT_ENDPOINT")

    secret_client = SecretClient(vault_url=KEYVAULT_ENDPOINT, credential=credential)
    CONNECTION_STRING = secret_client.get_secret("cosmosconnectionstring")
    
    print(CONNECTION_STRING.value)

    updates = []

    DB_NAME = "adventureworks"
    COLLECTION_NAME = "products"

    client = pymongo.MongoClient(CONNECTION_STRING.value)

    # Create database if it doesn't exist
    db = client[DB_NAME]
    if DB_NAME not in client.list_database_names():
        # Create a database
        db.command({"customAction": "CreateDatabase", "offerThroughput": 400})
        updates.append("Created db '{}' with shared throughput.\n".format(DB_NAME))
    else:
        updates.append("Using database: '{}'.\n".format(DB_NAME))

    # Create collection if it doesn't exist
    collection = db[COLLECTION_NAME]
    if COLLECTION_NAME not in db.list_collection_names():
        # Creates an unsharded collection that uses the DBs shared throughput
        db.command(
            {"customAction": "CreateCollection", "collection": COLLECTION_NAME}
        )
        updates.append("Created collection '{}'.\n".format(COLLECTION_NAME))
    else:
        updates.append("Using collection: '{}'.\n".format(COLLECTION_NAME))

    indexes = [
        {"key": {"_id": 1}, "name": "_id_1"},
        {"key": {"name": 2}, "name": "_id_2"},
    ]
    db.command(
        {
            "customAction": "UpdateCollection",
            "collection": COLLECTION_NAME,
            "indexes": indexes,
        }
    )
    updates.append("Indexes are: {}\n".format(sorted(collection.index_information())))

    """Create new document and upsert (create or replace) to collection"""
    product = {
        "category": "gear-surf-surfboards",
        "name": "Yamba Surfboard-{}".format(randint(50, 5000)),
        "quantity": 1,
        "sale": False,
    }
    result = collection.update_one(
        {"name": product["name"]}, {"$set": product}, upsert=True
    )
    updates.append("Upserted document with _id {}\n".format(result.upserted_id))

    doc = collection.find_one({"_id": result.upserted_id})
    updates.append("Found a document with _id {}: {}\n".format(result.upserted_id, doc))

    """Query for documents in the collection"""
    updates.append("Products with category 'gear-surf-surfboards':\n")
    allProductsQuery = {"category": "gear-surf-surfboards"}
    for doc in collection.find(allProductsQuery).sort(
        "name", pymongo.ASCENDING
    ):
        updates.append("Found a product with _id {}: {}\n".format(doc["_id"], doc))

    return render_template('index.html', messages=updates)


