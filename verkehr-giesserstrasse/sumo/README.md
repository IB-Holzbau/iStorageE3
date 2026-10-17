# SUMO-Modell Gießerstraße / Naumburger Straße

Mikroskopische Verkehrssimulation der Kreuzung in Leipzig-Plagwitz mit dem freien Simulator [Eclipse SUMO](https://eclipse.dev/sumo/). Das Modell vergleicht den Bestand mit drei Umbauvarianten und liefert Kennzahlen zu Sicherheit und Wartezeiten für die Bürgerkampagne. Das Browsermodell in `../modell` bleibt das Anschauungsmodell, dieses SUMO-Modell ist die nachvollziehbare Rechengrundlage.

**Abspieler im Browser** in [`grafik/abspieler.html`](grafik/abspieler.html). Die Datei herunterladen und im Browser öffnen, sie läuft ohne Internet (nur die Schrift kommt von Google Fonts). Fünf Minuten der Spitzenstunde je Variante, flüssig mit 60 Bildern je Sekunde, Beinahe-Unfälle blinken als Ringe auf.

| Bestand | Minikreisel |
|---|---|
| ![Bestand](grafik/abspieler_bestand.png) | ![Minikreisel](grafik/abspieler_minikreisel.png) |

## Aufruf

```bash
pip install -r requirements.txt     # SUMO, matplotlib, shapely, pillow
python3 build.py                    # Netze und Nachfrage aller Varianten
python3 run.py                      # 10 Läufe je Variante, etwa 2 Minuten
python3 plots.py                    # Vergleichsdiagramm und Netzbilder nach grafik/
python3 abspieler/export.py         # Browser-Abspieler grafik/abspieler.html
```

Weitere Schalter

- Standard ist der Regelbetrieb, die Busse fahren von Süd nach West. `python3 build.py --bus SN` bildet die derzeitige Baustellenumleitung ab (Naumburger Straße ist Sackgasse, die Busse fahren geradeaus Süd und Nord, so steht es im Oktober 2026 auch in OpenStreetMap).
- `python3 run.py --laeufe 3 --varianten bestand minikreisel` für schnelle Proben.
- `python3 run.py --nur-bericht` schreibt `vergleich.md` aus der vorhandenen CSV neu.
- `python3 werkzeuge/vorfahrt.py netze/bestand.net.xml J` zeigt, wer am Knoten auf wen wartet.
- Ansehen mit Oberfläche geht mit `sumo-gui -n netze/bestand.net.xml -r netze/bestand.rou.xml -a netze/haltestelle.add.xml`.

## Dateien

| Pfad | Inhalt |
|---|---|
| `build.py` | Liest die Geometrie aus `../daten/map.osm` und erzeugt je Variante Netz und Nachfrage |
| `run.py` | Simuliert, wertet aus, schreibt `ergebnisse/kennzahlen.csv` und `ergebnisse/vergleich.md` |
| `plots.py` | Netzbilder, Vergleichsdiagramm, optional GIFs (`--animation`) |
| `abspieler/export.py` | Simuliert je Variante fünf Minuten mit 0,2 s Schrittweite und baut daraus den Abspieler |
| `abspieler/vorlage.html` | Seite und Abspiellogik des Abspielers, die Daten werden beim Export eingesetzt |
| `netze/` | Erzeugte SUMO-Netze (`*.net.xml`), Nachfrage (`*.rou.xml`), Haltestelle |
| `ergebnisse/` | Kennzahlen je Lauf und Vergleichstabelle. Rohdaten unter `roh/` werden nicht eingecheckt |
| `grafik/` | `abspieler.html`, `abspieler_*.png`, `vergleich.png`, `netze.png`, `netz_*.png` |
| `werkzeuge/vorfahrt.py` | Prüfhilfe für die Vorfahrtregeln |

## Modellaufbau

**Geometrie.** Lage und Richtung der vier Arme stammen aus OpenStreetMap (Knoten 60015219). Jeder Arm ist 120 m lang. Der Südarm endet im OSM-Ausschnitt nach 90 m und wird gerade verlängert. Fahrstreifen 3,5 m, Ost nur 2,75 m je Richtung. Parkstreifen laut OSM (Ost beidseitig, West Südseite, Süd Westseite ab etwa 45 m, Nord Westseite ab etwa 16 m) sind als 2 m breite Spur ohne Verkehr enthalten. Sie legen nur Bordstein und Querungslänge fest. Die Engstelle Ost ist so geometrisch sichtbar, seitliche Konflikte im Begegnungsverkehr bildet SUMO aber nicht ab.

**Südarm.** Busbucht 45 bis 70 m vor dem Knoten mit der Haltestelle Naumburger Straße (LVB 0505, Halt 20 s). Auf den letzten 25 m zwei Fahrstreifen, links für Linksabbieger nach West, rechts geradeaus und rechts.

**Vorfahrt im Bestand.** Abknickende Vorfahrt Süd nach West. Nord hat ein Stoppschild (jedes Fahrzeug hält 1 s an der Haltlinie), Ost ist wartepflichtig. Zwischen Nord und Ost gilt rechts vor links, Ost wartet also auf Nord. Wer aus West geradeaus nach Ost fährt, verlässt die Vorfahrtstraße und wartet auf den Strom Süd nach West. Die Regeln sind in `build.py` als Kantenprioritäten und Verbote hinterlegt und mit `werkzeuge/vorfahrt.py` geprüft.

**Querungen.** An allen vier Armen gibt es Querungen ohne Markierung am Knotenrand. Fußgänger warten dort auf eine Lücke.

**Varianten**

| Variante | Änderungen gegenüber Bestand |
|---|---|
| `bestand` | wie oben, Tempo laut OSM (Süd und Nord 50, West 30, Ost ohne Schild also 50) |
| `rvl` | Rechts vor links an allen Armen, Tempo 30 überall, Querungen weiter ohne Markierung |
| `minikreisel` | Kreisfahrbahn 4,5 m breit, etwa 16 m Außendurchmesser, einstreifige Zufahrten, Zebrastreifen an allen Armen etwa 13 m vor der Mitte, Tempo 30 auf den Armen |
| `t30_zebra` | Bestand mit Tempo 30 überall und Zebrastreifen am Nord- und Westarm, um eine Wagenlänge vom Knoten abgesetzt |

**Nachfrage.** Spitzenstunde aus dem Browsermodell (`../modell/src/sim.js`, `DEMAND`). Pkw, Lkw, Sattelzüge und Räder kommen zufällig (Poisson), die Busse fahren im 10-Minuten-Takt je Richtung.

| Gruppe | je Stunde |
|---|---|
| Pkw | 941, davon Süd nach West 260 und West nach Süd 240 |
| Lkw und Sattelzüge | 33 |
| Gelenkbusse 18 m | 12 (Linien 60 und 60E, Regelbetrieb Süd nach West) |
| Rad | 198 |
| Fußgänger | 160 Wege, die je Querung etwa Nord 100, West 50, Süd 30, Ost 30 ergeben (Schätzung nach Beobachtung). Der Strom von Nordost zum Kiosk an der Südwestecke quert erst den Nordarm, dann den Westarm |

**Fahrverhalten.** SUMO-Standardmodell (Krauss) mit `sigma 0.5` und gestreuter Wunschgeschwindigkeit. Wartepflichtige Fahrer werden mit `impatience 0.5` mit der Zeit ungeduldiger und nehmen kleinere Lücken an. Radfahrende fahren auf der Fahrbahn ohne Überholen innerhalb des Fahrstreifens.

## Kennzahlen

| Kennzahl | Definition |
|---|---|
| Fahrzeugkonflikte | SUMO-Gerät SSM, gezählt wenn TTC unter 1,5 s, PET unter 1 s oder DRAC über 3 m/s², jeweils nur ab 15 km/h. Schwer heißt TTC unter 1 s oder PET unter 0,5 s. Getrennt nach Kreuzen und Einbiegen sowie Auffahren |
| Fußgängerkonflikte | Eigene Auswertung der Bewegungsdaten. Eine Person steht auf einer Querung und ein Fahrzeug über 15 km/h müsste stärker als 3 m/s² bremsen, um vor ihr zu halten. Das Fahrzeug folgt dabei seiner Fahrspur auch in Kurven |
| Zeitverlust | Fahrzeit gegenüber freier Fahrt einschließlich Einfahrverzug, wenn die Schlange über den Modellrand reicht |
| Wartezeit Fußgänger | Zeit, die Personen auf ihrem Weg stehen |
| Rückstau | Länge der stehenden Schlange je Zufahrt, Mittel und 95 %-Wert über die Stunde |
| Qualitätsstufe | Einordnung des mittleren Zeitverlusts je Zufahrt in A bis F nach den Grenzen des HBS 2015 für Knoten ohne Ampel. Vereinfacht, am Original prüfen |

Gezählt wird nur die Stunde nach 10 Minuten Einschwingzeit. Jeder Wert ist der Mittelwert aus 10 Läufen mit festen Startwerten 1 bis 10, die Streuung steht dabei.

## Ergebnisse

Die vollständigen Tabellen stehen in [`ergebnisse/vergleich.md`](ergebnisse/vergleich.md).

![Vergleich](grafik/vergleich.png)

Kernaussagen aus 10 Läufen je Variante (Mittelwert je Stunde, Stand mit Bus Süd nach West und neuen Fußgängerzahlen)

| | Bestand | Rechts vor links | Minikreisel | Tempo 30 und Zebra |
|---|---|---|---|---|
| Fahrzeugkonflikte gesamt | 91 | 32 | 19 | 79 |
| davon Kreuzen und Einbiegen | 62 | 23 | 0 | 61 |
| Schwere Fahrzeugkonflikte | 21 | 2 | 0 | 27 |
| Fußgänger auf der Querung bedrängt | 13 | 12 | 17 | 21 |
| Wartezeit Fußgänger in s | 6,5 | 8,1 | 0,0 | 2,1 |
| Zeitverlust Kfz in s | 13 | 8 | 10 | 11 |
| Zufahrt Nord, Zeitverlust Kfz in s und Stufe | 25, C | 8, A | 12, B | 18, B |

Lesart

- Im Bestand entstehen die meisten Konflikte zwischen Fahrzeugen. Ursache sind die Lückensuche am Nordarm und die Abbieger von der abknickenden Vorfahrt.
- Rechts vor links mit Tempo 30 und der Minikreisel senken die Fahrzeugkonflikte deutlich, der Minikreisel bei den kreuzenden Strömen auf null. Im Kreisel bleiben Auffahrkonflikte an den Einfahrten.
- Zebrastreifen senken die Wartezeit der Fußgänger fast auf null. Die Zahl der bedrängten Fußgänger steigt im Modell an den Zebrastreifen, weil SUMO-Fußgänger dort ohne Blick auf den Verkehr losgehen und Fahrzeuge dann kräftig bremsen. Real ist das eher zu hoch angesetzt.
- Tempo 30 mit Zebrastreifen bei sonst gleicher Vorfahrt ändert an den Fahrzeugkonflikten wenig.

## Abspieler

`abspieler/export.py` lässt SUMO je Variante mit Startwert 1 und 0,2 s Schrittweite laufen und zeichnet fünf Minuten nach zehn Minuten Einschwingzeit auf. Positionen werden in Dezimetern als Differenzen gespeichert, der Browser rechnet zwischen den Schritten weich weiter. Fahrzeuge werden aus der Bahn ihrer Front gezeichnet, das Heck folgt der Spur (Schleppkurve), Gelenkbus und Sattelzug knicken am Gelenk. Die Karte entsteht aus dem SUMO-Netz (Fahrbahn, Gehwege, Querungen), den Gebäuden aus `map.osm` und den Parkstreifen. Schilder und Markierungen sind je Variante gesetzt. Die Ringe zeigen dieselben Konflikte wie die Auswertung, nur aus diesem einen Fünf-Minuten-Ausschnitt. In fünf Minuten sind das nur wenige, die Stundenwerte in der Seitenleiste stammen aus den zehn ganzen Läufen.

## Abweichungen zwischen OSM und Beobachtung

| Punkt | OpenStreetMap | Beobachtung oder Browsermodell | Im Modell |
|---|---|---|---|
| Buslinien 60, 60E | geradeaus Süd und Nord auf der Gießerstraße | Süd nach West, derzeit wegen Baustelle umgeleitet (Naumburger Straße Sackgasse) | Regelbetrieb Süd nach West, Umleitung mit `--bus SN` |
| Tempo Ost | kein Schild, also innerorts 50 | Tempo 30 | 50, laut Recherche wurde Tempo 30 für den Ostteil 2024 abgelehnt |
| Vorfahrtschilder, Stoppschild | nicht erfasst | abknickende Vorfahrt Süd und West, Stopp Nord | nach Beobachtung |
| Linksabbiegestreifen Süd | `lane_markings=no` | Linksabbieger und Geradeaus getrennt | zwei Streifen auf 25 m |
| Haltestelle 0505 | Bussteig an der Ostseite des Südarms, 50 bis 70 m vor dem Knoten | Busbucht | Bucht 45 bis 70 m |
| Kiosk Südwestecke | an der Südwestecke vermutlich das Café „Lebensmittel A. Prinz“, weiter südlich der Spätkauf „Spätition“ | Kiosk | Ziel der Fußwege etwa 15 m westlich der Ecke |

Vor einer Veröffentlichung sollte jemand vor Ort prüfen, welche Schilder stehen, ob die Linksabbiegespur markiert ist und wo die Busse wirklich abbiegen.

## Grenzen

- Die Nachfrage ist geschätzt, es gibt keine Zählung. Das Modell zeigt Unterschiede zwischen Varianten, nicht die echten Werte.
- Die Wartezeit am Nordarm hängt stark von der Lückenannahme ab. Im Bestand ergibt `impatience 0` eine Überlastung mit über 500 s Zeitverlust, 0.3 rund 67 s, 0.5 rund 33 s und 0.6 rund 23 s (je 5 Läufe). Gewählt ist 0.5. Eine grobe Abschätzung nach dem HBS-Verfahren mit üblichen Grenzzeitlücken landet in derselben Größenordnung, ist aber nicht am Original geprüft. Eine Zählung mit Wartezeitmessung würde diesen Wert festlegen.
- Parkstreifen bestimmen nur die Geometrie. Ein- und Ausparken und die Enge im Begegnungsverkehr Ost bildet SUMO nicht ab.
- An unmarkierten Querungen warten SUMO-Fußgänger auf eine Lücke. An Zebrastreifen gehen sie ohne Blick auf den Verkehr los, deshalb sind Fußgängerkonflikte an Zebrastreifen eher überschätzt.
- Der Minikreisel ist vereinfacht. Busse fahren die Kreisfahrbahn wie Pkw, das Überfahren der Mitte und die Schleppkurve fehlen. Die Ablenkung, die real bremst, ersetzt Tempo 30 auf den Armen.
- Fehlverhalten aus dem Browsermodell (Geradeausfahren aus der Linksabbiegespur, Übersehen von Radfahrenden) ist nicht enthalten.
- SSM meldet zusätzlich Überschneidungen von Fahrzeugumrissen im Knoteninneren (Typ 111). Das sind meist Geometrieeffekte der Wartepositionen. Sie stehen getrennt in der Tabelle und sind nicht mitgezählt.
- Fußgänger wählen den kürzesten Weg. Sehr nah an den Netzenden würden sie um das Netzende herumlaufen, deshalb starten die Wege weit genug innen.

## Nächste Schritte

1. Zählung in der Spitzenstunde (Knotenstromzählung, gern per Video) und die Nachfrage in `build.py` ersetzen.
2. Vor-Ort-Prüfung der Punkte aus der Abweichungstabelle.
3. Unfalldaten der Polizei einholen und mit den Konfliktschwerpunkten vergleichen.
4. Weitere Varianten, zum Beispiel Radfahrstreifen mit Gehwegnasen oder Diagonalsperre, als neue Fälle in `baue_variante` ergänzen.
