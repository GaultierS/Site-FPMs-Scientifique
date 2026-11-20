from datetime import datetime
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError
from .models import (
    db,
    Utilisateur,
    Outil,
    AjouteRetire,
    Panier,
    Contient,
    ChangeEtat,
    Imprimante,
    Impression,
    Local,
    Etat,
    Reservation,
)

api = Blueprint("api", __name__)


def parse_iso_datetime(value: str) -> datetime:
    """Convertit une chaîne ISO 8601 (ex: '2026-11-20T14:00:00Z') en objet datetime."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# ==========================================
# 1. OUTILS & GESTION DES STOCKS
# ==========================================

@api.get("/outils")
def list_outils():
    outils = Outil.query.order_by(Outil.nom.asc()).all()
    return jsonify([o.to_dict() for o in outils])


@api.post("/outils")
def create_outil():
    data = request.get_json() or {}
    if not data.get("nom"):
        return jsonify({"error": "Le nom de l'outil est requis"}), 400

    outil = Outil(
        nom=data["nom"],
        quantite_disponible=data.get("quantite_disponible", 0),
        image=data.get("image"),
    )
    db.session.add(outil)
    db.session.commit()
    return jsonify(outil.to_dict()), 201


@api.post("/outils/<int:id_outil>/mouvement")
def mouvement_stock(id_outil):
    """Ajoute ou retire du stock avec traçabilité dans AjouteRetire."""
    data = request.get_json() or {}
    quantite = data.get("quantite")
    id_sso = data.get("id_sso")

    if quantite is None or not id_sso:
        return jsonify({"error": "quantite et id_sso sont requis"}), 400

    outil = db.session.get(Outil, id_outil)
    if not outil:
        return jsonify({"error": "Outil introuvable"}), 404

    if outil.quantite_disponible + quantite < 0:
        return jsonify({"error": "Stock insuffisant pour effectuer ce retrait"}), 400

    outil.quantite_disponible += quantite
    mouvement = AjouteRetire(
        id_outil=id_outil,
        id_sso=id_sso,
        quantite=quantite,
        motif=data.get("motif"),
    )
    db.session.add(mouvement)
    db.session.commit()
    return jsonify(outil.to_dict())


# ==========================================
# 2. PANIERS D'EMPRUNT
# ==========================================

@api.get("/paniers")
def list_paniers():
    paniers = Panier.query.order_by(Panier.date_creation.desc()).all()
    return jsonify([p.to_dict() for p in paniers])


@api.post("/paniers")
def create_panier():
    """
    Crée un panier et décrémente les stocks de manière atomique.
    Attendu : {"id_sso": "...", "outils": [{"id_outil": 1, "quantite": 2}]}
    """
    data = request.get_json() or {}
    id_sso = data.get("id_sso")
    items = data.get("outils", [])

    if not id_sso or not items:
        return jsonify({"error": "id_sso et une liste d'outils non vide sont requis"}), 400

    try:
        panier = Panier(createur_id_sso=id_sso, statut="en_attente")
        db.session.add(panier)
        db.session.flush()  # Récupère l'id_panier avant le commit

        for item in items:
            # Verrouillage de la ligne (SELECT FOR UPDATE) sous PostgreSQL pour éviter les accès concurrents
            outil = db.session.query(Outil).filter_by(id_outil=item["id_outil"]).with_for_update().first()
            qte = item.get("quantite", 1)

            if not outil or outil.quantite_disponible < qte:
                db.session.rollback()
                return jsonify({"error": f"Stock insuffisant pour l'outil ID {item['id_outil']}"}), 400

            outil.quantite_disponible -= qte
            db.session.add(Contient(id_outil=outil.id_outil, id_panier=panier.id_panier, quantite=qte))

        db.session.add(ChangeEtat(id_panier=panier.id_panier, id_sso=id_sso, nouveau_statut="en_attente"))
        db.session.commit()
        return jsonify(panier.to_dict()), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Utilisateur SSO invalide ou contrainte violée"}), 400


@api.patch("/paniers/<int:id_panier>/statut")
def update_panier_statut(id_panier):
    """Change le statut d'un panier et recrédite le stock si rendu ou refusé."""
    data = request.get_json() or {}
    nouveau_statut = data.get("statut")
    id_sso = data.get("id_sso")

    if not nouveau_statut or not id_sso:
        return jsonify({"error": "statut et id_sso sont requis"}), 400

    panier = db.session.get(Panier, id_panier)
    if not panier:
        return jsonify({"error": "Panier introuvable"}), 404

    # Si le panier passe à "rendu" ou "refuse" (et ne l'était pas déjà), on remet les outils en stock
    statuts_retour = {"rendu", "refuse"}
    if nouveau_statut in statuts_retour and panier.statut not in statuts_retour:
        for ligne in panier.outils_assoc:
            ligne.outil.quantite_disponible += ligne.quantite

    panier.statut = nouveau_statut
    db.session.add(ChangeEtat(id_panier=id_panier, id_sso=id_sso, nouveau_statut=nouveau_statut))
    db.session.commit()
    return jsonify(panier.to_dict())


# ==========================================
# 3. RÉSERVATIONS (IMPRIMANTES & LOCAUX)
# ==========================================

@api.get("/reservations")
def list_reservations():
    reservations = Reservation.query.order_by(Reservation.debut.asc()).all()
    return jsonify([r.to_dict() for r in reservations])


@api.post("/reservations")
def create_reservation():
    data = request.get_json() or {}
    try:
        debut = parse_iso_datetime(data["debut"])
        fin = parse_iso_datetime(data["fin"])
        id_sso = data["id_sso"]
        id_etat = data["id_etat"]
        id_imprimante = data.get("id_imprimante")
        id_local = data.get("id_local")
    except (KeyError, ValueError):
        return jsonify({"error": "Champs obligatoires manquants ou format de date ISO invalide"}), 400

    if fin <= debut:
        return jsonify({"error": "La date de fin doit être postérieure au début"}), 400

    if bool(id_imprimante) == bool(id_local):
        return jsonify({"error": "Vous devez cibler soit une imprimante, soit un local (exclusivement)"}), 400

    # Vérification des chevauchements horaires sur la ressource demandée
    conflit_query = Reservation.query.filter(
        Reservation.debut < fin,
        Reservation.fin > debut,
    )
    if id_imprimante:
        conflit_query = conflit_query.filter(Reservation.id_imprimante == id_imprimante)
    else:
        conflit_query = conflit_query.filter(Reservation.id_local == id_local)

    if conflit_query.first():
        return jsonify({"error": "Ce créneau est déjà réservé pour cette ressource"}), 409

    reservation = Reservation(
        debut=debut,
        fin=fin,
        id_sso=id_sso,
        id_etat=id_etat,
        id_imprimante=id_imprimante,
        id_local=id_local,
        commentaire=data.get("commentaire"),
        groupe=data.get("groupe"),
    )
    db.session.add(reservation)
    db.session.commit()
    return jsonify(reservation.to_dict()), 201


# ==========================================
# 4. IMPRESSIONS 3D & RESSOURCES
# ==========================================

@api.get("/impressions")
def list_impressions():
    impressions = Impression.query.order_by(Impression.date_envoi.desc()).all()
    return jsonify([i.to_dict() for i in impressions])


@api.post("/impressions")
def create_impression():
    data = request.get_json() or {}
    requis = ["fichier", "type_fil", "couleur", "id_sso"]
    if any(not data.get(k) for k in requis):
        return jsonify({"error": f"Champs requis : {', '.join(requis)}"}), 400

    impression = Impression(
        fichier=data["fichier"],
        taille=data.get("taille"),
        duree=data.get("duree"),
        type_fil=data["type_fil"],
        couleur=data["couleur"],
        id_sso=data["id_sso"],
        id_imprimante=data.get("id_imprimante"),
        commentaire=data.get("commentaire"),
    )
    db.session.add(impression)
    db.session.commit()
    return jsonify(impression.to_dict()), 201


@api.get("/ressources")
def list_ressources():
    """Renvoie les imprimantes, locaux et états disponibles pour peupler les formulaires Astro."""
    return jsonify({
        "imprimantes": [i.to_dict() for i in Imprimante.query.all()],
        "locaux": [l.to_dict(include_code=False) for l in Local.query.all()],
        "etats": [e.to_dict() for e in Etat.query.all()],
    })





""" from flask import Blueprint, jsonify

api = Blueprint("api", __name__)


@api.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "message": "Flask fonctionne correctement"
    }) """
