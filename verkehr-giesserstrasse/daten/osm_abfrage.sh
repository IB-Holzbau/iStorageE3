#!/usr/bin/env bash
# Lädt die OSM-Daten rund um die Kreuzung Gießerstraße/Naumburger Straße (Leipzig).
# Aufruf: bash osm_abfrage.sh   (im Ordner daten/)
set -euo pipefail
cd "$(dirname "$0")"
API=${API:-https://overpass-api.de/api/interpreter}
curl -sS --fail --data-urlencode data@osm_abfrage.overpassql "$API" -o osm_kreuzung.json
# Gleiche Abfrage als OSM-XML (für SUMO netconvert --osm-files)
sed 's/\[out:json\]/[out:xml]/' osm_abfrage.overpassql > /tmp/osm_abfrage_xml.overpassql
curl -sS --fail --data-urlencode data@/tmp/osm_abfrage_xml.overpassql "$API" -o osm_kreuzung.osm
python3 - <<'PY'
import json, collections
d = json.load(open("osm_kreuzung.json"))
keys = ("highway","name","lanes","lanes:forward","lanes:backward","turn:lanes","turn:lanes:forward",
        "turn:lanes:backward","maxspeed","oneway","cycleway","cycleway:both","cycleway:left","cycleway:right",
        "sidewalk","surface","width","parking:lane:both","parking:both","parking:left","parking:right",
        "crossing","crossing:markings","traffic_signals","traffic_sign","direction","railway",
        "public_transport","bus","route","ref","restriction","priority_road")
c = collections.Counter(e["type"] for e in d["elements"])
print("Elemente:", dict(c))
for e in d["elements"]:
    t = e.get("tags", {})
    sel = {k: v for k, v in t.items() if k in keys}
    if sel:
        print(e["type"], e["id"], sel)
PY
