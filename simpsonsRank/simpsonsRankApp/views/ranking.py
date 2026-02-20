import json

from bson import ObjectId
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from pymongo import MongoClient

from simpsonsRankApp.models import Locations, Character, Episodes, Ranking
from simpsonsRankApp.static.json.import_to_mongo import MONGO_URI, DB_NAME


def show_ranking(request):
    cat = (request.GET.get("cat") or "").strip()

    # =========================
    # Mongo: conectar
    # =========================
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
    except Exception:
        # si no hay mongo, render vacío
        return render(request, "ranking.html", {
            "my_rankings": [],
            "public_rankings": [],
            "categories": [],
            "categories_cards": [],
            "current_cat": cat,
            "top5_categories": [],
        })

    # =========================
    # Categorías (Mongo)
    # =========================
    categories = []
    try:
        # Admin ve todas; user solo activas
        cat_filter = {} if (request.user.is_authenticated and request.user.is_staff) else {"is_active": True}

        categories = list(
            db["categories"]
            .find(cat_filter, {"_id": 0})
            .sort("name", 1)
        )
    except Exception:
        categories = []

    cat_map = {c.get("slug"): c.get("name") for c in categories}

    # =========================
    # Helper imágenes (SQL)
    # =========================
    CDN = "https://cdn.thesimpsonsapi.com/1280"

    def cover_from_ref(t, _id):
        if t == "characters":
            x = Character.objects.filter(id=_id).first()
            return (CDN + x.portrait_path) if x and x.portrait_path else None
        if t == "locations":
            x = Locations.objects.filter(id=_id).first()
            return (CDN + x.image_path) if x and x.image_path else None
        if t == "episodes":
            x = Episodes.objects.filter(id=_id).first()
            return (CDN + x.image_path) if x and x.image_path else None
        return None

    # =========================
    # Rankings (Mongo)
    # =========================
    query = {}
    if cat:
        query["categoryCode"] = cat

    try:
        rankings_docs = list(
            db["rankings"]
            .find(query)
            .sort("rankinDate", -1)
        )
    except Exception:
        rankings_docs = []

    # =========================
    # Contar rankings por categoría (para bloquear editar)
    # =========================
    from collections import Counter

    cat_counter = Counter()
    for d in rankings_docs:
        slug = (d.get("categoryCode") or "").strip()
        if slug:
            cat_counter[slug] += 1

    ranked_slugs = set(cat_counter.keys())  # categorías con al menos 1 ranking

    # usuario actual (para mis rankings)
    me = (request.user.username if request.user.is_authenticated else "")
    me_low = me.lower()

    my_rankings = []
    public_rankings = []

    for d in rankings_docs:
        items = d.get("rankinList") or []

        first_img = None
        if items:
            first = items[0]
            first_img = cover_from_ref(first.get("type"), first.get("id"))

        category_slug = d.get("categoryCode", "")
        category_name = cat_map.get(category_slug, category_slug)

        # toma el título desde mongo
        title = (
            (d.get("title") or "")
            or (d.get("rankingTitle") or "")
            or (d.get("rankinTitle") or "")
        ).strip()

        if not title:
            title = f"Mi top de {category_name}" if category_name else "Mi ranking"

        card = {
            "id": str(d.get("_id")),
            "user": d.get("user", ""),
            "fecha": d.get("rankinDate"),
            "categoria_slug": category_slug,
            "categoria_nombre": category_name,
            "title": title,
            "num_items": len(items),
            "top3": "Top 3 al abrir",
            "first_img": first_img,
        }

        doc_user = (card["user"] or "")
        if me and doc_user.lower() == me_low:
            my_rankings.append(card)
        else:
            public_rankings.append(card)

    # =========================
    # Cards de categorías (con flag has_rankings)
    # =========================
    categories_cards = []
    for c in categories:
        attach = c.get("attach", {}) or {}
        cover_img = None

        if attach.get("characters"):
            cover_img = cover_from_ref("characters", attach["characters"][0])
        elif attach.get("locations"):
            cover_img = cover_from_ref("locations", attach["locations"][0])
        elif attach.get("episodes"):
            cover_img = cover_from_ref("episodes", attach["episodes"][0])

        slug = c.get("slug", "")

        categories_cards.append({
            "name": c.get("name", ""),
            "slug": slug,
            "description": c.get("description", ""),
            "is_active": c.get("is_active", True),
            "cover_img": cover_img,

            # para ocultar "Editar" si ya hay rankings en esa categoría
            "has_rankings": slug in ranked_slugs,
            "rankings_count": cat_counter.get(slug, 0),
        })

    # =========================
    # SIDEBAR: TOP 5 CATEGORÍAS (por nº de rankings)
    # =========================
    top5_categories = []
    for slug, count in cat_counter.most_common(5):
        name = cat_map.get(slug, slug)

        cover_img = None
        cdoc = next((c for c in categories if c.get("slug") == slug), None)
        if cdoc:
            attach = cdoc.get("attach", {}) or {}
            if attach.get("characters"):
                cover_img = cover_from_ref("characters", attach["characters"][0])
            elif attach.get("locations"):
                cover_img = cover_from_ref("locations", attach["locations"][0])
            elif attach.get("episodes"):
                cover_img = cover_from_ref("episodes", attach["episodes"][0])

        top5_categories.append({
            "slug": slug,
            "name": name,
            "count": count,
            "img": cover_img,
        })

    client.close()

    return render(request, "ranking.html", {
        "my_rankings": my_rankings,
        "public_rankings": public_rankings,
        "categories": categories,
        "categories_cards": categories_cards,
        "current_cat": cat,
        "top5_categories": top5_categories,
    })


@require_POST
@login_required
def create_ranking(request):
    category = (request.POST.get("category") or "").strip()
    title = (request.POST.get("title") or "").strip()
    items_json = request.POST.get("items_json") or "[]"

    try:
        items = json.loads(items_json)
    except Exception:
        messages.error(request, "Items inválidos.")
        return redirect("show_ranking")

    if len(title) < 3:
        messages.error(request, "Título demasiado corto.")
        return redirect("show_ranking")

    if not isinstance(items, list) or len(items) < 3:
        messages.error(request, "Añade al menos 3 items.")
        return redirect("show_ranking")

    try:
        rankin_list = [{"type": it["type"], "id": int(it["id"])} for it in items]
    except Exception:
        messages.error(request, "Formato de items inválido.")
        return redirect("show_ranking")

    # OVERWRITE: 1 ranking por usuario y categoría
    try:
        Ranking.objects.update_or_create(
            user=request.user.username,
            categoryCode=category,
            defaults={
                "title": title,
                "rankinList": rankin_list,
                "rankinDate": timezone.now().date(),
            }
        )
        messages.success(request, "Ranking guardado correctamente.")
    except Exception as e:
        return HttpResponse(f"ERROR guardando ranking: {e}")

    return redirect("show_ranking")

@require_POST
@login_required
def delete_ranking(request, ranking_id):
    """
    Borra ranking si es del usuario.
    Staff puede borrar cualquiera (opcional).
    """
    try:
        oid = ObjectId(ranking_id)
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid id"}, status=400)

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        col = db["rankings"]

        doc = col.find_one({"_id": oid})
        if not doc:
            client.close()
            return JsonResponse({"ok": False, "error": "Not found"}, status=404)

        owner = (doc.get("user") or "")
        me = request.user.username

        if (owner != me) and (not request.user.is_staff):
            client.close()
            return JsonResponse({"ok": False, "error": "Forbidden"}, status=403)

        col.delete_one({"_id": oid})
        client.close()
        return JsonResponse({"ok": True})

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)