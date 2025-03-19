import pandas as pd
import json
import argparse
import os
import requests
from urllib.parse import urljoin
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def convert_to_float(value):
    if pd.isna(value) or value == "":
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None

def get_value(value):
    return value if pd.notna(value) else "N/A"

def parse_int(value):
    if pd.isna(value):
        return 0
    try:
        value_str = str(value).replace(".0", "")
        return int(value_str)
    except ValueError:
        return 0

def download_image_from_url(page_url, save_path):
    if os.path.exists(save_path):
        logging.info(f"Bild existiert bereits: {save_path}")
        return True
    try:
        response = requests.get(page_url, timeout=15)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            logging.info(f"Bild erfolgreich heruntergeladen: {save_path}")
            return True
        else:
            logging.error(f"Fehler beim Download: Statuscode {response.status_code}")
            return False
    except requests.RequestException as e:
        logging.error(f"Fehler beim Abrufen der URL: {e}")
        return False

def download_picture(banner_nr, link):
    logging.info(f"Lade Bild für Banner-NR {banner_nr} herunter...")
    url = f"https://api.bannergress.com/bnrs/{link}"
    headers = {"Accept": "application/json"}
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"API-Abfrage fehlgeschlagen: {e}")
        return
    json_file = resp.json()
    picture_url = json_file.get("picture")
    if picture_url:
        page_url = urljoin("https://api.bannergress.com", picture_url)
        save_path = f"banner/{banner_nr}.jpg"
        download_image_from_url(page_url, save_path)
    else:
        logging.error("Bild-URL nicht in API-Antwort enthalten.")

def save_geojson(features, output_file):
    geojson = {"type": "FeatureCollection", "features": features}
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=4, ensure_ascii=False)
    logging.info(f"GeoJSON-Datei wurde erstellt: {output_file}")

def tsv_to_geojson(input_file, output_file, missions_threshold=5000):
    df = pd.read_csv(input_file, sep='\t', on_bad_lines='skip')
    os.makedirs("banner", exist_ok=True)
    need_picture_list = []

    features = []
    file_count = 1
    current_missions_sum = 0

    columns = df.columns.tolist()
    idx = {col: columns.index(col) for col in columns}

    for row in df.itertuples(index=False, name=None):
        banner_nr = get_value(row[idx["nummer"]])
        bg_link = get_value(row[idx["bg-link"]])
        missions = parse_int(row[idx["missions"]])

        lon = convert_to_float(row[idx["startLongitude"]])
        lat = convert_to_float(row[idx["startLatitude"]])
        if lon is None or lat is None:
            logging.warning(f"Ungültige Koordinaten für Banner-NR {banner_nr}. Überspringe Eintrag.")
            continue

        if bg_link != "N/A":
            link = bg_link.split("/")[-1]
            download_picture(banner_nr, link)
            picture_path = f"https://raw.githubusercontent.com/pommernMeg/myBannerMap/refs/heads/main/banner/{banner_nr}.jpg"
        else:
            save_path = f"banner/{banner_nr}.jpg"
            if not os.path.exists(save_path):
                need_picture_list.append(f"{banner_nr}: {get_value(row[idx['titel']])}")
                picture_path = "N/A"
            else:
                picture_path = f"https://raw.githubusercontent.com/pommernMeg/myBannerMap/refs/heads/main/banner/{banner_nr}.jpg"

        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "nummer": banner_nr,
                "title": get_value(row[idx["titel"]]),
                "picture": picture_path,
                "region": get_value(row[idx["region"]]),
                "country": get_value(row[idx["country"]]),
                "completed": parse_int(row[idx["completed"]]),
                "missions": missions,
                "category": get_value(row[idx["missions"]]),
                "date": get_value(row[idx["date"]]),
                "bg_link": bg_link,
                "description": get_value(row[idx["description"]]),
                "length_km": convert_to_float(row[idx["lengthKMeters"]]) or None
            }
        }

        if current_missions_sum + missions > missions_threshold and features:
            current_output_file = f"{output_file.rstrip('.geojson')}_{file_count}.geojson"
            save_geojson(features, current_output_file)
            features = []
            current_missions_sum = 0
            file_count += 1

        features.append(feature)
        current_missions_sum += missions

    if features:
        current_output_file = f"{output_file.rstrip('.geojson')}_{file_count}.geojson"
        save_geojson(features, current_output_file)

    if need_picture_list:
        with open("needPicture.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(need_picture_list))
        logging.info("Liste der Banner ohne BG-Link in needPicture.txt gespeichert.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TSV zu GeoJSON-Konverter.")
    parser.add_argument("input_file", help="Pfad zur Eingabe-TSV-Datei")
    parser.add_argument("output_file", help="Pfad zur Ausgabe-GeoJSON-Datei")
    parser.add_argument("--threshold", type=int, default=5000, help="Maximale Missionsanzahl je GeoJSON-Datei")
    args = parser.parse_args()

    tsv_to_geojson(args.input_file, args.output_file, args.threshold)

