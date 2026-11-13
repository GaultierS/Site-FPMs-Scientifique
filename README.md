<div align="center">

# 🔬 Site du Cercle Scientifique F.P.Ms

Site web du Cercle Scientifique de la Faculté Polytechnique de Mons.

![Astro](https://img.shields.io/badge/Frontend-Astro-BC52EE?logo=astro&logoColor=white)
![Flask](https://img.shields.io/badge/Backend-Flask-000000?logo=flask&logoColor=white)

</div>

---

## 📑 Sommaire

- [Aperçu](#-aperçu)
- [Technologies](#-technologies)
- [Structure du projet](#-structure-du-projet)
- [Installation](#-installation)
- [Lancer le projet](#-lancer-le-projet)
- [Références](#-références)

---

## 🌍 Aperçu

Ce projet est composé de deux parties :

- un **frontend** (Astro) qui affiche les pages du site ;
- un **backend** (Flask) qui gère la logique serveur et la base de données.

Les frameworks sont les mêmes que ceux utilisés par la commission web lors de la création de leurs sites fédé.

## 🛠️ Technologies

| Partie   | Framework | Port   | URL                     |
| :------- | :-------- | :----- | :---------------------- |
| Frontend | Astro     | `4321` | http://localhost:4321/  |
| Backend  | Flask     | `5000` | http://localhost:5000/  |

### Astro

Framework pour le frontend du site. Il permet de créer sans trop de difficultés des pages similaires à celles des sites fédé déjà existants. Le template utilisé est le plus simple de ceux mis à disposition par Astro (*Basics*).

### Flask

Framework pour le backend. Sa structure est plus simple que celle de Django, ce qui le rend plus adapté aux petits projets comme le nôtre.

## 📁 Structure du projet

```text
/
├── backend
│   ├── app
│   ├── instances
│   ├── requirements.txt
│   └── run.py
└── frontend
    ├── public/
    │   ├── favicon.ico
    │   └── favicon.svg
    ├── src
    │   ├── assets
    │   │   └── astro.svg
    │   ├── components
    │   │   └── Welcome.astro
    │   ├── layouts
    │   │   └── Layout.astro
    │   └── pages
    │       └── index.astro
    └── package.json
```

## ⚙️ Installation

### Frontend

```sh
cd frontend
npm install
```

### Backend

```sh
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 🚀 Lancer le projet

Il faut deux terminaux ouverts en même temps.

**Terminal 1 : Astro (frontend)**

```sh
cd frontend
npm run dev
```

➡️ Disponible sur http://localhost:4321/

**Terminal 2 : Flask (backend)**

```sh
cd backend
source venv/bin/activate
python run.py
```

➡️ Disponible sur http://localhost:5000/

### Commandes Astro utiles

| Commande          | Action                                        |
| :---------------- | :-------------------------------------------- |
| `npm install`     | Installe les dépendances                      |
| `npm run dev`     | Lance le serveur de développement             |
| `npm run build`   | Génère le site de production dans `./dist/`   |
| `npm run preview` | Prévisualise le build avant le déploiement    |

## 🔗 Références

- [Site fédé](https://github.com/CommissionWebFPMsAdmin/site-fpms) : utilise uniquement Astro, car il n'y a pas de base de données.
- [Site des cartes fédé](https://github.com/theau-pauwels/carte-fede/tree/main)
- [Documentation Astro](https://docs.astro.build)
- [Documentation Flask](https://flask.palletsprojects.com)
