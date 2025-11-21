import json
import os
from urllib.parse import quote_plus

from flask import Flask, jsonify, make_response, request
from pymongo import MongoClient

app = Flask(__name__)

PORT = 3203

JSON_FILE_PATH = '{}/databases/users.json'.format(".")
PERSISTENCE_TYPE = os.getenv("PERSISTENCE_TYPE", "MONGODB").upper()
default_password = quote_plus("*65%8XPuGaQ#")
MONGO_URL = os.getenv("MONGO_URL", f"mongodb://root:{default_password}@localhost:27017/")

client = None
db = None
collection = None
users = []

if PERSISTENCE_TYPE == "MONGODB":
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    db = client["users"]
    collection = db["users"]

    if collection.count_documents({}) == 0:
        with open(JSON_FILE_PATH, "r") as jsf:
            users_data = json.load(jsf)["users"]
            if users_data:
                collection.insert_many(users_data)
                print(f"Utilisateurs chargés: {len(users_data)} (MongoDB)")
    else:
        print(f"Base MongoDB déjà initialisée ({collection.count_documents({})} utilisateurs)")
else:
    with open(JSON_FILE_PATH, "r") as jsf:
        users = json.load(jsf)["users"]
        print(f"Utilisateurs chargés: {len(users)} (JSON)")


def write_users_to_file(data):
    with open(JSON_FILE_PATH, "w") as jsf:
        json.dump({"users": data}, jsf, indent=4)


@app.route("/", methods=['GET'])
def home():
    return "<h1 style='color:blue'>Welcome to the User service!</h1>"


@app.route("/users", methods=['GET'])
def get_users():
    if PERSISTENCE_TYPE == "MONGODB":
        users_list = list(collection.find({}))
        for user in users_list:
            if '_id' in user:
                user['_id'] = str(user['_id'])
        return make_response(jsonify(users_list), 200)
    return make_response(jsonify(users), 200)


@app.route("/users/<userid>", methods=['GET'])
def get_user_by_id(userid):
    if PERSISTENCE_TYPE == "MONGODB":
        user = collection.find_one({"id": str(userid)})
        if user is None:
            return make_response(jsonify({"error": "User ID not found"}), 404)
        if '_id' in user:
            user['_id'] = str(user['_id'])
        return make_response(jsonify(user), 200)
    else:
        user = next((user for user in users if str(user["id"]) == str(userid)), None)
        if user is None:
            return make_response(jsonify({"error": "User ID not found"}), 404)

        return make_response(jsonify(user), 200)


@app.route("/users/admin", methods=['GET'])
def get_admin_users():
    if PERSISTENCE_TYPE == "MONGODB":
        admins = list(collection.find({"role": "admin"}))
        if len(admins) == 0:
            return make_response(jsonify({"error": "No admin users found"}), 204)
        for admin in admins:
            if '_id' in admin:
                admin['_id'] = str(admin['_id'])
        return make_response(jsonify(admins), 200)
    else:
        admins = [user for user in users if user.get("role") == "admin"]
        if len(admins) == 0:
            return make_response(jsonify({"error": "No admin users found"}), 204)

        return make_response(jsonify(admins), 200)


@app.route("/users", methods=['POST'])
def add_user():
    req = request.get_json()

    if PERSISTENCE_TYPE == "MONGODB":
        if collection.find_one({"id": str(req.get("id"))}):
            return make_response(jsonify({"error": "User ID already exists"}), 400)
        collection.insert_one(req)
        return make_response(jsonify(req), 201)
    else:
        for user in users:
            if str(user["id"]) == str(req.get("id")):
                return make_response(jsonify({"error": "User ID already exists"}), 400)

        users.append(req)
        write_users_to_file(users)
        return make_response(jsonify(req), 201)


@app.route("/users/<userid>", methods=['PUT'])
def update_user(userid):
    req = request.get_json()
    if PERSISTENCE_TYPE == "MONGODB":
        result = collection.update_one({"id": str(userid)}, {"$set": req})
        if result.matched_count == 0:
            return make_response(jsonify({"error": "User ID not found"}), 404)
        user = collection.find_one({"id": str(userid)})
        if '_id' in user:
            user['_id'] = str(user['_id'])
        return make_response(jsonify(user), 200)
    else:
        user = next((user for user in users if str(user["id"]) == str(userid)), None)
        if user is None:
            return make_response(jsonify({"error": "User ID not found"}), 404)

        user.update(req)
        write_users_to_file(users)
        return make_response(jsonify(user), 200)


@app.route("/users/<userid>", methods=['DELETE'])
def delete_user(userid):
    if PERSISTENCE_TYPE == "MONGODB":
        result = collection.delete_one({"id": str(userid)})
        if result.deleted_count == 0:
            return make_response(jsonify({"error": "User ID not found"}), 404)
        return make_response(jsonify({"message": "User deleted successfully"}), 200)
    else:
        user = next((user for user in users if str(user["id"]) == str(userid)), None)
        if user is None:
            return make_response(jsonify({"error": "User ID not found"}), 404)

        users.remove(user)
        write_users_to_file(users)
        return make_response(jsonify({"message": "User deleted successfully"}), 200)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=PORT)
