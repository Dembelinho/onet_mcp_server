from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os
from app.client import OnetClient
from app import logic

# 1. Config
load_dotenv()

# 2. Initialisation des services
mcp = FastMCP("ONET Occupation Agent")
# On instancie le client ici pour qu'il soit vivant tant que le serveur tourne
try:
    onet_client = OnetClient()
except ValueError as e:
    print(f"Erreur de configuration: {e}")
    exit(1)

# 3. Définition des Tools MCP

@mcp.tool()
async def search_occupation(keyword: str) -> str:
    """
    Recherche un métier par mot-clé. Retourne une liste de métiers avec leurs codes SOC.
    """
    return await logic.search_occupation_logic(onet_client, keyword)


@mcp.tool()
async def get_occupation_details(soc_code: str) -> str:
    """
    Récupère le rapport complet d'un métier via son code SOC.
    Inclut : Description, Tâches, Tech, Skills, Knowledge, Education...
    """
    return await logic.get_details_logic(onet_client, soc_code)

if __name__ == "__main__":
    mcp.run()