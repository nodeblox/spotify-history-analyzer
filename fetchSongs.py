import json
import requests
import urllib.parse
import os
import time
import sys
from dotenv import load_dotenv

# === .env laden ===
load_dotenv()
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")

# === Last.fm Request ===
def get_lastfm_info(artist, track):
    encoded_artist = urllib.parse.quote(artist)
    encoded_track = urllib.parse.quote(track)
    url = (
        f"https://ws.audioscrobbler.com/2.0/?method=track.getInfo"
        f"&api_key={LASTFM_API_KEY}&artist={encoded_artist}&track={encoded_track}&format=json"
    )
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Last.fm-Fehler: {response.status_code} - {response.text}")
    return response.json()

# === Helper for streaming JSON array ===
class JSONStreamWriter:
    def __init__(self, filepath):
        self.file = open(filepath, 'w', encoding='utf-8')
        self.first = True
        self.file.write('[')
    def write(self, obj):
        if not self.first:
            self.file.write(',\n')
        self.first = False
        json.dump(obj, self.file, ensure_ascii=False)
    def close(self):
        self.file.write(']\n')
        self.file.close()

# === Cache-Handling ===
def load_cache(cache_path):
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

def save_cache(cache_path, cache):
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)

# === Hauptprogramm ===
def main(input_filename="spotify_history.json"):
    input_path = os.path.join("userdata", input_filename)
    output_filename = f"detailed_{input_filename}"
    output_path = os.path.join("userdata", output_filename)
    os.makedirs(os.path.join(".cache"), exist_ok=True)
    cache_path = os.path.join(".cache", "songdata.cache")

    if not os.path.exists(input_path):
        print(f"❌ Datei nicht gefunden: {input_path}")
        sys.exit(1)

    # === detailed Datei leeren ===
    with open(output_path, "w", encoding="utf-8") as f:
        f.write('[]')

    # === Cache laden ===
    track_cache = load_cache(cache_path)

    # === Daten laden ===
    with open(input_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    writer = JSONStreamWriter(output_path)

    print(f"📂 Lese Daten aus: {input_path}")
    dataCount = len(data)
    print(f"📊 Anzahl der Einträge: {dataCount}")
    current_count = 0
    for entry in data:
        current_count += 1
        in_cache = False
        spotify_data = entry if 'spotify_data' not in entry else entry['spotify_data']
        track_id = spotify_data.get('spotify_track_uri')
        artist = spotify_data.get("master_metadata_album_artist_name")
        track = spotify_data.get("master_metadata_track_name")
        if not track_id or not artist or not track:
            continue
        if track_id in track_cache:
            lastfm_data = track_cache[track_id]
            in_cache = True
        else:
            try:
                lastfm_data = get_lastfm_info(artist, track)
            except Exception as e:
                print(f"   ❌ Fehler: {e}")
                lastfm_data = None
            track_cache[track_id] = lastfm_data
            save_cache(cache_path, track_cache)  # Cache nach jedem neuen Request speichern
        writer.write({'spotify_data': spotify_data, 'lastfm_data': lastfm_data})
        print(f"   ✅ | {str(current_count).zfill(len(str(dataCount)))} / {dataCount} | {artist} - {track} (ID: {track_id}) ({'cache' if in_cache else 'api'})")
        if not in_cache:
            time.sleep(0.3)  # API-Rate-Limit
    writer.close()
    print(f"\n✅ Gespeichert in: {output_path}")

    return output_path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Fehler: Gib den Namen der history-Datei als Argument an (z. B. history.json)")
        sys.exit(1)
    input_filename = sys.argv[1]
    main(input_filename)
