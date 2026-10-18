# SUMO-Modell Gießerstraße / Naumburger Straße

Mikroskopische Verkehrssimulation der Kreuzung in Leipzig-Plagwitz mit dem freien Simulator [Eclipse SUMO](https://eclipse.dev/sumo/). Das Modell vergleicht den Bestand mit der empfohlenen Variante (bessere Markierung mit Tempo 30, abknickende Vorfahrt bleibt), roten Radwegen und als reinen Vergleich einer Tempo-30-Zone mit rechts vor links, und liefert Kennzahlen zu Sicherheit und Wartezeiten für die Bürgerkampagne. Das Browsermodell in `../modell` bleibt das Ideenmodell, dieses SUMO-Modell ist die nachvollziehbare Rechengrundlage.

**Abspieler im Browser** in [`grafik/abspieler.html`](grafik/abspieler.html). Die Datei im Browser öffnen, sie läuft ohne Internet (nur die Schrift kommt von Google Fonts). Fünf Minuten der Spitzenstunde je Variante mit 60 Bildern je Sekunde. Spurwechsel dauern einige Sekunden, Bus und Lkw holen beim Abbiegen aus, Gelenkbus und Sattelzug knicken, Blinker zeigen das Abbiegen, Beinahe-Unfälle blinken als Ringe auf. Verkehrszeichen sind nach StVO-Vorlage gezeichnet, mit Mast und einer Marke, die zum jeweiligen Fahrer zeigt.

| Bestand | Markierung und Tempo 30 (Empfehlung) |
|---|---|
| ![Bestand](grafik/abspieler_bestand.png) | ![Markierung](grafik/abspieler_markierung.png) |
| **Rote Radwege** | **Tempo-30-Zone (Vergleich, nicht empfohlen)** |
| ![Radwege](grafik/abspieler_radwege.png) | ![Zone](grafik/abspieler_zone.png) |

## Aufruf

```bash
pip install -r requirements.txt     # SUMO, matplotlib, shapely, pillow
python3 build.py                    # Netze und Nachfrage aller Varianten
python3 werkzeuge/schleppkurve.py   # Schleppkurven der Fahrbeziehungen
python3 run.py                      # 10 Läufe je Variante, etwa 2 Minuten
python3 plots.py                    # Vergleichsdiagramm und Netzbilder nach grafik/
python3 abspieler/export.py         # Browser-Abspieler grafik/abspieler.html
python3 werkzeuge/pruefe_abspieler.py   # Überlappungen, Bordstein und Knickwinkel im Abspieler prüfen
python3 werkzeuge/screenshots.py 60 grafik  # Bilder der Varianten nach 60 s
python3 werkzeuge/szenenbilder.py /tmp      # Bilder der kritischen Szenen
```

Weitere Schalter

- Standard ist der Regelbetrieb, die Busse fahren in beiden Richtungen zwischen Süd und West. `python3 build.py --bus SN` bildet die derzeitige Baustellenumleitung ab (Naumburger Straße ist Sackgasse, die Busse fahren geradeaus Süd und Nord, so steht es im Oktober 2026 auch in OpenStreetMap).
- `python3 run.py --laeufe 3 --varianten bestand radwege` für schnelle Proben. Die verworfenen Varianten (`rvl`, `t30_zebra`, `geschuetzt`, `minikreisel`) baut `python3 build.py --alt`, danach lassen sie sich mit `--varianten` rechnen.
- `python3 run.py --nur-bericht` schreibt `vergleich.md` aus der vorhandenen CSV neu.
- `python3 werkzeuge/vorfahrt.py netze/bestand.net.xml J` zeigt, wer am Knoten auf wen wartet.
- Ansehen mit Oberfläche geht mit `sumo-gui -n netze/bestand.net.xml -r netze/bestand.rou.xml -a netze/haltestelle.add.xml`.

## Dateien

| Pfad | Inhalt |
|---|---|
| `build.py` | Liest die Geometrie aus `../daten/map.osm` und erzeugt je Variante Netz und Nachfrage. Alle Ortsbeobachtungen stehen hier als Konstanten |
| `strassenraum.py` | Fahrbahn, Inseln, Radwege und Pflaster als Flächen für Zeichnung und Prüfungen |
| `kinematik.py` | Lage der Fahrzeugglieder mit Schleppkurve (wie `rigidUpdate` und `artUpdate` im Browsermodell) und Blinker |
| `diagonal.py` | Fußgänger, die diagonal über den Knoten gehen (neben SUMO geführt) |
| `run.py` | Simuliert, wertet aus, schreibt `ergebnisse/kennzahlen.csv` und `ergebnisse/vergleich.md` |
| `plots.py` | Netzbilder und Vergleichsdiagramm |
| `abspieler/export.py`, `abspieler/vorlage.html` | Baut den Abspieler |
| `abspieler/szenen.py` | Sucht die kritischen Szenen in den Rohdaten von `run.py` |
| `werkzeuge/schleppkurve.py` | Schleppkurven aller Fahrbeziehungen, `ergebnisse/schleppkurven.md` |
| `werkzeuge/pruefe_abspieler.py` | Prüft die fertige Seite auf sich überlappende Fahrzeuge und Fahrten über Bordstein und Inseln |
| `werkzeuge/vorfahrt.py` | Prüfhilfe für die Vorfahrtregeln |
| `netze/` | Erzeugte SUMO-Netze, Nachfrage, Haltestelle, Schleppkurvenflächen |
| `ergebnisse/` | Kennzahlen je Lauf, Vergleichstabelle, Schleppkurven. Rohdaten unter `roh/` werden nicht eingecheckt |

## Ortsbeobachtung der Initiative

Die Initiative hat im Oktober 2026 Luftbilder (Geoportal Leipzig, Google), Straßenfotos (Google Street View 2023 und 2026, eigene Fotos) und Beobachtungen beigesteuert. Fremde Bilder liegen nicht im Repository (Urheberrecht). Übernommen ist

| Punkt | Beobachtung | Im Modell |
|---|---|---|
| Busse 60 und 60E | Regelbetrieb in beiden Richtungen Süd nach West und West nach Süd. Derzeit wegen Baustelle umgeleitet (Naumburger Straße Sackgasse) | Takt 10 min je Richtung, Umleitung mit `--bus SN` |
| Haltestelle Süd | Halt auf der rechten Fahrbahnseite mit BUS und Zickzack, durch breite Strichlinie getrennt, am Südende ein Keil als Einfahrt, Wartehäuschen auf dem Ostgehweg. Südlich davon wird am rechten Rand geparkt, der Bus fährt dort auf der Fahrspur und schwenkt erst am Keil ein | Parkstreifen Ostseite ab 70 m, Haltebereich 45 bis 70 m nur für Bus und Rad, dahinter zwei Spuren |
| Bus Süd nach West nach dem Halt | muss von ganz rechts auf die Linksabbiegespur wechseln | eigene Kennzahl Spurwechsel und Konflikte dabei |
| Spurwechsel und Abbiegen | Spurwechsel dauern in echt einige Sekunden (Pkw 5 bis 6 s, Bus und Lkw 6 bis 8 s), Busse knicken beim Anfahren nicht, Bus und Lkw holen beim Rechtsabbiegen aus | Spurwechsel in SUMO 6 s, im Abspieler weich über 30 bis 60 m, Ausholen und Knickgrenze, siehe Fahrzeugkinematik |
| Süd nach Nord | viele fahren zügig geradeaus durch | 200 statt 110 Pkw je Stunde, 20 % schnelle Fahrer (Schätzung) |
| Blinken | Geradeausfahrer blinken nie, auch nicht beim Spurwechsel, Abbieger meistens | im Abspieler so gezeichnet, siehe Kritische Szenen |
| Südarm Markierung | zwei Spuren nordwärts mit Pfeilen links bzw. geradeaus und rechts, zur Gegenrichtung nur eine Leitlinie (eine früher eingezeichnete schmale Sperrfläche gibt es laut Initiative nicht). Gestrichelte Leitlinie mit großem Radius von der Linie zwischen Links- und Geradeausspur zur Nordwestecke, sie trennt die abknickende Vorfahrt vom Geradeausverkehr. Zweite schräge Linie von der Südost- zur Nordostecke über die Mündung des Ostarms | gezeichnet |
| Fehlverhalten Süd | etwa ein Viertel der Geradeausfahrer nach Nord nutzt die Linksabbiegespur oder fährt mittig | 25 % im Bestand über eine nur dafür freigegebene Verbindung (Fahrzeugklasse `taxi`), im Abspieler orange und mittig. Mit durchgezogener Linie (Markierung, Radwege) 8 %, in der Zone 15 % |
| Nordarm | 8,2 m, Westseite Längsparken mit Begrenzungslinie ab etwa 30 m, davor Halteverbot (Schild). STOP-Feld und Haltlinie | Parkstreifen ab 30 m (Fahrspuren dort 3,1 m), Haltlinie vor der Querung, STOP für Fahrer aus Norden lesbar |
| Zufluss Nord | am Stopp stehen höchstens etwa 6 Autos, typisch 1 bis 3, Verkehr kommt in Pulks von der Ampel etwa 350 m nördlich | Ampel als Zulaufstrecke, Menge und Lückenannahme daran kalibriert, siehe Zulauf Nord und Kalibrierung |
| Naumburger West | keine Mittelmarkierung, Tempo 30 per Streckenschild (274, Lärmaktionsplan seit 12/2025, OSM `maxspeed=30 sign`). Südseite Parken erst ab etwa 30 m vor der Knotenkante, davor Halteverbot Mo bis Fr 6 bis 14 Uhr (mit Wegweiser „Amt für Jugend, Familie und Bildung“), Nordseite kein Parken | Das Modell rechnet die Morgenspitze, dort ist der Abschnitt frei. Nachmittags ab 14 Uhr stehen dort Parker |
| Naumburger Ost | Tempo-30-Zone (274.1 kurz hinter dem Knoten auf der Südseite, Foto der Initiative). Die frühere Annahme Tempo 50 nach OSM war falsch. Keine Markierung, Nordseite Parken bis an die Ecke, Südseite ab etwa 10 m, Restfahrbahn nur etwa einspurig (4,5 bis 5 m) | Tempo 30, Parken so gezeichnet, zwei schmale Spuren je 2,75 m. Begegnungswarten bildet SUMO nicht ab (Vereinfachung) |
| Schilder | Süd und West Vorfahrtstraße (306) mit Zusatz 1002, Nord Halt (206), Ost Vorfahrt gewähren (205), beide mit Zusatz 1002 | nach StVO-Vorlage gezeichnet, 1002 aus Sicht des jeweiligen Fahrers (eigene Zufahrt unten) |
| Querungen | Fußgänger queren so früh wie möglich, also direkt am Beginn der Eckausrundung. Nord zwischen Haltlinie und Knoten (meistgenutzt, etwa 100 je Stunde), Ost direkt an der Knotenkante, West in Wunschlinie zum Kiosk | Querungsachse 0,5 m hinter dem Beginn der Ausrundung (Süd 9,7 m, Nord 10,3 m, West 11,3 m, Ost 10,7 m von der Knotenmitte). Näher geht in SUMO nicht, weil jede Querung einen eigenen Knoten am Rand des Hauptknotens braucht |
| Diagonalquerer | wenige Leute gehen schräg über den Knoten zum Kiosk, aber nur, wenn wirklich frei ist | siehe unten, ohne Gewicht im Vergleich |
| Kiosk Südwestecke | „Lebensmittel A. Prinz“ in der abgeschrägten Hausecke, Bordstein folgt der Abschrägung | gezeichnet |
| Schaltkasten | großer Verteilerkasten mit Werbung auf dem Gehweg der Naumburger Seite an der Südwestecke, Sichthindernis | gezeichnet, Sichtbehinderung nicht modelliert |
| Haltverbot Gießerstraße Süd Westseite | absolutes Haltverbot von der Kioskecke bis zur Parkreihe, oft missachtet, meist 1 bis 2 Falschparker (Lieferwagen, Pkw am Kiosk) | Schilder 283 Anfang und Ende. Bestand mit 2 Falschparkern (rot gestrichelt), ein Lieferwagen ragt 0,4 m in die Fahrspur (Spur dort 3,2 statt 3,6 m), sie verdecken Sichtlinien. Markierung und Zone mit Grenzmarkierung 299, angenommen nur noch 0 bis 1 (gezeichnet 1), Radwege mit Radfahrstreifen ohne Falschparker |
| Kurzhalter Naumburger West Nordseite | absolutes Haltverbot, trotzdem hält oft jemand 1 bis 3 Minuten mit Warnblinker und holt etwas am Kiosk | Bestand etwa alle 10 Minuten einer (3 versetzte Flüsse, 90 bis 150 s Halt), in SUMO mit `parking=true`, weil SUMO das Vorbeifahren über die Gegenspur nicht abbildet. Im Abspieler Warnblinker, rot gestrichelter Rahmen und eine gezeichnete Person, die zum Kiosk und zurück geht (nur Darstellung). In den Varianten Grenzmarkierung am Fahrbahnrand, angenommen halb so oft |
| Poller | kommen für die Initiative nicht in Frage | in keiner Variante, Halteverbote nur über Markierung, Beschilderung und Kontrolle (Annahme) |
| Baustellenschilder 2023 | Halteverbot und Gefahrzeichen an der Kioskecke waren mobil | nicht gezeichnet |

## Modellaufbau

**Geometrie.** Lage und Richtung der vier Arme stammen aus OpenStreetMap (Knoten 60015219). Jeder Arm ist eine Gerade von 120 m. Die Breiten sind mit Luftbild und OSM abgeglichen. Parkstreifen sind Spuren ohne Verkehr und legen den Bordstein fest.

| Arm | Fahrbahn | Querschnitt |
|---|---|---|
| Gießerstraße Süd | 13,0 m | West Parkstreifen 2,2 (geparkt erst ab 45 m), südwärts 3,6, nordwärts 7,2 (südlich der Haltestelle Parken 2,4 und eine breite Spur, Haltebereich, dann zwei Spuren) |
| Gießerstraße Nord | 8,2 m | je Richtung 4,1, ab 30 m Westseite Parken 2,0 und zwei Spuren je 3,1 |
| Naumburger West | 9,5 m | Südseite Parkstreifen 2,0, je Richtung 3,75 |
| Naumburger Ost | 9,5 m | beidseitig Parken 2,0, je Richtung 2,75 |

Die Nordecken sind mit 5 m ausgerundet, die Südecken wie die Hausecken abgeschrägt. Rechtsabbieger West nach Süd und Nord nach West fahren eine weitere Bahn als die Standardbahn von netconvert (`WEITE_KURVEN` in `build.py`), sonst würde schon ein Pkw mit dem Heck den Bordstein streifen.

**Vorfahrt im Bestand.** Abknickende Vorfahrt Süd nach West, Stoppschild Nord (Halt 1 s an der Haltlinie), Ost wartepflichtig, zwischen Nord und Ost rechts vor links. Wer aus West geradeaus nach Ost fährt, wartet auf den Strom Süd nach West.

**Varianten**

| Variante | Änderungen gegenüber Bestand |
|---|---|
| `bestand` | wie oben. Gießerstraße 50, Naumburger West 30 (Streckenschild), Naumburger Ost Tempo-30-Zone |
| `markierung` (Empfehlung) | Vorfahrt wie heute, Tempo 30 auf allen Armen streckenbezogen (Zeichen 274). Eine Tempo-30-Zone ist hier nicht möglich, weil Zonen nach VwV-StVO keine Vorfahrtstraßen umfassen dürfen. Klarer Bogen der Vorfahrt, durchgezogene Fahrstreifenbegrenzung (295) zwischen Links- und Geradeausspur auf den letzten 15 m, dadurch nur noch 8 % Fehlspur (Annahme, wer geradeaus aus der Linksabbiegespur fährt, überfährt eine durchgezogene Linie). Grenzmarkierung (299) an der Nordseite des Ostarms auf den ersten 7 m, damit Sichtfeld frei. Breitere Haltlinie Nord und Wartelinie Ost, Schilder 206 und 205 zusätzlich links, 306 zusätzlich links am Südarm, Tempo-30-Piktogramme auf der Fahrbahn aller Zufahrten. Keine Zebrastreifen, keine Poller |
| `radwege` | wie `markierung`, dazu rot eingefärbte Radfahrstreifen (Breitstrich, Breiten nach ERA 2010). Gießerstraße Süd nordwärts 1,85 m am rechten Rand (Haltebereich wie heute gemeinsam mit dem Bus, südlich davon 0,5 m Sicherheitstrennstreifen zu den Parkern), südwärts 2,0 m statt des Parkstreifens auf der Westseite. Naumburger West Richtung Knoten 1,85 m auf den letzten 30 m im heutigen Halteverbot. Rote Furten durch den Knoten West nach Süd und Süd nach Nord. Westwärts (3,75 m), Nord (8,2 m) und Ost (Engstelle) reicht die Breite nicht, dort Piktogramme. Linksabbiegen Süd nach West auf der Linksabbiegespur, indirektes Linksabbiegen und aufgeweiteter Radaufstellstreifen wurden geprüft, passen ohne Ampel aber nicht sinnvoll |
| `zone` (Vergleich, nicht empfohlen) | Tempo-30-Zone (274.1) an allen Zufahrten, damit rechts vor links an allen Armen, alle Vorfahrtschilder und Wartelinien entfallen. Grenzmarkierung an der Ostecke wie oben. Keine Zebrastreifen. Fehlspur 15 % (Pfeile bleiben) |

**Warum die Zone nur Vergleich ist.** Die Initiative empfiehlt keine grundsätzliche Änderung der Vorfahrt, weil sich die Menschen an die abknickende Vorfahrtstraße gewöhnt haben. Ein Wechsel auf rechts vor links würde gerade in der Umstellungszeit neue Unsicherheit schaffen. Die Zone bleibt deshalb nur als Vergleich im Modell, sie zeigt, was eine Änderung der Vorfahrt rechnerisch bewirken würde.

Die Vorfahrtstraße mit Radfahrstreifen ist bewusst die Basis der Variante `radwege`. In einer Tempo-30-Zone sind Radfahrstreifen nach VwV-StVO in der Regel nicht vorgesehen.

**Parkplätze im Modellausschnitt** (je Arm 120 m, ohne zufällige Lücken gezählt)

| Variante | Stellplätze | Unterschied |
|---|---|---|
| Bestand | 88 | |
| Markierung und Tempo 30 (Empfehlung) | 87 | −1 an der Nordseite des Ostarms (Grenzmarkierung) |
| Rote Radwege | 74 | −14, davon 13 auf der Westseite der Gießerstraße Süd (45 bis 120 m) und 1 am Ostarm. Jenseits des Modellausschnitts kostet der Radfahrstreifen dort etwa 18 Plätze je 100 m. Dazu entfallen auf der Naumburger West die etwa 5 Plätze, die heute nachmittags ab 14 Uhr im Halteverbotsabschnitt genutzt werden |
| Tempo-30-Zone (Vergleich) | 87 | −1 wie bei der Markierung |

**Verworfene Varianten.** Die Initiative hat nach den ersten Ergebnissen entschieden, Zebrastreifen, die geschützte Kreuzung und den Minikreisel nicht weiter zu verfolgen. Sie lassen sich mit `python3 build.py --alt` weiter bauen. Die letzten Kennzahlen (Stand Commit dc05a94, damals noch mit Querungen weiter vom Knoten, Ost Tempo 50, ohne Spurwechseldauer) stehen in `ergebnisse/vergleich_alt_stand_dc05a94.md`.

| Variante | Grund | Fahrzeugkonflikte je Stunde | davon schwer | Kfz gegen Rad |
|---|---|---|---|---|
| Rechts vor links, Tempo 30, ohne Markierung | aufgegangen in der Variante Tempo-30-Zone | 16 | 0,6 | 5 |
| Tempo 30 mit Zebra Nord und West | Zebrastreifen hier unrealistisch (Einschätzung der Initiative), kaum Wirkung auf die Fahrzeugkonflikte | 41 | 14 | 12 |
| Geschützte Kreuzung (angepasst) | an den Nordecken kein Platz für Radwege hinter Inseln, Furten direkt am Knotenrand, im Modell mehr Konflikte | 82 | 28 | 25 |
| Minikreisel | 18 m Gelenkbus Süd nach West, Nordarm 8,2 m, Knoten zu klein | nicht mehr gerechnet | | |

**Kinderwagen.** Von den 25 Personen je Stunde auf der Nordseite West nach Ost schieben etwa 6 einen Kinderwagen (eigener Fußgängertyp, 1,8 m lang, etwa 1,0 m/s). Im Abspieler steht die Person am Bordstein, der Wagen ragt beim Warten etwa 1 m in die Fahrbahn.

**Nachfrage.** Spitzenstunde aus dem Browsermodell (`../modell/src/sim.js`, `DEMAND`), angepasst nach Beobachtung. Pkw, Lkw, Sattelzüge und Räder kommen zufällig (Poisson), die Busse im 10-Minuten-Takt je Richtung. Die Menge aus Nord (157 Kfz je Stunde) ist an der Schlange am Stopp Nord kalibriert, siehe Kalibrierung.

| Gruppe | je Stunde |
|---|---|
| Pkw | etwa 1060, davon Süd nach West 260, West nach Süd 240 und Süd nach Nord 200 (nach Beobachtung erhöht, Schätzung) |
| aus Nord | 224 Kfz (Süd 60 %, West 35 %, Ost 5 %). Gewünscht waren etwa 300, damit ist der Nordarm im Modell aber überlastet (Zeitverlust 80 bis 290 s, wachsende Schlange). Mit 224 wartet in der Hälfte der Zeit mindestens ein Fahrzeug, in einem Viertel der Zeit zwei oder mehr |
| Schnelle Fahrer | aus Süd und West heute 20 % mit 10 bis 15 km/h über dem Limit, in den Tempo-30-Varianten 10 % mit 5 bis 10 km/h darüber (Schätzung) |
| Lkw und Sattelzüge | 33 |
| Gelenkbusse 18 m | 12 (6 je Richtung Süd nach West und West nach Süd) |
| Rad | 198 |
| Fußgänger | etwa 160 Wege mit Querungen Nord etwa 100, West 50, Süd 30, Ost 30, dazu wenige Diagonalquerer |

**Diagonalquerer.** SUMO kann keine Querung schräg über den ganzen Knoten abbilden. Diese Personen führt `diagonal.py` neben SUMO (etwa 10 je Stunde). Nach Angabe der Initiative gehen sie nur, wenn wirklich frei ist: kein Fahrzeug im Knoten und keines, das in den nächsten 7 s ankommt. Sonst nehmen sie nach 15 s die normalen Querungen. Ihre Konflikte stehen nur noch in der CSV, nicht im Vergleich.

**Fahrzeugkinematik im Abspieler.** SUMO liefert die Position der Fahrzeugfront. Spurwechsel dauern in SUMO 6 s (`--lanechange.duration`). An einigen Spurübergängen setzt SUMO Fahrzeuge trotzdem schlagartig um. Im Abspieler wird deshalb auf den Armen (ab 15 m vom Knoten) der Abstand zur Armachse geglättet: Er ändert sich höchstens mit 0,42 m/s (Pkw) bzw. 0,25 m/s (Bus, Lkw, Sattelzug) und höchstens 1 m je 14 m Fahrweg, als symmetrische Rampe. Dazu kommt ein gleitendes Mittel über den Fahrweg (auf Geraden lang, in Kurven kurz). Ein Spurwechsel wird so zu einer sanften S-Kurve über 30 bis 60 m, das Fahrzeug steht dabei leicht schräg. Die Vorderachse folgt dieser Bahn, die Hinterachse läuft als Schleppkurve nach. Gelenkbus 18 m (Vorderteil mit Radstand 5,9 m, Gelenk 1,6 m hinter der Mittelachse, Nachläufer 5,9 m) und Sattelzug (Zugmaschine 3,7 m, Auflieger 7,8 m) haben zwei Glieder. Bus, Lkw und Sattelzug **holen beim Rechtsabbiegen aus** (West nach Süd, Nord nach West): Ihre Hinterachse (beim Gelenkbus die Mittelachse) läuft auf der Fahrspur, die Vorderachse fährt tangential davor einen weiteren Bogen außen, das Heck bleibt innen knapp am Bordstein. Bei Linksabbiegern und Geradeausfahrern ist genug Platz, dort folgt die Vorderachse der Bahn. Der Knickwinkel ist begrenzt (Gelenkbus 42°, Sattelzug 65°). `werkzeuge/pruefe_abspieler.py` prüft über den ganzen Abspieler Überlappungen, Bordstein, Knickwinkel und die Quergeschwindigkeit auf den Armen (Grenze Pkw 0,55 m/s, Bus und Lkw 0,5 m/s, bei schneller Fahrt Neigung 1:12). Weil die geglätteten Bahnen seitlich etwas von SUMO abweichen, berühren sich im Abspieler je Variante 4 bis 5 Paare kurz. Halte von mindestens 3 s (Bus an der Haltestelle, Warten am Stopp) trennen die geglätteten Abschnitte, das Fahrzeug steht dort genau, wo SUMO es hält. Der Test prüft auch, dass jeder Bus nordwärts mindestens 15 s im Haltebereich steht (gemessen 20 s in allen Varianten). Als letzte Sicherung ist die Querbewegung der Vorderachse auf den Armen auf 0,42 m/s (Pkw) bzw. 0,25 m/s (Bus, Lkw) begrenzt, so schwenkt auch der Bus beim Anfahren aus dem Haltebereich über gut 20 m aus. Gemessen wird die Quergeschwindigkeit über je 1 s (die Bahnen sind auf 0,1 m gerundet), höchstens 0,44 m/s (Bus) und 0,41 m/s (Pkw). Die Haltestelle der Gegenrichtung (Busse West nach Süd) liegt nicht im OSM-Ausschnitt, diese Busse halten im Modell nicht. Die Bordstein-Kennzahl in `run.py` nutzt dieselbe Kinematik. SUMO selbst rechnet mit geraden Fahrzeugen.

## Kennzahlen

| Kennzahl | Definition |
|---|---|
| Fahrzeugkonflikte | SUMO-Gerät SSM, gezählt wenn TTC unter 1,5 s, PET unter 1 s oder DRAC über 3 m/s², jeweils ab 15 km/h und nur im Knotenbereich bis 22 m um die Mitte (alle Varianten gleich). Schwer heißt TTC unter 1 s oder PET unter 0,5 s. Getrennt ausgewiesen Kfz gegen Rad, mit Bus oder Lkw und mit Fehlspur-Fahrern |
| Fußgängerkonflikte | Eigene Auswertung der Bewegungsdaten. Eine Person steht auf einer Querung und ein Fahrzeug über 15 km/h müsste stärker als 3 m/s² bremsen |
| Nordarm | wartende Fahrzeuge im Mittel und höchstens, Anteil der Zeit mit 1, 2 oder 3 und mehr Wartenden |
| Bus Spurwechsel | Busse Süd nach West, die nach dem Halt auf die Linksabbiegespur wechseln, und Konflikte dieser Busse 4 s vor bis 6 s nach dem Wechsel |
| Bordstein und Inseln | Fahrzeugumrisse mit Schleppkurve gegen die Fahrbahnfläche, je Fahrt gezählt, wenn ein Glied mehr als 0,2 m² über Bordstein bzw. Insel oder Pflaster ragt |
| Zeitverlust, Rückstau, Qualitätsstufe | wie zuvor, Qualitätsstufe nach den Grenzen des HBS 2015 für Knoten ohne Ampel, vereinfacht, am Original prüfen |

Gezählt wird die Stunde nach 10 Minuten Einschwingzeit, Mittel aus 10 Läufen mit festen Startwerten.

## Ergebnisse

Vollständige Tabellen in [`ergebnisse/vergleich.md`](ergebnisse/vergleich.md), Schleppkurven der Standardbahnen in [`ergebnisse/schleppkurven.md`](ergebnisse/schleppkurven.md) (ohne Ausholen gerechnet, deshalb bei Rechtsabbiegern West nach Süd größer als in der Bordstein-Kennzahl).

![Vergleich](grafik/vergleich.png)

Kernaussagen je Stunde (Mittel aus 10 Läufen, Morgenspitze)

| | Bestand | Markierung und Tempo 30 (Empfehlung) | Rote Radwege | Tempo-30-Zone (Vergleich) |
|---|---|---|---|---|
| Fahrzeugkonflikte im Knoten | 55 | 42 | 49 | 21 |
| davon schwer | 15 | 16 | 19 | 1,6 |
| davon Kfz gegen Rad | 12 | 8,5 | 16 | 4,8 |
| Fußgänger auf Querung bedrängt | 23 | 18 | 19 | 18 |
| davon Fahrzeug schneller als 30 km/h | 5,6 | 3,4 | 3,8 | 3,5 |
| Wartezeit Fußgänger in s | 4,0 | 7,2 | 5,3 | 9,4 |
| Nordarm Zeitverlust Kfz in s | 33 (D) | 23 (C) | 21 (C) | 11 (B) |
| Nordarm größte Schlange (Fahrzeuge) | 6,2 | 6,0 | 5,6 | 3,6 |
| Nordarm Anteil der Zeit mit Wartenden | 30 % | 26 % | 26 % | 4 % |
| Zeitverlust Kfz in s | 15 | 10 | 9 | 12 |
| Stellplätze im Ausschnitt | 88 | 87 | 74 | 87 |

Gerechnet mit Pulks aus Nord (Ampel 350 m nördlich) und mit dem an der Schlange am Stopp Nord kalibrierten Bestand, siehe unten.

**Streuung.** Die Zahlen schwanken zwischen den zehn Läufen deutlich, bei den schweren Konflikten etwa ± 5 je Stunde. Schon ein zusätzlicher kleiner Fußgängerstrom (die Kinderwagen, 6 je Stunde) mischt die Zufallszahlen neu und verschiebt die schweren Konflikte um bis zu 3. Unterschiede unter etwa 3 bei den schweren Konflikten sind deshalb kein belastbarer Unterschied. Belastbar sind die großen Abstände (alle Konflikte, Zone gegen den Rest, schnelle Fahrzeuge an den Querungen, Nordarm).

Lesart

- **Markierung und Tempo 30 (Empfehlung)** senkt die Fahrzeugkonflikte um knapp ein Viertel (55 auf 42), Kfz gegen Rad um knapp ein Drittel und die schnellen Fahrzeuge an den Querungen um etwa 40 %. Der Nordarm wartet im Mittel 10 s weniger (33 auf 23 s). Die schweren Konflikte bleiben im Rahmen der Streuung gleich (15 und 16), siehe unten.
- **Was bei der Empfehlung bleibt.** Die schweren Konflikte im Modell sind fast alle Lückenkonflikte gegen den Hauptstrom Süd nach West. Über alle zehn Läufe je Stunde: Süd nach West gegen Linksabbieger West nach Nord etwa 5 (Pkw, Lkw und Bus), gegen Räder West nach Nord 1,6, gegen Einbieger aus Ost und Nord zusammen 1,8. Das sind gut zwei Drittel der schweren Konflikte (gezählt vor Ampel und Kalibrierung, damals 13 je Stunde). Wer aus West, Ost oder Nord einbiegt, muss eine Lücke im abbiegenden Hauptstrom finden, der aus der Linksabbiegespur kommt und dessen Ende man schlecht sieht. Das bleibt, solange die abknickende Vorfahrt bleibt. Die Maßnahmen dagegen wirken über Sicht und Aufmerksamkeit (freies Sichtfeld an der Ostecke, breitere Halt- und Wartelinien, zusätzliche Schilder links, Tempo-30-Piktogramme, weniger Falschparker). SUMO kennt Sicht nicht, deshalb sind sie gezeichnet, aber nicht als Zahl eingerechnet. Ihre Wirkung ist eher größer als im Modell.
- **Geprüft und verworfen** (Sensitivität für Bestand / Markierung / Radwege, schwere Konflikte je Stunde, gerechnet vor dem Kinderwagen-Strom, Grundwerte damals 16 / 14 / 12, Lückenannahme damals `impatience` 0,5). Vorsichtigeres Einbiegen aus Nord und Ost (`impatience` 0,35 statt 0,5) ergibt 16 / 13,5 / 13 bei 61 s Zeitverlust am Nordarm, mit 0,25 sogar 214 s, der Nordarm würde überlaufen. Langsamerer Bogen mit 20 km/h und Linksabbiegen West nach Nord nur mit Warten ergibt 16 / 17 / 20, also schlechter, weil sich die Ströme im Knoten länger überlagern. Beides bleibt deshalb aus dem Modell. Die Lückenannahme ist inzwischen an der Schlange am Stopp Nord kalibriert (siehe Kalibrierung).
- **Tempo-30-Zone mit rechts vor links (nur Vergleich, nicht empfohlen)** hätte rechnerisch die wenigsten Konflikte (21, schwer 1,6) und wenig Stau am Nordarm. Sie ändert aber die Vorfahrt grundsätzlich, an die sich alle gewöhnt haben, und die Umstellungszeit ist im Modell nicht abgebildet. Fußgänger warten dort am längsten (9,4 s).
- **Rote Radwege** bringen gegenüber der reinen Markierung im Modell keinen Sicherheitsgewinn, Kfz gegen Rad steigt sogar (16 statt 8,5). Vermutliche Ursache sind Radfahrende, die vom Radfahrstreifen rechts nach West links abbiegen wollen und dafür über die Geradeausspur wechseln, und Rechtsabbieger West nach Süd über den Radfahrstreifen. Ohne Ampel fehlt der geschützte Aufstellbereich. SUMO bildet das Einordnen der Räder grob ab, die Zahl ist eine Tendenz. Dafür kosten die Radwege 14 Stellplätze im Ausschnitt.
- **Fehlspur.** Mit durchgezogener Linie fast keine Konflikte mehr durch Geradeausfahrer aus der Linksabbiegespur, im Bestand im Modell etwa einer je Stunde.
- **Bus.** Der Wechsel vom Haltebereich auf die Linksabbiegespur passiert mit jedem Bus nach West (etwa 5 je Stunde), Konflikte dabei bleiben selten. Mit Ausholen beim Rechtsabbiegen überfahren Bus, Lkw und Sattelzug den Bordstein kaum noch (unter 0,5 Fahrten je Stunde).

## Kritische Szenen

Im Abspieler gibt es neben dem freien Abspielen den Modus **Kritische Szenen**. Jede Szene ist eine echte Stelle aus dem ersten der zehn Läufe je Variante (`ergebnisse/roh/<variante>_01`, Startwert 1, 0,5 s Schrittweite), gesucht mit einem festen Filter (`abspieler/szenen.py`). Kinderwagen sind selten, für Szene 1 werden deshalb alle zehn Läufe durchsucht (`run.py --behalte-roh`), der Untertitel nennt dann den Lauf. Es wird nichts nachgestellt. Die Szene läuft mit halber Geschwindigkeit, hält am kritischen Moment 2,5 s an und zeigt einen Untertitel in einfacher Sprache. Beteiligte sind gelb markiert, Pfeile zeigen die Fahrtrichtung. Wartende Fußgänger und langsame Fahrer zeigen einen Sichtkegel. Der Blick dreht weich, höchstens 90 Grad je Sekunde, mit sanftem Anfahren und Abbremsen. Wartend schaut man erst zur einen Seite, dann zur anderen und wieder zur ersten (in Szene 1 Süd, Nord, Süd, sonst erst links), gehend nach vorn mit kurzen Kontrollblicken. Sichtlinien führen zu fahrenden Fahrzeugen bis etwa 45 m und blenden weich ein und aus, je nach Abstand, Tempo und ob das Fahrzeug im Blick liegt, grün wenn frei, rot gestrichelt wenn Häuser, Schaltkasten, Parker oder andere Fahrzeuge die Sicht verdecken (2D-Strahltest). Über „So wäre es mit“ lässt sich je Szene die passende Stelle in einer anderen Variante zeigen, darunter steht die zugehörige Kennzahl je Variante.

| Nr | Szene | Filter |
|---|---|---|
| 1 | Kinderwagen an der Nordquerung, von Süden kommt es schnell | Person mit Kinderwagen wartet mindestens 2 s an der Nordwestecke, Fahrzeug aus Süd fährt bis 20 m vor der Querung vorbei, gewählt das schnellste (plus Wartezeit) |
| 2 | Rad biegt nach Nord ab und steht im Verkehr | Rad West nach Nord steht am längsten im Knoten, viel Verkehr ringsum |
| 3 | Nord gegen Ost, wer darf zuerst? | Konflikt zwischen Fahrzeugen aus Nord und Ost (auch langsam), sonst engste gleichzeitige Begegnung |
| 4 | Engstelle Ost, Begegnung zwischen Parkern | engste Begegnung zweier Fahrzeuge in Gegenrichtung auf dem Ostarm, schwere Fahrzeuge bevorzugt |
| 5 | Stopp Nord, Vorfahrt genommen | engster Konflikt zwischen einem Fahrzeug aus Nord und Rad bzw. Auto auf der Vorfahrt Süd und West |
| 6 | Ohne Blinker geradeaus aus der Abbiegespur | Geradeausfahrer in der Linksabbiegespur nahe der Nordquerung, mit Fußgänger dort |
| 7 | Bus wechselt nach dem Halt quer auf die Abbiegespur | Spurwechsel eines Busses nach West mit dem meisten Verkehr ringsum |
| 8 | Sicht vom Kiosk über die Naumburger Straße | Person wartet an der Westquerung auf der Kioskseite, viele Fahrzeuge in Sicht |
| 9 | Kurzhalter am Kiosk im Haltverbot | Kurzhalter auf der Nordseite West steht, viel Verkehr ringsum |

Alle neun Szenen kommen in allen vier Varianten vor. `python3 werkzeuge/szenenbilder.py <ordner> [variante]` macht Bilder am kritischen Moment.

**Blinken (Ortsbeobachtung, Schätzung).** Geradeausfahrer (Süd nach Nord, Nord nach Süd, West nach Ost, Ost nach West) blinken nie, auch nicht beim Spurwechsel am Südarm oder wenn sie in der Linksabbiegespur fahren. Abbieger, auch auf der abknickenden Vorfahrt, blinken zu etwa 88 %, und zwar nach ihrer Route ab etwa 35 m vor der Knotenmitte bis zum Verlassen des Knotens, danach sofort aus. Beim Einordnen und Busse beim Ein- und Ausschwenken an der Haltestelle blinkt es zur Seite des Spurwechsels. Busse blinken immer. Der Test prüft, dass niemand im Knotenbereich entgegen seiner Abbiegerichtung oder nach dem Verlassen des Knotens blinkt. Das ist nur im Abspieler dargestellt. In SUMO selbst wirkt das Blinken nicht, wartende Fahrer und Fußgänger kennen dort die Absicht der anderen. Die Unsicherheit durch fehlende Blinker ist deshalb in den Kennzahlen nicht enthalten, sie zeigt sich nur in Szene 6.

### Zulauf Nord mit Ampel (Pulks)

**Beobachtung der Initiative.** Etwa 350 m nördlich liegt an der Gießerstraße eine Ampel, der Verkehr aus Nord kommt deshalb oft stoßweise. Vermutlich ist es die Kreuzung Karl-Heine-Straße / Gießerstraße, für die laut Recherche (`../recherche/02-kreuzung-daten.md`) 2019/20 eine Ampel vorgesehen war. Die Lage ließ sich hier nicht in OSM nachsehen, weil OSM aus der Rechenumgebung nicht erreichbar war, bitte vor Ort bestätigen.

**Umsetzung (nur SUMO).** Der Nordarm ist um eine künstliche Zulaufstrecke verlängert, außerhalb des Abspieler-Ausschnitts. Die Ampel steht 350 m vor der Knotenmitte, davor liegen 100 m Einfahrstrecke. Festzeit als **Annahme**, Umlauf 80 s, Grün für die Gießerstraße 35 s, 3 s Gelb, 42 s Rot. Beide Richtungen der Gießerstraße haben gleichzeitig Grün, auch Süd nach Nord fährt auf diese Ampel zu. Die Stundenmenge aus Nord bleibt gleich. Auf den 340 m bis zum Knoten lösen sich die Pulks durch unterschiedliche Wunschgeschwindigkeiten etwas auf. Zeitverlust an der Ampel und beim Fahren im Pulk auf der Zulaufstrecke wird abgezogen, nur wer auf der Zulaufstrecke in der Schlange vom Stopp Nord steht, zählt zum Knoten. Im Abspieler zeigt oben eine kleine Anzeige die Phase dieser Ampel. Der alte gleichmäßige Zulauf lässt sich mit `ZULAUF_NORD=0` (dazu `SUMO_NETZE`, `SUMO_PLAIN`, `SUMO_ERG` auf eigene Ordner) weiter rechnen, Ergebnis in [`ergebnisse/vergleich_ohne_ampel_nord.md`](ergebnisse/vergleich_ohne_ampel_nord.md).

| je Stunde, ohne Ampel → mit Ampel (beides kalibrierte Menge) | Bestand | Empfehlung | Zone (Vergleich) |
|---|---|---|---|
| Pulkigkeit Zulauf Nord (1 = zufällig) | 1,0 → 1,4 | 1,0 → 1,4 | 1,0 → 1,3 |
| Nordarm Zeitverlust Kfz in s | 19 → 33 | 13 → 23 | 6 → 11 |
| Schlange am Stopp Nord, 95 %-Wert / größter Wert (Fahrzeuge) | 2 / 3,8 → 2,4 / 6,2 | 1,5 / 3,7 → 2,1 / 6,0 | 0 / 2,3 → 0,3 / 3,6 |
| Anteil der Zeit mit 5 und mehr Wartenden | 0,1 % → 1,1 % | 0 % → 0,6 % | 0 % → 0,1 % |
| Rückstau Nord größter Wert in m (Modellrand 110 m) | 28 → 50 | 30 → 47 | 19 → 26 |
| Fahrzeugkonflikte im Knoten / davon schwer | 70 / 14 → 55 / 15 | 46 / 15 → 42 / 16 | 21 / 1,7 → 21 / 1,6 |
| Nordquerung, Lücken ab 7 s | 172 → 174 | 179 → 178 | 171 → 173 |
| Nordquerung, Anteil der Zeit, in der man sofort gehen kann | 50 % → 50 % | 49 % → 49 % | 51 % → 50 % |
| Nordquerung, Wartezeit auf 7 s Lücke im Mittel / 95 %-Wert in s | 3,1 / 13 → 3,1 / 13 | 3,0 / 13 → 3,1 / 13 | 3,0 / 13 → 3,0 / 13 |

Lesart

- **Stopp Nord.** Wer im Pulk ankommt, muss hinter den anderen am Stopp warten, jeder einzeln auf eine Lücke. Die größte Schlange wächst von etwa 4 auf etwa 6 Fahrzeuge, der Zeitverlust aus Nord steigt deutlich (Bestand 19 auf 33 s). Erst mit den Pulks passt das Modell zur Beobachtung (höchstens etwa 6). Die Schlange bleibt in allen Läufen unter 110 m, sie wächst nie dauerhaft. Die Empfehlung bleibt besser als der Bestand.
- **Konflikte.** Insgesamt gibt es weniger Fahrzeugkonflikte, weil die Wartenden aus Nord häufiger hintereinander in der Schlange stehen statt einzeln in den Knoten zu drängen. Die schweren Konflikte ändern sich im Rahmen der Streuung nicht.
- **Lücken für Fußgänger an der Nordquerung.** Zwischen den Pulks entstehen längere Lücken, dafür ist es im Pulk dichter. Beides gleicht sich fast aus, weil die Nordquerung auch den starken Strom Süd nach Nord und die Linksabbieger West nach Nord quert, die nicht im Pulk kommen. Im Mittel wartet man etwa 3 s auf eine Lücke von 7 s, in 5 % der Fälle etwa 13 s. Wer gerade vor einem Pulk ankommt, wartet länger, wer danach kommt, kann sofort gehen.
- **Rückstau an der Ampel Richtung Norden.** Er reicht höchstens 75 bis 95 m zurück, bis zum Knoten (340 m) also bei weitem nicht.

### Kalibrierung am Stopp Nord

**Beobachtung der Initiative.** Am Stopp Nord stehen höchstens etwa 6 Autos, typisch 1 bis 3. Ziel für den Bestand war deshalb eine größte Schlange von im Mittel etwa 6 Fahrzeugen über die zehn Läufe (einzelne Läufe etwa 5 bis 7), typisch 1 bis 3 Wartende und keine dauerhaft wachsende Schlange. Vorher (224 Kfz je Stunde aus Nord, `impatience` 0,5, mit Pulks) waren es im Mittel 12, einzelne Läufe bis 16.

**Vorgehen.** Zuerst nur die Menge aus Nord verringert (alle Ströme aus Nord gleich, Aufteilung bleibt), Bestand mit je zehn Läufen. Selbst mit 134 Kfz je Stunde blieb die größte Schlange im Mittel bei 7, das liegt unter der Grenze von etwa 150 Kfz je Stunde. Deshalb zusätzlich die Lückenannahme der Wartepflichtigen angepasst. Eine längere Grünzeit an der Ampel (45 statt 35 s) hat kaum etwas geändert.

| Menge Nord Kfz/h | impatience | jmTimegapMinor in s | größte Schlange im Mittel (Läufe) | Anteil Zeit mit Wartenden |
|---|---|---|---|---|
| 224 | 0,5 | 1,0 | 11,9 (9 bis 16) | 53 % |
| 179 | 0,5 | 1,0 | 9,0 (6 bis 14) | 43 % |
| 157 | 0,5 | 1,0 | 8,1 (5 bis 14) | 41 % |
| 134 | 0,5 | 1,0 | 7,1 (4 bis 10) | 32 % |
| 157 | 0,8 | 1,0 | 6,8 (4 bis 10) | 32 % |
| 168 | 1,0 | 1,0 | 7,1 (5 bis 11) | 31 % |
| 179 | 1,0 | 0,5 | 7,6 (5 bis 9) | 31 % |
| **157** | **1,0** | **0,6** | **6,2 (4 bis 9)** | **29 %** |

**Gewählt** sind 157 Kfz je Stunde aus Nord (91 nach Süd, 55 nach West, 7 nach Ost, dazu 3 Lkw, Räder unverändert 45), `impatience` 1,0 (wer länger wartet, nimmt deutlich kleinere Lücken, oberes Ende des SUMO-Bereichs 0 bis 1) und `jmTimegapMinor` 0,6 s (Zeitlücke vor einem bevorrechtigten Fahrzeug, SUMO-Standard 1 s). Damit stehen im Bestand typisch 1 bis 2 Fahrzeuge (95 %-Wert der Schlange 2,4), die größte Schlange liegt im Mittel bei 6,2. Ausreißer bis 9 entstehen, wenn ein Rad oder Lkw am Stopp lange auf Fußgänger und Lücken wartet und gerade ein Pulk ankommt. Lückenannahme und Menge gelten für alle Varianten gleich. Mehr Mut beim Einbiegen erhöht im Bestand die Zahl der Fahrzeugkonflikte etwas. Die Werte ersetzen keine Zählung, sie sind an einer Beobachtung ausgerichtet. Kalibrierläufe lassen sich mit den Umgebungsvariablen `KAL_IMP`, `KAL_TGM` und `KAL_GRUEN` wiederholen.

## Überlappungen von Fahrzeugen

SUMO kann Fahrzeuge im Knoten übereinanderschieben, wenn die Vorfahrtlogik eine Lage nicht erkennt. Das ist ein Modellfehler, kein Unfall, und wird je Lauf gezählt. Bestand, Markierung und Zone um 1 je Stunde, Radwege 7,4 (dort meist Einbieger West nach Süd und Nord nach Süd, die gleichzeitig in die Fahrspur neben dem Radfahrstreifen einfädeln). `werkzeuge/pruefe_abspieler.py` findet im Abspieler je Variante 0 bis 4 kurze Berührungen, meist ein ausschwenkendes Heck neben einem Pkw.

## Grenzen

- Die Nachfrage ist geschätzt, es gibt keine Zählung. Das Modell zeigt Unterschiede zwischen Varianten, nicht die echten Werte. Gerechnet ist die Morgenspitze.
- Die Wartezeit am Nordarm hängt stark von Lückenannahme (`impatience` 1,0, `jmTimegapMinor` 0,6 s) und Zufluss ab. Beides ist an der beobachteten Schlange am Stopp Nord kalibriert, nicht an einer Zählung.
- Die Ampel im Norden ist mit angenommener Festzeit gerechnet (Umlauf 80 s, Grün 35 s). Echte Signalzeiten, eine Koordinierung oder Anforderung durch Fußgänger können die Pulks stärker oder schwächer machen.
- Die Zone ist ohne Umstellungszeit gerechnet, alle halten sich sofort an rechts vor links. Das ist der Hauptgrund, warum sie nur Vergleich ist.
- Parken bestimmt nur die Geometrie, Ein- und Ausparken und das Begegnungswarten im Ostarm fehlen. Sichtfelder (Grenzmarkierung, Schaltkasten) wirken in SUMO nicht, sie sind gezeichnet und begründet, aber nicht berechnet.
- Der Fehlspur-Anteil mit durchgezogener Linie (8 %) ist eine Annahme.
- Querungen liegen technisch bedingt 0,5 m hinter dem Beginn der Eckausrundung statt in der Ausrundung.
- Radfahrende wechseln in SUMO ohne Sublane-Modell nur ganze Spuren, das Fahren neben Autos und das Einordnen zum Linksabbiegen ist vereinfacht.
- Das Ausholen von Bus und Lkw ist eine Darstellung auf Grundlage der SUMO-Bahn, SUMO selbst kennt es nicht.

## Nächste Schritte

1. Zählung in der Spitzenstunde (Knotenstromzählung, gern per Video) und die Nachfrage in `build.py` ersetzen, auch für den Nachmittag mit Parkern auf der Naumburger West.
2. Unfalldaten der Polizei mit den Konfliktschwerpunkten vergleichen.
3. Wirkung fehlender Blinker auf Wartende als Sensitivität rechnen (in SUMO nur über eine eigene Entscheidungslogik möglich).
