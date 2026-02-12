from mcp.server import Server
import mcp.types as types
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
import uvicorn
import anyio
import os
from dotenv import load_dotenv

# Imports de votre logique métier
from app.client import OnetClient
from app import logic

# 1. Configuration
load_dotenv()

# 2. Initialisation du Serveur MCP (Nom interne)
server = Server("onet-server")

# 3. Initialisation du Client API O*NET
try:
    onet_client = OnetClient()
except ValueError as e:
    print(f"FATAL: Erreur de configuration O*NET: {e}")
    exit(1)


# 4. Définition des Outils (Tools)
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_occupation",
            description="Recherche un métier par mot-clé (Ex: Data Scientist). Retourne les codes SOC.",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "Mot-clé du métier"}
                },
                "required": ["keyword"]
            }
        ),
        types.Tool(
            name="get_occupation_details",
            description="Récupère le rapport complet (Tâches, Skills, Education) via le code SOC.",
            inputSchema={
                "type": "object",
                "properties": {
                    "soc_code": {"type": "string", "description": "Le code SOC (Ex: 15-1132.00)"}
                },
                "required": ["soc_code"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    if not arguments:
        raise ValueError("Arguments requis")

    try:
        if name == "search_occupation":
            keyword = arguments.get("keyword")
            result = await logic.search_occupation_logic(onet_client, keyword)
            return [types.TextContent(type="text", text=result)]

        elif name == "get_occupation_details":
            soc_code = arguments.get("soc_code")
            result = await logic.get_details_logic(onet_client, soc_code)
            return [types.TextContent(type="text", text=result)]

        else:
            raise ValueError(f"Outil inconnu: {name}")

    except Exception as e:
        # On capture l'erreur pour la renvoyer proprement au LLM
        return [types.TextContent(type="text", text=f"Erreur lors de l'exécution de l'outil : {str(e)}")]


# 5. Gestionnaire SSE (Server-Sent Events) - Version Robuste
async def handle_sse(request: Request):
    async def event_generator():
        # Création des canaux de communication (Streams)
        read_stream, write_stream = anyio.create_memory_object_stream(10)

        # On lance le serveur MCP en tâche de fond avec ces streams
        async with server.run(read_stream, write_stream, server.create_initialization_options()) as streams:

            # 1. On indique au client où envoyer les messages POST (l'endpoint /messages)
            yield {
                "event": "endpoint",
                "data": "/messages"
            }

            # 2. On écoute les messages sortants du serveur et on les envoie au client SSE
            async for message in streams:
                if isinstance(message, types.JSONRPCMessage):
                    yield {
                        "event": "message",
                        "data": message.model_dump_json()
                    }
                elif isinstance(message, Exception):
                    yield {
                        "event": "error",
                        "data": str(message)
                    }

    return EventSourceResponse(event_generator())


# 6. Gestionnaire des Messages Entrants (POST)
async def handle_messages(request: Request):
    try:
        # On lit le JSON envoyé par Claude/Client
        data = await request.json()

        # On le valide et on l'injecte dans le serveur
        # Note: process_request injecte les données dans le read_stream créé plus haut
        await server.process_request(request.scope, request.receive, request.send)

        return JSONResponse({"status": "accepted"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status=500)


# 7. Configuration Starlette
routes = [
    Route("/sse", endpoint=handle_sse),
    Route("/messages", endpoint=handle_messages, methods=["POST"])
]

starlette_app = Starlette(routes=routes)

# 8. Lancement
if __name__ == "__main__":
    # Écoute sur toutes les interfaces (0.0.0.0) port 8000
    uvicorn.run(starlette_app, host="0.0.0.0", port=8000)