import sqlite3
import json
import os
from config import DB_PATH, CACHE_DIR

class DatabaseManager:
    def __init__(self):
        os.makedirs(CACHE_DIR, exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()
        self._create_tables()
    
    def _create_tables(self):
        """Create necessary database tables"""
        self.cur.execute("CREATE TABLE IF NOT EXISTS songdata (id TEXT PRIMARY KEY, json JSON)")
        self.cur.execute("CREATE TABLE IF NOT EXISTS artistdata (artist_name TEXT PRIMARY KEY, json JSON)")
        self.conn.commit()
    
    def get_song_data(self, track_id):
        """Get song data from cache"""
        self.cur.execute("SELECT json FROM songdata WHERE id = ?", [track_id])
        row = self.cur.fetchone()
        if row:
            return json.loads(row["json"]).get("track")
        return None
    
    def store_song_data(self, track_id, data):
        """Store song data in cache"""
        self.cur.execute("INSERT OR REPLACE INTO songdata (id, json) VALUES (?, ?)", 
                        [track_id, json.dumps(data)])
        self.conn.commit()
    
    def get_artist_data(self, artist_name):
        """Get artist data from cache"""
        self.cur.execute("SELECT json FROM artistdata WHERE artist_name = ?", [artist_name])
        row = self.cur.fetchone()
        if row:
            return json.loads(row["json"])
        return None
    
    def store_artist_data(self, artist_name, data):
        """Store artist data in cache"""
        self.cur.execute("INSERT OR REPLACE INTO artistdata (artist_name, json) VALUES (?, ?)",
                        (artist_name, json.dumps(data, ensure_ascii=False)))
        self.conn.commit()
    
    def has_song_data(self, track_id):
        """Check if song data exists in cache"""
        return self.get_song_data(track_id) is not None
    
    def get_artist_url_from_song_data(self, track_id):
        """Get artist URL from cached song data"""
        song_data = self.get_song_data(track_id)
        if song_data:
            return song_data.get("artist", {}).get("url")
        return None
    
    def close(self):
        """Close database connection"""
        self.conn.close()

# Global database instance
db = DatabaseManager()
