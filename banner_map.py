import pandas as pd
import json
import argparse
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from requests.structures import CaseInsensitiveDict


def convert_to_float(value):
    """Wandelt eine Zahl mit Komma als Dezimaltrennzeichen in eine Float-Zahl um."""
    if isinstance(value, float):
        return value  # Bereits ein Float, direkt zurückgeben
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None

def get_value(value):
    """Gibt den Wert zurück oder 'N/A', falls er nicht verfügbar ist."""
    return value if pd.notna(value) else "N/A"


def download_image_from_url(page_url, save_path):
    """
    Lädt das erste Bild eines Hyperlinks herunter, falls es noch nicht existiert.
    :param page_url: URL der Webseite, von der das Bild heruntergeladen werden soll
    :param save_path: Pfad, unter dem das Bild gespeichert werden soll
    """
    if os.path.exists(save_path):
        print(f"Bild existiert bereits: {save_path}")
        return False
    
    try:
        # Anfrage an die URL senden
        response = requests.get(page_url, timeout=15)

        # Prüfen, ob der Request erfolgreich war
        if response.status_code == 200:
            # Datei lokal speichern
            with open(save_path, 'wb') as f:
                f.write(response.content)
        else:
            print(f"Fehler beim Download des Bildes: Statuscode {response.status_code}")
                # Webseite abrufen
    except requests.RequestException as e:
        print(f"Fehler beim Abrufen der URL: {e}")
        return False

def download_picture(banner_nr, link):
    """Dummy-Funktion zum Herunterladen eines Bildes von Bannergress."""
    print(f"Lade Bild für Banner-NR {banner_nr} herunter...")
    url = f"https://api.bannergress.com/bnrs/{link}"

    headers = CaseInsensitiveDict()
    headers["Accept"] = "application/xml"

    resp = requests.get(url, headers=headers, timeout=120)
    string = json.dumps(resp.text)
    dump = json.loads(string)

    with open('temp.json', 'w', encoding='utf8') as the_file:
        output = f"{dump}"
        the_file.write(f'{output}\n')
    
    f = open('temp.json')
    json_file = json.load(f)

    page_url = f"""https://api.bannergress.com{json_file["picture"]}"""
    save_path = f"""banner/{banner_nr}.jpg"""
    download_image_from_url(page_url, save_path)


def tsv_to_geojson(input_file, output_file):
    # TSV-Datei einlesen
    df = pd.read_csv(input_file, sep='\t')

    # Sicherstellen, dass der Ordner für Bilder existiert
    os.makedirs("banner", exist_ok=True)

    # Liste für Banner ohne BG-Link
    need_picture_list = []

    # GeoJSON-Grundstruktur
    geojson = {
        "type": "FeatureCollection",
        "features": []
    }

    # Durch die Zeilen iterieren und GeoJSON-Features erstellen
    for _, row in df.iterrows():
        banner_nr = get_value(row["nummer"])
        bg_link = get_value(row["bg-link"])

        if bg_link != "N/A":
            link = bg_link.split("/")
            link = link[len(link) - 1]
            download_picture(banner_nr, link)
            picture_path = f"https://raw.githubusercontent.com/pommernMeg/myBannerMap/refs/heads/main/banner/{banner_nr}.jpg"
        else:
            save_path = f"""banner/{banner_nr}.jpg"""
            if not os.path.exists(save_path):
                need_picture_list.append(f"{banner_nr}: {get_value(row['titel'])}")
                picture_path = "N/A"
            else:
                picture_path = f"https://raw.githubusercontent.com/pommernMeg/myBannerMap/refs/heads/main/banner/{banner_nr}.jpg"

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [convert_to_float(row["startLongitude"]), convert_to_float(row["startLatitude"])]
            },
            "properties": {
                "nummer": banner_nr,
                "title": get_value(row["titel"]),
                "picture": picture_path,
                "region": get_value(row["region"]),
                "country": get_value(row["country"]),
                "completed": get_value(row["completed"]),
                "missions": get_value(row["missions"]),
                "category": get_value(row["missions"]),
                "date": get_value(row["date"]),
                "bg_link": bg_link,
                "description": get_value(row["description"]),
                "length_km": get_value(convert_to_float(row["lengthKMeters"]))
            }
        }
        geojson["features"].append(feature)

    # GeoJSON speichern
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=4, ensure_ascii=False)

    print(f"GeoJSON-Datei wurde erstellt: {output_file}")

    # Liste der Banner ohne BG-Link speichern
    if need_picture_list:
        with open("needPicture.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(need_picture_list))
        print("Liste der Banner ohne BG-Link wurde in needPicture.txt gespeichert.")

def main():
    parser = argparse.ArgumentParser(description="Konvertiert eine TSV-Datei in eine GeoJSON-Datei.")
    parser.add_argument("input_file", help="Pfad zur Eingabe-TSV-Datei")
    parser.add_argument("output_file", help="Pfad zur Ausgabe-GeoJSON-Datei")
    args = parser.parse_args()

    tsv_to_geojson(args.input_file, args.output_file)

if __name__ == "__main__":
    main()
