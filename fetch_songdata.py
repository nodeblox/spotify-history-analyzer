import json
import requests
import urllib.parse
import os
import time
import sys
from dotenv import load_dotenv
import sqlite3

# === Datenbank initialisieren ===
os.makedirs(os.path.join(".cache"), exist_ok=True)
conn = sqlite3.connect("./.cache/cache.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
# Tabelle erstellen
cur.execute("CREATE TABLE IF NOT EXISTS songdata (id STRING PRIMARY KEY, json JSON)")
conn.commit()

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

def fetch_and_store(artist, track, track_id):
    try:
        lastfm_data = get_lastfm_info(artist, track)
    except Exception as e:
        print(f"   ❌ Fehler: {e}")
        return track_id, artist, track, 'error'
    cur.execute("INSERT INTO songdata VALUES (?, ?)", [track_id, json.dumps(lastfm_data)])
    conn.commit()
    return track_id, artist, track, 'api'

# === Hauptprogramm ===
def main(input_filename="spotify_history.json"):
    input_path = os.path.join("userdata", input_filename)

    if not os.path.exists(input_path):
        print(f"❌ Datei nicht gefunden: {input_path}")
        sys.exit(1)

    # === Daten laden ===
    with open(input_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    print(f"📂 Lese Daten aus: {input_path}")
    dataCount = len(data)
    print(f"📊 Anzahl der Einträge: {dataCount}")
    current_count = 0
    for entry in data:
        start_processing_ts = time.time()
        current_count += 1
        in_cache = False
        track_id = entry.get('spotify_track_uri')
        artist = entry.get("master_metadata_album_artist_name")
        track = entry.get("master_metadata_track_name")

        if not track_id or not artist or not track:
            continue

        cur.execute("SELECT * FROM songdata WHERE id = ?", [track_id])
        row = cur.fetchone()
        if row:
            lastfm_data = row['json']
            in_cache = True
        else:
            try:
                lastfm_data = get_lastfm_info(artist, track)
            except Exception as e:
                print(f"   ❌ Fehler: {e}")
                continue
            cur.execute("INSERT INTO songdata VALUES (?, ?)", [track_id, json.dumps(lastfm_data)])
            conn.commit()
        print(f"   ✅ | {str(current_count).zfill(len(str(dataCount)))} / {dataCount} | {artist} - {track} (ID: {track_id}) ({'cache' if in_cache else 'api'})")
        end_processing_ts = time.time()
        sleep_time: float = 0.25 - (end_processing_ts - start_processing_ts)
        if not in_cache and sleep_time > 0:
            time.sleep(sleep_time)  # API-Rate-Limit
    conn.close()
    print(f"\n✅ Alle Songdaten abgerufen!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Fehler: Gib den Namen der history-Datei als Argument an (z. B. history.json)")
        sys.exit(1)
    input_filename = sys.argv[1]
    main(input_filename)
