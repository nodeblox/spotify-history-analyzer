from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from collections import defaultdict
import json
from config import MIN_PLAY_DURATION, TIMEZONE

def filter_valid_entries(data, min_duration=None):
    """Filter entries that have a timestamp, meet the minimum play duration, and contain track metadata."""
    if min_duration is None:
        min_duration = MIN_PLAY_DURATION
    
    return [
        entry for entry in data
        if entry.get("ts") 
        and entry.get("ms_played", 0) >= min_duration
        and entry.get("master_metadata_track_name")
        and entry.get("spotify_track_uri")
    ]

def group_by_month(data):
    """Group data entries by their month of playback."""
    monthly_data = defaultdict(list)
    
    for entry in data:
        ts = entry.get('ts')
        if not ts:
            continue
            
        date = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if TIMEZONE:
            date = date.astimezone(ZoneInfo(TIMEZONE))
        month_key = date.strftime("%Y-%m")
        monthly_data[month_key].append(entry)
    
    return monthly_data

def calculate_song_stats(data):
    """Generate statistics for songs, including the number of times each song was played."""
    song_stats = {}
    
    for entry in filter_valid_entries(data):
        uri = entry["spotify_track_uri"]
        
        if uri not in song_stats:
            new_entry = json.loads(json.dumps(entry))  # deepcopy via JSON
            new_entry["times_played"] = 1
            song_stats[uri] = new_entry
        else:
            song_stats[uri]["times_played"] += 1
    
    return song_stats

def calculate_artist_stats(data):
    """Calculate total play time for each artist."""
    artist_stats = defaultdict(int)
    
    for entry in data:
        artist = entry.get("master_metadata_album_artist_name")
        if artist:
            artist_stats[artist] += entry.get("ms_played", 0)
    
    return artist_stats

def get_date_range(data):
    """Determine the earliest and latest playback dates in the data."""
    if not data:
        return None, None
    
    dates = []
    for entry in data:
        ts = entry.get('ts')
        if ts:
            date = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
            if TIMEZONE:
                date = date.astimezone(ZoneInfo(TIMEZONE))
            dates.append(date.date())
    
    return min(dates), max(dates) if dates else (None, None)

def get_unique_days_with_activity(data):
    """Identify unique days with playback activity."""
    days = set()
    
    for entry in data:
        ts = entry.get('ts')
        if ts:
            date = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
            if TIMEZONE:
                date = date.astimezone(ZoneInfo(TIMEZONE))
            days.add(date.date())
    
    return days
