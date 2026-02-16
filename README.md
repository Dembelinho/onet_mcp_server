# ONET MCP Server

Un serveur **MCP** léger et performant conçu pour interroger l'API **O*NET Web Services**. Il fournit des fiches métiers structurées et enrichies pour les agents d'IA. 
Il expose ses outils via le transport **SSE (Server-Sent Events)**.
Le serveur expose deux tools MCP:
- recherche de metier par mot-cle
- rapport complet d'un metier a partir d'un code SOC

## Fonctionnalites ✨
* **Protocole MCP complet** : Support du transport SSE pour une communication fluide.
* **Recherche intelligente** : Recherche de métiers par mot-clé (retourne les codes SOC).
* **Enrichissement de données** : Génération de rapports complets (Tâches, Skills, Knowledge, Tech, Education, etc.).
* **Performance** : Agrégation asynchrone des appels API O*NET (via `httpx` et `asyncio.gather`) pour des réponses rapides.

## Prerequis 🛠️
- Python 3.10+
- Une cle API O*NET (Web Services) valide

## Installation

```bash
# Créer un environnement virtuel
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration
Creer un fichier `.env` a la racine du projet:
```
ONET_API_KEY=VOTRE_CLE_API
PORT=8000
```

## Lancer le serveur

```bash
python main.py
```
Le serveur démarrera sur `http://0.0.0.0:8000/sse`

### Utilisation (Agent AI)

Vous pouvez connecter un agent Python (dans un autre projet) à ce serveur pour lui donner accès aux données O*NET.

**Installation du client dans votre autre projet :**

```bash
pip install mcp

```

**Exemple de code pour l'Agent :**

```python
import asyncio
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

# URL de votre serveur déployé (ou localhost)
SERVER_URL = "http://localhost:8000/sse" 
# En production ex: "https://onet.votre-domaine.com/sse"

async def run_agent_tool():
    # Connexion au flux SSE
    async with sse_client(SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            # 1. Initialisation (Handshake)
            await session.initialize()
            
            # 2. Lister les outils disponibles
            tools = await session.list_tools()
            print(f"Outils connectés : {[t.name for t in tools.tools]}")

            # 3. Exécuter un outil (Ex: Rechercher un métier)
            print("--- Recherche 'Python Developer' ---")
            search_result = await session.call_tool(
                "search_occupation",
                arguments={"keyword": "Python Developer"}
            )
            print(search_result.content[0].text)

            # 4. Exécuter un outil (Ex: Détails d'un code SOC)
            print("\n--- Détails pour SOC 15-1252.00 ---")
            details_result = await session.call_tool(
                "get_occupation_details",
                arguments={"soc_code": "15-1252.00"}
            )
            print(details_result.content[0].text)

if __name__ == "__main__":
    asyncio.run(run_agent_tool())

```


## 🧰 Tools Disponibles

1) `search_occupation`
Recherche des métiers correspondants à un mot-clé.
- **Input :** `keyword` (str)
- **Output :** liste Markdown des metiers et codes SOC correspondants.

2) `get_occupation_details`
Récupère la fiche complète d'un métier via son code SOC.
- Entree: `soc_code` (str)
- Sortie: Rapport metier complet au format Markdown

## 📂 Structure du projet
* `main.py`: point d'entree du serveur (Configuration Starlette/SSE & Routes MCP)
* `app/`
* `client.py` : Client HTTP asynchrone pour l'API O*NET.
* `logic.py` : Logique métier et orchestration des appels.
* `formatters.py` : Transformation des données JSON brutes en Markdown lisible pour les LLMs.
* `requirements.txt`: dependances
* `Dockerfile` : Configuration pour la conteneurisation.

## Notes
* Les appels API vers O*NET sont parallélisés pour garantir que la génération du rapport complet (qui nécessite ~10 appels API distincts) reste rapide.
* Le formatage Markdown est optimisé pour être facilement ingéré et compris par les LLMs.