import json
from pathlib import Path
from pymongo import MongoClient

MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "simpsonsRank"

FILES = {
    "characters": Path("simpsons_characters.json"),
    "episodes": Path("simpsons_episodes.json"),
    "locations": Path("simpsons_locations.json"),
}

RESET_COLLECTIONS = True  # True = borra y vuelve a insertar


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    for collection_name, path in FILES.items():
        if not path.exists():
            print(f"[ERROR] No existe: {path}")
            continue

        data = load_json(path)
        if not isinstance(data, list):
            print(f"[ERROR] {path} no contiene una lista JSON.")
            continue

        col = db[collection_name]

        if RESET_COLLECTIONS:
            col.delete_many({})

        if data:
            col.insert_many(data)
            print(f"[OK] {collection_name}: insertados {len(data)} documentos.")
        else:
            print(f"[WARN] {collection_name}: lista vacía.")

    print("DONE.")


if __name__ == "__main__":
    main()
