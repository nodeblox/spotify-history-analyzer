# NUR FÜR DIE ENTWICKLUNG RELEVANT
# -------------------------------------------

import json
import os

detailed_path = os.path.join("userdata", "detailed_xxxxxxxxxxxxxxxxxxxxxxxx.json")
cache_path = os.path.join(".cache")

if not os.path.exists(detailed_path):
    print(f"❌ Datei nicht gefunden: {detailed_path}")
    exit(1)

with open(detailed_path, "r", encoding="utf-8") as f:
    data = json.load(f)

cache = {}
for entry in data:
    spotify_data = entry.get("spotify_data", entry)
    track_id = spotify_data.get("spotify_track_uri")
    lastfm_data = entry.get("lastfm_data")
    if track_id and lastfm_data is not None:
        cache[track_id] = lastfm_data

with open(cache_path, "w", encoding="utf-8") as f:
    json.dump(cache, f, ensure_ascii=False)

print(f"✅ {len(cache)} Einträge nach {cache_path} übertragen.")
