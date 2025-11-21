import json
import os
from urllib.parse import quote_plus

import requests
from flask import Flask, request, jsonify, make_response
from pymongo import MongoClient

# Configuration de l'application Flask
app = Flask(__name__)
PORT = 3200
HOST = '0.0.0.0'

is_admin_cache = {}

JSON_FILE_PATH = '{}/databases/movies.json'.format(".")
PERSISTENCE_TYPE = os.getenv("PERSISTENCE_TYPE", "MONGODB").upper()
default_password = quote_plus("*65%8XPuGaQ#")
MONGO_URL = os.getenv("MONGO_URL", f"mongodb://root:{default_password}@localhost:27017/")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:3203")

client = None
db = None
collection = None
movies = []

if PERSISTENCE_TYPE == "MONGODB":
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    db = client["movies"]
    collection = db["movies"]

    if collection.count_documents({}) == 0:
        with open(JSON_FILE_PATH, 'r') as jsf:
            movies_data = json.load(jsf)["movies"]
            if movies_data:
                collection.insert_many(movies_data)
                print("Films chargés:", len(movies_data), "films (MongoDB)")
    else:
        print(f"Base MongoDB déjà initialisée ({collection.count_documents({})} films)")
else:
    with open(JSON_FILE_PATH, 'r') as jsf:
        movies = json.load(jsf)["movies"]
        print("Films chargés:", len(movies), "films (JSON)")


def write_movies_to_file(movies_data):
    # Sauvegarde les données de films dans le fichier JSON
    with open(JSON_FILE_PATH, 'w') as f:
        full = {}
        full['movies'] = movies_data
        json.dump(full, f, indent=4)


def check_admin(author) -> bool:
    # Vérifie si l'utilisateur est un administrateur
    if author in is_admin_cache:
        return is_admin_cache[author]

    try:
        resp = requests.get(f"{USER_SERVICE_URL}/users/{author}")
        if resp.status_code == 200:
            data = resp.json()
            is_admin = data.get("role", "") == "admin"
            is_admin_cache[author] = is_admin
            return is_admin
        else:
            return False
    except Exception as e:
        return False


# ============================================================================
# ROUTES DE L'API
# ============================================================================

# Route pour l'accueil du service Movie
@app.route("/", methods=['GET'])
def home():
    # Page d'accueil du service Movie
    return make_response("<h1 style='color:blue'>Bienvenue dans le service Films!</h1>", 200)


# ============================================================================
# OPÉRATIONS CRUD - READ
# ============================================================================

# Route pour récupérer tous les films
@app.route("/json", methods=['GET'])
def get_all_movies():
    # Récupérer tous les films
    if PERSISTENCE_TYPE == "MONGODB":
        movies_list = list(collection.find({}))
        for movie in movies_list:
            if '_id' in movie:
                movie['_id'] = str(movie['_id'])
        return make_response(jsonify(movies_list), 200)
    return make_response(jsonify(movies), 200)


# Route pour récupérer un film par son titre
@app.route("/moviesbytitle", methods=['GET'])
def get_movie_by_title():
    # Récupérer un film par son titre
    if not request.args or 'title' not in request.args:
        return make_response(jsonify({"error": "Paramètre 'title' requis"}), 400)

    title = request.args['title']

    if PERSISTENCE_TYPE == "MONGODB":
        movie = collection.find_one({"title": {"$regex": f"^{title}$", "$options": "i"}})
        if movie:
            if '_id' in movie:
                movie['_id'] = str(movie['_id'])
            return make_response(jsonify(movie), 200)
    else:
        # Recherche du film par titre
        for movie in movies:
            if str(movie["title"]).lower() == str(title).lower():
                return make_response(jsonify(movie), 200)

    return make_response(jsonify({"error": "Titre de film non trouvé"}), 404)


# Route pour récupérer un film par son ID
@app.route("/movies/<movieid>", methods=['GET'])
def get_movie_by_id(movieid):
    # Récupérer un film par son ID
    if PERSISTENCE_TYPE == "MONGODB":
        movie = collection.find_one({"id": str(movieid)})
        if movie:
            if '_id' in movie:
                movie['_id'] = str(movie['_id'])
            return make_response(jsonify(movie), 200)
    else:
        for movie in movies:
            if str(movie["id"]) == str(movieid):
                return make_response(jsonify(movie), 200)

    return make_response(jsonify({"error": "Film ID non trouvé"}), 404)


# ============================================================================
# OPÉRATIONS CRUD - CREATE
# ============================================================================

# Route pour ajouter un film
@app.route("/movies/<movieid>", methods=['POST'])
def add_movie(movieid):
    req = request.get_json()
    if not req:
        return make_response(jsonify({"error": "Données JSON requises"}), 400)

    author = req.get('author', None)
    if not check_admin(author):
        return make_response(jsonify({"error": "Accès refusé, administrateur requis"}), 403)

    if PERSISTENCE_TYPE == "MONGODB":
        existing = collection.find_one({"id": str(movieid)})
        if existing:
            return make_response(jsonify({"error": "Film ID déjà existant"}), 409)
        collection.insert_one(req)
        if '_id' in req:
            req['_id'] = str(req['_id'])
    else:
        # Vérification de l'unicité de l'ID
        for movie in movies:
            if str(movie["id"]) == str(movieid):
                return make_response(jsonify({"error": "Film ID déjà existant"}), 409)

        # Ajout du nouveau film
        movies.append(req)
        write_movies_to_file(movies)

    return make_response(jsonify({"message": "Film ajouté avec succès", "data": req}), 201)


# ============================================================================
# OPÉRATIONS CRUD - UPDATE
# ============================================================================

# Route pour mettre à jour la note d'un film
@app.route("/movies/<movieid>/<rate>", methods=['PUT'])
def update_movie_rating(movieid, rate):
    req = request.get_json()
    if not req:
        return make_response(jsonify({"error": "Données JSON requises"}), 400)

    author = req.get('author', None)
    if not check_admin(author):
        return make_response(jsonify({"error": "Accès refusé, administrateur requis"}), 403)

    if PERSISTENCE_TYPE == "MONGODB":
        result = collection.update_one({"id": str(movieid)}, {"$set": {"rating": rate}})
        if result.matched_count == 0:
            return make_response(jsonify({"error": "Film ID non trouvé"}), 404)
        movie = collection.find_one({"id": str(movieid)})
        if movie and '_id' in movie:
            movie['_id'] = str(movie['_id'])
        return make_response(jsonify({"message": "Note mise à jour avec succès", "data": movie}), 200)
    else:
        # Mettre à jour la note d'un film
        for movie in movies:
            if str(movie["id"]) == str(movieid):
                movie["rating"] = rate
                write_movies_to_file(movies)
                return make_response(jsonify({"message": "Note mise à jour avec succès", "data": movie}), 200)

    return make_response(jsonify({"error": "Film ID non trouvé"}), 404)


# ============================================================================
# OPÉRATIONS CRUD - DELETE
# ============================================================================

# Route pour supprimer un film
@app.route("/movies/<movieid>", methods=['DELETE'])
def delete_movie(movieid):
    req = request.get_json()
    if not req:
        return make_response(jsonify({"error": "Données JSON requises"}), 400)

    author = req.get('author', None)
    if not check_admin(author):
        return make_response(jsonify({"error": "Accès refusé, administrateur requis"}), 403)

    if PERSISTENCE_TYPE == "MONGODB":
        result = collection.delete_one({"id": str(movieid)})
        if result.deleted_count == 0:
            return make_response(jsonify({"error": "Film ID non trouvé"}), 404)
        return make_response(jsonify({"message": "Film supprimé avec succès"}), 200)
    else:
        # Supprimer un film
        for movie in movies:
            if str(movie["id"]) == str(movieid):
                movies.remove(movie)
                write_movies_to_file(movies)
                return make_response(jsonify({"message": "Film supprimé avec succès", "data": movie}), 200)

    return make_response(jsonify({"error": "Film ID non trouvé"}), 404)


# ============================================================================
# DÉMARRAGE DU SERVEUR
# ============================================================================

if __name__ == "__main__":
    print("Server running in port %s" % (PORT))
    app.run(host=HOST, port=PORT)
