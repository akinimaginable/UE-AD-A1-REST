# UE-AD-A1-REST - Application de Gestion de Cinéma

Application de gestion de salle de cinéma composée de 4 micro-services REST.

Pour la première partie ne vous souciez pas des fichiers Docker, cela sera abordé par la suite en séance 4.

## Architecture des Services

L'application est composée de 4 micro-services interconnectés :

- **User** (port 3203) : Gestion des utilisateurs et authentification
- **Movie** (port 3200) : Gestion du catalogue de films
- **Schedule** (port 3202) : Gestion de la programmation des films par date
- **Booking** (port 3201) : Gestion des réservations des utilisateurs

## Relations entre Services

### Movie → User
Le service Movie appelle User pour vérifier les droits d'administration avant d'autoriser certaines opérations (création, modification, suppression de films).

**Routes concernées :**
- `POST /movies/<movieid>` → appelle `GET /users/<userid>` pour vérifier le rôle admin
- `PUT /movies/<movieid>/<rate>` → appelle `GET /users/<userid>` pour vérifier le rôle admin
- `DELETE /movies/<movieid>` → appelle `GET /users/<userid>` pour vérifier le rôle admin

### Booking → User
Le service Booking appelle User pour vérifier les droits d'administration pour l'accès à toutes les réservations.

**Routes concernées :**
- `GET /bookings?userid=<userid>` → appelle `GET /users/<userid>` pour vérifier le rôle admin

### Booking → Movie
Le service Booking appelle Movie pour récupérer les détails complets d'un film lors de la création d'une réservation ou de la consultation des réservations détaillées.

**Routes concernées :**
- `POST /bookings` → appelle `GET /movies/<movieid>` pour vérifier l'existence du film
- `GET /bookings/<userid>/detailed` → appelle `GET /movies/<movieid>` pour enrichir les réservations avec les détails des films

### Booking → Schedule
Le service Booking appelle Schedule pour vérifier qu'un film est bien programmé à une date donnée avant de créer une réservation.

**Routes concernées :**
- `POST /bookings` → appelle `GET /schedule/<movieid>/<date>` pour valider la programmation
- `GET /bookings/<userid>/detailed` → appelle `GET /schedule/<movieid>/<date>` pour enrichir les réservations avec les horaires

## Routes Inter-Services (Routes utilisant 2+ services)

### 1. POST /bookings - Création de réservation
**Services impliqués : Booking + Movie + Schedule**

Crée une nouvelle réservation en validant le film et la programmation.
- Vérifie l'existence du film via Movie
- Vérifie la programmation via Schedule
- Enregistre la réservation

**Payload :**
```json
{
    "userid": "chris_rivers",
    "movieid": "720d006c-3a57-4b6a-b18f-9b713b073f3c",
    "date": "20151130"
}
```

### 2. GET /bookings/<userid>/detailed - Réservations détaillées
**Services impliqués : Booking + Movie + Schedule**

Récupère les réservations d'un utilisateur enrichies avec les détails complets des films et de la programmation.
- Récupère les réservations de l'utilisateur
- Pour chaque réservation, enrichit avec les détails du film (Movie)
- Pour chaque réservation, enrichit avec les horaires (Schedule)

**Réponse :**
```json
{
    "userid": "chris_rivers",
    "bookings": [
        {
            "date": "20151130",
            "movies": [
                {
                    "movie": {
                        "id": "720d006c-3a57-4b6a-b18f-9b713b073f3c",
                        "title": "Creed",
                        "rating": 8.8,
                        "director": "Ryan Coogler"
                    },
                    "schedule": {
                        "date": "20151130",
                        "movieid": "720d006c-3a57-4b6a-b18f-9b713b073f3c",
                        "available": true
                    }
                }
            ]
        }
    ]
}
```

### 3. GET /bookings?userid=<admin_userid> - Toutes les réservations (admin)
**Services impliqués : Booking + User**

Récupère toutes les réservations (accès réservé aux administrateurs).
- Vérifie le rôle admin de l'utilisateur via User
- Retourne toutes les réservations si autorisé

### 4. POST /movies/<movieid> - Ajout de film
**Services impliqués : Movie + User**

Ajoute un nouveau film au catalogue (accès réservé aux administrateurs).
- Vérifie le rôle admin via User
- Ajoute le film si autorisé

**Payload :**
```json
{
    "author": "chris_rivers",
    "id": "new-movie-id",
    "title": "Nouveau Film",
    "rating": 7.5,
    "director": "Réalisateur"
}
```

### 5. PUT /movies/<movieid>/<rate> - Mise à jour de note
**Services impliqués : Movie + User**

Met à jour la note d'un film (accès réservé aux administrateurs).
- Vérifie le rôle admin via User
- Met à jour la note si autorisé

**Payload :**
```json
{
    "author": "chris_rivers"
}
```

### 6. DELETE /movies/<movieid> - Suppression de film
**Services impliqués : Movie + User**

Supprime un film du catalogue (accès réservé aux administrateurs).
- Vérifie le rôle admin via User
- Supprime le film si autorisé

**Payload :**
```json
{
    "author": "chris_rivers"
}
```

## API Endpoints par Service

### User Service (Port 3203)

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/` | Page d'accueil |
| GET | `/users` | Liste tous les utilisateurs |
| GET | `/users/<userid>` | Récupère un utilisateur par ID |
| GET | `/users/admin` | Liste les administrateurs |
| POST | `/users` | Ajoute un nouvel utilisateur |
| PUT | `/users/<userid>` | Met à jour un utilisateur |
| DELETE | `/users/<userid>` | Supprime un utilisateur |

### Movie Service (Port 3200)

| Méthode | Route | Description | Inter-service |
|---------|-------|-------------|---------------|
| GET | `/` | Page d'accueil | - |
| GET | `/json` | Liste tous les films | - |
| GET | `/moviesbytitle?title=<title>` | Récupère un film par titre | - |
| GET | `/movies/<movieid>` | Récupère un film par ID | - |
| POST | `/movies/<movieid>` | Ajoute un film (admin) | → User |
| PUT | `/movies/<movieid>/<rate>` | Met à jour la note (admin) | → User |
| DELETE | `/movies/<movieid>` | Supprime un film (admin) | → User |

### Schedule Service (Port 3202)

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/` | Page d'accueil |
| GET | `/schedule` | Liste tous les horaires |
| GET | `/schedule/<date>` | Récupère les horaires pour une date |
| GET | `/schedule/movie/<movieid>` | Récupère les dates d'un film |
| GET | `/schedule/<movieid>/<date>` | Vérifie si un film est programmé à une date |
| POST | `/schedule` | Ajoute un horaire |
| DELETE | `/schedule/<movieid>/<date>` | Supprime un horaire spécifique |
| DELETE | `/schedule/date/<date>` | Supprime tous les horaires d'une date |

### Booking Service (Port 3201)

| Méthode | Route | Description | Inter-service |
|---------|-------|-------------|---------------|
| GET | `/` | Page d'accueil | - |
| GET | `/bookings?userid=<userid>` | Toutes les réservations (admin) | → User |
| GET | `/bookings/<userid>` | Réservations d'un utilisateur | - |
| GET | `/bookings/<userid>/detailed` | Réservations détaillées | → Movie, Schedule |
| POST | `/bookings` | Crée une réservation | → Movie, Schedule |
| DELETE | `/bookings/<userid>` | Supprime toutes les réservations d'un utilisateur | - |
| DELETE | `/bookings/<userid>/<movieid>/<date>` | Supprime une réservation spécifique | - |

## Fonctionnalités Spéciales

### Contrôle d'accès basé sur les rôles
- Les utilisateurs avec `"role": "admin"` peuvent ajouter, modifier et supprimer des films
- Les utilisateurs avec `"role": "admin"` peuvent consulter toutes les réservations
- Les utilisateurs normaux ne peuvent consulter que leurs propres réservations

### Validation croisée
- Lors de la création d'une réservation, le système vérifie :
  - Que le film existe dans le catalogue (Movie)
  - Que le film est bien programmé à la date demandée (Schedule)
  - Qu'il n'y a pas de doublon de réservation

### Enrichissement des données
- La route `/bookings/<userid>/detailed` combine les données de 3 services (Booking, Movie, Schedule) pour fournir une vue complète des réservations avec tous les détails des films et des horaires

## Démarrage des Services

Pour démarrer tous les services :

```bash
# Terminal 1 - User Service
cd user
python user.py

# Terminal 2 - Movie Service
cd movie
python movie.py

# Terminal 3 - Schedule Service
cd schedule
python schedule.py

# Terminal 4 - Booking Service
cd booking
python booking.py
```

Les services seront accessibles sur :
- User: http://localhost:3203
- Movie: http://localhost:3200
- Schedule: http://localhost:3202
- Booking: http://localhost:3201

## Utilisateurs de Test

Administrateurs :
- `chris_rivers` (role: admin)
- `peter_curley` (role: admin)

Utilisateurs normaux :
- `garret_heaton`
- `michael_scott`
- `jim_halpert`
- `pam_beesly`
- `dwight_schrute`
