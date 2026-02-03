# ONET MCP Server

Serveur MCP (Model Context Protocol) pour interroger l'API O*NET et fournir
des fiches metiers structurees. Le serveur expose deux tools MCP:
- recherche de metier par mot-cle
- rapport complet d'un metier a partir d'un code SOC

## Fonctionnalites
- Recherche de metiers par mot-cle (liste de codes SOC)
- Rapport complet: description, taches, technologies, skills, knowledge, education, etc.
- Aggregation des appels API O*NET en parallele

## Prerequis
- Python 3.10+ (recommande)
- Une cle API O*NET

## Installation
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration
Creer un fichier `.env` a la racine du projet:
```
ONET_API_KEY=VOTRE_CLE_API
```

## Lancer le serveur
```bash
python main.py
```

## Tools MCP
Le serveur expose les tools suivants:

1) `search_occupation`
- Entree: `keyword` (str)
- Sortie: liste de metiers avec leur code SOC

2) `get_occupation_details`
- Entree: `soc_code` (str)
- Sortie: fiche metier complete au format Markdown

## Structure du projet
- `main.py`: point d'entree unique (tres court)
- `app/__init__.py`: initialisation du package
- `app/client.py`: client API O*NET (appels HTTP bruts)
- `app/formatters.py`: fonctions `_format_xxx` pour les sorties
- `app/logic.py`: orchestration entre client et formatters
- `requirements.txt`: dependances Python

## Notes
- La cle API est lue depuis `ONET_API_KEY` dans le fichier `.env`.
- Les appels a l'API O*NET sont asynchrones via `httpx`.
