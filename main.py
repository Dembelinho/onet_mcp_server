from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from onet_client import OnetClient
import tools

# 1. Configuration
load_dotenv()

# 2. Initialisation des services
mcp = FastMCP("ONET Occupation Agent")
onet_client = OnetClient()


# 3. Définition des Tools MCP

@mcp.tool()
async def search_occupation(keyword: str) -> str:
    """
    Recherche un métier par mot-clé ou titre.
    Retourne une liste de métiers avec leurs codes SOC.

    Args:
        keyword: Le terme recherché (ex: "Cybersecurity", "Nurse").
    """
    # Délègue la logique à tools.py en passant le client
    return await tools.search_occupation_logic(onet_client, keyword)


@mcp.tool()
async def get_occupation_details(soc_code: str) -> str:
    """
    Récupère le rapport complet d'un métier via son code SOC.
    Inclut : Description, Tâches, Tech, Skills, Knowledge, Education.

    Args:
        soc_code: Le code unique obtenu via la recherche (ex: '15-1122.00').
    """
    # Délègue la logique à tools.py
    return await tools.get_details_logic(onet_client, soc_code)

if __name__ == "__main__":
    # Lancement du serveur
    mcp.run()