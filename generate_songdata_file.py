import utils
import os
import sqlite3
import json
from dotenv import load_dotenv

load_dotenv()
MIN_PLAY_DURATION = os.getenv("MIN_PLAY_DURATION", 20000)  # in ms
RECREATE_SONGDATA_FILES = os.getenv("RECREATE_SONGDATA_FILES", False)

created_files = set()

# === Datenbank initialisieren ===
os.makedirs(os.path.join(".cache"), exist_ok=True)
conn = sqlite3.connect("./.cache/cache.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
# Tabelle erstellen
cur.execute("CREATE TABLE IF NOT EXISTS songdata (id STRING PRIMARY KEY, json JSON)")
conn.commit()

def generate_songdata_file(track_id, data_path, output_path):
    os.makedirs(os.path.join(output_path), exist_ok=True)
    
    if track_id in created_files: return
    print(f"🆕 | Generiere songdata file {track_id}...")

    if not track_id or not data_path:
        print("❌ | Zum Erstellen einer songdata file muss eine track_id und ein data_path gegeben sein! - Generierung wird übersprungen!")
        return "error"
    
    songdata_file = os.path.join(output_path, track_id[14:] + ".md")
    if os.path.exists(songdata_file) and not RECREATE_SONGDATA_FILES: 
        print(f"ℹ️ | Songdata file existiert bereits. ({track_id})")
        return "done"

    spotify_data = [s for s in utils.load_data(data_path) if s.get("spotify_track_uri") == track_id]
    if not spotify_data:
        print(f"⚠️ | Es wurde keine Höraktivität für den Song {track_id} gefunden. - Diese wird der songdata file nicht beigefügt!")
    
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
        print(f"⚠️ | Es wurden keine Album-Informationen für den Song {track_id} gefunden. - Diese werden der songdata file nicht beigefügt!")

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
        print(f"⚠️ | Es wurde kein Cover für den Song {track_id} gefunden. - Dieses wird der songdata file nicht beigefügt!")

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
    utils.append_md(songdata_file, file_content)
    print(f"✅ | Songdata file erfolgreich generiert! ({track_id})")
    return "done"

def generate_all(input_filename):
    for song in utils.load_data(os.path.join("userdata", input_filename)):
        generate_songdata_file(song.get("spotify_track_uri"), os.path.join("userdata", input_filename), os.path.join("output", input_filename.replace(".json", ""), "songs"))