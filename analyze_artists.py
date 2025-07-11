import os
import sys
import utils
from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import json
import requests
import urllib.parse
import time

load_dotenv()
TIMEZONE = os.getenv("TIMEZONE")

def main(input_filename):
    input_path = os.path.join("userdata", input_filename)
    output_path = os.path.join("output", input_filename.replace(".json", ""))
    os.makedirs(os.path.join(output_path, "artists"), exist_ok=True)
    output_file = os.path.join("output", input_filename.replace(".json", ""), "artists.md")

    print(f"📂 Lese Daten aus: {input_path}")
    data = utils.load_data(input_path)

    utils.clear_md(output_file)
    analyse(data, output_file, output_path)

def analyse(data, output_file, output_path):
    print("📊 Analysiere Artists...")

    artist_times = defaultdict(int)
    artist_urls = defaultdict(str)

    for song in data:
        artist = song['spotify_data'].get("master_metadata_album_artist_name", 'unknown')
        artist_urls[artist] = (song.get('lastfm_data', {}) or {}).get('track', {}).get('artist', {}).get('url', None)
        artist_times[artist] += song['spotify_data']['ms_played']
        ts = song['spotify_data']['ts']
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(ZoneInfo(TIMEZONE) if TIMEZONE else None)

    artist_times_sorted = sorted(artist_times.items(), key=lambda x: x[1], reverse=True)

    top_artists = artist_times_sorted[:500]

    utils.append_md(output_file, f"### Top 500 Artists")

    i = 0
    for artist, played_ms in top_artists:
        if artist == "unknown":
            continue
        i += 1
        filename = utils.sanitize_filename(artist) + ".md"
        utils.append_md(output_file, f"{i}. **[[./artists/{filename}|{artist}]]** mit **{(played_ms / 1000 / 60 / 60):.2f} Stunden** Spielzeit")

        # .md-Datei für den Artist erzeugen
        get_artist_data(i, data, artist, output_path, artist_url=artist_urls[artist])


def get_artist_data(i, data, artist_name, output_path, artist_url=None):
    os.makedirs(".cache", exist_ok=True)
    cache_path = os.path.join(".cache", "artists.cache")
    cache = {}

    # Cache laden
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            try:
                cache = json.load(f)
            except:
                cache = {}

    if artist_name in cache:
        artist_data = cache[artist_name]
        from_cache = True
    else:
        encoded_artist = urllib.parse.quote(artist_name)
        url = (
            f"https://ws.audioscrobbler.com/2.0/?method=artist.getinfo"
            f"&api_key={os.getenv('LASTFM_API_KEY')}&artist={encoded_artist}&format=json"
        )
        response = requests.get(url)
        if response.status_code != 200:
            print(f"❌ Fehler beim Laden von {artist_name}: {response.status_code}")
            return
        artist_data = response.json()
        cache[artist_name] = artist_data
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
        from_cache = False

    # .md Datei schreiben
    artist_filename = utils.sanitize_filename(artist_name) + ".md"
    artist_filepath = os.path.join(output_path, "artists", artist_filename)

    summary = artist_data.get("artist", {}).get("bio", {}).get("summary", "Keine Beschreibung verfügbar.")
    summary = utils.html_to_md_links(summary)
    tags = artist_data.get("artist", {}).get("tags", {}).get("tag", [])

    utils.clear_md(artist_filepath)
    utils.append_md(artist_filepath, f"# {artist_name}")
    if artist_url:
        utils.append_md(artist_filepath, f"[Last.fm-Profil]({artist_url})\n")
    utils.append_md(artist_filepath, f"**Tags**: " + ", ".join([tag["name"] for tag in tags]) if tags else "Keine Tags gefunden.")
    utils.append_md(artist_filepath, "\n" + summary)

    get_most_heared_songs(data, artist_name, artist_filepath, output_path)

    print(f"✅ | {str(i).zfill(3)} / 500 | {'📄 (Cache)' if from_cache else '🆕 (API)'}: {artist_name}")
    if not from_cache:
            time.sleep(0.3)  # API-Rate-Limit

def get_most_heared_songs(data, artist, artist_filepath, output_path):
    """
    Fügt die 25 meistgehörten Songs des gegebenen Künstlers zur Artist-Markdown-Datei hinzu.
    """
    from collections import defaultdict
    import utils

    # Songs des Künstlers sammeln und Playcount zählen
    song_stats = {}
    for entry in data:
        track_data = entry.get("spotify_data", {})
        lastfm_data = (entry.get("lastfm_data", {}) or {}).get("track", {})
        artist_name = track_data.get("master_metadata_album_artist_name", "")
        track_uri = track_data.get("spotify_track_uri")
        track_name = track_data.get("master_metadata_track_name", "Unbekannt")
        if artist_name != artist or not track_uri:
            continue
        if track_uri not in song_stats:
            song_stats[track_uri] = {
                "track_name": track_name,
                "times_played": 1,
                "lastfm_data": lastfm_data,
            }
        else:
            song_stats[track_uri]["times_played"] += 1

    # Nach Plays sortieren, Top 25 nehmen
    top_songs = sorted(song_stats.items(), key=lambda x: x[1]["times_played"], reverse=True)[:25]

    if not top_songs:
        utils.append_md(artist_filepath, "\n**Keine Songs gefunden.**")
        return
    
    i = 0
    utils.append_md(artist_filepath, "\n### Meistgehörte Songs")
    if len(top_songs) > 10:
        utils.append_md(artist_filepath, "##### 1 bis 10")
    for track_uri, song in top_songs:
        if i == 10: utils.append_md(artist_filepath, "##### 11 bis 25")
        i+=1
        track_name = song["track_name"]
        times_played = song["times_played"]
        lastfm_data = song["lastfm_data"]

        path_exists = os.path.exists(os.path.join(output_path, "songs", track_uri[14:] + ".md"))

        # Link zur Songdatei, falls lastfm_data vorhanden
        if lastfm_data is not None and path_exists:
            link = f'[[../songs/{track_uri[14:]}.md|{track_name}]]'
        else:
            link = track_name
        utils.append_md(
            artist_filepath,
            f"{i}. **{link}** – **{times_played}** mal gehört"
        )

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Fehler: Gib den Namen der history-Datei als Argument an (z. B. detailed_history.json)")
        sys.exit(1)
    input_filename = sys.argv[1]
    main(input_filename)
