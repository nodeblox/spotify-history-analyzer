import matplotlib.pyplot as plt
import sys
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from collections import defaultdict
import analyze_artists
import utils
import sqlite3
import json

# === Datenbank initialisieren ===
os.makedirs(os.path.join(".cache"), exist_ok=True)
conn = sqlite3.connect("./.cache/cache.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
# Tabelle erstellen
cur.execute("CREATE TABLE IF NOT EXISTS songdata (id STRING PRIMARY KEY, json JSON)")
conn.commit()

load_dotenv()
TIMEZONE = os.getenv("TIMEZONE")

MIN_PLAY_DURATION = os.getenv("MIN_PLAY_DURATION", 20000)  # in ms

def main(input_filename):
    input_path = os.path.join("userdata", input_filename)
    output_path = os.path.join("output", input_filename.replace(".json", ""))
    os.makedirs(output_path, exist_ok=True)
    os.makedirs(os.path.join(output_path, "img"), exist_ok=True)
    os.makedirs(os.path.join(output_path, "songs"), exist_ok=True)
    os.makedirs(os.path.join(output_path, "tags"), exist_ok=True)
    output_file = os.path.join("output", input_filename.replace(".json", ""), "general.md")
    print(f"📂 Lese Daten aus: {input_path}")
    data = utils.load_data(input_path)

    utils.clear_md(output_file)
    utils.append_md(output_file, f"# WICHTIG:\n"
                            f"- Es werden in bestimmten Statistiken nur Songs verarbeitet, die mindestens {(MIN_PLAY_DURATION / 1000):.0f} Sekunden lang angehört wurden.\n"
                            f"- Songs, zu denen keine Tags auf Last.fm gefunden wurden, fließen nicht in tagspezifische Statistiken ein.\n")
    
    utils.append_md(output_file, f"# Analyse")
    analyse_general(data, output_file)
    analyse_activity_by_time(data, output_file, output_path)
    analyse_top_songs(data, output_file, output_path)
    analyse_top_artists(data, output_file, output_path)
    analyze_artists.main(input_filename)
    utils.append_md(output_file, f"### [[./artists.md|Mehr Artist-Informationen]]\n[[./artists.md]]")

    return output_file

def analyse_general(data, output_file):
    print("📊 Analysiere allgemeine Statistiken...")
    total_songs = len(data)
    songs_with_min_duration = sum(1 for entry in data if entry.get('ms_played', 0) >= MIN_PLAY_DURATION)
    total_duration = sum(entry.get('ms_played', 0) for entry in data) / 1000  # in Sekunden
    total_duration_hours = total_duration / 3600
    total_duration_days = total_duration_hours / 24
    different_songs = set()
    for entry in data:
        track_uri = entry.get('spotify_track_uri')
        if track_uri:
            different_songs.add(track_uri)

    start_date = datetime.strptime(data[0].get('ts'), '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).astimezone(ZoneInfo(TIMEZONE) if TIMEZONE else None).date()
    end_date = datetime.strptime(data[-1].get('ts'), '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).astimezone(ZoneInfo(TIMEZONE) if TIMEZONE else None).date()

    days_count = (end_date - start_date).days + 1  # +1, damit Start- und Endtag mitzählen

    days_with_activity = set()
    for entry in data:
        ts = entry.get('ts')
        if ts:
            date = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).astimezone(ZoneInfo(TIMEZONE) if TIMEZONE else None).date()
            days_with_activity.add(date)

    utils.append_md(output_file, f"## Allgemeine Statistiken\n"
                            f"- **Zeitspanne der Daten:** {start_date} bis {end_date} ({days_count} Tage)\n"
                            f"- **Anzahl der Tage (mit Höraktivität):** {len(days_with_activity)}\n"
                            f"- **Anzahl der gehörten Songs:** {total_songs}\n"
                            f"- **Anzahl der gehörten Songs mit mindestens {(MIN_PLAY_DURATION / 1000):.0f} Sekunden Hördauer:** {songs_with_min_duration}\n"
                            f"- **Anzahl der unterschiedlichen Songs:** {len(different_songs)}\n"
                            f"- **Gesamthördauer:** {total_duration_days:.2f} Tage ({total_duration_hours:.2f} Stunden) ({total_duration / 60:.2f} Minuten)\n"
                            f"- **Durchschnittliche Hördauer pro Tag:** {total_duration / days_count / 60:.2f} Minuten\n"
                            f"- **Durchschnittliche Hördauer pro Tag (mit Höraktivität):** {total_duration / len(days_with_activity)/60:.2f} Minuten\n"
                            f"- **Durchschnittliche Hördauer pro Song:** {(total_duration / total_songs) / 60:.2f} Minuten\n"
                            f"- **Durchschnittliche Anzahl Songs (min {(MIN_PLAY_DURATION / 1000):.0f}s) pro Tag:** {songs_with_min_duration / days_count:.2f}\n"
                            f"- **Durchschnittliche Anzahl Songs (min {(MIN_PLAY_DURATION / 1000):.0f}s) pro Tag (mit Höraktivität):** {songs_with_min_duration / len(days_with_activity):.2f}\n")

def analyse_activity_by_time(data, output_file, output_path):
    print("📊 Analysiere Hörverhalten zu verschiedenen Zeiten...")
    utils.append_md(output_file, f"## Zeitliche Verteilung der Songs")

    # Gesamtanzahl Songs pro Monat zählen
    songs_per_month = defaultdict(int)

    for entry in data:
        ts = entry.get('ts')
        if not ts or entry.get('ms_played', 0) < MIN_PLAY_DURATION:
            continue
        date = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(ZoneInfo(TIMEZONE) if TIMEZONE else None)
        month = date.strftime("%Y-%m")  # z.B. "2025-07"
        songs_per_month[month] += 1

    # Sortieren nach Monat (chronologisch)
    sorted_months = sorted(songs_per_month.keys())
    counts = [songs_per_month[m] for m in sorted_months]

    # Monatsnamen im deutschen Format für die x-Achse (z.B. "07.2025")
    labels = [datetime.strptime(m, "%Y-%m").replace(tzinfo=timezone.utc).astimezone(ZoneInfo(TIMEZONE) if TIMEZONE else None).strftime("%m.%Y") for m in sorted_months]

    plt.figure(figsize=(12, 6))
    plt.bar(labels, counts, color="skyblue")
    plt.ylabel("Anzahl gehörter Songs")
    plt.title("Gesamte Anzahl der gehörten Songs pro Monat")
    plt.xticks(rotation=45)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()

    chart_path = os.path.join(output_path, "img", "songs_per_month.png")
    plt.savefig(chart_path, bbox_inches='tight', pad_inches=0.5)
    plt.close()

    utils.append_md(output_file, "### Höraktivität pro Monat\n"
                            "![Songs pro Monat](./img/songs_per_month.png)\n")

    # Dictionaries für Gesamtanzahl & Vorkommen des Wochentags
    total_songs = defaultdict(int)
    weekday_counts = defaultdict(int)

    for entry in data:
        ts = entry.get('ts')
        if not ts or entry.get('ms_played', 0) < MIN_PLAY_DURATION:
            continue
        date = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(ZoneInfo(TIMEZONE) if TIMEZONE else None)
        weekday = date.strftime("%A")
        date_str = date.strftime("%Y-%m-%d")

        total_songs[weekday] += 1
        weekday_counts[f"{weekday}_{date_str}"] = 1  # pro Tag nur einmal zählen

    # Anzahl einzelner Tage pro Wochentag berechnen
    unique_days_per_weekday = defaultdict(int)
    for key in weekday_counts.keys():
        wd = key.split("_")[0]
        unique_days_per_weekday[wd] += 1

    # Durchschnitt berechnen
    average_songs = {}
    for weekday in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        days_count = unique_days_per_weekday.get(weekday, 1)  # zur Sicherheit nicht durch 0 teilen
        average_songs[weekday] = total_songs[weekday] / days_count

    # Plotten
    plt.figure(figsize=(10, 6))
    plt.bar(average_songs.keys(), average_songs.values(), color="skyblue")

    # Zahlen über Balken schreiben
    for i, (day, value) in enumerate(average_songs.items()):
        plt.text(i, value + 0.2, f"{value:.1f}", ha='center', va='bottom', fontsize=9)

    plt.title("Durchschnittliche Songs pro Wochentag")
    plt.ylabel("⌀ Anzahl Songs pro Tag")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.xticks(rotation=45)
    plt.tight_layout()

    chart_path = os.path.join(output_path, "img", "songs_per_day_in_week.png")
    plt.savefig(chart_path, bbox_inches='tight', pad_inches=0.5)
    plt.close()

    utils.append_md(output_file, f"### Hörverhalten nach Wochentag\n"
                            f"![Anzahl der Songs pro Tag](./img/songs_per_day_in_week.png)\n")
    
    activity_by_quarter = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    days_by_quarter = defaultdict(lambda: defaultdict(set))

    for entry in data:
        spotify_data = entry
        ts = spotify_data.get('ts')
        ms_played = spotify_data.get('ms_played')  # Dauer in Millisekunden

        if not ts or not ms_played:
            continue
        
        date = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(ZoneInfo(TIMEZONE) if TIMEZONE else None)
        weekday = date.strftime("%A")
        hour = date.hour
        quarter = f"{date.year}-Q{(date.month - 1)//3 + 1}"
        date_str = date.strftime("%Y-%m-%d")

        duration_min = ms_played / 60000  # Millisekunden in Minuten umrechnen

        activity_by_quarter[quarter][weekday][hour] += duration_min
        days_by_quarter[quarter][weekday].add(date_str)

    # Farben definieren für Wochentage
    weekday_colors = {
        "Monday": "blue",
        "Tuesday": "orange",
        "Wednesday": "green",
        "Thursday": "red",
        "Friday": "purple",
        "Saturday": "brown",
        "Sunday": "pink"
    }

    for quarter in sorted(activity_by_quarter.keys()):
        plt.figure(figsize=(12, 6))
        for weekday in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
            hour_counts = activity_by_quarter[quarter][weekday]
            total_days = len(days_by_quarter[quarter][weekday]) or 1  # Verhindert Division durch 0

            # Mittelwert pro Stunde berechnen
            hourly_avg = [hour_counts.get(h, 0) / total_days for h in range(24)]

            plt.plot(range(24), hourly_avg, label=weekday, color=weekday_colors[weekday])

            # Start- und Enddatum für das Quartal bestimmen
        year, q = map(int, quarter.replace("-Q", "-").split("-"))
        start_month = (q - 1) * 3 + 1
        start_date = datetime(year, start_month, 1)
        if start_month == 10:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, start_month + 3, 1) - timedelta(days=1)

        start_str = start_date.strftime("%d.%m.%Y")
        end_str = end_date.strftime("%d.%m.%Y")

        plt.title(f"Durchschnittliche Höraktivität pro Stunde – {start_str} bis {end_str}")

        plt.xlabel("Stunde (0–23)")
        plt.ylabel("⌀ Minuten pro Stunde")
        plt.ylim(0, 60)
        plt.xticks(range(0, 24))
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.legend()
        plt.tight_layout()

        chart_path = os.path.join(output_path, "img", f"songs_per_hour_{quarter}.png")
        plt.savefig(chart_path, bbox_inches='tight', pad_inches=0.5)
        plt.close()

        utils.append_md(output_file, f"### Hörverhalten nach Uhrzeit – {start_str} bis {end_str}\n"
                                f"![Songs pro Stunde – {quarter}](./img/songs_per_hour_{quarter}.png)\n")

def analyse_top_songs(data, output_file, output_path):
    print("📊 Analysiere Top-Songs...")
    utils.append_md(output_file, "## Top-Songs")

    # Songs nach Monaten gruppieren
    top_songs_per_month = defaultdict(list)
    top_songs_full_time = []

    for entry in data:
        spotify_data = entry
        ts = spotify_data.get('ts')
        if not ts or spotify_data.get('ms_played', 0) > MIN_PLAY_DURATION or not spotify_data.get('master_metadata_track_name'):
            continue
        date = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(ZoneInfo(TIMEZONE) if TIMEZONE else None)
        month = date.strftime("%Y-%m")

        if not any(song["spotify_track_uri"] == entry["spotify_track_uri"] for song in top_songs_per_month[month]):
            entry["times_played"] = 1
            top_songs_per_month[month].append(entry)
        else:
            for song in top_songs_per_month[month]:
                if song["spotify_track_uri"] == entry["spotify_track_uri"]:
                    song["times_played"] += 1
                    break

        if not any(song["spotify_track_uri"] == entry["spotify_track_uri"] for song in top_songs_full_time):
            entry["times_played"] = 1
            top_songs_full_time.append(entry)
        else:
            for song in top_songs_full_time:
                if song["spotify_track_uri"] == entry["spotify_track_uri"]:
                    song["times_played"] += 1
                    break

    top_songs_full_time.sort(key=lambda x: x["times_played"], reverse=True)
    top_songs_full_time_top_25 = top_songs_full_time[:25]

    utils.append_md(output_file, f"### Top-Songs (gesamt)")

    i = 0
    utils.append_md(output_file, "##### 1 bis 10")
    for song in top_songs_full_time_top_25:
        if i == 10: utils.append_md(output_file, "##### 11 bis 25")
        i+=1
        
        cur.execute("SELECT * FROM songdata WHERE id = ?", [song.get("spotify_track_uri")])
        lastfm_data = cur.fetchone()

        track_name = song.get("master_metadata_track_name", "Unbekannt")
        artist_name = song.get("master_metadata_album_artist_name", "Unbekannt")
        times_played = song.get("times_played", 0)
        if lastfm_data:
            link = f'[[./songs/{song["spotify_track_uri"][14:]}.md|{track_name}]]'
        else:
            link = track_name

        utils.append_md(
            output_file,
            f"{i}. **{link}** von {artist_name} – **{times_played}** mal gehört",
        )
    utils.append_md(output_file, "\n")

    for month in sorted(top_songs_per_month.keys()):
        songs = top_songs_per_month[month]
        # Sortiere Songs nach Anzahl der Plays
        songs.sort(key=lambda x: x["times_played"], reverse=True)

        # Nimm die Top 10 Songs
        top_songs = songs[:25]

        utils.append_md(output_file, f"### Top-Songs im Monat {month}")

        i = 0
        utils.append_md(output_file, "##### 1 bis 10")
        for song in top_songs:
            if i == 10: utils.append_md(output_file, "##### 11 bis 25")
            i+=1

            cur.execute("SELECT * FROM songdata WHERE id = ?", [song.get("spotify_track_uri")])
            row = cur.fetchone()
            lastfm_data = json.loads(row["json"]).get("track") if row else None

            track_name = song.get("master_metadata_track_name", "Unbekannt")
            artist_name = song.get("master_metadata_album_artist_name", "Unbekannt")
            times_played = song.get("times_played", 0)

            if lastfm_data:
                link = f'[[./songs/{song["spotify_track_uri"][14:]}.md|{track_name}]]'
            else:
                link = track_name

            utils.append_md(
                output_file,
                f"{i}. **{link}** von {artist_name} – **{times_played}** mal gehört",
            )
        utils.append_md(output_file, "\n")

def analyse_top_artists(data, output_file, output_path):
    print("📊 Analysiere Top-Artists...")
    utils.append_md(output_file, "## Top-Artists")

    artist_times = defaultdict(int)
    artist_urls = defaultdict(str)
    artist_times_by_month = defaultdict(lambda: defaultdict(int)) # Monat → Künstler → Zeit

    for song in data:
        if song is None: continue
        artist = song.get("master_metadata_album_artist_name")
        cur.execute("SELECT * FROM songdata WHERE id = ?", [song.get("spotify_track_uri")])
        row = cur.fetchone()
        lastfm_data = json.loads(row["json"]).get("track") if row else None
        artist_urls[artist] = lastfm_data['artist']['url'] if lastfm_data else None
        artist_times[artist] += song['ms_played']
        ts = song['ts']
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(ZoneInfo(TIMEZONE) if TIMEZONE else None)
        month = dt.strftime("%Y-%m")
        artist_times_by_month[month][artist] += song['ms_played']

    artist_times_sorted = sorted(artist_times.items(), key=lambda x: x[1], reverse=True)

    top_artists = artist_times_sorted[:40]

    utils.append_md(output_file, f"### Top-Artists (gesamt)")

    i = 0
    utils.append_md(output_file, "##### 1 bis 10")
    for artist, played_ms in top_artists:
        if not artist: continue
        if i == 10: utils.append_md(output_file, "##### 11 bis 25")
        if i == 25: utils.append_md(output_file, "##### 26 bis 40")
        i+=1
        link = f"[{artist}]({artist_urls[artist]})" if artist_urls[artist] is not None else artist
        utils.append_md(output_file, f"{i}. **{link}** mit **{(played_ms / 1000 / 60 / 60):.2f} Stunden** Spielzeit")

    # Monatliche Auswertung
    for month in sorted(artist_times_by_month):
        utils.append_md(output_file, f"\n### Top-Artists im Monat {month}")
        monthly_sorted = sorted(
            artist_times_by_month[month].items(), key=lambda x: x[1], reverse=True
        )[:10]

        for idx, (artist, played_ms) in enumerate(monthly_sorted, start=1):
            if artist == "unknown":
                continue
            link = f"[{artist}]({artist_urls[artist]})" if artist_urls[artist] else artist
            stunden = played_ms / 1000 / 60 / 60
            utils.append_md(output_file, f"{idx}. **{link}** – **{stunden:.2f} Stunden**")
    
        # --- Diagramm: Top 10 Artists pro Monat (Stunden gehört) ---
    import matplotlib.pyplot as plt

    # Alle Monate chronologisch sortieren
    all_months = sorted(artist_times_by_month.keys())
    # Top 10 Artists nach Gesamtspielzeit
    top10_artists = [artist for artist, _ in top_artists[:10]]

    # Für jeden Artist: Liste der gehörten Stunden pro Monat (0 wenn nicht vorhanden)
    artist_month_hours = {artist: [] for artist in top10_artists}
    for month in all_months:
        for artist in top10_artists:
            ms = artist_times_by_month[month].get(artist, 0)
            hours = ms / 1000 / 60 / 60
            artist_month_hours[artist].append(hours)

    plt.figure(figsize=(14, 7))
    for artist in top10_artists:
        plt.plot(all_months, artist_month_hours[artist], marker='o', label=utils.to_ascii(artist))

    plt.title("Top 10 Artists: Gehört pro Monat (Stunden)")
    plt.xlabel("Monat")
    plt.ylabel("Gehörte Stunden")
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()

    chart_path = os.path.join(output_path, "img", "top10_artists_per_month.png")
    plt.savefig(chart_path, bbox_inches='tight', pad_inches=0.5)
    plt.close()

    utils.append_md(output_file, "### Top 10 Artists – Gehört pro Monat\n"
                                "![Top 10 Artists pro Monat](./img/top10_artists_per_month.png)\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Fehler: Gib den Namen der history-Datei als Argument an (z. B. detailed_history.json)")
        sys.exit(1)
    input_filename = sys.argv[1]
    main(input_filename)
