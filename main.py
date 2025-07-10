import os
import sys
import fetchSongs
import analyze_general

def main(input_filename):
    fetchSongs.main(input_filename)
    output_path = analyze_general.main("detailed_" + input_filename)
    print("✅ Analyse erfolgreich abgeschlossen!")
    print(f"📂 Du findest deine Analyseergebnisse unter {os.path.realpath(output_path)}.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Fehler: Gib den Namen der history-Datei als Argument an (z. B. history.json)")
        sys.exit(1)
    input_filename = sys.argv[1]
    main(input_filename)
