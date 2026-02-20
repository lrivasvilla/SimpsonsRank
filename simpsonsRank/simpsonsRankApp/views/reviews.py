from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from pymongo import MongoClient

from simpsonsRankApp.static.json.import_to_mongo import MONGO_URI, DB_NAME


@require_POST
@login_required
def create_character_review(request, character_id):
    """Crea o actualiza (upsert) una review para un personaje: 1 por usuario y personaje."""
    try:
        character_id = int(character_id)
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid character"}, status=400)

    rating = (request.POST.get("rating") or "").strip()
    comment = (request.POST.get("comment") or "").strip()

    try:
        rating = int(rating)
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid rating"}, status=400)

    if rating < 1 or rating > 5:
        return JsonResponse({"ok": False, "error": "Rating must be 1..5"}, status=400)

    if len(comment) < 2:
        return JsonResponse({"ok": False, "error": "Comment too short"}, status=400)

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]

        # UPSERT: si existe (user+characterCode) actualiza; si no, crea
        db["reviews"].update_one(
            {"user": request.user.username, "characterCode": character_id},
            {"$set": {
                "rating": rating,
                "comment": comment,
                "reviewDate": timezone.now(),
            }},
            upsert=True
        )

        client.close()
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

    return JsonResponse({"ok": True})


@require_GET
def episode_reviews(request, episode_id):
    """Devuelve reviews de un episodio (últimas primero)."""
    try:
        episode_id = int(episode_id)
    except Exception:
        return JsonResponse({"results": []}, status=400)

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        docs = list(
            db["reviews"]
            .find({"episodeCode": episode_id})
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


@require_POST
@login_required
def create_episode_review(request, episode_id):
    """Crea o actualiza (upsert) una review para un episodio: 1 por usuario y episodio."""
    try:
        episode_id = int(episode_id)
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid episode"}, status=400)

    rating = (request.POST.get("rating") or "").strip()
    comment = (request.POST.get("comment") or "").strip()

    try:
        rating = int(rating)
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid rating"}, status=400)

    if rating < 1 or rating > 5:
        return JsonResponse({"ok": False, "error": "Rating must be 1..5"}, status=400)

    if len(comment) < 2:
        return JsonResponse({"ok": False, "error": "Comment too short"}, status=400)

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]

        # UPSERT: si existe (user+episodeCode) actualiza; si no, crea
        db["reviews"].update_one(
            {"user": request.user.username, "episodeCode": episode_id},
            {"$set": {
                "rating": rating,
                "comment": comment,
                "reviewDate": timezone.now(),
            }},
            upsert=True
        )

        client.close()
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

    return JsonResponse({"ok": True})


@require_GET
def location_reviews(request, location_id):
    try:
        location_id = int(location_id)
    except Exception:
        return JsonResponse({"results": []}, status=400)

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        docs = list(
            db["reviews"]
            .find({"locationCode": location_id})
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


@require_POST
@login_required
def create_location_review(request, location_id):
    """Crea o actualiza (upsert) una review para una localización: 1 por usuario y location."""
    try:
        location_id = int(location_id)
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid location"}, status=400)

    rating = (request.POST.get("rating") or "").strip()
    comment = (request.POST.get("comment") or "").strip()

    try:
        rating = int(rating)
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid rating"}, status=400)

    if rating < 1 or rating > 5:
        return JsonResponse({"ok": False, "error": "Rating must be 1..5"}, status=400)

    if len(comment) < 2:
        return JsonResponse({"ok": False, "error": "Comment too short"}, status=400)

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]

        # UPSERT: si existe (user+locationCode) actualiza; si no, crea
        db["reviews"].update_one(
            {"user": request.user.username, "locationCode": location_id},
            {"$set": {
                "rating": rating,
                "comment": comment,
                "reviewDate": timezone.now(),
            }},
            upsert=True
        )

        client.close()
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

    return JsonResponse({"ok": True})