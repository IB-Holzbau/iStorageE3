# Vergleich der Varianten (SUMO)

Je Variante 10 Läufe mit festen Startwerten, je Lauf 60 Minuten Spitzenstunde nach 10 Minuten Einschwingzeit. Angegeben ist Mittelwert ± Standardabweichung über die Läufe. Busroute SW. Die Nachfrage ist geschätzt und das Modell ist nicht kalibriert, die Zahlen zeigen Unterschiede zwischen den Varianten, keine absoluten Werte für die echte Kreuzung.

## Überblick je Stunde

| Kennzahl | Bestand |
|---|---|
| Konflikte Fahrzeug mit Fahrzeug im Knotenbereich (22 m), TTC < 1,5 s, PET < 1 s oder DRAC > 3 m/s² | 71.3 ± 10.2 |
| davon Kreuzen und Einbiegen | 41.3 ± 8.5 |
| davon Auffahren | 30.0 ± 3.9 |
| davon Kfz gegen Rad | 23.1 ± 6.7 |
| davon mit Bus oder Lkw | 4.2 ± 2.6 |
| davon mit Geradeausfahrer aus der Linksabbiegespur (Fehlspur) | 3.9 ± 2.4 |
| davon schwer (TTC < 1 s oder PET < 0,5 s) | 16.6 ± 4.2 |
| Fahrzeugkonflikte außerhalb des Knotenbereichs (nicht mitgezählt) | 478.6 ± 37.4 |
| Fußgänger auf Querung, Fahrzeug über 15 km/h müsste mit über 3 m/s² bremsen | 18.4 ± 2.8 |
| davon Fahrzeug schneller als 30 km/h | 5.3 ± 1.9 |
| davon durch Rad | 1.0 ± 0.8 |
| davon durch Fehlspur-Fahrer | 1.9 ± 1.4 |
| Kfz überholt Rad (Vorgänge je Stunde, Sublane-Modell) | 247.5 ± 25.6 |
| davon Überholabstand < 1,5 m (StVO innerorts) | 246.9 ± 25.6 |
| davon Überholabstand < 1,0 m | 217.5 ± 22.8 |
| Überholabstand im Median in m | 0.9 ± 0.0 |
| Mittlerer Zeitverlust Kfz in s | 12.5 ± 3.0 |
| Mittlerer Zeitverlust Rad in s | 11.0 ± 4.9 |
| Mittlerer Zeitverlust Bus in s | 10.4 ± 2.0 |
| Mittlere Wartezeit Fußgänger in s | 6.4 ± 1.1 |
| Nordarm: wartende Fahrzeuge im Mittel | 1.2 ± 0.5 |
| Nordarm: größte Schlange (Fahrzeuge) | 9.4 ± 2.7 |
| Nordarm: Anteil der Zeit mit mindestens 1 wartenden Fahrzeug in % | 49.8 ± 7.5 |
| Nordarm: Anteil der Zeit mit 2 oder mehr in % | 31.1 ± 8.3 |
| Nordarm: Anteil der Zeit mit 3 oder mehr in % | 13.0 ± 7.0 |
| Nordarm: Anteil der Zeit mit 5 oder mehr in % | 6.0 ± 4.7 |
| Nordarm: Schlange, 95 %-Wert (Fahrzeuge) | 5.1 ± 2.6 |
| Nordarm: Rückstau größter Wert in m (Modellrand bei 110 m vor der Haltlinie) | 70.7 ± 20.2 |
| Zulauf Nord: Pulkigkeit (Streuung der Abstände geteilt durch Mittel, 1 = zufällig) | 1.1 ± 0.1 |
| Zulauf Nord: Anteil der Fahrzeuge höchstens 3 s hinter dem Vordermann in % | 36.9 ± 3.1 |
| Nordquerung: Lücken von mindestens 7 s je Stunde (beide Richtungen) | 176.6 ± 7.0 |
| Nordquerung: Lücken von mindestens 15 s je Stunde | 81.4 ± 4.6 |
| Nordquerung: Anteil der Zeit, in der man sofort gehen kann (Lücke ab 7 s) in % | 49.8 ± 1.9 |
| Nordquerung: Wartezeit auf eine Lücke von 7 s im Mittel in s | 3.0 ± 0.1 |
| Nordquerung: Wartezeit auf eine Lücke von 7 s, 95 %-Wert in s | 13.0 ± 0.6 |
| Ampel Nord: Rückstau Richtung Norden, größter Wert in m (Knoten bei 340 m) | 46.1 ± 12.4 |
| Bus Süd nach West: Spurwechsel vom Haltebereich zur Linksabbiegespur | 6.0 ± 0.0 |
| dabei Konflikte (±5 s um den Wechsel) | 1.2 ± 1.0 |
| Bus überfährt Bordstein (Fahrten je Stunde) | 0.4 ± 0.5 |
| Lkw überfährt Bordstein | 0.1 ± 0.3 |
| Sattelzug überfährt Bordstein | 0.0 ± 0.0 |
| Pkw überfährt Bordstein | 7.1 ± 0.3 |
| Bus überfährt Insel oder Pflaster | 0.0 ± 0.0 |
| Lkw überfährt Insel oder Pflaster | 0.0 ± 0.0 |
| Sattelzug überfährt Insel oder Pflaster | 0.0 ± 0.0 |
| Pkw überfährt Insel oder Pflaster | 0.0 ± 0.0 |
| Teleports (Verklemmungen im Modell) | 0.0 ± 0.0 |
| Überlappungen im Modell (SUMO-Zusammenstöße, Modellfehler) | 6.5 ± 3.8 |
| Überschneidungen im Knoteninneren (SSM-Typ 111, nicht mitgezählt) | 40.3 ± 7.0 |

## Durchfahrtstempo der Pkw im Knoten in km/h

Tempo im Knotenkern (bis 12 m um die Mitte), je Fahrzeug gemittelt. Angegeben Mittel / 85 %-Wert über alle Pkw, dahinter bei Geradeausfahrern das Mittel der Pkw ohne Bremsen (innerhalb 40 m um die Mitte nie unter 85 % ihres dortigen Höchsttempos, also ungehindert), bei Abbiegern ohne Halt (dort nie unter 15 km/h). Fehlspur-Fahrer zählen zu Süd nach Nord.

| Relation | Bestand |
|---|---|
| Süd nach Nord | 44 / 56, ohne Bremsen 51 |
| Süd nach West | 34 / 40, ohne Halt 35 |
| Süd nach Ost | 25 / 29, ohne Halt 27 |
| West nach Süd | 25 / 29, ohne Halt 27 |
| West nach Nord | 18 / 30, ohne Halt 30 |
| West nach Ost | 24 / 30, ohne Bremsen 26 |
| Nord nach Süd | 17 / 20 |
| Nord nach West | 16 / 18 |
| Nord nach Ost | 12 / 17 |
| Ost nach Süd | 12 / 23, ohne Halt 28 |
| Ost nach West | 20 / 27, ohne Bremsen 26 |
| Ost nach Nord | 21 / 28, ohne Halt 27 |

## Fußgängerkonflikte je Querung

| Querung über Arm | Bestand |
|---|---|
| Süd (Gießerstr.) | 7.3 ± 2.9 |
| Nord (Gießerstr.) | 6.0 ± 1.9 |
| West (Naumburger Str.) | 3.9 ± 1.7 |
| Ost (Naumburger Str.) | 1.2 ± 1.2 |

## Zufahrten, Zeitverlust Kfz und Qualitätsstufe

Qualitätsstufe aus dem mittleren Zeitverlust der Kfz je Zufahrt mit den Grenzen für Knoten ohne Ampel A bis 10 s, B bis 20 s, C bis 30 s, D bis 45 s, E darüber, F bei Überlastung (mittlerer Einfahrverzug über 10 s, die Schlange reicht also über den Modellrand). Nach HBS 2015, am Original prüfen. Das HBS bewertet nur wartepflichtige Ströme, hier wird vereinfacht die ganze Zufahrt betrachtet.

| Zufahrt | Bestand |
|---|---|
| Süd (Gießerstr.) | 4.7 ± 0.6 s, QSV A |
| Nord (Gießerstr.) | 46.6 ± 16.7 s, QSV E |
| West (Naumburger Str.) | 6.4 ± 0.7 s, QSV A |
| Ost (Naumburger Str.) | 11.7 ± 3.1 s, QSV B |

## Rückstau je Zufahrt in Metern (Mittel / 95 %-Wert)

| Zufahrt | Bestand |
|---|---|
| Süd (Gießerstr.) | 0 / 0 |
| Nord (Gießerstr.) | 9 / 38 |
| West (Naumburger Str.) | 1 / 7 |
| Ost (Naumburger Str.) | 0 / 4 |

## Wartezeit der Fußgänger je Weg in s

| Weg | Bestand |
|---|---|
| Diagonal über den Knoten zwischen Nordost- und Südwestecke (Kiosk) | 0.0 ± 0.0 |
| Ostseite Süd nach Nord, quert Ostarm | 0.7 ± 0.5 |
| Ostseite Nord nach Süd, quert Ostarm | 0.7 ± 0.4 |
| Von Nordost zum Kiosk, quert Nord- und Westarm | 3.9 ± 0.7 |
| Vom Kiosk nach Nordost, quert West- und Nordarm | 15.6 ± 3.7 |
| Nordseite West nach Ost mit Kinderwagen, quert Nordarm | 4.7 ± 3.8 |
| Nordseite Ost nach West, quert Nordarm | 3.5 ± 0.6 |
| Nordseite West nach Ost, quert Nordarm | 2.9 ± 1.0 |
| Quert Südarm am Knoten | 12.9 ± 3.2 |
