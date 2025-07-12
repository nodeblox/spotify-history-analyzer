import utils
import os
import sqlite3
import json
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

load_dotenv()
MIN_PLAY_DURATION = os.getenv("MIN_PLAY_DURATION", 20000)  # in ms
RECREATE_SONGDATA_FILES = os.getenv("RECREATE_SONGDATA_FILES", False)
TIMEZONE = os.getenv("TIMEZONE")

created_files = set()

# === Datenbank initialisieren ===
os.makedirs(os.path.join(".cache"), exist_ok=True)
conn = sqlite3.connect("./.cache/cache.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
# Tabelle erstellen
cur.execute("CREATE TABLE IF NOT EXISTS songdata (id STRING PRIMARY KEY, json JSON)")
conn.commit()

def plot_song_listening_over_time(spotify_data, track_id, lastfm_data, filename, output_path):
    song_name=lastfm_data.get("name", "Unbekannt")
    artist_name=lastfm_data.get("artist", {}).get("name", "Unbekannt")
    
    TIMEZONE_OBJ = ZoneInfo(TIMEZONE) if TIMEZONE else None

    # Gültige Plays des gewünschten Songs filtern
    filtered = [
        entry for entry in spotify_data
        if entry.get("spotify_track_uri") == track_id
        and entry.get("ms_played", 0) > MIN_PLAY_DURATION
        and entry.get("spotify_track_uri") is not None
    ]

    if not filtered:
        print(f"⚠️  Keine gültigen Abspiel-Daten für Song {song_name}. Kein Diagramm erstellt.")
        return None

    # X-Achse: alle Monate im Datensatz (aus spotify_data)
    months_all = [
        datetime.strptime(e["ts"], "%Y-%m-%dT%H:%M:%SZ")
        .replace(tzinfo=timezone.utc).astimezone(TIMEZONE_OBJ)
        .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        for e in spotify_data
    ]
    start, end = min(months_all), max(months_all)

    # Zeitachse erzeugen (alle Monate im Zeitraum)
    full_months = []
    current = start
    while current <= end:
        full_months.append(current.strftime("%Y-%m"))
        current += timedelta(days=32)
        current = current.replace(day=1)

    # Zählung gültiger Plays des Songs pro Monat
    count_by_month = {}
    for entry in filtered:
        dt = datetime.strptime(entry["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(TIMEZONE_OBJ)
        key = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m")
        count_by_month[key] = count_by_month.get(key, 0) + 1

    # Y-Achse: Anzahl Plays (0 wenn keine)
    counts = [count_by_month.get(month, 0) for month in full_months]

    # Plot
    plt.figure(figsize=(10, 5))
    plt.bar(full_months, counts, color="skyblue")
    ax = plt.gca()
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    plt.title(f"Listening activity per month: {utils.to_ascii(song_name)} - {utils.to_ascii(artist_name)}")
    plt.ylabel("times listened")
    plt.xticks(rotation=45)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()

    os.makedirs(output_path, exist_ok=True)
    path = os.path.join(output_path, filename)
    plt.savefig(path, bbox_inches='tight', pad_inches=0.5)
    plt.close()
    return filename

def generate_songdata_file(track_id, data_path, output_path):
    os.makedirs(os.path.join(output_path), exist_ok=True)
    
    if track_id in created_files: return
    print(f"🆕 | Generiere songdata file {track_id}...")

    if not track_id or not data_path:
        print("❌ | Zum Erstellen einer songdata file muss eine track_id und ein data_path gegeben sein! - Generierung wird übersprungen!")
        return "error"
    
    songdata_file = os.path.join(output_path, track_id[14:] + ".md")
    if os.path.exists(songdata_file) and not RECREATE_SONGDATA_FILES: 
        print(f"ℹ️  | Songdata file existiert bereits. ({track_id})")
        return "done"

    spotify_data = [s for s in utils.load_data(data_path) if s.get("spotify_track_uri") == track_id]
    if not spotify_data:
        print(f"⚠️  | Es wurde keine Höraktivität für den Song {track_id} gefunden. - Diese wird der songdata file nicht beigefügt!")
    
    cur.execute("SELECT * FROM songdata WHERE id = ?", [track_id])
    row = cur.fetchone()

    if row is None:
        print(f"❌ | Keine gecachten Last.FM-Daten für Song-ID {track_id} gefunden – Generierung wird übersprungen!")
        return "error"

    try:
        lastfm_data = json.loads(row["json"]).get("track")
    except (KeyError, TypeError, json.JSONDecodeError):
        print(f"❌ | Fehler beim Verarbeiten der gecachten Daten für Song-ID {track_id} – Generierung wird übersprungen!")
        return "error"

    if not lastfm_data or not lastfm_data.get("name"):
        print(f"❌ | Unvollständige Last.FM-Daten für Song-ID {track_id} – Generierung wird übersprungen!")
        return "error"

    
    album_data = lastfm_data.get("album", {})
    if not album_data:
        print(f"⚠️  | Es wurden keine Album-Informationen für den Song {track_id} gefunden. - Diese werden der songdata file nicht beigefügt!")

    utils.clear_md(songdata_file)
    file_content = ""
    created_files.add(track_id)

    file_content += f'# {lastfm_data["name"]}\n'

    if album_data:
        file_content += f"from Album **[{album_data['title']}]({album_data['url']})**\n"

    file_content += f"by **[{lastfm_data['artist']['name']}]({lastfm_data['artist']['url']})**\n"

    duration_ms = int(lastfm_data.get('duration', '0'))
    duration_string = f"{duration_ms // 60000}min, {((duration_ms%60000)/1000):.0f}sec"
    if duration_ms > 0:
        file_content += f"**Duration:** {duration_string}\n"

    if spotify_data:
        file_content += f"You've listened to this song **{len([s for s in spotify_data if s['ms_played'] > MIN_PLAY_DURATION])}** times.\n"


    cover_image = next(
        (item.get("#text") for item in album_data.get("image", []) if item.get("size") == "extralarge"),
        None,
    )
    if cover_image:
        file_content += f'\n![{album_data["title"] if album_data else "unknown album"}]({cover_image})\n'
    else:
        print(f"⚠️  | Es wurde kein Cover für den Song {track_id} gefunden. - Dieses wird der songdata file nicht beigefügt!")

    song_wiki = lastfm_data.get("wiki", None)
    if song_wiki is not None:
       file_content += "### Wiki\n" + utils.html_to_md_links(song_wiki['content']) + f"\n\n(**Published:** {song_wiki['published']})\n"
    else:
        file_content += f'\n[{lastfm_data["url"]}]({lastfm_data["url"]})\n'

    tags = lastfm_data.get('toptags', {}).get('tag', [])
    if len(tags) > 0:
        file_content += "### Tags / Genres\n"
        for tag in tags:
            file_content += f"- [[../tags/{utils.sanitize_filename(tag['name'])}.md|{tag['name']}]]\n"
            
    # Create plot of listening activity per month (if spotify_data available)
    if spotify_data:
        plot_file = plot_song_listening_over_time(
            utils.load_data(data_path),
            track_id,
            lastfm_data,
            filename=track_id[14:] + "_listening_over_time.png",
            output_path=os.path.join(output_path, "..", "img")
        )
        if plot_file:
            # Bild im Markdown verlinken
            file_content += "### Listening Activity per Month\n"
            file_content += f"![listening activity per month](../img/{plot_file})\n"

    utils.append_md(songdata_file, file_content)
    print(f"✅ | Songdata file erfolgreich generiert! ({track_id})")
    return "done"

def generate_all(input_filename):
    data = utils.load_data(os.path.join("userdata", input_filename))
    data_count = len(data)
    for i, song in enumerate(data):
        generate_songdata_file(song.get("spotify_track_uri"), os.path.join("userdata", input_filename), os.path.join("output", input_filename.replace(".json", ""), "songs"))
        print(f"✅ | {str(i).zfill(len(str(data_count)))} / {data_count}")