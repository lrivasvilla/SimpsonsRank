import re
from pymongo import MongoClient

CDN = "https://cdn.thesimpsonsapi.com/1280"

def search_mongo(db_uri, db_name, type_key, q, limit=50):
    col_map = {"character": "characters", "episode": "episodes", "location": "locations"}
    col_name = col_map.get(type_key)
    if not col_name or not q:
        return []

    client = MongoClient(db_uri)
    db = client[db_name]
    col = db[col_name]

    rx = re.compile(re.escape(q), re.IGNORECASE)

    if type_key == "character":
        docs = list(col.find(
            {"name": rx},
            {"id": 1, "name": 1, "occupation": 1, "portrait_path": 1, "age": 1, "status": 1, "description": 1, "phrases": 1}
        ).limit(limit))
        out = []
        for d in docs:
            phrases = d.get("phrases") if isinstance(d.get("phrases"), list) else []
            out.append({
                "id": d.get("id"),
                "title": d.get("name", ""),
                "subtitle": d.get("occupation", ""),
                "image": CDN + (d.get("portrait_path") or ""),
                "age": d.get("age"),
                "status": d.get("status", ""),
                "description": d.get("description", ""),
                "quote": (phrases[0] if phrases else ""),
            })
    elif type_key == "location":
        docs = list(col.find(
            {"name": rx},
            {"id": 1, "name": 1, "town": 1, "image_path": 1}
        ).limit(limit))
        out = [{
            "id": d.get("id"),
            "title": d.get("name", ""),
            "subtitle": d.get("town", ""),
            "image": CDN + (d.get("image_path") or ""),
        } for d in docs]
    else:
        docs = list(col.find(
            {"name": rx},
            {"id": 1, "name": 1, "season": 1, "episode_number": 1, "image_path": 1}
        ).limit(limit))
        out = [{
            "id": d.get("id"),
            "title": d.get("name", ""),
            "subtitle": f"S{d.get('season')} · E{d.get('episode_number')}",
            "image": CDN + (d.get("image_path") or ""),
        } for d in docs]

    client.close()
    return out