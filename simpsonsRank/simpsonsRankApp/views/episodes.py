from django.core.paginator import Paginator
from django.shortcuts import render
from pymongo import MongoClient

from simpsonsRankApp.models import Episodes
from simpsonsRankApp.static.json.import_to_mongo import MONGO_URI, DB_NAME


def show_episodes(request):
    episodes = Episodes.objects.all().order_by("id")

    paginator = Paginator(episodes, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    CDN_BASE = "https://cdn.thesimpsonsapi.com/1280"

    stats_map = {}
    top5_episodes = []
    latest_comments = []

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]

        # ===== stats para cards (solo episodios de la página) =====
        ep_ids = [e.id for e in page_obj]

        pipeline_page = [
            {"$match": {"episodeCode": {"$in": ep_ids}}},
            {"$group": {
                "_id": "$episodeCode",
                "avg": {"$avg": "$rating"},
                "count": {"$sum": 1},
            }},
        ]

        for row in db["reviews"].aggregate(pipeline_page):
            eid = int(row["_id"])
            stats_map[eid] = {
                "avg": float(row.get("avg") or 0),
                "count": int(row.get("count") or 0),
            }

        # ===== TOP 5 EPISODES =====
        pipeline_top5 = [
            {"$match": {"episodeCode": {"$exists": True}}},
            {"$group": {
                "_id": "$episodeCode",
                "avg": {"$avg": "$rating"},
                "count": {"$sum": 1},
            }},
            {"$sort": {"avg": -1, "count": -1}},
            {"$limit": 5},
        ]

        top_docs = list(db["reviews"].aggregate(pipeline_top5))
        top_ids = [int(d["_id"]) for d in top_docs]

        eps = {e.id: e for e in Episodes.objects.filter(id__in=top_ids)}

        for d in top_docs:
            eid = int(d["_id"])
            e = eps.get(eid)
            if not e:
                continue
            top5_episodes.append({
                "id": eid,
                "name": e.name,
                "img": CDN_BASE + (e.image_path or ""),
                "avg": float(d.get("avg") or 0),
                "count": int(d.get("count") or 0),
            })

        # ===== ÚLTIMOS COMENTARIOS (solo con texto) =====
        latest_docs = list(
            db["reviews"]
            .find({
                "episodeCode": {"$exists": True},
                "comment": {"$exists": True, "$type": "string", "$ne": ""}
            })
            .sort("reviewDate", -1)
            .limit(5)
        )

        ep_ids_latest = []
        for d in latest_docs:
            try:
                ep_ids_latest.append(int(d.get("episodeCode")))
            except Exception:
                pass

        eps_latest = {e.id: e for e in Episodes.objects.filter(id__in=ep_ids_latest)}

        for d in latest_docs:
            try:
                eid = int(d.get("episodeCode"))
            except Exception:
                continue

            e = eps_latest.get(eid)
            if not e:
                continue

            latest_comments.append({
                "episode_id": eid,
                "episode_name": e.name,
                "episode_img": CDN_BASE + (e.image_path or ""),
                "user": d.get("user", "anon"),
                "rating": int(d.get("rating", 0) or 0),
                "comment": d.get("comment", ""),
            })

        client.close()

    except Exception:
        stats_map = {}
        top5_episodes = []
        latest_comments = []

    # ===== lista episodios para el grid =====
    lista_episodios = []
    for e in page_obj:
        st = stats_map.get(e.id, {"avg": 0, "count": 0})
        lista_episodios.append({
            "id": e.id,
            "nombre": e.name,
            "temporada": e.season,
            "numero": e.episode_number,
            "fecha": e.airdate,
            "imagen_url": CDN_BASE + (e.image_path or ""),
            "sinopsis": e.synopsis,

            "avg_rating": st["avg"],
            "reviews_count": st["count"],
        })

    return render(request, "episodes.html", {
        "episodios": lista_episodios,
        "page_obj": page_obj,
        "top5_episodes": top5_episodes,
        "latest_episode_comments": latest_comments,
    })