import httpx
import asyncio
from typing import Dict
import os


class OnetClient:
    BASE_URL = "https://api-v2.onetcenter.org"

    def __init__(self):
        # Récupération des crédentiels
        self.api_key = os.getenv("ONET_API_KEY")
        if not self.api_key:
            raise ValueError("ONET_API_KEY manquante dans le fichier .env")

        # Authentification via Header standard X-API-Key
        self.headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
            "User-Agent": "MCP-Agent/1.0" # identifier le client (optionnel)
        }

    async def _get(self, client: httpx.AsyncClient, endpoint: str, params: Dict = None) -> Dict:
        """Méthode générique pour les appels API avec gestion d'erreurs."""

        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"

        try:
            response = await client.get(
                f"{self.BASE_URL}{endpoint}",
                headers=self.headers,
                params=params,
                timeout=30.0 # Timeout augmenté (beaucoup de requêtes)
            )
            return response.json()

        except httpx.HTTPStatusError as e:
            error_details = {
                "error": f"HTTP {e.response.status_code}",
                "url": str(e.request.url),
                "detail": e.response.text
            }
            return error_details

        except Exception as e:
            return {"error": "Connection Error", "detail": str(e)}

    async def search_occupation(self, keyword: str) -> Dict:
        """Recherche par keyword"""
        async with httpx.AsyncClient() as client:
            return await self._get(client, "/online/search", {"keyword": keyword, "end": 5})

    async def get_full_occupation_details(self, soc_code: str) -> Dict:
        """
        Agrégateur : Effectue plusieurs appels en parallèle pour construire
        un profil complet (Tasks, Skills, Tech, etc.)
        """
        async with httpx.AsyncClient() as client:
            # Paramètres standards de pagination
            p= {"start": 1, "end": 20}

            # Pour Detailed Work Activities
            p_dwa = {"start": 1, "end": 35}

            results = await asyncio.gather(
                # 0. Infos de base (Including sample_of_reported_titles)
                self._get(client, f"online/occupations/{soc_code}"),
                # 1. Tâches
                self._get(client, f"online/occupations/{soc_code}/details/tasks", p),
                # 2. Technologies (hot technologies, in demand, pourcentage)
                self._get(client, f"online/occupations/{soc_code}/details/technology_skills", p),
                # 3. Skills (Compétences)
                self._get(client, f"online/occupations/{soc_code}/details/skills", p),
                # 4. Knowledge (Connaissance / Savoir)
                self._get(client, f"online/occupations/{soc_code}/details/knowledge", p),
                # 5. Work Activities (Activités professionnelles)
                self._get(client, f"online/occupations/{soc_code}/details/work_activities", p),
                # 6. Education
                self._get(client, f"online/occupations/{soc_code}/details/education"),
                # 7. Detailed Work Activities (Activités pro détaillées)
                self._get(client, f"online/occupations/{soc_code}/details/detailed_work_activities", p_dwa),
                # 8. Job Zone (Zone d'emploi)
                self._get(client, f"online/occupations/{soc_code}/details/job_zone"),
                # 9. Work Context (Contexte professionnel)
                self._get(client, f"online/occupations/{soc_code}/details/work_context", p),
                # 10. Abilities (Capacités)
                self._get(client, f"online/occupations/{soc_code}/details/abilities", p),
                # 11. Interests (Intérêts)
                self._get(client, f"online/occupations/{soc_code}/details/interests"),
                # 12. Work Styles (Styles de travail)
                self._get(client, f"online/occupations/{soc_code}/details/work_styles")
            )

        return {
            "summary": results[0],
            "tasks": results[1],
            "technology_skills": results[2],
            "skills": results[3],
            "knowledge": results[4],
            "work_activities": results[5],
            "education": results[6],
            "detailed_work_activities": results[7],
            "job_zone": results[8],
            "work_context": results[9],
            "abilities": results[10],
            "interests": results[11],
            "work_styles": results[12]
        }