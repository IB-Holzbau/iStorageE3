# Vergleich der Varianten (SUMO)

Je Variante 10 Läufe mit festen Startwerten, je Lauf 60 Minuten Spitzenstunde nach 10 Minuten Einschwingzeit. Angegeben ist Mittelwert ± Standardabweichung über die Läufe. Busroute SN. Die Nachfrage ist geschätzt und das Modell ist nicht kalibriert, die Zahlen zeigen Unterschiede zwischen den Varianten, keine absoluten Werte für die echte Kreuzung.

## Überblick je Stunde

| Kennzahl | Bestand | Rechts vor links, Tempo 30 | Minikreisel mit Zebrastreifen | Bestand mit Tempo 30 und Zebra Nord und West |
|---|---|---|---|---|
| Konflikte Fahrzeug mit Fahrzeug (TTC < 1,5 s, PET < 1 s oder DRAC > 3 m/s²) | 110.7 ± 16.6 | 39.4 ± 8.6 | 36.0 ± 4.8 | 114.0 ± 12.3 |
| davon Kreuzen und Einbiegen | 78.2 ± 13.4 | 30.3 ± 6.9 | 0.2 ± 0.6 | 68.2 ± 8.3 |
| davon Auffahren | 32.5 ± 6.4 | 9.1 ± 3.4 | 35.8 ± 4.7 | 45.8 ± 6.0 |
| davon mit Rad | 22.0 ± 5.4 | 8.9 ± 3.2 | 5.3 ± 1.9 | 22.0 ± 5.5 |
| davon mit Bus oder Lkw | 8.6 ± 2.5 | 5.4 ± 3.9 | 3.7 ± 1.1 | 12.0 ± 4.1 |
| davon schwer (TTC < 1 s oder PET < 0,5 s) | 22.4 ± 7.4 | 3.6 ± 1.8 | 0.3 ± 0.5 | 28.5 ± 5.7 |
| Fußgänger auf Querung, Fahrzeug über 15 km/h müsste mit über 3 m/s² bremsen | 44.6 ± 10.6 | 46.5 ± 13.9 | 43.5 ± 6.4 | 49.2 ± 6.9 |
| davon Fahrzeug schneller als 30 km/h | 4.6 ± 3.2 | 2.7 ± 1.6 | 6.1 ± 3.0 | 9.3 ± 3.5 |
| davon durch Rad | 4.9 ± 2.5 | 3.6 ± 2.1 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| Mittlerer Zeitverlust Kfz in s | 13.9 ± 1.9 | 8.7 ± 0.9 | 17.4 ± 1.9 | 22.4 ± 4.0 |
| Mittlerer Zeitverlust Rad in s | 8.9 ± 2.1 | 5.0 ± 0.7 | 13.4 ± 1.9 | 19.8 ± 4.0 |
| Mittlerer Zeitverlust Bus in s | 18.1 ± 4.3 | 8.0 ± 1.8 | 16.6 ± 3.2 | 27.0 ± 7.6 |
| Mittlere Wartezeit Fußgänger in s | 9.8 ± 1.0 | 8.8 ± 0.7 | 0.5 ± 0.1 | 0.5 ± 0.1 |
| Mittlerer Zeitverlust Fußgänger in s | 18.9 ± 1.0 | 17.9 ± 0.7 | 9.8 ± 0.2 | 9.7 ± 0.3 |
| Teleports (Verklemmungen im Modell) | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| Überschneidungen im Knoteninneren (SSM-Typ 111, nicht mitgezählt) | 32.1 ± 8.0 | 5.4 ± 1.9 | 6.0 ± 2.6 | 17.3 ± 3.2 |

## Fußgängerkonflikte je Querung

| Querung über Arm | Bestand | Rechts vor links, Tempo 30 | Minikreisel mit Zebrastreifen | Bestand mit Tempo 30 und Zebra Nord und West |
|---|---|---|---|---|
| Süd (Gießerstr.) | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 |
| Nord (Gießerstr.) | 17.1 ± 6.8 | 16.9 ± 7.6 | 18.7 ± 5.0 | 19.9 ± 3.6 |
| West (Naumburger Str.) | 24.4 ± 7.4 | 25.0 ± 8.5 | 21.8 ± 3.2 | 28.2 ± 5.0 |
| Ost (Naumburger Str.) | 3.1 ± 1.1 | 4.6 ± 2.7 | 3.0 ± 1.7 | 1.1 ± 1.4 |

## Zufahrten, Zeitverlust Kfz und Qualitätsstufe

Qualitätsstufe aus dem mittleren Zeitverlust der Kfz je Zufahrt mit den Grenzen für Knoten ohne Ampel A bis 10 s, B bis 20 s, C bis 30 s, D bis 45 s, E darüber, F bei Überlastung (mittlerer Einfahrverzug über 10 s, die Schlange reicht also über den Modellrand). Nach HBS 2015, am Original prüfen. Das HBS bewertet nur wartepflichtige Ströme, hier wird vereinfacht die ganze Zufahrt betrachtet.

| Zufahrt | Bestand | Rechts vor links, Tempo 30 | Minikreisel mit Zebrastreifen | Bestand mit Tempo 30 und Zebra Nord und West |
|---|---|---|---|---|
| Süd (Gießerstr.) | 8.6 ± 0.5 s, QSV A | 8.8 ± 0.6 s, QSV A | 16.9 ± 2.0 s, QSV B | 11.4 ± 0.8 s, QSV B |
| Nord (Gießerstr.) | 29.8 ± 7.5 s, QSV C | 7.9 ± 1.1 s, QSV A | 21.7 ± 3.0 s, QSV C | 48.5 ± 14.4 s, QSV E |
| West (Naumburger Str.) | 11.3 ± 1.1 s, QSV B | 9.5 ± 1.8 s, QSV A | 15.7 ± 2.6 s, QSV B | 21.6 ± 3.1 s, QSV C |
| Ost (Naumburger Str.) | 11.0 ± 1.4 s, QSV B | 4.9 ± 0.8 s, QSV A | 16.2 ± 4.4 s, QSV B | 14.0 ± 2.2 s, QSV B |

## Rückstau je Zufahrt in Metern (Mittel / 95 %-Wert)

| Zufahrt | Bestand | Rechts vor links, Tempo 30 | Minikreisel mit Zebrastreifen | Bestand mit Tempo 30 und Zebra Nord und West |
|---|---|---|---|---|
| Süd (Gießerstr.) | 0 / 0 | 0 / 1 | 2 / 14 | 1 / 6 |
| Nord (Gießerstr.) | 7 / 29 | 1 / 5 | 5 / 24 | 12 / 48 |
| West (Naumburger Str.) | 1 / 7 | 1 / 9 | 4 / 21 | 6 / 32 |
| Ost (Naumburger Str.) | 0 / 0 | 0 / 0 | 0 / 4 | 0 / 3 |

## Wartezeit der Fußgänger je Weg in s

| Weg | Bestand | Rechts vor links, Tempo 30 | Minikreisel mit Zebrastreifen | Bestand mit Tempo 30 und Zebra Nord und West |
|---|---|---|---|---|
| Ostseite Süd nach Nord, quert Ostarm | 2.0 ± 1.1 | 0.6 ± 0.3 | 0.4 ± 0.2 | 1.3 ± 0.8 |
| Ostseite Nord nach Süd, quert Ostarm | 1.8 ± 1.1 | 0.7 ± 0.1 | 0.4 ± 0.5 | 1.3 ± 1.1 |
| Vom Kiosk nach Norden (Ostseite) | 17.5 ± 2.5 | 16.2 ± 1.8 | 0.9 ± 0.3 | 0.6 ± 0.3 |
| Vom Kiosk nach Norden (Westseite) | 12.9 ± 1.6 | 9.7 ± 1.3 | 0.2 ± 0.1 | 0.1 ± 0.1 |
| Von Norden (Ostseite) zum Kiosk, quert Nord- und Westarm | 17.4 ± 2.0 | 15.9 ± 2.1 | 0.7 ± 0.3 | 0.6 ± 0.2 |
| Von Norden (Westseite) zum Kiosk, quert Westarm | 11.0 ± 2.1 | 9.2 ± 1.6 | 0.3 ± 0.1 | 0.2 ± 0.2 |
| Nordseite Ost nach West, quert Nordarm | 5.6 ± 1.9 | 7.0 ± 0.9 | 0.5 ± 0.1 | 0.5 ± 0.2 |
| Nordseite West nach Ost, quert Nordarm | 5.6 ± 0.8 | 6.9 ± 0.9 | 0.6 ± 0.2 | 0.6 ± 0.2 |
| Quert Westarm am Knoten | 12.0 ± 2.9 | 8.9 ± 2.3 | 0.2 ± 0.1 | 0.3 ± 0.4 |
