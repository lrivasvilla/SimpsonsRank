from django.core.paginator import Paginator
from django.shortcuts import render
from pymongo import MongoClient

from simpsonsRankApp.models import Locations
from simpsonsRankApp.static.json.import_to_mongo import DB_NAME, MONGO_URI


def show_locations(request):
    locations = Locations.objects.all().order_by("id")

    paginator = Paginator(locations, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    CDN_BASE = "https://cdn.thesimpsonsapi.com/1280"

    stats_map = {}
    top5_locations = []
    latest_comments = []

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]

        # ===== stats para cards (solo locations de la página) =====
        loc_ids = [l.id for l in page_obj]

        pipeline_page = [
            {"$match": {"locationCode": {"$in": loc_ids}}},
            {"$group": {
                "_id": "$locationCode",
                "avg": {"$avg": "$rating"},
                "count": {"$sum": 1},
            }},
        ]

        for row in db["reviews"].aggregate(pipeline_page):
            lid = int(row["_id"])
            stats_map[lid] = {
                "avg": float(row.get("avg") or 0),
                "count": int(row.get("count") or 0),
            }

        # ===== TOP 5 LOCATIONS =====
        pipeline_top5 = [
            {"$match": {"locationCode": {"$exists": True}}},
            {"$group": {
                "_id": "$locationCode",
                "avg": {"$avg": "$rating"},
                "count": {"$sum": 1},
            }},
            {"$sort": {"avg": -1, "count": -1}},
            {"$limit": 5},
        ]

        top_docs = list(db["reviews"].aggregate(pipeline_top5))
        top_ids = [int(d["_id"]) for d in top_docs]

        locs = {l.id: l for l in Locations.objects.filter(id__in=top_ids)}

        for d in top_docs:
            lid = int(d["_id"])
            l = locs.get(lid)
            if not l:
                continue
            top5_locations.append({
                "id": lid,
                "name": l.name,
                "img": CDN_BASE + (l.image_path or ""),
                "avg": float(d.get("avg") or 0),
                "count": int(d.get("count") or 0),
            })

        # ===== ÚLTIMOS COMENTARIOS (solo con texto) =====
        latest_docs = list(
            db["reviews"]
            .find({
                "locationCode": {"$exists": True},
                "comment": {"$exists": True, "$type": "string", "$ne": ""}
            })
            .sort("reviewDate", -1)
            .limit(5)
        )

        loc_ids_latest = []
        for d in latest_docs:
            try:
                loc_ids_latest.append(int(d.get("locationCode")))
            except Exception:
                pass

        locs_latest = {l.id: l for l in Locations.objects.filter(id__in=loc_ids_latest)}

        for d in latest_docs:
            try:
                lid = int(d.get("locationCode"))
            except Exception:
                continue

            l = locs_latest.get(lid)
            if not l:
                continue

            latest_comments.append({
                "location_id": lid,
                "location_name": l.name,
                "location_img": CDN_BASE + (l.image_path or ""),
                "user": d.get("user", "anon"),
                "rating": int(d.get("rating", 0) or 0),
                "comment": d.get("comment", ""),
            })

        client.close()

    except Exception:
        stats_map = {}
        top5_locations = []
        latest_comments = []

    # ===== lista locations para el grid =====
    lista_locations = []
    for l in page_obj:
        st = stats_map.get(l.id, {"avg": 0, "count": 0})
        lista_locations.append({
            "id": l.id,
            "nombre": l.name,
            "pueblo": l.town,
            "uso": l.use,
            "imagen_url": CDN_BASE + (l.image_path or ""),

            "avg_rating": st["avg"],
            "reviews_count": st["count"],
        })

    return render(request, "locations.html", {
        "locations": lista_locations,
        "page_obj": page_obj,
        "top5_locations": top5_locations,
        "latest_location_comments": latest_comments,
    })