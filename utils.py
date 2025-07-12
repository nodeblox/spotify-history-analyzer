from unidecode import unidecode
import matplotlib.pyplot as plt
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
    except Exception as e:
        print(f"Fehler beim Anhängen an die Datei '{filename}': {e}")

def clear_md(filename):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            pass
    except Exception as e:
        print(f"Fehler beim Leeren der Datei '{filename}': {e}")


def to_ascii(text):
    converted = unidecode(text)

    replacements = {
        # Interpunktion (volle Breite & ideografisch)
        '、': ', ', '。': '. ', '，': ', ', '．': '. ', '：': ': ', '；': '; ',
        '？': '? ', '！': '! ', '¡': '! ', '¿': '? ',
        '「': '"', '」': '"', '『': '"', '』': '"',
        '《': '"', '》': '"', '〈': '"', '〉': '"',
        '“': '"', '”': '"', '‘': "'", '’': "'",

        # Klammern & mathematische Zeichen
        '（': '(', '）': ')', '［': '[', '］': ']', '｛': '{', '｝': '}',
        '＜': '<', '＞': '>', '«': '"', '»': '"', '‹': '"', '›': '"',
        '【': '[', '】': ']', '〔': '[', '〕': ']', '〘': '[', '〙': ']',

        # Trennzeichen & Linien
        'ー': '-', '—': '-', '–': '-', '―': '-', '−': '-', '‐': '-', '‑': '-',
        '・': '-', '･': '-', '〜': '~', '～': '~',

        # Punkte, Auslassung & Leerzeichen
        '…': '...', '‥': '..', '・': '.', '•': '*', '∙': '*', '⋅': '*',
        '　': ' ',  # full-width space

        # Symbole, Pfeile & Dekoration
        '★': '*', '☆': '*', '♠': '<>', '♣': '<>', '♥': '<3', '♦': '<>', '✓': 'check', '✔': 'check',
        '✕': 'X', '✖': 'X', '✗': 'X', '❌': 'X', '⭕': 'O',
        '→': '->', '←': '<-', '↑': '^', '↓': 'v',
        '↔': '<->', '↕': '|', '⇧': '^', '⇩': 'v',

        # Gradzeichen und ähnliches
        '℃': '°C', '℉': '°F', '°': '°',
        '©': '(c)', '®': '(r)', '™': '(tm)',

        # Musik
        '♩': '', '♪': '', '♫': '', '♬': '',

        # Währungen
        '￥': '¥', '￦': '₩', '€': 'EUR', '£': 'GBP', '¢': 'cent', '₹': 'INR',
        '₽': 'RUB', '₺': 'TRY', '₩': 'KRW', '₴': 'UAH', '฿': 'THB',

        # Zahlenzeichen
        '①': '1', '②': '2', '③': '3', '④': '4', '⑤': '5',
        '⑥': '6', '⑦': '7', '⑧': '8', '⑨': '9', '⑩': '10',
    }

    
    for orig, repl in replacements.items():
        converted = converted.replace(orig, repl)

    return converted

def html_to_md_links(text):
    # Regulärer Ausdruck zum Erkennen von <a href="...">...</a>
    return re.sub(r'<a\s+href=["\'](.*?)["\'].*?>(.*?)<\/a>', r'[\2](\1)', text)

def sanitize_filename(text):
    text = to_ascii(text)
    # Verbotene Zeichen ersetzen durch '_'
    return re.sub(r'[<>:"/\\|?*\n\r\t]', '_', text).strip()

def count_files(directory):
    return len([name for name in os.listdir(directory)
                if os.path.isfile(os.path.join(directory, name))])
    
def plot_pie_chart(
    data_dict: dict,
    title: str,
    filename: str,
    output_path: str,
    data_size: int = 15,
    display_legend: bool = True,
    legend_title: str = "",
    show_percentages_in_legend: bool = False
):
    sorted_items = sorted(data_dict.items(), key=lambda x: x[1], reverse=True)
    top_items = sorted_items[:data_size]
    rest_value = sum(v for _, v in sorted_items[data_size:])
    
    labels = [to_ascii(artist) if artist else "Unbekannt" for artist, _ in top_items]
    sizes = [v for _, v in top_items]
    
    if rest_value > 0:
        labels.append("Rest")
        sizes.append(rest_value)

    fig, ax = plt.subplots(figsize=(18, 9))
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        autopct="%1.1f%%",
        startangle=90,
        counterclock=False,
        textprops={'fontsize': 8}
    )
    ax.axis("equal")
    ax.set_title(title)

    if display_legend:
        if show_percentages_in_legend:
            total = sum(sizes)
            legend_labels = [f"{label} ({size / total * 100:.1f}%)" for label, size in zip(labels, sizes)]
        else:
            legend_labels = labels
        
        if legend_title:
            ax.legend(wedges, legend_labels, title=legend_title, loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
        else:
            ax.legend(wedges, legend_labels, loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))

    path = os.path.join(output_path, "img", filename)
    plt.tight_layout()
    plt.savefig(path, bbox_inches='tight', pad_inches=0.5)
    plt.close()
    return path
