import asyncio
import httpx
import json
import sys

SERVERS = [
    {"name": "ONET", "url": "https://onet.mcp.expehris.com"},
    # {"name": "ESCO", "url": "https://esco.mcp.expehris.com"}
]


async def send_rpc(client, post_url, method, params=None, msg_id=None):
    payload = {
        "jsonrpc": "2.0",
        "method": method
    }
    if params is not None:
        payload["params"] = params
    if msg_id is not None:
        payload["id"] = msg_id

    print(f"   📤 Envoi POST : {method}")
    resp = await client.post(post_url, json=payload)
    if resp.status_code != 202:  # Le serveur renvoie 202 Accepted
        print(f"   ⚠️ Status POST {resp.status_code}: {resp.text}")
    return resp


async def test_server_concurrent(name, base_url):
    print(f"\n{'=' * 40}")
    print(f"📡 TEST DU SERVEUR : {name}")
    print(f"{'=' * 40}")

    # On utilise un événement pour dire au main thread "C'est bon, j'ai l'ID"
    session_ready = asyncio.Event()
    session_info = {"url": None, "id": None}

    async with httpx.AsyncClient(timeout=30.0) as client:

        # --- TÂCHE 1 : ÉCOUTE SSE (Background) ---
        async def listen_sse():
            print("🎧 Démarrage écoute SSE...")
            try:
                async with client.stream("GET", f"{base_url}/sse") as response:
                    print("✅ SSE Connecté (200 OK)")
                    async for line in response.aiter_lines():
                        if not line: continue

                        if line.startswith("data: "):
                            data_str = line.replace("data: ", "").strip()

                            # Cas A : On reçoit l'endpoint (au début)
                            if "/messages" in data_str and not session_ready.is_set():
                                session_info["url"] = f"{base_url}{data_str}"
                                session_info["id"] = data_str.split("=")[1]
                                print(f"🔑 Session ID reçu : {session_info['id']}")
                                session_ready.set()  # DÉBLOQUE LA TÂCHE 2

                            # Cas B : On reçoit une réponse JSON-RPC (suite aux commandes)
                            elif data_str.startswith("{"):
                                try:
                                    msg = json.loads(data_str)
                                    # Si c'est le résultat de tools/list
                                    if "result" in msg and "tools" in msg["result"]:
                                        tools = msg["result"]["tools"]
                                        print(f"\n🎉 RÉPONSE REÇUE VIA SSE ! {len(tools)} outils trouvés :")
                                        for t in tools:
                                            print(f"   - 🛠️  {t['name']}")
                                        # On a fini, on peut arrêter le script propremen
                                        return True
                                    elif "error" in msg:
                                        print(f"❌ Erreur reçue du serveur : {msg['error']}")
                                    else:
                                        print(f"📥 Message SSE reçu : {data_str[:100]}...")
                                except:
                                    pass
            except Exception as e:
                print(f"❌ Erreur connexion SSE : {e}")
            return False

        # On lance l'écoute en tâche de fond
        listener_task = asyncio.create_task(listen_sse())

        # --- TÂCHE 2 : ENVOI DES COMMANDES (Main) ---

        # On attend que la tâche 1 ait récupéré l'ID (max 5 secondes)
        try:
            await asyncio.wait_for(session_ready.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            print("❌ Timeout : Pas reçu de session ID.")
            listener_task.cancel()
            return

        post_url = session_info["url"]

        # 1. Handshake : Initialize
        await send_rpc(client, post_url, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-script", "version": "1.0"}
        }, msg_id=0)

        # 2. Handshake : Initialized
        await send_rpc(client, post_url, "notifications/initialized", {})

        # 3. Demande des outils
        print("🤞 Demande de la liste des outils...")
        await send_rpc(client, post_url, "tools/list", msg_id=1)

        # On attend un peu que la réponse arrive via SSE (Tâche 1)
        try:
            # On attend que listener_task finisse (return True) ou timeout de 5s
            await asyncio.wait_for(listener_task, timeout=5.0)
        except asyncio.TimeoutError:
            print("⏱️ Fin du test (Timeout d'attente réponse).")


async def main():
    for server in SERVERS:
        await test_server_concurrent(server["name"], server["url"])


if __name__ == "__main__":
    asyncio.run(main())