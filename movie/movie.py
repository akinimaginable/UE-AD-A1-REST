from flask import Flask, request, jsonify, make_response
import json

# Configuration de l'application Flask
app = Flask(__name__)
PORT = 3200
HOST = '0.0.0.0'

# Chargement de la base de données des films au démarrage
with open('{}/databases/movies.json'.format("."), 'r') as jsf:
    movies = json.load(jsf)["movies"]
    print("Films chargés:", len(movies), "films")

def write_movies_to_file(movies_data):
    # Sauvegarde les données de films dans le fichier JSON
    with open('{}/databases/movies.json'.format("."), 'w') as f:
        full = {}
        full['movies'] = movies_data
        json.dump(full, f, indent=4)

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
    return make_response(jsonify(movies), 200)

# Route pour récupérer un film par son titre
@app.route("/moviesbytitle", methods=['GET'])
def get_movie_by_title():
    # Récupérer un film par son titre
    if not request.args or 'title' not in request.args:
        return make_response(jsonify({"error": "Paramètre 'title' requis"}), 400)
    
    title = request.args['title']
    
    # Recherche du film par titre
    for movie in movies:
        if str(movie["title"]).lower() == str(title).lower():
            return make_response(jsonify(movie), 200)
    
    return make_response(jsonify({"error": "Titre de film non trouvé"}), 404)

# Route pour récupérer un film par son ID
@app.route("/movies/<movieid>", methods=['GET'])
def get_movie_by_id(movieid):
    # Récupérer un film par son ID
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
    # Ajouter un nouveau film
    req = request.get_json()
    
    if not req:
        return make_response(jsonify({"error": "Données JSON requises"}), 400)
    
    # Vérification de l'unicité de l'ID
    for movie in movies:
        if str(movie["id"]) == str(movieid):
            return make_response(jsonify({"error": "Film ID déjà existant"}), 409)
    
    # Ajout du nouveau film
    movies.append(req)
    write_movies_to_file(movies)
    
    return make_response(jsonify({
        "message": "Film ajouté avec succès",
        "data": req
    }), 201)

# ============================================================================
# OPÉRATIONS CRUD - UPDATE
# ============================================================================

# Route pour mettre à jour la note d'un film
@app.route("/movies/<movieid>/<rate>", methods=['PUT'])
def update_movie_rating(movieid, rate):
    # Mettre à jour la note d'un film
    for movie in movies:
        if str(movie["id"]) == str(movieid):
            movie["rating"] = rate
            write_movies_to_file(movies)
            return make_response(jsonify({
                "message": "Note mise à jour avec succès",
                "data": movie
            }), 200)
    
    return make_response(jsonify({"error": "Film ID non trouvé"}), 404)

# ============================================================================
# OPÉRATIONS CRUD - DELETE
# ============================================================================

# Route pour supprimer un film
@app.route("/movies/<movieid>", methods=['DELETE'])
def delete_movie(movieid):
    # Supprimer un film
    for movie in movies:
        if str(movie["id"]) == str(movieid):
            movies.remove(movie)
            write_movies_to_file(movies)
            return make_response(jsonify({
                "message": "Film supprimé avec succès",
                "data": movie
            }), 200)
    
    return make_response(jsonify({"error": "Film ID non trouvé"}), 404)

# ============================================================================
# DÉMARRAGE DU SERVEUR
# ============================================================================

if __name__ == "__main__":
    print("Server running in port %s" % (PORT))
    app.run(host=HOST, port=PORT)
