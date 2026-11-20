from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint

# Initialisation de db ici (comme dans votre exemple Docker) pour éviter les imports circulaires
db = SQLAlchemy() # les classes db.x vont hériter de tous les pouvoirs de SQL ALCHEMY


def utcnow():        # évite les bugs  de fuseaux horaires du serveur (th + notation moderne)
    return datetime.now(timezone.utc)


# Table d'association N:N pure : Utilisateur <-> Flag ("Possede")
utilisateur_flag = db.Table(
    "utilisateur_flag",
    db.Column("id_sso", db.String(100), db.ForeignKey("utilisateur.id_sso", ondelete="CASCADE"), primary_key=True), # 2 utilisateurs ne peuvent donc pas posséder le même flag / le même id
    db.Column("id_flag", db.Integer, db.ForeignKey("flag.id_flag", ondelete="CASCADE"), primary_key=True),      #ondelete casade = si utili ou flag supp -> toutes ses lignes correspondantes dans cette table seront supp
)


class Utilisateur(db.Model):
    __tablename__ = "utilisateur"

    id_sso = db.Column(db.String(100), primary_key=True)
    # Cache des infos SSO pour l'affichage et les notifications sans dépendre du serveur SSO
    nom = db.Column(db.String(100), nullable=True)
    prenom = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(150), unique=True, nullable=True)

    # Relations
    flags = db.relationship("Flag", secondary=utilisateur_flag, back_populates="utilisateurs")  #db.relationship = raccourci python -> si on a un obet imp -> on peut écrire imp.utilisateur.email pour lire directement l'email sans écrire de jointure sql (jointure <- combine des informations)
    paniers_crees = db.relationship("Panier", foreign_keys="Panier.createur_id_sso", back_populates="createur")
    changements_etat = db.relationship("ChangeEtat", back_populates="utilisateur")
    mouvements_outils = db.relationship("AjouteRetire", back_populates="utilisateur")
    impressions = db.relationship("Impression", back_populates="utilisateur")
    reservations = db.relationship("Reservation", back_populates="utilisateur")

    def to_dict(self):
        return {
            "id_sso": self.id_sso,
            "nom": self.nom,
            "prenom": self.prenom,
            "email": self.email,
            "flags": [f.nom for f in self.flags],
        }


class Flag(db.Model):
    __tablename__ = "flag"

    id_flag = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), unique=True, nullable=False)

    utilisateurs = db.relationship("Utilisateur", secondary=utilisateur_flag, back_populates="flags")

    def to_dict(self):
        return {"id_flag": self.id_flag, "nom": self.nom}


class Outil(db.Model):
    __tablename__ = "outil"

    id_outil = db.Column(db.Integer, primary_key=True)   # integer + ..=True -> implémente automatiquement 1,2,3...
    nom = db.Column(db.String(120), nullable=False)
    quantite_disponible = db.Column(db.Integer, nullable=False, default=0)
    image = db.Column(db.String(255), nullable=True)

    __table_args__ = (
        CheckConstraint("quantite_disponible >= 0", name="check_outil_quantite_positive"),
    )

    mouvements = db.relationship("AjouteRetire", back_populates="outil", cascade="all, delete-orphan")
    paniers_assoc = db.relationship("Contient", back_populates="outil")

    def to_dict(self):
        return {
            "id_outil": self.id_outil,
            "nom": self.nom,
            "quantite_disponible": self.quantite_disponible,
            "image": self.image,
        }


class AjouteRetire(db.Model):
    """Journal des entrées/sorties de stock (ajout, perte, casse)"""
    __tablename__ = "ajoute_retire"

    id_mouvement = db.Column(db.Integer, primary_key=True)
    id_outil = db.Column(db.Integer, db.ForeignKey("outil.id_outil", ondelete="CASCADE"), nullable=False)
    id_sso = db.Column(db.String(100), db.ForeignKey("utilisateur.id_sso"), nullable=False)
    date_ajout = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    quantite = db.Column(db.Integer, nullable=False)  # Positif = ajout, Négatif = retrait
    motif = db.Column(db.String(255), nullable=True)

    outil = db.relationship("Outil", back_populates="mouvements")
    utilisateur = db.relationship("Utilisateur", back_populates="mouvements_outils")


class Panier(db.Model):
    __tablename__ = "panier"

    id_panier = db.Column(db.Integer, primary_key=True)
    statut = db.Column(db.String(50), nullable=False, default="en_attente")

    # Association "Cree" (1,1 côté Panier -> 0,N côté Utilisateur)
    createur_id_sso = db.Column(db.String(100), db.ForeignKey("utilisateur.id_sso"), nullable=False)
    date_creation = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    createur = db.relationship("Utilisateur", foreign_keys=[createur_id_sso], back_populates="paniers_crees")
    outils_assoc = db.relationship("Contient", back_populates="panier", cascade="all, delete-orphan")
    historique_etats = db.relationship("ChangeEtat", back_populates="panier", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id_panier": self.id_panier,
            "statut": self.statut,
            "createur_id_sso": self.createur_id_sso,
            "date_creation": self.date_creation.isoformat(),
            "outils": [
                {
                    "id_outil": c.id_outil,
                    "nom": c.outil.nom,
                    "quantite": c.quantite,
                }
                for c in self.outils_assoc
            ],
        }


class Contient(db.Model):
    """Association Outil <-> Panier avec quantité empruntée"""
    __tablename__ = "contient"

    id_outil = db.Column(db.Integer, db.ForeignKey("outil.id_outil"), primary_key=True)
    id_panier = db.Column(db.Integer, db.ForeignKey("panier.id_panier", ondelete="CASCADE"), primary_key=True)
    quantite = db.Column(db.Integer, nullable=False, default=1)

    __table_args__ = (
        CheckConstraint("quantite > 0", name="check_contient_quantite_positive"),
    )

    outil = db.relationship("Outil", back_populates="paniers_assoc")
    panier = db.relationship("Panier", back_populates="outils_assoc")


class ChangeEtat(db.Model):
    """Journal d'audit des changements d'état d'un panier"""
    __tablename__ = "change_etat"

    id_changement = db.Column(db.Integer, primary_key=True)
    id_panier = db.Column(db.Integer, db.ForeignKey("panier.id_panier", ondelete="CASCADE"), nullable=False)
    id_sso = db.Column(db.String(100), db.ForeignKey("utilisateur.id_sso"), nullable=False)
    nouveau_statut = db.Column(db.String(50), nullable=False)
    date_changement = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    panier = db.relationship("Panier", back_populates="historique_etats")
    utilisateur = db.relationship("Utilisateur", back_populates="changements_etat")


class Imprimante(db.Model):
    __tablename__ = "imprimante"

    id_imprimante = db.Column(db.Integer, primary_key=True)
    modele = db.Column(db.String(100), nullable=False)
    multi_filament = db.Column(db.Boolean, default=False, nullable=False)

    reservations = db.relationship("Reservation", back_populates="imprimante")
    impressions = db.relationship("Impression", back_populates="imprimante")

    def to_dict(self):
        return {
            "id_imprimante": self.id_imprimante,
            "modele": self.modele,
            "multi_filament": self.multi_filament,
        }


class Impression(db.Model):
    __tablename__ = "impression"

    id_impression = db.Column(db.Integer, primary_key=True)
    fichier = db.Column(db.String(255), nullable=False)
    taille = db.Column(db.Float, nullable=True)   # ex: poids en grammes
    duree = db.Column(db.Integer, nullable=True)  # durée estimée en minutes
    type_fil = db.Column(db.String(50), nullable=False)
    couleur = db.Column(db.String(50), nullable=False)
    statut = db.Column(db.String(50), nullable=False, default="en_attente")

    # Association "Envoie" (1,1 côté Impression -> 0,N côté Utilisateur)
    id_sso = db.Column(db.String(100), db.ForeignKey("utilisateur.id_sso"), nullable=False)
    date_envoi = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    commentaire = db.Column(db.Text, nullable=True)

    # Lien vers l'imprimante assignée
    id_imprimante = db.Column(db.Integer, db.ForeignKey("imprimante.id_imprimante"), nullable=True)

    utilisateur = db.relationship("Utilisateur", back_populates="impressions")
    imprimante = db.relationship("Imprimante", back_populates="impressions")

    def to_dict(self):
        return {
            "id_impression": self.id_impression,
            "fichier": self.fichier,
            "taille": self.taille,
            "duree": self.duree,
            "type_fil": self.type_fil,
            "couleur": self.couleur,
            "statut": self.statut,
            "id_sso": self.id_sso,
            "id_imprimante": self.id_imprimante,
            "date_envoi": self.date_envoi.isoformat(),
            "commentaire": self.commentaire,
        }


class Local(db.Model):
    __tablename__ = "local"

    id_local = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False, default="Local Principal")
    code_master_lock = db.Column(db.String(50), nullable=True)

    reservations = db.relationship("Reservation", back_populates="local")

    def to_dict(self, include_code=False):
        data = {"id_local": self.id_local, "nom": self.nom}
        # Ne renvoie le code du cadenas que si explicitement autorisé (ex: réservation validée)
        if include_code:
            data["code_master_lock"] = self.code_master_lock
        return data


class Etat(db.Model):
    __tablename__ = "etat"

    id_etat = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), unique=True, nullable=False)
    couleur = db.Column(db.String(20), nullable=False, default="#808080")

    reservations = db.relationship("Reservation", back_populates="etat")

    def to_dict(self):
        return {"id_etat": self.id_etat, "nom": self.nom, "couleur": self.couleur}


class Reservation(db.Model):
    __tablename__ = "reservation"

    id_reservation = db.Column(db.Integer, primary_key=True)

    # Fusion de dateDebut/heureDebut et dateFin/heureFin en DateTime avec fuseau horaire (PostgreSQL TIMESTAMPTZ)
    debut = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    fin = db.Column(db.DateTime(timezone=True), nullable=False, index=True)

    # Association "Demande" (1,1 côté Reservation -> 0,N côté Utilisateur)
    id_sso = db.Column(db.String(100), db.ForeignKey("utilisateur.id_sso"), nullable=False)
    commentaire = db.Column(db.Text, nullable=True)
    groupe = db.Column(db.String(100), nullable=True)

    # Association "Possede" vers Etat (1,1 -> 0,N)
    id_etat = db.Column(db.Integer, db.ForeignKey("etat.id_etat"), nullable=False)

    # Associations "Concerne" (0,1 -> 0,N) vers Imprimante OU Local
    id_imprimante = db.Column(db.Integer, db.ForeignKey("imprimante.id_imprimante"), nullable=True)
    id_local = db.Column(db.Integer, db.ForeignKey("local.id_local"), nullable=True)

    __table_args__ = (
        CheckConstraint("fin > debut", name="check_reservation_dates_valides"),
        # Garantit qu'une réservation cible soit une imprimante, soit un local (jamais les deux, jamais aucun)
        CheckConstraint(
            "(id_imprimante IS NOT NULL AND id_local IS NULL) OR (id_imprimante IS NULL AND id_local IS NOT NULL)",
            name="check_cible_reservation_exclusive",
        ),
    )

    utilisateur = db.relationship("Utilisateur", back_populates="reservations")
    etat = db.relationship("Etat", back_populates="reservations")
    imprimante = db.relationship("Imprimante", back_populates="reservations")
    local = db.relationship("Local", back_populates="reservations")

    def to_dict(self):
        return {
            "id_reservation": self.id_reservation,
            "debut": self.debut.isoformat(),
            "fin": self.fin.isoformat(),
            "id_sso": self.id_sso,
            "commentaire": self.commentaire,
            "groupe": self.groupe,
            "etat": self.etat.to_dict() if self.etat else None,
            "id_imprimante": self.id_imprimante,
            "id_local": self.id_local,
        }