from . import formatters
from .client import OnetClient

async def search_occupation_logic(client: OnetClient, keyword: str) -> str:
    """Logique de recherche et formatage des résultats."""
    data = await client.search_occupation(keyword)

    # Gestion des erreurs HTTP
    if "error" in data:
        return f"Erreur lors de la recherche : {data.get('detail', data['error'])}"

    if "occupation" not in data or not data["occupation"]:
        return "Aucun métier trouvé pour ce mot-clé."

    # Formatage Markdown pour le LLM
    result_text = f"Résultats trouvés pour '{keyword}' :\n"
    for item in data["occupation"]:
        code = item.get('code')
        title = item.get('title')
        result_text += f"- **{title}** (Code SOC: `{code}`)\n"

    result_text += "\nUtilisez le Code SOC pour obtenir les détails."
    return result_text


async def get_details_logic(client: OnetClient, soc_code: str) -> str:
    """Logique d'agrégation et de création du rapport complet."""

    # Nettoyage préventif du code
    clean_code = soc_code.strip().replace("'", "").replace('"', "")

    data = await client.get_full_occupation_details(clean_code)

    summary = data.get('summary', {})
    if "error" in summary:
        return (f"ERREUR API O*NET pour le code '{clean_code}'\n"
                f"Détail : {summary.get('detail', summary)}\n")

    # Construction du rapport
    title = summary.get('title')
    desc = summary.get('description')
    # --- EXTRACTION DES TITRES SIMILAIRES ---
    sample_titles = summary.get('sample_of_reported_titles', [])
    sample_titles_str = ", ".join(sample_titles) if sample_titles else "Aucun titre similaire disponible."

    report = f"""
# FICHE MÉTIER : {title} **Code SOC** : {summary.get('code')}

## 📝 Description
{desc}

## 📌 Titres Similaires (Reported Titles)
{sample_titles_str}

## Zone d'Emploi (Job Zone)
{formatters.format_job_zone(data.get('job_zone', {}))}

## 1. Tâches Principales
{formatters.format_tasks(data.get('tasks', {}))}

## 2. Activités Professionnelles Générales (Work Activities)
{formatters.format_scored_elements(data.get('work_activities', {}))}

## 3. Activités Détaillées (Detailed Work Activities)
{formatters.format_dwa(data.get('detailed_work_activities', {}))}

## 4. Technologies & Outils
{formatters.format_technology(data.get('technology_skills', {}), limit_per_cat=6)}

## 5. Compétences Transversales (Skills)
{formatters.format_scored_elements(data.get('skills', {}))}

## 6. Capacités (Abilities)
{formatters.format_scored_elements(data.get('abilities', {}))}

## 7. Connaissances (Knowledge)
{formatters.format_scored_elements(data.get('knowledge', {}))}

## 8. Contexte de Travail (Work Context)
{formatters.format_work_context(data.get('work_context', {}))}

## 9. Éducation & Diplômes
{formatters.format_education(data.get('education', {}))}
"""
    return report