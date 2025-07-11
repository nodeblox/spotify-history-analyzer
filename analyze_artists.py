import os
import sys
import json
import time
import sqlite3
import requests
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

import utils

# === Datenbank initialisieren ===
CACHE_DIR = ".cache"
DB_PATH = os.path.join(CACHE_DIR, "cache.db")
os.makedirs(CACHE_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Tabellen erstellen
cur.execute("CREATE TABLE IF NOT EXISTS songdata (id TEXT PRIMARY KEY, json JSON)")
cur.execute("CREATE TABLE IF NOT EXISTS artistdata (artist_name TEXT PRIMARY KEY, json JSON)")
conn.commit()

# === Konfiguration laden ===
load_dotenv()
TIMEZONE = os.getenv("TIMEZONE")


def main(input_filename: str):
    input_path = os.path.join("userdata", input_filename)
    output_dir = os.path.join("output", input_filename.replace(".json", ""))
    os.makedirs(os.path.join(output_dir, "artists"), exist_ok=True)

    output_file = os.path.join(output_dir, "artists.md")

    print(f"📂 Lese Daten aus: {input_path}")
    data = utils.load_data(input_path)

    utils.clear_md(output_file)
    analyse(data, output_file, output_dir)


def analyse(data, output_file, output_dir):
    print("📊 Analysiere Artists...")

    artist_times = defaultdict(int)
    artist_urls = {}

    for song in data:
        artist = song.get("master_metadata_album_artist_name")
        if not artist:
            continue

        track_id = song.get("spotify_track_uri")
        cur.execute("SELECT json FROM songdata WHERE id = ?", [track_id])
        row = cur.fetchone()

        if row:
            lastfm_data = json.loads(row["json"]).get("track")
            if artist not in artist_urls and lastfm_data:
                artist_urls[artist] = lastfm_data.get("artist", {}).get("url")
        artist_times[artist] += song.get("ms_played", 0)

    top_artists = sorted(artist_times.items(), key=lambda x: x[1], reverse=True)[:500]

    utils.append_md(output_file, "### Top 500 Artists\n")

    for i, (artist, played_ms) in enumerate(top_artists, start=1):
        filename = utils.sanitize_filename(artist) + ".md"
        playtime_h = played_ms / 1000 / 60 / 60
        utils.append_md(output_file, f"{i}. **[[./artists/{filename}|{artist}]]** mit **{playtime_h:.2f} Stunden** Spielzeit")
        get_artist_data(i, data, artist, output_dir, artist_url=artist_urls.get(artist))


def get_artist_data(index, data, artist_name, output_dir, artist_url=None):
    start = time.time()

    cur.execute("SELECT json FROM artistdata WHERE artist_name = ?", [artist_name])
    row = cur.fetchone()

    if row:
        artist_data = json.loads(row["json"])
        from_cache = True
    else:
        api_url = (
            f"https://ws.audioscrobbler.com/2.0/?method=artist.getinfo"
            f"&api_key={os.getenv('LASTFM_API_KEY')}&artist={urllib.parse.quote(artist_name)}&format=json"
        )
        response = requests.get(api_url)
        if response.status_code != 200:
            print(f"❌ Fehler beim Laden von {artist_name}: HTTP {response.status_code}")
            return

        artist_data = response.json()
        cur.execute(
            "INSERT OR REPLACE INTO artistdata (artist_name, json) VALUES (?, ?)",
            (artist_name, json.dumps(artist_data, ensure_ascii=False))
        )
        conn.commit()
        from_cache = False

    # Markdown-Datei schreiben
    artist_filename = utils.sanitize_filename(artist_name) + ".md"
    artist_filepath = os.path.join(output_dir, "artists", artist_filename)

    summary = artist_data.get("artist", {}).get("bio", {}).get("summary", "Keine Beschreibung verfügbar.")
    summary = utils.html_to_md_links(summary)
    tags = artist_data.get("artist", {}).get("tags", {}).get("tag", [])

    utils.clear_md(artist_filepath)
    utils.append_md(artist_filepath, f"# {artist_name}")
    if artist_url:
        utils.append_md(artist_filepath, f"[Last.fm-Profil]({artist_url})\n")
    if tags:
        tag_list = ", ".join(tag["name"] for tag in tags)
        utils.append_md(artist_filepath, f"**Tags**: {tag_list}")
    else:
        utils.append_md(artist_filepath, "Keine Tags gefunden.")
    utils.append_md(artist_filepath, "\n" + summary)

    get_most_heared_songs(data, artist_name, artist_filepath, output_dir)

    print(f"✅ | {str(index).zfill(3)} / 500 | {'📄 (Cache)' if from_cache else '🆕 (API)'}: {artist_name}")

    # API-Rate-Limit beachten
    elapsed = time.time() - start
    if not from_cache and elapsed < 0.25:
        time.sleep(0.25 - elapsed)


def get_most_heared_songs(data, artist, artist_filepath, output_dir):
    """
    Fügt die 25 meistgehörten Songs eines Artists zur Markdown-Datei hinzu.
    """
    song_stats = {}
    for entry in data:
        artist_name = entry.get("master_metadata_album_artist_name", "")
        track_uri = entry.get("spotify_track_uri")
        track_name = entry.get("master_metadata_track_name", "Unbekannt")

        if artist_name != artist or not track_uri:
            continue

        cur.execute("SELECT json FROM songdata WHERE id = ?", [track_uri])
        row = cur.fetchone()
        lastfm_data = json.loads(row["json"]).get("track") if row else None

        if track_uri not in song_stats:
            song_stats[track_uri] = {
                "track_name": track_name,
                "times_played": 1,
                "lastfm_data": lastfm_data,
            }
        else:
            song_stats[track_uri]["times_played"] += 1

    top_songs = sorted(song_stats.items(), key=lambda x: x[1]["times_played"], reverse=True)[:25]

    if not top_songs:
        utils.append_md(artist_filepath, "\n**Keine Songs gefunden.**")
        return

    utils.append_md(artist_filepath, "\n### Meistgehörte Songs\n")

    for i, (track_uri, song) in enumerate(top_songs, start=1):
        if i == 1:
            utils.append_md(artist_filepath, "##### 1 bis 10\n")
            utils.append_md(artist_filepath, "##### 11 bis 25\n")
        elif i == 11:
            utils.append_md(artist_filepath, "##### 11 bis 25\n")

        track_name = song["track_name"]
        times_played = song["times_played"]
        lastfm_data = song["lastfm_data"]

        song_path = os.path.join(output_dir, "songs", track_uri[14:] + ".md")
        link = f'[[../songs/{track_uri[14:]}.md|{track_name}]]' if lastfm_data and os.path.exists(song_path) else track_name
        utils.append_md(artist_filepath, f"{i}. **{link}** – **{times_played}** mal gehört")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Fehler: Gib den Namen der history-Datei als Argument an (z. B. history.json)")
        sys.exit(1)

    main(sys.argv[1])
