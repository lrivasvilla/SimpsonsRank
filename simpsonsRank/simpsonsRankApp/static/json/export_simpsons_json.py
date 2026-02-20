import json
import time
from typing import Optional, Iterable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://thesimpsonsapi.com/api"
LIMIT = 50

SLEEP = 0.10          # entre páginas
DETAIL_SLEEP = 0.12   # entre detalles (sube si el servidor corta)
TIMEOUT = (8, 40)     # (connect_timeout, read_timeout)

# ---------- sesión con retries ----------
def make_session() -> requests.Session:
    s = requests.Session()

    retry = Retry(
        total=8,                # reintentos totales
        connect=8,
        read=8,
        status=8,
        backoff_factor=0.6,     # espera: 0.6, 1.2, 2.4, 4.8...
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
        respect_retry_after_header=True,
    )

    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    s.mount("https://", adapter)
    s.mount("http://", adapter)

    s.headers.update({
        "User-Agent": "simpsons-export/1.0 (+requests)",
        "Accept": "application/json",
    })
    return s

SESSION = make_session()

# ---------- helpers ----------
def get_json(url: str, *, params: Optional[dict] = None) -> dict:
    r = SESSION.get(url, params=params, timeout=TIMEOUT)
    # si el servidor devuelve 4xx/5xx fuera de los reintentos, esto lo deja claro
    r.raise_for_status()
    return r.json()

def fetch_all(endpoint: str) -> list[dict]:
    page = 1
    all_items: list[dict] = []

    while True:
        url = f"{BASE}/{endpoint}"
        try:
            data = get_json(url, params={"page": page, "limit": LIMIT})
        except requests.RequestException as e:
            # Si una página falla pese a retries, puedes: reintentar manualmente, o abortar.
            # Aquí lo reintentamos manualmente con una pausa mayor y seguimos.
            print(f"[WARN] {endpoint} página {page} falló: {e}. Reintentando en 3s...")
            time.sleep(3)
            continue

        items = data.get("results", [])
        if not items:
            break

        all_items.extend(items)
        print(f"{endpoint}: página {page} -> total {len(all_items)}")
        page += 1
        time.sleep(SLEEP)

    return all_items

def fetch_detail(endpoint: str, item_id: int) -> dict:
    url = f"{BASE}/{endpoint}/{item_id}"
    return get_json(url)

def enrich_with_details(
    endpoint: str,
    items: list[dict],
    fields: Optional[set[str]] = None,
    *,
    skip_failures: bool = True,
) -> list[dict]:
    enriched: list[dict] = []

    for i, item in enumerate(items, start=1):
        item_id = item.get("id")
        if item_id is None:
            enriched.append(item)
            continue

        try:
            detail = fetch_detail(endpoint, int(item_id))
        except requests.RequestException as e:
            msg = f"[WARN] detalle {endpoint}/{item_id} falló: {e}"
            if skip_failures:
                print(msg + " -> se omite y se continúa")
                enriched.append(item)
                time.sleep(DETAIL_SLEEP)
                continue
            raise

        if fields is not None:
            for k in fields:
                if k in detail:
                    item[k] = detail[k]
        else:
            item.update(detail)

        enriched.append(item)

        if i % 50 == 0:
            print(f"{endpoint}: detalles {i}/{len(items)}")

        time.sleep(DETAIL_SLEEP)

    return enriched

def write_json(filename: str, data: list[dict]):
    if not data:
        print(f"{filename}: no hay datos")
        return

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"OK -> {filename} ({len(data)} registros)")

def main():
    print("Descargando personajes (lista)...")
    characters = fetch_all("characters")

    print("Enriqueciendo personajes con description (detalle por id)...")
    characters = enrich_with_details("characters", characters, fields={"description"})

    print("Descargando episodios...")
    episodes = fetch_all("episodes")

    print("Descargando lugares...")
    locations = fetch_all("locations")

    write_json("simpsons_characters.json", characters)
    write_json("simpsons_episodes.json", episodes)
    write_json("simpsons_locations.json", locations)

if __name__ == "__main__":
    main()
