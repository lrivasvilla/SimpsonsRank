import json
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.template.defaultfilters import slugify
from django.views.decorators.http import require_POST, require_GET
from pymongo import MongoClient

from simpsonsRankApp.static.json.import_to_mongo import MONGO_URI, DB_NAME


@require_POST
@login_required
def upload_json(request):
    if not request.user.is_staff:
        messages.error(request, "No tienes permisos para subir archivos.")
        return redirect("home")

    collection = request.POST.get("collection")
    if collection not in {"characters", "episodes", "locations"}:
        messages.error(request, "Colección inválida.")
        return redirect("home")

    f = request.FILES.get("json_file")
    if not f:
        messages.error(request, "No se ha subido ningún archivo.")
        return redirect("home")

    try:
        data = json.load(f)
    except Exception as e:
        messages.error(request, f"El archivo no es un JSON válido: {e}")
        return redirect("home")

    if not isinstance(data, list):
        messages.error(request, "El JSON debe ser una lista de documentos.")
        return redirect("home")

    reset = request.POST.get("reset") == "on"

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        col = db[collection]

        if reset:
            col.delete_many({})

        if data:
            col.insert_many(data)
            messages.success(request, f" Se han importado {len(data)} documentos en '{collection}'.")
        else:
            messages.warning(request, f"La colección '{collection}' estaba vacía. No se insertó nada.")

        client.close()

    except Exception as e:
        messages.error(request, f"Error al insertar en MongoDB: {e}")

    return redirect("home")

@require_GET
@login_required
def admin_get_category(request, slug):
    if not request.user.is_staff:
        return JsonResponse({"ok": False, "error": "Forbidden"}, status=403)

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        doc = db["categories"].find_one({"slug": slug})
        client.close()
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

    if not doc:
        return JsonResponse({"ok": False, "error": "Category not found"}, status=404)

    doc["_id"] = str(doc["_id"])
    return JsonResponse({"ok": True, "category": doc})


@require_POST
@login_required
def admin_toggle_category(request, slug):
    if not request.user.is_staff:
        return JsonResponse({"ok": False, "error": "Forbidden"}, status=403)

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        col = db["categories"]

        doc = col.find_one({"slug": slug})
        if not doc:
            client.close()
            return JsonResponse({"ok": False, "error": "Category not found"}, status=404)

        current = bool(doc.get("is_active", True))
        col.update_one({"_id": doc["_id"]}, {"$set": {"is_active": (not current)}})

        client.close()
        return JsonResponse({"ok": True, "is_active": (not current)})

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@require_POST
@login_required
def admin_update_category(request, slug):
    """
    Actualiza: name, slug, description, is_active y attach.
    Devuelve 409 si el slug o el name ya existe en otra categoría.
    """
    if not request.user.is_staff:
        return JsonResponse({"ok": False, "error": "Forbidden"}, status=403)

    name = (request.POST.get("name") or "").strip()
    new_slug = (request.POST.get("slug") or "").strip()
    description = (request.POST.get("description") or "").strip()
    is_active = request.POST.get("is_active") == "on"

    char_ids = request.POST.getlist("character_ids[]")
    loc_ids = request.POST.getlist("location_ids[]")
    ep_ids = request.POST.getlist("episode_ids[]")

    if len(name) < 3:
        return JsonResponse({"ok": False, "error": "Nombre demasiado corto"}, status=400)

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        col = db["categories"]

        current = col.find_one({"slug": slug})
        if not current:
            client.close()
            return JsonResponse({"ok": False, "error": "Category not found"}, status=404)

        # Si slug viene vacío, lo autogeneramos. Si aun así queda vacío, mantenemos el actual.
        if not new_slug:
            new_slug = slugify(name) or current.get("slug", slug)
        if not new_slug:
            client.close()
            return JsonResponse({"ok": False, "error": "Slug inválido"}, status=400)

        # Duplicados EXCLUYENDO el propio documento
        dup = col.find_one({
            "_id": {"$ne": current["_id"]},
            "$or": [
                {"slug": new_slug},
                {"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}}
            ]
        })
        if dup:
            client.close()
            return JsonResponse({"ok": False, "error": "Ya existe otra categoría con ese nombre o slug"}, status=409)

        update_doc = {
            "name": name,
            "slug": new_slug,
            "description": description,
            "is_active": is_active,
            "attach": {
                "characters": [int(x) for x in char_ids if str(x).strip().isdigit()],
                "locations": [int(x) for x in loc_ids if str(x).strip().isdigit()],
                "episodes": [int(x) for x in ep_ids if str(x).strip().isdigit()],
            }
        }

        col.update_one({"_id": current["_id"]}, {"$set": update_doc})
        client.close()

        return JsonResponse({"ok": True, "slug": new_slug})

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@require_POST
@login_required
def create_category(request):
    if not request.user.is_staff:
        messages.error(request, "No tienes permisos para crear categorías.")
        return redirect("home")

    name = (request.POST.get("name") or "").strip()
    slug = (request.POST.get("slug") or "").strip()
    description = (request.POST.get("description") or "").strip()
    is_active = request.POST.get("is_active") == "on"

    char_ids = request.POST.getlist("character_ids[]")
    loc_ids = request.POST.getlist("location_ids[]")
    ep_ids = request.POST.getlist("episode_ids[]")

    # Validación
    if len(name) < 3:
        messages.error(request, "El nombre debe tener al menos 3 caracteres.")
        return redirect(request.META.get("HTTP_REFERER", "home"))

    # Si no viene slug, lo generamos
    if not slug:
        slug = slugify(name)

    # slug vacío (por ejemplo, si el nombre es solo símbolos)
    if not slug:
        messages.error(request, "Slug inválido. Usa letras y números.")
        return redirect(request.META.get("HTTP_REFERER", "home"))

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        col = db["categories"]  # <- colección de categorías

        # Duplicados: mismo slug o mismo name (case-insensitive)
        dup = col.find_one({
            "$or": [
                {"slug": slug},
                {"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}}
            ]
        })

        if dup:
            messages.error(request, "Ya existe una categoría con ese nombre o slug.")
            client.close()
            return redirect(request.META.get("HTTP_REFERER", "home"))

        col.insert_one({
            "name": name,
            "slug": slug,
            "description": description,
            "is_active": is_active,
            "attach": {
                "characters": [int(x) for x in char_ids],
                "locations": [int(x) for x in loc_ids],
                "episodes": [int(x) for x in ep_ids],
            }
        })

        client.close()
        messages.success(request, "Categoría creada correctamente.")

    except Exception as e:
        messages.error(request, f"Error al crear categoría en MongoDB: {e}")

    return redirect(request.META.get("HTTP_REFERER", "home"))
