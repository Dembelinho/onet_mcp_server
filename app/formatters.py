from typing import Dict, List

# FONCTIONS DE FORMATAGE (HELPERS)

def format_tasks(data: Dict, limit: int = 15) -> str:
    """
    Formate la liste des tâches (Tasks) avec leur score d'importance.
    """
    if not data or 'error' in data:
        return "Données de tâches indisponibles."

    tasks_list = data.get('task', [])

    if not tasks_list:
        return "Aucune tâche répertoriée."

    # Tri par importance décroissante
    tasks_list.sort(key=lambda x: x.get('importance', 0), reverse=True)

    formatted_lines = []
    for item in tasks_list[:limit]:
        title = item.get('title', 'Titre non spécifié')
        importance = item.get('importance', 0)
        category = item.get('category', 'N/A')

        # On ajoute une icône visuelle si c'est une tâche "Core"
        prefix = "🔹" if category == "Core" else "🔸"

        # Format: - **Titre** (Importance: 90)
        formatted_lines.append(f"{prefix} **{title}** (Imp: {importance})")

    return "\n".join(formatted_lines)


def format_technology(data: Dict, limit_per_cat: int = 6) -> str:
    """
    Formate les compétences techniques par catégorie, triées par demande sur le marché.
    """
    if not data or 'error' in data:
        return "Données technologiques indisponibles."

    categories = data.get('category', [])
    if not categories:
        return "Aucune technologie répertoriée."

    output_lines = []

    for cat in categories:
        cat_title = cat.get('title', 'Divers')

        # 1. Fusionner 'example' et 'example_more'
        all_tools = cat.get('example', []) + cat.get('example_more', [])

        # 2. Préparer les données pour le tri
        processed_tools = []
        for tool in all_tools:
            name = tool.get('title', 'Inconnu')
            is_hot = tool.get('hot_technology', False)
            in_demand = tool.get('in_demand', False)
            percent = tool.get('percentage', 0)

            # Construction des marqueurs
            markers = ""
            if is_hot: markers += "🔥"
            if in_demand: markers += "📈"

            # Ajout du pourcentage si pertinent (>0)
            display_str = f"{name} {markers}".strip()
            if percent > 0:
                display_str += f" ({percent}%)"

            processed_tools.append({
                "display": display_str,
                "score": percent + (50 if in_demand else 0) + (20 if is_hot else 0)  # Algorithme de tri simple
            })

        # 3. Trier par score décroissant (les plus demandés en premier)
        processed_tools.sort(key=lambda x: x["score"], reverse=True)

        # 4. Formater la ligne
        # On ne garde que les top 'limit_per_cat' outils pour ne pas saturer le contexte
        top_tools = [t["display"] for t in processed_tools[:limit_per_cat]]

        if top_tools:
            output_lines.append(f"- **{cat_title}**: {', '.join(top_tools)}")

    return "\n".join(output_lines)


def format_scored_elements(data: Dict, limit: int = 12) -> str:
    """
    Formate les éléments standards (Skills, Knowledge, Abilities) avec score et description.
    Structure attendue : liste sous la clé 'element' contenant {name, importance, description}.
    """
    if not data or 'error' in data:
        return "Données indisponibles."

    items = data.get('element', [])
    if not items:
        return "Aucune donnée répertoriée."

    # Tri par importance décroissante
    items.sort(key=lambda x: x.get('importance', 0), reverse=True)

    formatted_lines = []
    for item in items[:limit]:
        name = item.get('name', 'Inconnu')
        score = item.get('importance', 0)
        desc = item.get('description', '').strip()

        # Format: - **Nom** (Score): Description
        formatted_lines.append(f"- **{name}** ({score}/100): {desc}")

    return "\n".join(formatted_lines)


def format_education(data: Dict) -> str:
    """
    Formate les niveaux d'éducation requis par pourcentage de répondants.
    """
    if not data or 'error' in data:
        return "Données d'éducation indisponibles."

    # le tableau est sous "response", parfois sous "level"
    items = data.get('response', []) or data.get('level', [])

    if not items:
        return "Aucune donnée d'éducation."

    # Normalisation pour le tri : extraction du pourcentage
    cleaned_items = []
    for item in items:
        pct = item.get('percentage_of_respondents') or item.get('percentage', 0)
        title = item.get('title') or item.get('name', 'N/A')

        # On ne garde que ce qui est significatif (> 0%)
        if pct > 0:
            cleaned_items.append({'title': title, 'pct': pct})

    # Tri décroissant pour voir le diplôme le plus courant en premier
    cleaned_items.sort(key=lambda x: x['pct'], reverse=True)

    formatted_lines = []
    for item in cleaned_items:
        # Format: - **Bachelor’s degree** (46%)
        formatted_lines.append(f"- **{item['title']}** ({item['pct']}%)")

    return "\n".join(formatted_lines)


def format_dwa(data: Dict, limit: int = 35) -> str:
    """
    Formate les activités de travail détaillées (DWAs). C'est une liste plate.
    """
    if not data or 'error' in data:
        return "Données d'activités détaillées indisponibles."

    # La clé ici est 'activity'
    activities = data.get('activity', [])

    if not activities:
        return "Aucune activité détaillée répertoriée."

    formatted_lines = []
    # On prend les X premiers éléments tels quels
    for item in activities[:limit]:
        title = item.get('title', '').strip()
        if title:
            formatted_lines.append(f"- {title}")

    return "\n".join(formatted_lines)


def format_job_zone(data: Dict) -> str:
    """
    Formate les informations de la Zone d'Emploi (Job Zone).
    Indique le niveau de préparation nécessaire.
    """
    if not data or 'error' in data:
        return "Info Job Zone non disponible."

    # les clés sont à la racine, mais par sécurité on vérifie
    target = data.get('job_zone', data)
    # Si c'est une liste (cas rare), on prend le premier
    if isinstance(target, list) and target:
        target = target[0]

    code = target.get('code', '?')
    title = target.get('title', 'Titre non spécifié')
    svp = target.get('svp_range', 'Non spécifié')

    education = target.get('education', 'Non spécifié')
    experience = target.get('related_experience', 'Non spécifié')
    training = target.get('job_training', 'Non spécifié')

    return (
        f"**Zone {code} : {title}** (SVP Range: {svp})\n"
        f"- **Éducation** : {education}\n"
        f"- **Expérience** : {experience}\n"
        f"- **Formation** : {training}"
    )


def format_work_context(data: Dict, limit: int = 10) -> str:
    """
    Formate le contexte de travail en extrayant la condition la plus fréquente.
    """
    if not data or 'error' in data:
        return "Données de contexte indisponibles."

    items = data.get('element', [])
    if not items:
        return "Aucun contexte répertorié."

    # 1. On trie d'abord par score global de contexte
    items.sort(key=lambda x: x.get('context', 0), reverse=True)

    formatted_lines = []
    for item in items[:limit]:
        name = item.get('name', 'Inconnu')
        context_score = item.get('context', 0) # Optionnel

        # 2. On cherche la réponse la plus fréquente parmi les choix possibles
        responses = item.get('response', [])
        top_response = None

        if responses:
            # On trie les réponses par pourcentage décroissant
            responses.sort(key=lambda x: x.get('percentage_of_respondents', 0), reverse=True)
            top_response = responses[0]

        # 3. Construction de la ligne
        if top_response:
            answer = top_response.get('description', '')
            pct = top_response.get('percentage_of_respondents', 0)
            # Format: - **E-Mail**: Every day (92%)
            formatted_lines.append(f"- **{name}**: {answer} ({pct}%)")
        else:
            formatted_lines.append(f"- **{name}**")

    return "\n".join(formatted_lines)

