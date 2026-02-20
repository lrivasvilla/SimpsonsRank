# Create your views here.
from django.core.paginator import Paginator
from django.shortcuts import render
from pymongo import MongoClient

from simpsonsRankApp.models import Character
from simpsonsRankApp.static.json.import_to_mongo import MONGO_URI, DB_NAME


def go_home(request):
    characters = Character.objects.all()

    paginator = Paginator(characters, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    CDN_BASE = "https://cdn.thesimpsonsapi.com/1280"

    # ===== stats cards (solo los de la página) =====
    char_ids = [c.id for c in page_obj]
    stats_map = {}  # { id: {"avg": float, "count": int} }

    # ===== sidebar =====
    top5 = []
    latest_reviews = []

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]

        # --- 1) stats de la página (para estrellas en cards) ---
        pipeline_page = [
            {"$match": {"characterCode": {"$in": char_ids}}},
            {"$group": {
                "_id": "$characterCode",
                "avg": {"$avg": "$rating"},
                "count": {"$sum": 1},
            }},
        ]

        for row in db["reviews"].aggregate(pipeline_page):
            cid = int(row["_id"])
            stats_map[cid] = {
                "avg": float(row.get("avg") or 0),
                "count": int(row.get("count") or 0),
            }

        # --- 2) TOP 5 global ---
        pipeline_top5 = [
            {"$match": {"characterCode": {"$exists": True}}},
            {"$group": {
                "_id": "$characterCode",
                "avg": {"$avg": "$rating"},
                "count": {"$sum": 1},
            }},
            {"$sort": {"avg": -1, "count": -1}},
            {"$limit": 5},
        ]
        top_docs = list(db["reviews"].aggregate(pipeline_top5))
        top_ids = [int(d["_id"]) for d in top_docs]

        chars_top = {c.id: c for c in Character.objects.filter(id__in=top_ids)}
        for d in top_docs:
            cid = int(d["_id"])
            c = chars_top.get(cid)
            if not c:
                continue
            top5.append({
                "id": cid,
                "name": c.name,
                "img": CDN_BASE + (c.portrait_path or ""),
                "avg": float(d.get("avg") or 0),
                "count": int(d.get("count") or 0),
            })

        # --- 3) ÚLTIMAS valoraciones globales (solo coemntarios) ---
        latest_docs = list(
            db["reviews"]
            .find({
                "characterCode": {"$exists": True},
                "comment": {"$exists": True, "$type": "string", "$ne": ""}
            })
            .sort("reviewDate", -1)
            .limit(5)
        )

        latest_ids = []
        for d in latest_docs:
            try:
                latest_ids.append(int(d.get("characterCode")))
            except Exception:
                pass

        chars_latest = {c.id: c for c in Character.objects.filter(id__in=latest_ids)}

        for d in latest_docs:
            cid = d.get("characterCode")
            try:
                cid = int(cid)
            except Exception:
                continue

            c = chars_latest.get(cid)
            if not c:
                continue

            latest_reviews.append({
                "character_id": cid,
                "character_name": c.name,
                "character_img": CDN_BASE + (c.portrait_path or ""),
                "user": d.get("user", "anon"),
                "rating": int(d.get("rating", 0) or 0),
                "comment": d.get("comment", ""),
                "reviewDate": d.get("reviewDate"),
            })

        client.close()

    except Exception:
        stats_map = {}
        top5 = []
        latest_reviews = []

    # ===== construir lista para el template =====
    personajes = []
    for c in page_obj:
        st = stats_map.get(c.id, {"avg": 0, "count": 0})
        personajes.append({
            "id": c.id,
            "nombre": c.name,
            "rol": c.occupation,
            "imagen_url": CDN_BASE + (c.portrait_path or ""),
            "edad": c.age,
            "vivo": (c.status or "").lower() == "alive",
            "frase": c.phrases[0] if c.phrases else "",
            "descripcion": getattr(c, "description", ""),

            "avg_rating": st["avg"],
            "reviews_count": st["count"],
        })

    return render(request, "home.html", {
        "personajes": personajes,
        "page_obj": page_obj,
        "top5": top5,
        "latest_reviews": latest_reviews,
    })
