# Vergleich der Varianten (SUMO)

Je Variante 10 Läufe mit festen Startwerten, je Lauf 60 Minuten Spitzenstunde nach 10 Minuten Einschwingzeit. Angegeben ist Mittelwert ± Standardabweichung über die Läufe. Busroute SW. Die Nachfrage ist geschätzt und das Modell ist nicht kalibriert, die Zahlen zeigen Unterschiede zwischen den Varianten, keine absoluten Werte für die echte Kreuzung.

## Überblick je Stunde

| Kennzahl | Bestand | Rechts vor links, Tempo 30 | Minikreisel mit Zebrastreifen | Bestand mit Tempo 30 und Zebra Nord und West |
|---|---|---|---|---|
| Konflikte Fahrzeug mit Fahrzeug (TTC < 1,5 s, PET < 1 s oder DRAC > 3 m/s²) | 74.6 ± 10.9 | 25.5 ± 5.4 | 25.5 ± 6.2 | 74.6 ± 8.5 |
| davon Kreuzen und Einbiegen | 49.9 ± 8.0 | 12.8 ± 5.9 | 9.2 ± 4.3 | 51.6 ± 7.9 |
| davon Auffahren | 24.7 ± 6.4 | 12.7 ± 2.4 | 16.3 ± 3.5 | 23.0 ± 4.4 |
| davon mit Rad | 16.6 ± 5.9 | 7.6 ± 2.0 | 1.9 ± 1.5 | 17.2 ± 3.6 |
| davon mit Bus oder Lkw | 4.5 ± 1.8 | 4.2 ± 2.7 | 2.0 ± 1.5 | 6.0 ± 3.2 |
| davon schwer (TTC < 1 s oder PET < 0,5 s) | 17.3 ± 4.3 | 1.1 ± 1.3 | 0.6 ± 0.8 | 23.2 ± 4.6 |
| Fußgänger auf Querung, Fahrzeug über 15 km/h müsste mit über 3 m/s² bremsen | 19.0 ± 4.3 | 18.9 ± 4.6 | 17.7 ± 3.0 | 22.4 ± 5.1 |
| davon Fahrzeug schneller als 30 km/h | 9.6 ± 3.3 | 4.8 ± 1.9 | 2.5 ± 1.6 | 4.7 ± 1.9 |
| davon durch Rad | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| Mittlerer Zeitverlust Kfz in s | 10.6 ± 1.0 | 7.5 ± 0.7 | 10.5 ± 0.8 | 11.1 ± 1.2 |
| Mittlerer Zeitverlust Rad in s | 6.2 ± 1.1 | 4.3 ± 0.7 | 6.5 ± 0.5 | 8.6 ± 1.4 |
| Mittlerer Zeitverlust Bus in s | 8.5 ± 1.5 | 9.8 ± 3.4 | 12.3 ± 3.7 | 10.9 ± 2.5 |
| Mittlere Wartezeit Fußgänger in s | 6.4 ± 0.7 | 5.4 ± 0.6 | 0.1 ± 0.0 | 2.6 ± 0.6 |
| Mittlerer Zeitverlust Fußgänger in s | 14.8 ± 0.9 | 13.8 ± 0.6 | 8.5 ± 0.4 | 10.8 ± 0.7 |
| Teleports (Verklemmungen im Modell) | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| Überlappungen im Modell (SUMO-Zusammenstöße, Modellfehler) | 0.7 ± 0.7 | 0.6 ± 0.7 | 0.1 ± 0.3 | 0.7 ± 0.9 |
| Überschneidungen im Knoteninneren (SSM-Typ 111, nicht mitgezählt) | 1.1 ± 0.9 | 0.1 ± 0.3 | 4.6 ± 3.2 | 1.0 ± 1.2 |

## Fußgängerkonflikte je Querung

| Querung über Arm | Bestand | Rechts vor links, Tempo 30 | Minikreisel mit Zebrastreifen | Bestand mit Tempo 30 und Zebra Nord und West |
|---|---|---|---|---|
| Süd (Gießerstr.) | 5.0 ± 1.3 | 5.3 ± 2.1 | 3.2 ± 2.4 | 4.8 ± 1.9 |
| Nord (Gießerstr.) | 6.9 ± 2.3 | 9.0 ± 2.9 | 8.1 ± 1.7 | 10.3 ± 3.8 |
| West (Naumburger Str.) | 5.8 ± 2.3 | 3.9 ± 2.2 | 4.8 ± 1.7 | 5.9 ± 2.2 |
| Ost (Naumburger Str.) | 1.3 ± 1.3 | 0.7 ± 1.1 | 1.6 ± 1.1 | 1.4 ± 1.1 |

## Zufahrten, Zeitverlust Kfz und Qualitätsstufe

Qualitätsstufe aus dem mittleren Zeitverlust der Kfz je Zufahrt mit den Grenzen für Knoten ohne Ampel A bis 10 s, B bis 20 s, C bis 30 s, D bis 45 s, E darüber, F bei Überlastung (mittlerer Einfahrverzug über 10 s, die Schlange reicht also über den Modellrand). Nach HBS 2015, am Original prüfen. Das HBS bewertet nur wartepflichtige Ströme, hier wird vereinfacht die ganze Zufahrt betrachtet.

| Zufahrt | Bestand | Rechts vor links, Tempo 30 | Minikreisel mit Zebrastreifen | Bestand mit Tempo 30 und Zebra Nord und West |
|---|---|---|---|---|
| Süd (Gießerstr.) | 6.8 ± 0.9 s, QSV A | 7.4 ± 1.1 s, QSV A | 10.4 ± 1.1 s, QSV B | 7.3 ± 0.9 s, QSV A |
| Nord (Gießerstr.) | 19.9 ± 2.7 s, QSV B | 7.7 ± 0.9 s, QSV A | 11.5 ± 1.3 s, QSV B | 20.5 ± 3.3 s, QSV C |
| West (Naumburger Str.) | 10.0 ± 0.7 s, QSV B | 8.0 ± 0.8 s, QSV A | 10.0 ± 1.2 s, QSV B | 10.2 ± 1.0 s, QSV B |
| Ost (Naumburger Str.) | 9.3 ± 2.0 s, QSV A | 4.9 ± 1.0 s, QSV A | 9.6 ± 1.5 s, QSV A | 10.8 ± 2.2 s, QSV B |

## Rückstau je Zufahrt in Metern (Mittel / 95 %-Wert)

| Zufahrt | Bestand | Rechts vor links, Tempo 30 | Minikreisel mit Zebrastreifen | Bestand mit Tempo 30 und Zebra Nord und West |
|---|---|---|---|---|
| Süd (Gießerstr.) | 0 / 0 | 1 / 3 | 1 / 12 | 0 / 0 |
| Nord (Gießerstr.) | 4 / 19 | 1 / 7 | 2 / 12 | 4 / 21 |
| West (Naumburger Str.) | 1 / 8 | 1 / 9 | 1 / 12 | 2 / 12 |
| Ost (Naumburger Str.) | 0 / 0 | 0 / 0 | 0 / 1 | 0 / 2 |

## Wartezeit der Fußgänger je Weg in s

| Weg | Bestand | Rechts vor links, Tempo 30 | Minikreisel mit Zebrastreifen | Bestand mit Tempo 30 und Zebra Nord und West |
|---|---|---|---|---|
| Ostseite Süd nach Nord, quert Ostarm | 0.7 ± 0.4 | 1.3 ± 0.7 | 0.1 ± 0.1 | 0.9 ± 0.5 |
| Ostseite Nord nach Süd, quert Ostarm | 0.9 ± 0.9 | 1.0 ± 0.5 | 0.1 ± 0.1 | 0.7 ± 0.6 |
| Von Nordost zum Kiosk, quert Nord- und Westarm | 5.5 ± 1.4 | 3.5 ± 1.1 | 0.0 ± 0.0 | 0.7 ± 0.3 |
| Vom Kiosk nach Nordost, quert West- und Nordarm | 11.4 ± 2.0 | 9.4 ± 2.0 | 0.1 ± 0.1 | 0.1 ± 0.1 |
| Nordseite Ost nach West, quert Nordarm | 3.2 ± 0.9 | 3.2 ± 1.4 | 0.0 ± 0.0 | 0.0 ± 0.1 |
| Nordseite West nach Ost, quert Nordarm | 8.8 ± 2.1 | 4.1 ± 1.7 | 0.0 ± 0.0 | 0.8 ± 0.6 |
| Quert Südarm am Knoten | 9.5 ± 1.7 | 10.9 ± 1.9 | 0.1 ± 0.1 | 11.4 ± 2.0 |
