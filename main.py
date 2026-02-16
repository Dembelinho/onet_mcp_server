from mcp.server import Server
import mcp.types as types
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
import uvicorn
import logging
import anyio
import uuid
from dotenv import load_dotenv
from app.client import OnetClient
from app import logic

# Configuration du logging (pour la prod)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("onet-server")

load_dotenv()

server = Server("onet-server")
try:
    onet_client = OnetClient()
except ValueError as e:
    logger.error(f"Erreur de configuration critique : {e}")
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
        logger.error(f"Erreur outil {name}: {e}")
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


# --- GESTION DES SESSIONS ET STREAMS ---

active_connections = {}

async def handle_sse(request: Request):
    session_id = str(uuid.uuid4())

    async def event_generator():
        in_send, in_recv = anyio.create_memory_object_stream(10)
        out_send, out_recv = anyio.create_memory_object_stream(10)

        active_connections[session_id] = in_send

        init_options = server.create_initialization_options()

        try:
            async with anyio.create_task_group() as tg:
                tg.start_soon(server.run, in_recv, out_send, init_options)

                yield {
                    "event": "endpoint",
                    "data": f"/messages?session_id={session_id}"
                }

                async for message in out_recv:
                    try:
                        if isinstance(message, types.JSONRPCMessage):
                            yield {
                                "event": "message",
                                "data": message.model_dump_json()
                            }
                        elif isinstance(message, Exception):
                            logger.error(f"Erreur interne MCP: {message}")
                            yield {
                                "event": "error",
                                "data": str(message)
                            }
                    except Exception as e:
                        logger.error(f"Erreur yield SSE: {e}")
                        raise

        except Exception as e:
            logger.error(f"Session crash {session_id}: {e}")
        finally:
            if session_id in active_connections:
                del active_connections[session_id]

    return EventSourceResponse(event_generator())


async def handle_messages(request: Request):
    session_id = request.query_params.get("session_id")
    if not session_id or session_id not in active_connections:
        return JSONResponse({"error": "Session not found or invalid"}, status_code=404)

    try:
        data = await request.json()
        message = types.JSONRPCMessage.model_validate(data)

        write_stream = active_connections[session_id]
        await write_stream.send(message)

        return JSONResponse({"status": "accepted"}, status_code=202)

    except anyio.BrokenResourceError:
        return JSONResponse({"error": "Stream connection closed"}, status_code=410)
    except Exception as e:
        logger.error(f"Erreur handle_messages: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


routes = [
    Route("/sse", endpoint=handle_sse),
    Route("/messages", endpoint=handle_messages, methods=["POST"])
]

starlette_app = Starlette(routes=routes)

if __name__ == "__main__":
    uvicorn.run(starlette_app, host="0.0.0.0", port=8000)