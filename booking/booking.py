

from flask import Flask, render_template, request, jsonify, make_response
import requests
import json
from werkzeug.exceptions import NotFound

# Configuration de l'application Flask
app = Flask(__name__)
PORT = 3201
HOST = '0.0.0.0'

# URLs des autres services microservices
MOVIE_SERVICE_URL = "http://localhost:3200"
SCHEDULE_SERVICE_URL = "http://localhost:3202"

# Chargement de la base de données des réservations au démarrage
with open('{}/databases/bookings.json'.format("."), "r") as jsf:
   bookings = json.load(jsf)["bookings"]

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def write_bookings_to_file(data):
    # Sauvegarde les données de réservations dans le fichier JSON
    with open('{}/databases/bookings.json'.format("."), "w") as jsf:
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

@app.route("/bookings", methods=['GET'])
def get_all_bookings():
    # Récupérer toutes les réservations (accès admin)
    return make_response(jsonify(bookings), 200)

@app.route("/bookings/<userid>", methods=['GET'])
def get_user_bookings(userid):
    # Récupérer toutes les réservations d'un utilisateur
    user_booking = None
    for booking in bookings:
        if booking['userid'] == userid:
            user_booking = booking
            break
    
    if not user_booking:
        return make_response(jsonify({"error": "Aucune réservation trouvée pour cet utilisateur"}), 404)
    
    return make_response(jsonify(user_booking), 200)

@app.route("/bookings/<userid>/detailed", methods=['GET'])
def get_detailed_user_bookings(userid):
    # Récupérer les réservations détaillées d'un utilisateur avec informations des films et horaires
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

@app.route("/bookings/<userid>/<movieid>/<date>", methods=['DELETE'])
def delete_booking(userid, movieid, date):
    # Supprimer une réservation spécifique
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

@app.route("/bookings/<userid>", methods=['DELETE'])
def delete_all_user_bookings(userid):
    # Supprimer toutes les réservations d'un utilisateur
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
