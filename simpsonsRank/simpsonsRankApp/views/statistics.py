from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from pymongo import MongoClient

from simpsonsRankApp.models import Character, Episodes, Locations
from simpsonsRankApp.static.json.import_to_mongo import MONGO_URI, DB_NAME


def _mongo():
    client = MongoClient(MONGO_URI)
    return client, client[DB_NAME]

def _scope_match(request):
    """
    Admin puede ver global o propio:
      ?scope=global  -> todo
      ?scope=me      -> solo user
    Usuario normal siempre "me".
    """
    if not request.user.is_authenticated:
        return {"user": "__no_user__"}  # no debería llegar aquí

    if request.user.is_staff and (request.GET.get("scope") == "global"):
        return {}  # global
    return {"user": request.user.username}

@require_GET
@login_required
def statistics_page(request):
    # solo render (la data la pedimos por fetch)
    return render(request, "statistics.html", {
        "is_admin": request.user.is_staff,
    })


@require_GET
@login_required
def statistics_data(request):
    match_user = _scope_match(request)

    client, db = _mongo()
    reviews = db["reviews"]
    rankings = db["rankings"]

    CDN = "https://cdn.thesimpsonsapi.com/1280"

    try:
        # =========================
        # REVIEWS: totales + media
        # =========================
        total_reviews = reviews.count_documents(match_user)
        avg_rating_doc = list(reviews.aggregate([
            {"$match": match_user},
            {"$group": {"_id": None, "avg": {"$avg": "$rating"}}}
        ]))
        avg_rating = float(avg_rating_doc[0]["avg"]) if avg_rating_doc else 0.0

        # Distribución estrellas 1..5
        dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        dist_docs = list(reviews.aggregate([
            {"$match": match_user},
            {"$group": {"_id": "$rating", "n": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]))
        for d in dist_docs:
            k = int(d["_id"] or 0)
            if k in dist:
                dist[k] = int(d["n"])

        # =========================
        # REVIEWS: Top mejor valorados / más valorados
        # =========================
        def top_rated(field, limit=20, min_count=1):
            pipeline = [
                {"$match": {**match_user, field: {"$exists": True}}},
                {"$group": {
                    "_id": f"${field}",
                    "avg": {"$avg": "$rating"},
                    "count": {"$sum": 1},
                }},
                {"$match": {"count": {"$gte": min_count}}},
                {"$sort": {"avg": -1, "count": -1}},
                {"$limit": limit},
            ]
            out = []
            for x in reviews.aggregate(pipeline):
                out.append({
                    "id": int(x["_id"]),
                    "avg": round(float(x["avg"]), 2),
                    "count": int(x["count"]),
                })
            return out

        def most_reviewed(field, limit=10):
            pipeline = [
                {"$match": {**match_user, field: {"$exists": True}}},
                {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": limit},
            ]
            out = []
            for x in reviews.aggregate(pipeline):
                out.append({"id": int(x["_id"]), "count": int(x["count"])})
            return out

        top_char = top_rated("characterCode")
        top_ep   = top_rated("episodeCode")
        top_loc  = top_rated("locationCode")

        most_char = most_reviewed("characterCode")
        most_ep   = most_reviewed("episodeCode")
        most_loc  = most_reviewed("locationCode")

        # =========================
        # HIDRATAR: añadir label/img/subtitle a los tops
        # =========================
        def hydrate_char(items):
            ids = [x["id"] for x in items]
            qs = Character.objects.filter(id__in=ids)
            m = {c.id: c for c in qs}
            out = []
            for it in items:
                c = m.get(it["id"])
                out.append({
                    **it,
                    "label": c.name if c else f"Character {it['id']}",
                    "img": (CDN + c.portrait_path) if (c and getattr(c, "portrait_path", None)) else None,
                    "subtitle": (c.occupation or "") if c else "",
                })
            return out

        def hydrate_ep(items):
            ids = [x["id"] for x in items]
            qs = Episodes.objects.filter(id__in=ids)
            m = {e.id: e for e in qs}
            out = []
            for it in items:
                e = m.get(it["id"])
                out.append({
                    **it,
                    "label": e.name if e else f"Episode {it['id']}",
                    "img": (CDN + e.image_path) if (e and getattr(e, "image_path", None)) else None,
                    "subtitle": (f"S{e.season} · E{e.episode_number}") if e else "",
                })
            return out

        def hydrate_loc(items):
            ids = [x["id"] for x in items]
            qs = Locations.objects.filter(id__in=ids)
            m = {l.id: l for l in qs}
            out = []
            for it in items:
                l = m.get(it["id"])
                out.append({
                    **it,
                    "label": l.name if l else f"Location {it['id']}",
                    "img": (CDN + l.image_path) if (l and getattr(l, "image_path", None)) else None,
                    "subtitle": (l.town or "") if l else "",
                })
            return out

        # top_rated + most_reviewed enriquecidos
        top_char  = hydrate_char(top_char)
        top_ep    = hydrate_ep(top_ep)
        top_loc   = hydrate_loc(top_loc)

        most_char = hydrate_char(most_char)
        most_ep   = hydrate_ep(most_ep)
        most_loc  = hydrate_loc(most_loc)

        # =========================
        # Media por tipo
        # =========================
        def avg_for_type(field):
            docs = list(reviews.aggregate([
                {"$match": {**match_user, field: {"$exists": True}}},
                {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}}
            ]))
            if not docs:
                return {"avg": 0.0, "count": 0}
            return {"avg": round(float(docs[0]["avg"]), 2), "count": int(docs[0]["count"])}

        avg_by_type = {
            "characters": avg_for_type("characterCode"),
            "episodes": avg_for_type("episodeCode"),
            "locations": avg_for_type("locationCode"),
        }

        # =========================
        # RANKINGS: totales + por categoría
        # =========================
        total_rankings = rankings.count_documents(match_user)

        by_category = list(rankings.aggregate([
            {"$match": match_user},
            {"$group": {"_id": "$categoryCode", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 20}
        ]))
        rankings_by_category = [{"category": (x["_id"] or ""), "count": int(x["count"])} for x in by_category]

        # Solo global: top users
        top_users = []
        if request.user.is_staff and request.GET.get("scope") == "global":
            docs = list(rankings.aggregate([
                {"$group": {"_id": "$user", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]))
            top_users = [{"user": x["_id"], "count": int(x["count"])} for x in docs]

        client.close()

        return JsonResponse({
            "ok": True,
            "scope": "global" if (match_user == {}) else "me",

            "reviews": {
                "total": total_reviews,
                "avg": round(avg_rating, 2),
                "dist": dist,
                "avg_by_type": avg_by_type,

                "top_rated": {
                    "characters": top_char,
                    "episodes": top_ep,
                    "locations": top_loc,
                },
                "most_reviewed": {
                    "characters": most_char,
                    "episodes": most_ep,
                    "locations": most_loc,
                }
            },

            "rankings": {
                "total": total_rankings,
                "by_category": rankings_by_category,
                "top_users": top_users,
            }
        })

    except Exception as e:
        client.close()
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@require_GET
@login_required
def category_avg_ranking(request, category_slug):
    """
    Devuelve el ranking promedio (por posición) de una categoría.
    Respeta scope=me/global (global solo admin).
    """
    match_user = _scope_match(request)
    CDN = "https://cdn.thesimpsonsapi.com/1280"

    client, db = _mongo()
    rankings = db["rankings"]

    try:
        # Traemos solo lo necesario
        cursor = rankings.find(
            {**match_user, "categoryCode": category_slug},
            {"_id": 0, "rankinList": 1}
        )

        docs = list(cursor)
        n_rankings = len(docs)

        if n_rankings == 0:
            client.close()
            return JsonResponse({
                "ok": True,
                "category": category_slug,
                "rankings_count": 0,
                "results": []
            })

        # Acumuladores: clave = (type, id)
        sum_pos = {}
        count = {}

        for d in docs:
            lst = d.get("rankinList") or []
            for idx, it in enumerate(lst, start=1):  # pos 1..N
                t = (it.get("type") or "").strip()
                _id = it.get("id")
                if not t or _id is None:
                    continue
                key = (t, int(_id))
                sum_pos[key] = sum_pos.get(key, 0) + idx
                count[key] = count.get(key, 0) + 1

        # Construimos resultados
        items = []
        for (t, _id), s in sum_pos.items():
            c = count.get((t, _id), 0)
            if c <= 0:
                continue
            avg_pos = s / c
            items.append({
                "type": t,          # "characters" | "episodes" | "locations"
                "id": _id,
                "avg_pos": round(avg_pos, 2),
                "appearances": int(c),
            })

        # Orden: mejor avg_pos primero, luego más apariciones
        items.sort(key=lambda x: (x["avg_pos"], -x["appearances"]))

        # ===== Hidratación (label/img/subtitle) =====
        def hydrate(items, model, img_field, label_field="name", subtitle_fn=None):
            ids = [x["id"] for x in items]
            qs = model.objects.filter(id__in=ids)
            m = {obj.id: obj for obj in qs}

            out = []
            for it in items:
                obj = m.get(it["id"])
                label = getattr(obj, label_field, None) if obj else None
                img_path = getattr(obj, img_field, None) if obj else None

                subtitle = ""
                if obj and subtitle_fn:
                    try:
                        subtitle = subtitle_fn(obj) or ""
                    except Exception:
                        subtitle = ""

                out.append({
                    **it,
                    "label": label or f"{it['type']} {it['id']}",
                    "img": (CDN + img_path) if img_path else None,
                    "subtitle": subtitle,
                })
            return out

        chars = [x for x in items if x["type"] == "characters"]
        eps   = [x for x in items if x["type"] == "episodes"]
        locs  = [x for x in items if x["type"] == "locations"]

        chars = hydrate(
            chars, Character, "portrait_path",
            label_field="name",
            subtitle_fn=lambda c: (c.occupation or "")
        )
        eps = hydrate(
            eps, Episodes, "image_path",
            label_field="name",
            subtitle_fn=lambda e: f"S{e.season} · E{e.episode_number}"
        )
        locs = hydrate(
            locs, Locations, "image_path",
            label_field="name",
            subtitle_fn=lambda l: (l.town or "")
        )

        # Volvemos a unir manteniendo orden original (ya ordenado por avg_pos)
        hydrated_map = {(x["type"], x["id"]): x for x in (chars + eps + locs)}
        final = [hydrated_map[(x["type"], x["id"])] for x in items if (x["type"], x["id"]) in hydrated_map]

        client.close()
        return JsonResponse({
            "ok": True,
            "category": category_slug,
            "rankings_count": n_rankings,
            "results": final[:50],  # límite por UI
        })

    except Exception as e:
        client.close()
        return JsonResponse({"ok": False, "error": str(e)}, status=500)