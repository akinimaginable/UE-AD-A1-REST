

from flask import Flask, render_template, request, jsonify, make_response
import json
from werkzeug.exceptions import NotFound

# Configuration de l'application Flask
app = Flask(__name__)
PORT = 3202
HOST = '0.0.0.0'

# Chargement de la base de données des horaires au démarrage
with open('{}/databases/times.json'.format("."), "r") as jsf:
   schedule = json.load(jsf)["schedule"]

def write_schedule_to_file(data):
    # Sauvegarde les données d'horaires dans le fichier JSON
    with open('{}/databases/times.json'.format("."), "w") as jsf:
        json.dump({"schedule": data}, jsf, indent=4)

# ============================================================================
# ROUTES DE L'API
# ============================================================================

@app.route("/", methods=['GET'])
def home():
    # Page d'accueil du service Schedule
    return "<h1 style='color:blue'>Bienvenue dans le service Horaires!</h1>"

# ============================================================================
# OPÉRATIONS CRUD - CREATE
# ============================================================================

@app.route("/schedule", methods=['POST'])
def add_movie_to_schedule():
    # Ajouter un film à l'horaire
    req = request.get_json()
    
    # Validation des données requises
    if not req or 'movieid' not in req or 'date' not in req:
        return make_response(jsonify({"error": "movieid et date requis"}), 400)
    
    # Vérification des doublons (même film, même date, même heure)
    for item in schedule:
        if (item.get('movieid') == req['movieid'] and 
            item.get('date') == req['date'] and 
            item.get('time') == req.get('time')):
            return make_response(jsonify({"error": "Film déjà programmé à cette date/heure"}), 409)
    
    # Ajout du nouvel horaire
    schedule.append(req)
    write_schedule_to_file(schedule)
    
    return make_response(jsonify({
        "message": "Film ajouté à l'horaire", 
        "data": req
    }), 201)
 
# ============================================================================
# OPÉRATIONS CRUD - READ
# ============================================================================

@app.route("/schedule", methods=['GET'])
def get_all_schedules():
    # Récupérer tous les horaires
    return make_response(jsonify(schedule), 200)

@app.route("/schedule/<date>", methods=['GET'])
def get_schedule_by_date(date):
    # Récupérer les horaires pour une date spécifique
    filtered_schedule = [item for item in schedule if item.get('date') == date]
    
    if filtered_schedule:
        return make_response(jsonify(filtered_schedule), 200)
    else:
        return make_response(jsonify({"error": "Aucun horaire trouvé pour cette date"}), 404)

@app.route("/schedule/movie/<movieid>", methods=['GET'])
def get_schedule_by_movie(movieid):
    # Récupérer tous les horaires d'un film spécifique
    filtered_schedule = [item for item in schedule if item.get('movieid') == movieid]
    
    if filtered_schedule:
        return make_response(jsonify(filtered_schedule), 200)
    else:
        return make_response(jsonify({"error": "Aucun horaire trouvé pour ce film"}), 404)


# ============================================================================
# OPÉRATIONS CRUD - DELETE
# ============================================================================

@app.route("/schedule/<movieid>/<date>", methods=['DELETE'])
def delete_schedule(movieid, date):
    # Supprimer un horaire spécifique (film + date)
    global schedule
    original_length = len(schedule)
    
    # Filtrer pour supprimer l'horaire correspondant
    schedule = [item for item in schedule if not (
        item.get('movieid') == movieid and item.get('date') == date
    )]
    
    if len(schedule) < original_length:
        write_schedule_to_file(schedule)
        return make_response(jsonify({"message": "Horaire supprimé avec succès"}), 200)
    else:
        return make_response(jsonify({"error": "Horaire non trouvé"}), 404)

@app.route("/schedule/date/<date>", methods=['DELETE'])
def delete_all_schedules_for_date(date):
    # Supprimer tous les horaires d'une date
    global schedule
    original_length = len(schedule)
    
    # Filtrer pour supprimer tous les horaires de la date
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
