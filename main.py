from mcp.server import Server
import mcp.types as types
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
import uvicorn
import anyio
import uuid
from dotenv import load_dotenv

# Imports Logic
from app.client import OnetClient
from app import logic

load_dotenv()

server = Server("onet-server")
try:
    onet_client = OnetClient()
except ValueError as e:
    print(f"Erreur config: {e}")
    exit(1)


# --- OUTILS ---
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(name="search_occupation", description="Recherche métier",
                   inputSchema={"type": "object", "properties": {"keyword": {"type": "string"}},
                                "required": ["keyword"]}),
        types.Tool(name="get_occupation_details", description="Détails métier SOC",
                   inputSchema={"type": "object", "properties": {"soc_code": {"type": "string"}},
                                "required": ["soc_code"]})
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    if not arguments: raise ValueError("Args required")
    try:
        if name == "search_occupation":
            res = await logic.search_occupation_logic(onet_client, arguments.get("keyword"))
        elif name == "get_occupation_details":
            res = await logic.get_details_logic(onet_client, arguments.get("soc_code"))
        else:
            raise ValueError(f"Unknown tool: {name}")
        return [types.TextContent(type="text", text=res)]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


# --- GESTION DES SESSIONS ET STREAMS (CŒUR DU SYSTÈME) ---

# Dictionnaire pour stocker les canaux d'écriture des sessions actives
# Key: session_id, Value: MemoryObjectSendStream
active_connections = {}


async def handle_sse(request: Request):
    session_id = str(uuid.uuid4())

    async def event_generator():
        # 1. Création des tuyaux (Streams)
        # in_stream: Pour envoyer des données AU serveur (depuis POST)
        in_send, in_recv = anyio.create_memory_object_stream(10)
        # out_stream: Pour lire les données DU serveur (vers SSE)
        out_send, out_recv = anyio.create_memory_object_stream(10)

        # On enregistre le canal d'entrée dans la liste globale pour le POST
        active_connections[session_id] = in_send

        # Options d'init
        init_options = server.create_initialization_options()

        # 2. On lance le serveur et la boucle de lecture en parallèle
        async with anyio.create_task_group() as tg:
            # Lancement du serveur MCP (Il lit in_recv et écrit dans out_send)
            # On utilise start_soon pour ne pas bloquer
            tg.start_soon(server.run, in_recv, out_send, init_options)

            # Envoi de l'URL du endpoint POST avec l'ID de session
            yield {
                "event": "endpoint",
                "data": f"/messages?session_id={session_id}"
            }

            # Boucle de lecture des réponses du serveur pour les envoyer au client SSE
            async for message in out_recv:
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

        # Nettoyage à la déconnexion
        if session_id in active_connections:
            del active_connections[session_id]

    return EventSourceResponse(event_generator())


async def handle_messages(request: Request):
    # Récupération de l'ID de session
    session_id = request.query_params.get("session_id")
    if not session_id or session_id not in active_connections:
        return JSONResponse({"error": "Session not found or invalid"}, status=404)

    try:
        data = await request.json()
        message = types.JSONRPCMessage.model_validate(data)

        # On récupère le canal d'écriture correspondant à la session
        write_stream = active_connections[session_id]

        # On injecte le message dans le tuyau
        await write_stream.send(message)

        return JSONResponse({"status": "accepted"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status=500)


routes = [
    Route("/sse", endpoint=handle_sse),
    Route("/messages", endpoint=handle_messages, methods=["POST"])
]

starlette_app = Starlette(routes=routes)

if __name__ == "__main__":
    uvicorn.run(starlette_app, host="0.0.0.0", port=8000)