import csv
import requests
import time

BASE = "https://thesimpsonsapi.com/api"
LIMIT = 50          # máximo permitido por la API
SLEEP = 0.1         # para no saturar

def fetch_all(endpoint: str) -> list[dict]:
    page = 1
    all_items = []

    while True:
        url = f"{BASE}/{endpoint}"
        r = requests.get(url, params={"page": page, "limit": LIMIT}, timeout=30)
        r.raise_for_status()

        data = r.json()
        items = data.get("results", [])

        if not items:
            break

        all_items.extend(items)
        print(f"{endpoint}: página {page} -> total {len(all_items)}")

        page += 1
        time.sleep(SLEEP)

    return all_items


def write_csv(filename: str, rows: list[dict]):
    if not rows:
        print(f"{filename}: no hay datos")
        return

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"OK -> {filename} ({len(rows)} filas)")


def main():
    print("Descargando personajes...")
    characters = fetch_all("characters")

    print("Descargando episodios...")
    episodes = fetch_all("episodes")

    print("Descargando lugares...")
    locations = fetch_all("locations")

    write_csv("../simpsons_characters.csv", characters)
    write_csv("../simpsons_episodes.csv", episodes)
    write_csv("../simpsons_locations.csv", locations)


if __name__ == "__main__":
    main()
