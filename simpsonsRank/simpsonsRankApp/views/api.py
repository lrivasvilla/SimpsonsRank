import re

from bson import ObjectId
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from pymongo import MongoClient

from simpsonsRankApp.models import Character, Locations, Episodes
from simpsonsRankApp.service.mongo_search import search_mongo
from simpsonsRankApp.static.json.import_to_mongo import MONGO_URI, DB_NAME


@require_GET
def search_attachables(request):
    q = (request.GET.get("q") or "").strip()
    t = (request.GET.get("type") or "").strip()
    results = search_mongo(MONGO_URI, DB_NAME, t, q, limit=50)
    return JsonResponse({"results": results})

@require_GET
@login_required
def category_items(request, slug):
    # 1) cargar categoría desde Mongo
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        query = {"slug": slug, "is_active": True}
        if request.user.is_authenticated and request.user.is_staff:
            query = {"slug": slug}  # admin puede cargar aunque esté inactiva

        cat = db["categories"].find_one(query, {"_id": 0})

        client.close()
    except Exception:
        cat = None

    if not cat:
        return JsonResponse({"ok": False, "results": []}, status=404)

    attach = cat.get("attach", {}) or {}
    char_ids = attach.get("characters", []) or []
    loc_ids = attach.get("locations", []) or []
    ep_ids = attach.get("episodes", []) or []

    CDN = "https://cdn.thesimpsonsapi.com/1280"
    results = []

    if char_ids:
        qs = Character.objects.filter(id__in=char_ids)
        for x in qs:
            results.append({
                "type": "characters",
                "id": x.id,
                "label": x.name,
                "img": CDN + x.portrait_path,
                "subtitle": x.occupation or "",
            })

    if loc_ids:
        qs = Locations.objects.filter(id__in=loc_ids)
        for x in qs:
            results.append({
                "type": "locations",
                "id": x.id,
                "label": x.name,
                "img": CDN + x.image_path,
                "subtitle": x.town or "",
            })

    if ep_ids:
        qs = Episodes.objects.filter(id__in=ep_ids)
        for x in qs:
            results.append({
                "type": "episodes",
                "id": x.id,
                "label": x.name,
                "img": CDN + x.image_path,
                "subtitle": f"S{x.season} · E{x.episode_number}",
            })

    return JsonResponse({
        "ok": True,
        "category": {"slug": slug, "name": cat.get("name", "")},
        "results": results
    })

@require_GET
@login_required
def ranking_items(request, ranking_id):
    # 1) Traer ranking desde Mongo por _id (ObjectId)
    try:
        oid = ObjectId(ranking_id)
    except Exception:
        return JsonResponse({"results": []}, status=404)

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        doc = db["rankings"].find_one({"_id": oid})
        client.close()
    except Exception:
        doc = None

    if not doc:
        return JsonResponse({"results": []}, status=404)

    refs = doc.get("rankinList") or []

    CDN = "https://cdn.thesimpsonsapi.com/1280"
    results = []

    # 2) Cargar todo de golpe
    char_ids = [r["id"] for r in refs if r.get("type") == "characters"]
    loc_ids = [r["id"] for r in refs if r.get("type") == "locations"]
    ep_ids = [r["id"] for r in refs if r.get("type") == "episodes"]

    chars = {c.id: c for c in Character.objects.filter(id__in=char_ids)}
    locs = {l.id: l for l in Locations.objects.filter(id__in=loc_ids)}
    eps = {e.id: e for e in Episodes.objects.filter(id__in=ep_ids)}

    # 3) Mantener el orden exacto del ranking
    for ref in refs:
        t = ref.get("type")
        _id = ref.get("id")

        if t == "characters":
            c = chars.get(_id)
            if not c:
                continue
            results.append({
                "type": "characters",
                "id": c.id,
                "label": c.name,
                "img": (CDN + c.portrait_path) if c.portrait_path else None,
                "subtitle": c.occupation or "",
            })

        elif t == "locations":
            l = locs.get(_id)
            if not l:
                continue
            results.append({
                "type": "locations",
                "id": l.id,
                "label": l.name,
                "img": (CDN + l.image_path) if l.image_path else None,
                "subtitle": l.town or "",
            })

        elif t == "episodes":
            e = eps.get(_id)
            if not e:
                continue
            results.append({
                "type": "episodes",
                "id": e.id,
                "label": e.name,
                "img": (CDN + e.image_path) if e.image_path else None,
                "subtitle": f"S{e.season} · E{e.episode_number}",
            })

    return JsonResponse({"results": results})


@require_GET
def character_reviews(request, character_id):
    """Devuelve reviews de un personaje (últimas primero)."""
    try:
        character_id = int(character_id)
    except Exception:
        return JsonResponse({"results": []}, status=400)

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        docs = list(
            db["reviews"]
            .find({"characterCode": character_id})
            .sort("reviewDate", -1)
            .limit(30)
        )
        client.close()
    except Exception:
        docs = []

    results = []
    for d in docs:
        results.append({
            "user": d.get("user", "anon"),
            "rating": int(d.get("rating", 0) or 0),
            "comment": d.get("comment", ""),
            "reviewDate": d.get("reviewDate"),
        })

    return JsonResponse({"results": results})
