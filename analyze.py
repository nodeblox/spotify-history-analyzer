import matplotlib.pyplot as plt
import numpy as np
import json
import sys
import os
from datetime import datetime
from pykakasi import kakasi
from collections import defaultdict

def to_ascii(text):
    kks = kakasi()
    kks.setMode('J', 'a')  # Japanese zu ascii (Romaji)
    kks.setMode('K', 'a')  # Katakana zu ascii
    kks.setMode('H', 'a')  # Hiragana zu ascii
    converter = kks.getConverter()
    return converter.do(text)

def main(input_filename):
    input_path = os.path.join("userdata", input_filename)
    output_path = os.path.join("output", input_filename.replace(".json", ""))
    os.makedirs(output_path, exist_ok=True)
    output_file = os.path.join("output", input_filename.replace(".json", ""), input_filename.replace(".json", ".md"))
    print(f"📂 Lese Daten aus: {input_path}")
    data = load_data(input_path)

    clear_md(output_file)
    append_md(output_file, f"# WICHTIG:\n"
                            f"- Es werden in bestimmten Statistiken nur Songs verarbeitet, die mindestens 20 Sekunden lang angehört wurden.\n"
                            f"- Songs, zu denen keine Tags auf Last.fm gefunden wurden, fließen nicht in tagspezifische Statistiken ein.\n")
    
    append_md(output_file, f"# Analyse")
    analyse_general(data, output_file)
    analyse_by_time(data, output_file, output_path)

def load_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)
    
def append_md(filename, text=""):
    """
    Hängt den gegebenen Text an eine Markdown-Datei an.

    :param filename: Pfad zur Markdown-Datei
    :param text: Text, der angehängt werden soll (String)
    """
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(text + '\n')

def clear_md(filename):
    with open(filename, 'w', encoding='utf-8') as f:
        pass  # Datei wird geöffnet und sofort geschlossen – Inhalt ist jetzt leer

def analyse_general(data, output_file):
    print("📊 Analysiere allgemeine Statistiken...")
    total_songs = len(data)
    songs_with_min_duration = sum(1 for entry in data if entry.get('spotify_data', {}).get('ms_played', 0) >= 20000)
    total_duration = sum(entry.get('spotify_data', {}).get('ms_played', 0) for entry in data) / 1000  # in Sekunden
    total_duration_hours = total_duration / 3600

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
                            f"- **Anzahl der gehörten Songs mit mindestens 20 Sekunden Hördauer:** {songs_with_min_duration}\n"
                            f"- **Gesamthördauer:** {total_duration_hours:.2f} Stunden ({total_duration / 60:.2f} Minuten)\n"
                            f"- **Durchschnittliche Hördauer pro Tag:** {total_duration / days_count / 60:.2f} Minuten\n"
                            f"- **Durchschnittliche Hördauer pro Tag (mit Höraktivität):** {total_duration / len(days_with_activity)/60:.2f} Minuten\n"
                            f"- **Durchschnittliche Hördauer pro Song:** {(total_duration / total_songs) / 60:.2f} Minuten\n"
                            f"- **Durchschnittliche Anzahl Songs (min 20s) pro Tag (mit Höraktivität):** {songs_with_min_duration / len(days_with_activity):.2f}\n")

def analyse_by_time(data, output_file, output_path):
    print("📊 Analysiere Hörverhalten zu verschiedenen Zeiten...")

    # Dictionaries für Gesamtanzahl & Vorkommen des Wochentags
    total_songs = defaultdict(int)
    weekday_counts = defaultdict(int)

    for entry in data:
        ts = entry.get('spotify_data', {}).get('ts')
        if not ts:
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

    chart_path = os.path.join(output_path, "songs_per_day_in_week.png")
    plt.savefig(chart_path, bbox_inches='tight', pad_inches=0.5)
    plt.close()

    append_md(output_file, f"## Zeitliche Verteilung der Songs\n"
                           f"Dies zeigt die **durchschnittliche** Anzahl Songs pro Tag des jeweiligen Wochentags.\n"
                           f"![Anzahl der Songs pro Tag](songs_per_day_in_week.png)\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Fehler: Gib den Namen der history-Datei als Argument an (z. B. detailed_history.json)")
        sys.exit(1)
    input_filename = sys.argv[1]
    main(input_filename)
