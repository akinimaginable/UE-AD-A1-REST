from flask import Flask, render_template, request, jsonify, make_response
import json
from werkzeug.exceptions import NotFound

app = Flask(__name__)

PORT = 3202
HOST = '0.0.0.0'

with open('{}/databases/times.json'.format("."), "r") as jsf:
   schedule = json.load(jsf)["schedule"]

def write(data):
    with open('{}/databases/times.json'.format("."), "w") as jsf:
        json.dump({"schedule": data}, jsf, indent=4)

@app.route("/", methods=['GET'])
def home():
   return "<h1 style='color:blue'>Bienvenue dans le service Horaires!</h1>"

# CREATE - Ajouter un film dans l'horaire
@app.route("/schedule", methods=['POST'])
def add_movie_to_schedule():
    req = request.get_json()
    if not req or 'movieid' not in req or 'date' not in req:
        return make_response(jsonify({"error": "movieid et date requis"}), 400)
    
    # Vérifier si le film n'est pas déjà programmé à cette date/heure
    for item in schedule:
        if item.get('movieid') == req['movieid'] and item.get('date') == req['date'] and item.get('time') == req.get('time'):
            return make_response(jsonify({"error": "Film déjà programmé à cette date/heure"}), 409)
    
    schedule.append(req)
    write(schedule)
    return make_response(jsonify({"message": "Film ajouté à l'horaire", "data": req}), 201)
 
# READ - Récupérer tous les horaires
@app.route("/schedule", methods=['GET'])
def get_all_schedules():
    return make_response(jsonify(schedule), 200)

# READ - Récupérer un horaire par date
@app.route("/schedule/<date>", methods=['GET'])
def get_schedule_by_date(date):
    filtered_schedule = [item for item in schedule if item.get('date') == date]
    if filtered_schedule:
        return make_response(jsonify(filtered_schedule), 200)
    else:
        return make_response(jsonify({"error": "Aucun horaire trouvé pour cette date"}), 404)

# READ - Récupérer les horaires d'un film spécifique
@app.route("/schedule/movie/<movieid>", methods=['GET'])
def get_schedule_by_movie(movieid):
    filtered_schedule = [item for item in schedule if item.get('movieid') == movieid]
    if filtered_schedule:
        return make_response(jsonify(filtered_schedule), 200)
    else:
        return make_response(jsonify({"error": "Aucun horaire trouvé pour ce film"}), 404)


# DELETE - Supprimer un horaire par movieid et date
@app.route("/schedule/<movieid>/<date>", methods=['DELETE'])
def delete_schedule(movieid, date):
    global schedule
    original_length = len(schedule)
    schedule = [item for item in schedule if not (item.get('movieid') == movieid and item.get('date') == date)]
    
    if len(schedule) < original_length:
        write(schedule)
        return make_response(jsonify({"message": "Horaire supprimé avec succès"}), 200)
    else:
        return make_response(jsonify({"error": "Horaire non trouvé"}), 404)

# DELETE - Supprimer tous les horaires d'une date
@app.route("/schedule/date/<date>", methods=['DELETE'])
def delete_all_schedules_for_date(date):
    global schedule
    original_length = len(schedule)
    schedule = [item for item in schedule if item.get('date') != date]
    
    if len(schedule) < original_length:
        write(schedule)
        return make_response(jsonify({"message": f"Tous les horaires du {date} ont été supprimés"}), 200)
    else:
        return make_response(jsonify({"error": "Aucun horaire trouvé pour cette date"}), 404)

if __name__ == "__main__":
   print("Server running in port %s"%(PORT))
   app.run(host=HOST, port=PORT)
