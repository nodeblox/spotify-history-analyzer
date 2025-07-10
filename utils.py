from pykakasi import kakasi
import time
import os
import re
import json

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
    text = to_ascii(text)
    # Verbotene Zeichen ersetzen durch '_'
    return re.sub(r'[<>、。:"/\\|?*\n\r\t]', '_', text).strip()
