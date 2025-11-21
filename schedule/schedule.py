import json
import os
from urllib.parse import quote_plus

from flask import Flask, request, jsonify, make_response
from pymongo import MongoClient

# Configuration de l'application Flask
app = Flask(__name__)
PORT = 3202
HOST = '0.0.0.0'

JSON_FILE_PATH = '{}/databases/times.json'.format(".")
PERSISTENCE_TYPE = os.getenv("PERSISTENCE_TYPE", "MONGODB").upper()
default_password = quote_plus("*65%8XPuGaQ#")
MONGO_URL = os.getenv("MONGO_URL", f"mongodb://root:{default_password}@localhost:27017/")

client = None
db = None
collection = None
schedule = []

if PERSISTENCE_TYPE == "MONGODB":
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    db = client["schedule"]
    collection = db["entries"]

    if collection.count_documents({}) == 0:
        with open(JSON_FILE_PATH, "r") as jsf:
            schedule_data = json.load(jsf)["schedule"]
            if schedule_data:
                collection.insert_many(schedule_data)
                print(f"Horaires chargés: {len(schedule_data)} (MongoDB)")
    else:
        print(f"Base MongoDB déjà initialisée ({collection.count_documents({})} dates)")
else:
    with open(JSON_FILE_PATH, "r") as jsf:
        schedule = json.load(jsf)["schedule"]
        print(f"Horaires chargés: {len(schedule)} (JSON)")


def write_schedule_to_file(data):
    # Sauvegarde les données d'horaires dans le fichier JSON
    with open(JSON_FILE_PATH, "w") as jsf:
        json.dump({"schedule": data}, jsf, indent=4)

# ============================================================================
# ROUTES DE L'API
# ============================================================================

# Route pour l'accueil du service Schedule
@app.route("/", methods=['GET'])
def home():
    # Page d'accueil du service Schedule
    return "<h1 style='color:blue'>Bienvenue dans le service Horaires!</h1>"

# ============================================================================
# OPÉRATIONS CRUD - CREATE
# ============================================================================

# Route pour ajouter un film à l'horaire
@app.route("/schedule", methods=['POST'])
def add_movie_to_schedule():
    # Ajouter un film à l'horaire
    req = request.get_json()
    
    # Validation des données requises
    if not req or 'movieid' not in req or 'date' not in req:
        return make_response(jsonify({"error": "movieid et date requis"}), 400)
    
    movieid = req['movieid']
    date = req['date']

    if PERSISTENCE_TYPE == "MONGODB":
        entry = collection.find_one({"date": date})
        if entry:
            movies = entry.get("movies", [])
            if movieid in movies:
                return make_response(jsonify({"error": "Film déjà programmé à cette date"}), 409)
            movies.append(movieid)
            collection.update_one({"date": date}, {"$set": {"movies": movies}})
            updated_entry = {"date": date, "movies": movies}
        else:
            updated_entry = {"date": date, "movies": [movieid]}
            collection.insert_one(updated_entry)
    else:
        global schedule
        entry = next((item for item in schedule if item.get('date') == date), None)
        if entry:
            if movieid in entry.get("movies", []):
                return make_response(jsonify({"error": "Film déjà programmé à cette date"}), 409)
            entry.setdefault("movies", []).append(movieid)
        else:
            entry = {"date": date, "movies": [movieid]}
            schedule.append(entry)
        write_schedule_to_file(schedule)
        updated_entry = entry
    
    return make_response(jsonify({
        "message": "Film ajouté à l'horaire", 
        "data": updated_entry
    }), 201)
 
# ============================================================================
# OPÉRATIONS CRUD - READ
# ============================================================================

@app.route("/schedule", methods=['GET'])
def get_all_schedules():
    # Récupérer tous les horaires
    if PERSISTENCE_TYPE == "MONGODB":
        entries = list(collection.find({}))
        for item in entries:
            if '_id' in item:
                item['_id'] = str(item['_id'])
        return make_response(jsonify(entries), 200)
    return make_response(jsonify(schedule), 200)

# Route pour récupérer les horaires pour une date spécifique
@app.route("/schedule/<date>", methods=['GET'])
def get_schedule_by_date(date):
    # Récupérer les horaires pour une date spécifique
    if PERSISTENCE_TYPE == "MONGODB":
        entry = collection.find_one({"date": date})
        if entry:
            if '_id' in entry:
                entry['_id'] = str(entry['_id'])
            return make_response(jsonify([entry]), 200)
    else:
        entry = next((item for item in schedule if item.get('date') == date), None)
        if entry:
            return make_response(jsonify([entry]), 200)
    
    return make_response(jsonify({"error": "Aucun horaire trouvé pour cette date"}), 404)

# Route pour récupérer les horaires pour un film spécifique
@app.route("/schedule/movie/<movieid>", methods=['GET'])
def get_schedule_by_movie(movieid):
    # Récupérer tous les horaires d'un film spécifique
    if PERSISTENCE_TYPE == "MONGODB":
        entries = list(collection.find({"movies": movieid}))
        for item in entries:
            if '_id' in item:
                item['_id'] = str(item['_id'])
        if entries:
            return make_response(jsonify(entries), 200)
    else:
        filtered_schedule = [item for item in schedule if movieid in item.get('movies', [])]
        if filtered_schedule:
            return make_response(jsonify(filtered_schedule), 200)
    
    return make_response(jsonify({"error": "Aucun horaire trouvé pour ce film"}), 404)

# Route pour vérifier si un film est programmé à une date spécifique (utilisée par Booking)
@app.route("/schedule/<movieid>/<date>", methods=['GET'])
def check_movie_schedule(movieid, date):
    # Vérifie si un film est programmé à une date spécifique
    if PERSISTENCE_TYPE == "MONGODB":
        entry = collection.find_one({"date": date, "movies": movieid})
        if entry:
            return make_response(jsonify({
                "date": date,
                "movieid": movieid,
                "available": True
            }), 200)
    else:
        for item in schedule:
            if item.get('date') == date and movieid in item.get('movies', []):
                return make_response(jsonify({
                    "date": date,
                    "movieid": movieid,
                    "available": True
                }), 200)

    return make_response(jsonify({"error": "Film non programmé à cette date"}), 404)


# ============================================================================
# OPÉRATIONS CRUD - DELETE
# ============================================================================

# Route pour supprimer un horaire spécifique (film + date)
@app.route("/schedule/<movieid>/<date>", methods=['DELETE'])
def delete_schedule(movieid, date):
    # Supprimer un horaire spécifique (film + date)
    if PERSISTENCE_TYPE == "MONGODB":
        entry = collection.find_one({"date": date})
        if not entry:
            return make_response(jsonify({"error": "Horaire non trouvé"}), 404)
        movies = entry.get("movies", [])
        if movieid not in movies:
            return make_response(jsonify({"error": "Horaire non trouvé"}), 404)
        movies.remove(movieid)
        if movies:
            collection.update_one({"date": date}, {"$set": {"movies": movies}})
        else:
            collection.delete_one({"date": date})
        return make_response(jsonify({"message": "Horaire supprimé avec succès"}), 200)
    else:
        global schedule
        modified = False
        new_schedule = []
        for item in schedule:
            if item.get('date') == date and movieid in item.get('movies', []):
                modified = True
                movies = item.get('movies', [])
                movies.remove(movieid)
                if movies:
                    item['movies'] = movies
                    new_schedule.append(item)
            else:
                new_schedule.append(item)
        if not modified:
            return make_response(jsonify({"error": "Horaire non trouvé"}), 404)
        schedule = new_schedule
        write_schedule_to_file(schedule)
        return make_response(jsonify({"message": "Horaire supprimé avec succès"}), 200)

# Route pour supprimer tous les horaires d'une date spécifique
@app.route("/schedule/date/<date>", methods=['DELETE'])
def delete_all_schedules_for_date(date):
    # Supprimer tous les horaires d'une date
    if PERSISTENCE_TYPE == "MONGODB":
        result = collection.delete_one({"date": date})
        if result.deleted_count == 0:
            return make_response(jsonify({"error": "Aucun horaire trouvé pour cette date"}), 404)
        return make_response(jsonify({
            "message": f"Tous les horaires du {date} ont été supprimés"
        }), 200)
    else:
        global schedule
        original_length = len(schedule)
        schedule = [item for item in schedule if item.get('date') != date]
        if len(schedule) < original_length:
            write_schedule_to_file(schedule)
            return make_response(jsonify({
                "message": f"Tous les horaires du {date} ont été supprimés"
            }), 200)
        else:
            return make_response(jsonify({"error": "Aucun horaire trouvé pour cette date"}), 404)

# ============================================================================
# DÉMARRAGE DU SERVEUR
# ============================================================================

if __name__ == "__main__":
    print("Server running in port %s" % (PORT))
    app.run(host=HOST, port=PORT)
