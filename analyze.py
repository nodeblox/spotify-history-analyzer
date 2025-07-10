import matplotlib.pyplot as plt
import numpy as np
import json
import sys
import os
from datetime import datetime, timedelta
from pykakasi import kakasi
from collections import defaultdict
import time
import re

MIN_PLAY_DURATION = 20000  # in ms

def main(input_filename):
    input_path = os.path.join("userdata", input_filename)
    output_path = os.path.join("output", input_filename.replace(".json", ""))
    os.makedirs(output_path, exist_ok=True)
    os.makedirs(os.path.join(output_path, "img"), exist_ok=True)
    os.makedirs(os.path.join(output_path, "songs"), exist_ok=True)
    os.makedirs(os.path.join(output_path, "tags"), exist_ok=True)
    output_file = os.path.join("output", input_filename.replace(".json", ""), input_filename.replace(".json", ".md"))
    print(f"📂 Lese Daten aus: {input_path}")
    data = load_data(input_path)

    clear_md(output_file)
    append_md(output_file, f"# WICHTIG:\n"
                            f"- Es werden in bestimmten Statistiken nur Songs verarbeitet, die mindestens {(MIN_PLAY_DURATION / 1000):.0f} Sekunden lang angehört wurden.\n"
                            f"- Songs, zu denen keine Tags auf Last.fm gefunden wurden, fließen nicht in tagspezifische Statistiken ein.\n")
    
    append_md(output_file, f"# Analyse")
    analyse_general(data, output_file)
    analyse_activity_by_time(data, output_file, output_path)
    analyse_top_songs(data, output_file, output_path)
    analyse_top_artists(data, output_file, output_path)

def to_ascii(text):
    kks = kakasi()
    kks.setMode('J', 'a')  # Japanese zu ascii (Romaji)
    kks.setMode('K', 'a')  # Katakana zu ascii
    kks.setMode('H', 'a')  # Hiragana zu ascii
    converter = kks.getConverter()
    return converter.do(text)

def html_to_md_links(text):
    # Regulärer Ausdruck zum Erkennen von <a href="...">...</a>
    return re.sub(r'<a\s+href=["\'](.*?)["\'].*?>(.*?)<\/a>', r'[\2](\1)', text)

def sanitize_filename(text):
    # Verbotene Zeichen ersetzen durch '_'
    return re.sub(r'[<>:"/\\|?*\n\r\t]', '_', text).strip()

def generate_songdata_file(song, output_path, processed_songfiles=set()):
    track_data = song.get('spotify_data', {})
    lastfm_data = song.get("lastfm_data", {"track": None})["track"]

    if (
        lastfm_data is not None
        and lastfm_data.get("name") is not None
        and track_data["spotify_track_uri"] not in processed_songfiles
    ):
        processed_songfiles.add(track_data["spotify_track_uri"])
        songdata_file = os.path.join(
            output_path, "songs", track_data["spotify_track_uri"][14:] + ".md"
        )
        clear_md(songdata_file)

        image_list = lastfm_data.get("album", {}).get("image", [])
        extralarge_image = next(
            (item.get("#text") for item in image_list if item.get("size") == "extralarge"),
            None,
        )

        append_md(
            songdata_file,
            f'# {lastfm_data["name"]}'
        )

        if lastfm_data.get("album", {}):
            append_md(songdata_file, f"from Album **[{lastfm_data['album']['title']}]({lastfm_data['album']['url']})**")

        if lastfm_data.get("album", {}):
            append_md(songdata_file, f"by **[{lastfm_data['artist']['name']}]({lastfm_data['artist']['url']})**")

        duration_ms = int(lastfm_data.get('duration', '0'))
        duration_string = f"{duration_ms // 60000}min, {((duration_ms%60000)/1000):.0f}sec"
        append_md(songdata_file, f"**Duration:** {duration_string if duration_ms > 0 else 'unknown'}")

        if extralarge_image:
            append_md(
                songdata_file,
                f'\n![{lastfm_data["album"]["title"]}]({extralarge_image})',
            )

        song_wiki = lastfm_data.get("wiki", None)
        if song_wiki is not None:
            append_md(songdata_file, "### Wiki\n"
                                    + html_to_md_links(song_wiki['content'])
                                    + f"\n\n(**Published:** {song_wiki['published']})")
        else:
            append_md(songdata_file, f'\n[{lastfm_data["url"]}]({lastfm_data["url"]})\n',)

        tags = lastfm_data.get('toptags', {}).get('tag', [])
        if len(tags) > 0:
            append_md(songdata_file, "### Tags / Genres")
            for tag in tags:
                append_md(songdata_file, f"- [[../tags/{sanitize_filename(tag['name'])}.md|{tag['name']}]]")


def load_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def append_md(filename, text=""):
    try:
        with open(filename, 'a', encoding='utf-8') as f:
            f.write(text + '\n')
        for _ in range(50):
            if os.path.exists(filename):
                break
            time.sleep(0.05)
    except Exception as e:
        print(f"Fehler beim Anhängen an die Datei '{filename}': {e}")

def clear_md(filename):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            pass
        time.sleep(0.02)
    except Exception as e:
        print(f"Fehler beim Leeren der Datei '{filename}': {e}")


def analyse_general(data, output_file):
    print("📊 Analysiere allgemeine Statistiken...")
    total_songs = len(data)
    songs_with_min_duration = sum(1 for entry in data if entry.get('spotify_data', {}).get('ms_played', 0) >= MIN_PLAY_DURATION)
    total_duration = sum(entry.get('spotify_data', {}).get('ms_played', 0) for entry in data) / 1000  # in Sekunden
    total_duration_hours = total_duration / 3600
    total_duration_days = total_duration_hours / 24
    different_songs = set()
    for entry in data:
        track_uri = entry.get('spotify_data', {}).get('spotify_track_uri')
        if track_uri:
            different_songs.add(track_uri)

    start_date = datetime.strptime(data[0].get('spotify_data', {}).get('ts'), '%Y-%m-%dT%H:%M:%SZ').date()
    end_date = datetime.strptime(data[-1].get('spotify_data', {}).get('ts'), '%Y-%m-%dT%H:%M:%SZ').date()

    days_count = (end_date - start_date).days + 1  # +1, damit Start- und Endtag mitzählen

    days_with_activity = set()
    for entry in data:
        ts = entry.get('spotify_data', {}).get('ts')
        if ts:
            date = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ').date()
            days_with_activity.add(date)

    append_md(output_file, f"## Allgemeine Statistiken\n"
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
    append_md(output_file, f"## Zeitliche Verteilung der Songs")

    # Gesamtanzahl Songs pro Monat zählen
    songs_per_month = defaultdict(int)

    for entry in data:
        ts = entry.get('spotify_data', {}).get('ts')
        if not ts or entry.get('spotify_data', {}).get('ms_played', 0) < MIN_PLAY_DURATION:
            continue
        date = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
        month = date.strftime("%Y-%m")  # z.B. "2025-07"
        songs_per_month[month] += 1

    # Sortieren nach Monat (chronologisch)
    sorted_months = sorted(songs_per_month.keys())
    counts = [songs_per_month[m] for m in sorted_months]

    # Monatsnamen im deutschen Format für die x-Achse (z.B. "07.2025")
    labels = [datetime.strptime(m, "%Y-%m").strftime("%m.%Y") for m in sorted_months]

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

    append_md(output_file, "### Höraktivität pro Monat\n"
                            "![Songs pro Monat](img/songs_per_month.png)\n")

    # Dictionaries für Gesamtanzahl & Vorkommen des Wochentags
    total_songs = defaultdict(int)
    weekday_counts = defaultdict(int)

    for entry in data:
        ts = entry.get('spotify_data', {}).get('ts')
        if not ts or entry.get('spotify_data', {}).get('ms_played', 0) < MIN_PLAY_DURATION:
            continue
        date = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
        weekday = date.strftime("%A")

        total_songs[weekday] += 1
        weekday_counts[weekday + "_" + date.strftime("%Y-%m-%d")] = 1  # pro Tag nur einmal zählen

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

    append_md(output_file, f"### Hörverhalten nach Wochentag\n"
                            f"![Anzahl der Songs pro Tag](img/songs_per_day_in_week.png)\n")
    
    activity_by_quarter = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    days_by_quarter = defaultdict(lambda: defaultdict(set))

    for entry in data:
        spotify_data = entry.get('spotify_data', {})
        ts = spotify_data.get('ts')
        ms_played = spotify_data.get('ms_played')  # Dauer in Millisekunden

        if not ts or not ms_played:
            continue
        
        date = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
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

        append_md(output_file, f"### Hörverhalten nach Uhrzeit – {start_str} bis {end_str}\n"
                                f"![Songs pro Stunde – {quarter}](img/songs_per_hour_{quarter}.png)\n")

def analyse_top_songs(data, output_file, output_path):
    print("📊 Analysiere Top-Songs...")
    append_md(output_file, "## Top-Songs")

    # Songs nach Monaten gruppieren
    top_songs_per_month = defaultdict(list)
    top_songs_full_time = []

    for entry in data:
        spotify_data = entry.get('spotify_data', {})
        ts = spotify_data.get('ts')
        if not ts or spotify_data.get('ms_played', 0) < MIN_PLAY_DURATION:
            continue
        date = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
        month = date.strftime("%Y-%m")

        if not any(song["spotify_data"]["spotify_track_uri"] == entry["spotify_data"]["spotify_track_uri"] for song in top_songs_per_month[month]):
            entry["times_played"] = 1
            top_songs_per_month[month].append(entry)
        else:
            for song in top_songs_per_month[month]:
                if song["spotify_data"]["spotify_track_uri"] == entry["spotify_data"]["spotify_track_uri"]:
                    song["times_played"] += 1
                    break

        if not any(song["spotify_data"]["spotify_track_uri"] == entry["spotify_data"]["spotify_track_uri"] for song in top_songs_full_time):
            entry["times_played"] = 1
            top_songs_full_time.append(entry)
        else:
            for song in top_songs_full_time:
                if song["spotify_data"]["spotify_track_uri"] == entry["spotify_data"]["spotify_track_uri"]:
                    song["times_played"] += 1
                    break

    processed_songfiles = set()

    top_songs_full_time.sort(key=lambda x: x["times_played"], reverse=True)
    top_songs_full_time_top_25 = top_songs_full_time[:25]

    append_md(output_file, f"### Top-Songs (gesamt)")

    i = 0
    append_md(output_file, "##### 1 bis 10")
    for song in top_songs_full_time_top_25:
        if i == 10: append_md(output_file, "##### 11 bis 25")
        i+=1
        track_data = song.get('spotify_data', {})
        lastfm_data = song.get("lastfm_data", {"track": None})["track"]
        
        generate_songdata_file(song, output_path, processed_songfiles)

        track_name = track_data.get("master_metadata_track_name", "Unbekannt")
        artist_name = track_data.get("master_metadata_album_artist_name", "Unbekannt")
        times_played = song.get("times_played", 0)
        if (
            lastfm_data is not None
            and lastfm_data.get("name") is not None
        ):
            link = f'[[./songs/{track_data["spotify_track_uri"][14:]}.md|{track_name}]]'
        else:
            link = track_name

        append_md(
            output_file,
            f"{i}. **{link}** von {artist_name} – **{times_played}** mal gehört",
        )
    append_md(output_file, "\n")

    for month in sorted(top_songs_per_month.keys()):
        songs = top_songs_per_month[month]
        # Sortiere Songs nach Anzahl der Plays
        songs.sort(key=lambda x: x["times_played"], reverse=True)

        # Nimm die Top 10 Songs
        top_songs = songs[:25]

        append_md(output_file, f"### Top-Songs im Monat {month}")

        i = 0
        append_md(output_file, "##### 1 bis 10")
        for song in top_songs:
            if i == 10: append_md(output_file, "##### 11 bis 25")
            i+=1

            track_data = song.get('spotify_data', {})
            lastfm_data = song.get("lastfm_data", {"track": None})["track"]
            
            generate_songdata_file(song, output_path, processed_songfiles)

            track_name = track_data.get("master_metadata_track_name", "Unbekannt")
            artist_name = track_data.get("master_metadata_album_artist_name", "Unbekannt")
            times_played = song.get("times_played", 0)

            if (
                lastfm_data is not None
                and lastfm_data.get("name") is not None
            ):
                link = f'[[./songs/{track_data["spotify_track_uri"][14:]}.md|{track_name}]]'
            else:
                link = track_name

            append_md(
                output_file,
                f"{i}. **{link}** von {artist_name} – **{times_played}** mal gehört",
            )
        append_md(output_file, "\n")

def analyse_top_artists(data, output_file, output_path):
    print("📊 Analysiere Top-Artists...")
    append_md(output_file, "## Top-Artists")

    artist_times = defaultdict(int)
    artist_urls = defaultdict(str)
    artist_times_by_month = defaultdict(lambda: defaultdict(int)) # Monat → Künstler → Zeit

    for song in data:
        artist = song['spotify_data'].get("master_metadata_album_artist_name", 'unknown')
        artist_urls[artist] = song.get('lastfm_data', {'track': {}})['track'].get('artist', {}).get('url', None)
        artist_times[artist] += song['spotify_data']['ms_played']
        ts = song['spotify_data']['ts']
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
        month = dt.strftime("%Y-%m")
        artist_times_by_month[month][artist] += song['spotify_data']['ms_played']

    artist_times_sorted = sorted(artist_times.items(), key=lambda x: x[1], reverse=True)

    top_artists = artist_times_sorted[:40]

    append_md(output_file, f"### Top-Artists (gesamt)")

    i = 0
    append_md(output_file, "##### 1 bis 10")
    for artist, played_ms in top_artists:
        if artist == "unknown": continue
        if i == 10: append_md(output_file, "##### 11 bis 25")
        if i == 25: append_md(output_file, "##### 26 bis 40")
        i+=1
        link = f"[{artist}]({artist_urls[artist]})" if artist_urls[artist] is not None else artist
        append_md(output_file, f"{i}. **{link}** mit **{(played_ms / 1000 / 60 / 60):.2f} Stunden** Spielzeit")

    # Monatliche Auswertung
    for month in sorted(artist_times_by_month):
        append_md(output_file, f"\n### Top-Artists im Monat {month}")
        monthly_sorted = sorted(
            artist_times_by_month[month].items(), key=lambda x: x[1], reverse=True
        )[:10]

        for idx, (artist, played_ms) in enumerate(monthly_sorted, start=1):
            if artist == "unknown":
                continue
            link = f"[{artist}]({artist_urls[artist]})" if artist_urls[artist] else artist
            stunden = played_ms / 1000 / 60 / 60
            append_md(output_file, f"{idx}. **{link}** – **{stunden:.2f} Stunden**")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Fehler: Gib den Namen der history-Datei als Argument an (z. B. detailed_history.json)")
        sys.exit(1)
    input_filename = sys.argv[1]
    main(input_filename)
