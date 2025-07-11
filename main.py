import os
import sys
import fetch_songdata
import analyze_general
import utils
import generate_songdata_file

def main(input_filename):
    fetch_songdata.main(input_filename)
    generate_songdata_file.generate_all(input_filename)
    output_path = analyze_general.main(input_filename)
    print("✅ Analyse erfolgreich abgeschlossen!")
    print(f"📂 Du findest deine Analyseergebnisse unter {os.path.realpath(output_path)}.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Fehler: Gib den Namen der history-Datei als Argument an (z. B. history.json)")
        sys.exit(1)
    input_filename = sys.argv[1]
    main(input_filename)
