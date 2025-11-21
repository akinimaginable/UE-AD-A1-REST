import json
import os
from urllib.parse import quote_plus

import requests
from flask import Flask, request, jsonify, make_response
from pymongo import MongoClient

# Configuration de l'application Flask
app = Flask(__name__)
PORT = 3201
HOST = '0.0.0.0'

# URLs des autres services microservices
MOVIE_SERVICE_URL = os.getenv("MOVIE_SERVICE_URL", "http://localhost:3200")
SCHEDULE_SERVICE_URL = os.getenv("SCHEDULE_SERVICE_URL", "http://localhost:3202")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:3203")

JSON_FILE_PATH = '{}/databases/bookings.json'.format(".")
PERSISTENCE_TYPE = os.getenv("PERSISTENCE_TYPE", "MONGODB").upper()
default_password = quote_plus("*65%8XPuGaQ#")
MONGO_URL = os.getenv("MONGO_URL", f"mongodb://root:{default_password}@localhost:27017/")

client = None
db = None
collection = None
bookings = []

if PERSISTENCE_TYPE == "MONGODB":
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    db = client["bookings"]
    collection = db["bookings"]

    if collection.count_documents({}) == 0:
        with open(JSON_FILE_PATH, "r") as jsf:
            bookings_data = json.load(jsf)["bookings"]
            if bookings_data:
                collection.insert_many(bookings_data)
                print(f"Réservations chargées: {len(bookings_data)} utilisateurs (MongoDB)")
    else:
        print(f"Base MongoDB déjà initialisée ({collection.count_documents({})} utilisateurs)")
else:
    with open(JSON_FILE_PATH, "r") as jsf:
        bookings = json.load(jsf)["bookings"]
        print(f"Réservations chargées: {len(bookings)} utilisateurs (JSON)")

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def write_bookings_to_file(data):
    # Sauvegarde les données de réservations dans le fichier JSON
    with open(JSON_FILE_PATH, "w") as jsf:
        json.dump({"bookings": data}, jsf, indent=4)

def get_movie_details(movie_id):
    # Récupère les détails d'un film depuis le service Movie
    try:
        response = requests.get(f"{MOVIE_SERVICE_URL}/movies/{movie_id}")
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException:
        return None

def get_schedule_details(movie_id, date):
    # Récupère les détails d'un horaire depuis le service Schedule
    try:
        response = requests.get(f"{SCHEDULE_SERVICE_URL}/schedule/{movie_id}/{date}")
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException:
        return None

def get_user_details(userid):
    # Récupère les détails d'un utilisateur depuis le service User
    try:
        response = requests.get(f"{USER_SERVICE_URL}/users/{userid}")
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException:
        return None

def is_admin_user(userid):
    # Vérifie si l'utilisateur est un administrateur
    user_details = get_user_details(userid)
    if user_details and user_details.get('role') == 'admin':
        return True
    return False

# ============================================================================
# ROUTES DE L'API
# ============================================================================

@app.route("/", methods=['GET'])
def home():
    # Page d'accueil du service Booking
    return "<h1 style='color:blue'>Bienvenue dans le service Réservations!</h1>"

# ============================================================================
# OPÉRATIONS CRUD - CREATE
# ============================================================================

# Route pour créer une nouvelle réservation
@app.route("/bookings", methods=['POST'])
def create_booking():
    # Créer une nouvelle réservation
    req = request.get_json()
    
    # Validation des données requises
    if not req or 'userid' not in req or 'movieid' not in req or 'date' not in req:
        return make_response(jsonify({"error": "userid, movieid et date requis"}), 400)
    
    userid = req['userid']
    movieid = req['movieid']
    date = req['date']
    
    # Vérification de l'existence du film
    movie_details = get_movie_details(movieid)
    if not movie_details:
        return make_response(jsonify({"error": "Film non trouvé"}), 404)
    
    # Vérification de la programmation du film
    schedule_details = get_schedule_details(movieid, date)
    if not schedule_details:
        return make_response(jsonify({"error": "Film non programmé à cette date"}), 404)
    
    if PERSISTENCE_TYPE == "MONGODB":
        user_booking = collection.find_one({"userid": userid})
        if not user_booking:
            user_booking = {"userid": userid, "dates": []}
            collection.insert_one(user_booking)
        
        dates = user_booking.get("dates", [])
        date_entry = next((d for d in dates if d['date'] == date), None)
        if not date_entry:
            date_entry = {"date": date, "movies": []}
            dates.append(date_entry)
        
        if movieid in date_entry['movies']:
            return make_response(jsonify({"error": "Film déjà réservé pour cette date"}), 409)
        
        date_entry['movies'].append(movieid)
        collection.update_one({"userid": userid}, {"$set": {"dates": dates}})
    else:
        global bookings
        # Recherche ou création de l'utilisateur
        user_booking = None
        for booking in bookings:
            if booking['userid'] == userid:
                user_booking = booking
                break
        
        if not user_booking:
            user_booking = {"userid": userid, "dates": []}
            bookings.append(user_booking)
        
        # Recherche ou création de la date
        date_entry = None
        for date_item in user_booking['dates']:
            if date_item['date'] == date:
                date_entry = date_item
                break
        
        if not date_entry:
            date_entry = {"date": date, "movies": []}
            user_booking['dates'].append(date_entry)
        
        # Vérification des doublons
        if movieid in date_entry['movies']:
            return make_response(jsonify({"error": "Film déjà réservé pour cette date"}), 409)
        
        # Ajout de la réservation
        date_entry['movies'].append(movieid)
        write_bookings_to_file(bookings)
    
    return make_response(jsonify({
        "message": "Réservation créée avec succès",
        "booking": {
            "userid": userid,
            "movieid": movieid,
            "date": date
        }
    }), 201)

# ============================================================================
# OPÉRATIONS CRUD - READ
# ============================================================================

# Route pour récupérer toutes les réservations
@app.route("/bookings", methods=['GET'])
def get_all_bookings():
    # Récupérer toutes les réservations (accès admin uniquement)
    # Vérification de l'autorisation admin via paramètre userid
    userid = request.args.get('userid')
    
    if not userid:
        return make_response(jsonify({"error": "userid requis pour accéder aux réservations"}), 400)
    
    if not is_admin_user(userid):
        return make_response(jsonify({"error": "Accès refusé - droits administrateur requis"}), 403)
    
    if PERSISTENCE_TYPE == "MONGODB":
        bookings_list = list(collection.find({}))
        for booking in bookings_list:
            if '_id' in booking:
                booking['_id'] = str(booking['_id'])
        return make_response(jsonify(bookings_list), 200)
    else:
        return make_response(jsonify(bookings), 200)

# Route pour récupérer toutes les réservations d'un utilisateur
@app.route("/bookings/<userid>", methods=['GET'])
def get_user_bookings(userid):
    # Récupérer toutes les réservations d'un utilisateur
    if PERSISTENCE_TYPE == "MONGODB":
        booking = collection.find_one({"userid": userid})
        if not booking:
            return make_response(jsonify({"error": "Aucune réservation trouvée pour cet utilisateur"}), 404)
        if '_id' in booking:
            booking['_id'] = str(booking['_id'])
        return make_response(jsonify(booking), 200)
    else:
        user_booking = None
        for booking in bookings:
            if booking['userid'] == userid:
                user_booking = booking
                break
        
        if not user_booking:
            return make_response(jsonify({"error": "Aucune réservation trouvée pour cet utilisateur"}), 404)
        
        return make_response(jsonify(user_booking), 200)

# Route pour récupérer les réservations détaillées d'un utilisateur
@app.route("/bookings/<userid>/detailed", methods=['GET'])
def get_detailed_user_bookings(userid):
    # Récupérer les réservations détaillées d'un utilisateur avec informations des films et horaires
    if PERSISTENCE_TYPE == "MONGODB":
        user_booking = collection.find_one({"userid": userid})
    else:
        user_booking = None
        for booking in bookings:
            if booking['userid'] == userid:
                user_booking = booking
                break
    
    if not user_booking:
        return make_response(jsonify({"error": "Aucune réservation trouvée pour cet utilisateur"}), 404)
    
    detailed_bookings = []
    for date_entry in user_booking['dates']:
        date = date_entry['date']
        movies_details = []
        
        # Récupération des détails pour chaque film réservé
        for movie_id in date_entry['movies']:
            movie_details = get_movie_details(movie_id)
            schedule_details = get_schedule_details(movie_id, date)
            
            if movie_details and schedule_details:
                movies_details.append({
                    "movie": movie_details,
                    "schedule": schedule_details
                })
        
        if movies_details:
            detailed_bookings.append({
                "date": date,
                "movies": movies_details
            })
    
    return make_response(jsonify({
        "userid": userid,
        "bookings": detailed_bookings
    }), 200)

# ============================================================================
# OPÉRATIONS CRUD - DELETE
# ============================================================================

# Route pour supprimer une réservation spécifique
@app.route("/bookings/<userid>/<movieid>/<date>", methods=['DELETE'])
def delete_booking(userid, movieid, date):
    # Supprimer une réservation spécifique
    if PERSISTENCE_TYPE == "MONGODB":
        booking = collection.find_one({"userid": userid})
        if not booking:
            return make_response(jsonify({"error": "Réservation non trouvée"}), 404)
        
        updated_dates = []
        found = False
        for date_entry in booking['dates']:
            if date_entry['date'] == date and movieid in date_entry['movies']:
                found = True
                date_entry['movies'].remove(movieid)
                if date_entry['movies']:
                    updated_dates.append(date_entry)
            else:
                updated_dates.append(date_entry)
        
        if not found:
            return make_response(jsonify({"error": "Réservation non trouvée"}), 404)
        
        if not updated_dates:
            collection.delete_one({"userid": userid})
        else:
            collection.update_one({"userid": userid}, {"$set": {"dates": updated_dates}})
        return make_response(jsonify({"message": "Réservation supprimée avec succès"}), 200)
    else:
        global bookings
        
        for booking in bookings:
            if booking['userid'] == userid:
                for date_entry in booking['dates']:
                    if date_entry['date'] == date and movieid in date_entry['movies']:
                        # Suppression du film de la réservation
                        date_entry['movies'].remove(movieid)
                        
                        # Suppression de la date si plus de films
                        if not date_entry['movies']:
                            booking['dates'].remove(date_entry)
                        
                        # Suppression de l'utilisateur si plus de dates
                        if not booking['dates']:
                            bookings.remove(booking)
                        
                        write_bookings_to_file(bookings)
                        return make_response(jsonify({"message": "Réservation supprimée avec succès"}), 200)
        
        return make_response(jsonify({"error": "Réservation non trouvée"}), 404)

# Route pour supprimer toutes les réservations d'un utilisateur
@app.route("/bookings/<userid>", methods=['DELETE'])
def delete_all_user_bookings(userid):
    # Supprimer toutes les réservations d'un utilisateur
    if PERSISTENCE_TYPE == "MONGODB":
        result = collection.delete_one({"userid": userid})
        if result.deleted_count == 0:
            return make_response(jsonify({"error": "Aucune réservation trouvée pour cet utilisateur"}), 404)
        return make_response(jsonify({
            "message": f"Toutes les réservations de {userid} ont été supprimées"
        }), 200)
    else:
        global bookings
        
        for booking in bookings:
            if booking['userid'] == userid:
                bookings.remove(booking)
                write_bookings_to_file(bookings)
                return make_response(jsonify({
                    "message": f"Toutes les réservations de {userid} ont été supprimées"
                }), 200)
        
        return make_response(jsonify({"error": "Aucune réservation trouvée pour cet utilisateur"}), 404)

# ============================================================================
# DÉMARRAGE DU SERVEUR
# ============================================================================

if __name__ == "__main__":
    print("Server running in port %s" % (PORT))
    app.run(host=HOST, port=PORT)
