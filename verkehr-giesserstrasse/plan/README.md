# Eintragsplan der Kreuzung

`plan_bestand.pdf` ist der Plan zum Ausdrucken oder Bemalen auf dem Tablet (2 Seiten A3 hoch, Gesamtplan 1:400 und Knoten im Detail 1:200, auf A4 gedruckt entsprechend 1:566 bzw. 1:283, die Maßstabsleiste stimmt immer).

## Referenzstand

Der Plan zeigt den Bestand des SUMO-Abspielers. Gemerkt sind

- `plan_bestand_s1.png`, `plan_bestand_s2.png` als Referenzbilder in 150 dpi
- `plan_meta.json` mit Git-Stand, Maßstab, Kartenfeld in Seiten-Millimetern, Lage der Passmarken und Rasterlinien in Modellmetern (Ursprung Knotenmitte, x Ost, y Süd)

## Eintragungen zurückholen

1. Foto oder Scan der bemalten Seite (alle vier Passmarken sichtbar) bzw. das bemalte PDF hochladen.
2. Die Passmarken werden gesucht, das Bild per Projektion auf das Referenzbild entzerrt und mit ihm verglichen. Alles, was neu und farbig ist, wird als Eintragung erkannt.
3. Lage der Eintragungen wird in Modellmeter umgerechnet und kann so direkt in Netz und Abspieler übernommen werden. Die Rasterfelder (z.B. „E5“) helfen bei der Beschreibung.

Neu bauen mit `python3 build_plan.py [pfad/zu/abspieler.html]`.
