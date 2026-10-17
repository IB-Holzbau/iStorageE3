# Vergleich der Varianten (SUMO)

Je Variante 10 Läufe mit festen Startwerten, je Lauf 60 Minuten Spitzenstunde nach 10 Minuten Einschwingzeit. Angegeben ist Mittelwert ± Standardabweichung über die Läufe. Busroute SW. Die Nachfrage ist geschätzt und das Modell ist nicht kalibriert, die Zahlen zeigen Unterschiede zwischen den Varianten, keine absoluten Werte für die echte Kreuzung.

## Überblick je Stunde

| Kennzahl | Bestand | Rechts vor links, Tempo 30 | Minikreisel mit Zebrastreifen | Bestand mit Tempo 30 und Zebra Nord und West |
|---|---|---|---|---|
| Konflikte Fahrzeug mit Fahrzeug (TTC < 1,5 s, PET < 1 s oder DRAC > 3 m/s²) | 90.6 ± 14.2 | 32.0 ± 5.8 | 18.8 ± 4.2 | 79.4 ± 8.9 |
| davon Kreuzen und Einbiegen | 61.6 ± 9.7 | 23.4 ± 5.1 | 0.0 ± 0.0 | 61.3 ± 8.1 |
| davon Auffahren | 29.0 ± 7.7 | 8.6 ± 3.8 | 18.8 ± 4.2 | 18.1 ± 6.0 |
| davon mit Rad | 16.8 ± 5.1 | 7.7 ± 2.9 | 2.5 ± 1.6 | 16.3 ± 6.3 |
| davon mit Bus oder Lkw | 6.1 ± 3.3 | 3.7 ± 2.6 | 1.1 ± 1.0 | 7.9 ± 2.9 |
| davon schwer (TTC < 1 s oder PET < 0,5 s) | 21.0 ± 6.2 | 2.4 ± 1.6 | 0.1 ± 0.3 | 26.6 ± 5.9 |
| Fußgänger auf Querung, Fahrzeug über 15 km/h müsste mit über 3 m/s² bremsen | 12.9 ± 4.1 | 12.0 ± 2.6 | 17.4 ± 3.0 | 21.1 ± 4.8 |
| davon Fahrzeug schneller als 30 km/h | 2.9 ± 1.8 | 0.7 ± 0.8 | 2.9 ± 1.7 | 3.0 ± 2.1 |
| davon durch Rad | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| Mittlerer Zeitverlust Kfz in s | 12.9 ± 2.9 | 8.2 ± 0.6 | 9.9 ± 0.8 | 11.3 ± 1.1 |
| Mittlerer Zeitverlust Rad in s | 9.1 ± 4.5 | 5.1 ± 0.6 | 6.3 ± 0.5 | 8.6 ± 1.5 |
| Mittlerer Zeitverlust Bus in s | 8.7 ± 4.1 | 7.9 ± 2.1 | 9.2 ± 2.4 | 9.8 ± 3.5 |
| Mittlere Wartezeit Fußgänger in s | 6.5 ± 1.7 | 8.1 ± 1.1 | 0.0 ± 0.0 | 2.1 ± 0.5 |
| Mittlerer Zeitverlust Fußgänger in s | 14.6 ± 1.8 | 16.4 ± 1.0 | 8.7 ± 0.4 | 10.5 ± 0.5 |
| Teleports (Verklemmungen im Modell) | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| Überschneidungen im Knoteninneren (SSM-Typ 111, nicht mitgezählt) | 19.6 ± 6.2 | 0.8 ± 1.0 | 3.1 ± 1.9 | 2.4 ± 1.7 |

## Fußgängerkonflikte je Querung

| Querung über Arm | Bestand | Rechts vor links, Tempo 30 | Minikreisel mit Zebrastreifen | Bestand mit Tempo 30 und Zebra Nord und West |
|---|---|---|---|---|
| Süd (Gießerstr.) | 4.2 ± 1.9 | 3.7 ± 1.4 | 3.5 ± 1.5 | 3.3 ± 2.2 |
| Nord (Gießerstr.) | 4.7 ± 2.5 | 4.3 ± 2.9 | 8.8 ± 2.6 | 11.3 ± 4.5 |
| West (Naumburger Str.) | 3.2 ± 2.2 | 2.7 ± 1.8 | 3.3 ± 1.7 | 5.5 ± 2.2 |
| Ost (Naumburger Str.) | 0.8 ± 0.6 | 1.3 ± 0.8 | 1.8 ± 1.0 | 1.0 ± 1.1 |

## Zufahrten, Zeitverlust Kfz und Qualitätsstufe

Qualitätsstufe aus dem mittleren Zeitverlust der Kfz je Zufahrt mit den Grenzen für Knoten ohne Ampel A bis 10 s, B bis 20 s, C bis 30 s, D bis 45 s, E darüber, F bei Überlastung (mittlerer Einfahrverzug über 10 s, die Schlange reicht also über den Modellrand). Nach HBS 2015, am Original prüfen. Das HBS bewertet nur wartepflichtige Ströme, hier wird vereinfacht die ganze Zufahrt betrachtet.

| Zufahrt | Bestand | Rechts vor links, Tempo 30 | Minikreisel mit Zebrastreifen | Bestand mit Tempo 30 und Zebra Nord und West |
|---|---|---|---|---|
| Süd (Gießerstr.) | 8.6 ± 1.0 s, QSV A | 8.7 ± 0.9 s, QSV A | 9.9 ± 1.1 s, QSV A | 8.0 ± 1.1 s, QSV A |
| Nord (Gießerstr.) | 24.6 ± 10.5 s, QSV C | 7.5 ± 1.0 s, QSV A | 12.1 ± 1.9 s, QSV B | 18.2 ± 3.8 s, QSV B |
| West (Naumburger Str.) | 11.4 ± 1.6 s, QSV B | 8.7 ± 1.1 s, QSV A | 8.7 ± 0.6 s, QSV A | 11.6 ± 1.3 s, QSV B |
| Ost (Naumburger Str.) | 11.3 ± 2.8 s, QSV B | 4.7 ± 1.0 s, QSV A | 9.6 ± 1.7 s, QSV A | 9.1 ± 1.7 s, QSV A |

## Rückstau je Zufahrt in Metern (Mittel / 95 %-Wert)

| Zufahrt | Bestand | Rechts vor links, Tempo 30 | Minikreisel mit Zebrastreifen | Bestand mit Tempo 30 und Zebra Nord und West |
|---|---|---|---|---|
| Süd (Gießerstr.) | 0 / 0 | 0 / 2 | 1 / 5 | 0 / 0 |
| Nord (Gießerstr.) | 3 / 20 | 0 / 1 | 2 / 12 | 3 / 16 |
| West (Naumburger Str.) | 1 / 8 | 1 / 6 | 1 / 9 | 2 / 15 |
| Ost (Naumburger Str.) | 0 / 1 | 0 / 0 | 0 / 1 | 0 / 0 |

## Wartezeit der Fußgänger je Weg in s

| Weg | Bestand | Rechts vor links, Tempo 30 | Minikreisel mit Zebrastreifen | Bestand mit Tempo 30 und Zebra Nord und West |
|---|---|---|---|---|
| Ostseite Süd nach Nord, quert Ostarm | 3.2 ± 1.8 | 1.6 ± 1.0 | 0.0 ± 0.1 | 1.3 ± 1.5 |
| Ostseite Nord nach Süd, quert Ostarm | 3.3 ± 2.0 | 1.7 ± 1.0 | 0.0 ± 0.1 | 1.7 ± 1.3 |
| Von Nordost zum Kiosk, quert Nord- und Westarm | 4.9 ± 1.2 | 6.2 ± 1.5 | 0.0 ± 0.0 | 0.3 ± 0.3 |
| Vom Kiosk nach Nordost, quert West- und Nordarm | 14.6 ± 2.5 | 11.9 ± 3.3 | 0.1 ± 0.1 | 0.1 ± 0.1 |
| Nordseite Ost nach West, quert Nordarm | 4.8 ± 2.4 | 7.2 ± 2.6 | 0.0 ± 0.0 | 0.2 ± 0.2 |
| Nordseite West nach Ost, quert Nordarm | 4.7 ± 2.5 | 7.5 ± 2.2 | 0.0 ± 0.0 | 0.1 ± 0.2 |
| Quert Südarm am Knoten | 8.2 ± 2.6 | 14.2 ± 2.7 | 0.0 ± 0.0 | 9.2 ± 1.9 |
