import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import os
from datetime import datetime, timedelta
from collections import defaultdict
import utils
from config import MIN_PLAY_DURATION

def create_monthly_listening_chart(spotify_data, track_id, lastfm_data, filename, output_path):
    """Create a chart showing listening activity per month for a specific song"""
    song_name = lastfm_data.get("name", "Unbekannt")
    artist_name = lastfm_data.get("artist", {}).get("name", "Unbekannt")

    # Filter valid plays for the desired song
    filtered = [
        entry for entry in spotify_data
        if entry.get("spotify_track_uri") == track_id
        and entry.get("ms_played", 0) > MIN_PLAY_DURATION
        and entry.get("spotify_track_uri") is not None
    ]

    if not filtered:
        print(f"⚠️  Keine gültigen Abspiel-Daten für Song {song_name}. Kein Diagramm erstellt.")
        return None

    # Generate time axis using the new utility function
    months_all = []
    for entry in spotify_data:
        date = utils.parse_timestamp(entry["ts"])
        if date:
            months_all.append(date.replace(day=1, hour=0, minute=0, second=0, microsecond=0))
    
    if not months_all:
        return None
        
    start, end = min(months_all), max(months_all)

    full_months = []
    current = start
    while current <= end:
        full_months.append(current.strftime("%Y-%m"))
        current += timedelta(days=32)
        current = current.replace(day=1)

    # Count plays per month
    count_by_month = {}
    for entry in filtered:
        date = utils.parse_timestamp(entry["ts"])
        if date:
            key = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m")
            count_by_month[key] = count_by_month.get(key, 0) + 1

    counts = [count_by_month.get(month, 0) for month in full_months]

    # Create plot
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

def create_artist_monthly_chart(data, artist_name, output_path):
    """Create monthly listening chart for an artist"""
    monthly_minutes = defaultdict(float)
    
    for entry in data:
        if entry.get("master_metadata_album_artist_name") == artist_name:
            date = utils.parse_timestamp(entry.get("ts"))
            if date:
                month = date.strftime("%Y-%m")
                minutes = entry.get("ms_played", 0) / 60000
                monthly_minutes[month] += minutes

    if not monthly_minutes:
        return None

    months = sorted(monthly_minutes.keys())
    minutes = [monthly_minutes[m] for m in months]

    plt.figure(figsize=(12, 6))
    plt.bar(months, minutes, color='skyblue')
    plt.title(f"Listening minutes per month for {utils.to_ascii(artist_name)}")
    plt.ylabel("listening minutes")
    plt.xticks(rotation=45)
    plt.tight_layout()

    chart_filename = f"{utils.sanitize_filename(artist_name)}_monthly_minutes.png"
    chart_path = os.path.join(output_path, chart_filename)
    os.makedirs(os.path.dirname(chart_path), exist_ok=True)
    plt.savefig(chart_path, bbox_inches='tight', pad_inches=0.5)
    plt.close()
    
    return chart_filename

def create_artist_share_chart(data, artist_name, output_path):
    """Create pie chart showing artist's share of total listening time"""
    total_artist_minutes = 0
    total_all_minutes = 0

    for entry in data:
        ms_played = entry.get("ms_played", 0)
        minutes = ms_played / 60000
        total_all_minutes += minutes
        if entry.get("master_metadata_album_artist_name") == artist_name:
            total_artist_minutes += minutes

    if total_artist_minutes <= 0:
        return None

    rest_minutes = total_all_minutes - total_artist_minutes
    labels = [f"{utils.to_ascii(artist_name)}", "others"]
    sizes = [total_artist_minutes, rest_minutes]

    plt.figure(figsize=(6, 6))
    plt.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90, counterclock=False, colors=["#ff9999", "#dddddd"])
    plt.title(f"{utils.to_ascii(artist_name)} vs. rest - total listening time")
    plt.axis("equal")
    
    chart_filename = f"{utils.sanitize_filename(artist_name)}_share_vs_rest.png"
    chart_path = os.path.join(output_path, chart_filename)
    plt.savefig(chart_path, bbox_inches='tight', pad_inches=0.5)
    plt.close()
    
    return chart_filename
    chart_filename = f"{utils.sanitize_filename(artist_name)}_share_vs_rest.png"
    chart_path = os.path.join(output_path, chart_filename)
    plt.savefig(chart_path, bbox_inches='tight', pad_inches=0.5)
    plt.close()
    
    return chart_filename
