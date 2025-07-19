import os
import sys
import time
import requests
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import matplotlib.pyplot as plt
import utils
from database import db
from config import TIMEZONE, MIN_PLAY_DURATION

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
        lastfm_data = db.get_song_data(track_id)
        if lastfm_data:
            if artist not in artist_urls:
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

    artist_data = db.get_artist_data(artist_name)

    if artist_data:
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
        db.store_artist_data(artist_name, artist_data)
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
    utils.append_md(artist_filepath, "\n")
    
    # === Monatsbalkendiagramm ===
    monthly_minutes = defaultdict(float)
    total_artist_minutes = 0
    total_all_minutes = 0

    for entry in data:
        ts = entry.get("ts")
        if not ts:
            continue
        ms_played = entry.get("ms_played", 0)
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if TIMEZONE:
            dt = dt.astimezone(ZoneInfo(TIMEZONE))
        month = dt.strftime("%Y-%m")
        minutes = ms_played / 60000
        total_all_minutes += minutes
        if not monthly_minutes[month]: monthly_minutes[month] = 0
        if entry.get("master_metadata_album_artist_name") == artist_name:
            monthly_minutes[month] += minutes
            total_artist_minutes += minutes

    # Monats-Balkendiagramm generieren
    if monthly_minutes:
        months = sorted(monthly_minutes.keys())
        minutes = [monthly_minutes[m] for m in months]

        plt.figure(figsize=(12, 6))
        plt.bar(months, minutes, color='skyblue')
        plt.title(f"Listening minutes per month for {utils.to_ascii(artist_name)}")
        plt.ylabel("listening minutes")
        plt.xticks(rotation=45)
        plt.tight_layout()

        monthly_chart_filename = f"{utils.sanitize_filename(artist_name)}_monthly_minutes.png"
        monthly_chart_path = os.path.join(output_dir, "img", monthly_chart_filename)
        os.makedirs(os.path.dirname(monthly_chart_path), exist_ok=True)
        plt.savefig(monthly_chart_path, bbox_inches='tight', pad_inches=0.5)
        plt.close()

        utils.append_md(artist_filepath, f"![Listening behavior per month](../img/{monthly_chart_filename})")
    else:
        utils.append_md(artist_filepath, "_Keine Daten für monatliches Hörverhalten gefunden._")

    # === Kreisdiagramm Gesamtzeit: Artist vs. Rest ===
    if total_artist_minutes > 0:
        rest_minutes = total_all_minutes - total_artist_minutes
        labels = [f"{utils.to_ascii(artist_name)}", "others"]
        sizes = [total_artist_minutes, rest_minutes]

        plt.figure(figsize=(6, 6))
        plt.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90, counterclock=False, colors=["#ff9999", "#dddddd"])
        plt.title(f"{utils.to_ascii(artist_name)} vs. rest - total listening time")
        plt.axis("equal")
        pie_chart_filename = f"{utils.sanitize_filename(artist_name)}_share_vs_rest.png"
        pie_chart_path = os.path.join(output_dir, "img", pie_chart_filename)
        plt.savefig(pie_chart_path, bbox_inches='tight', pad_inches=0.5)
        plt.close()

        utils.append_md(artist_filepath, f"![Proportion of total playing time](../img/{pie_chart_filename})")
    else:
        utils.append_md(artist_filepath, "_Keine Hörzeit für diesen Artist vorhanden._")

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
        ms_played = entry.get("ms_played")

        if artist_name != artist or not track_uri or not ms_played or ms_played < MIN_PLAY_DURATION:
            continue

        lastfm_data = db.get_song_data(track_uri)

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
        elif i == 11:
            utils.append_md(artist_filepath, "##### 11 bis 25\n")

        track_name = song["track_name"]
        times_played = song["times_played"]
        lastfm_data = song["lastfm_data"]

        link = f'[[../songs/{track_uri[14:]}.md|{track_name}]]' if lastfm_data else track_name
        utils.append_md(artist_filepath, f"{i}. **{link}** – **{times_played}** mal gehört")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Fehler: Gib den Namen der history-Datei als Argument an (z.B. history.json)")
        sys.exit(1)

    main(sys.argv[1])
