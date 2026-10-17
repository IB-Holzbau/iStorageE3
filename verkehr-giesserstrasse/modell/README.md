# Verkehrsmodell Gießerstraße – Übergabe

Agentenbasiertes Verkehrsmodell der Einmündung Gießerstraße / Naumburger Straße in Leipzig-Plagwitz. Es dient als Anschauungsmaterial für eine Petition an die Stadt Leipzig. Die Seite läuft komplett im Browser als eine einzige HTML-Datei ohne Abhängigkeiten außer Google Fonts.

## Ziel und Kontext

- Gefährliche Einmündung mit abknickender Vorfahrt Süd ↔ West, Tempo 50 auf der Vorfahrt, Tempo 30 auf der Naumburger Straße beidseitig.
- Hauptprobleme: Querung Nord (meistgenutzt, gefährlichste), Geradeausfahrer aus der Linksabbiegespur, unklare Vorfahrt Nord gegen Ost, Radverkehr beim Linksabbiegen West → Nord, Radfahrer auf der Vorfahrt werden vom Stoppschild Nord übersehen, Gelenkbusse in beide Richtungen, Engstelle Ost durch parkende Autos, Kiosk an der Südwestecke zieht Fußgänger aus Norden an.
- Varianten zum Vergleich: Bestand, Rechts vor links, Minikreisel mit überfahrbarer Mitte, plus Markierungen und Umbauten.

## Aufbau

```
build.py                    baut dist/verkehrsmodell_giesserstrasse.html
src/map_static.py.txt       Python-Snippet, zeichnet die statische Karte (Straßen, Gehwege, Schilder, Parken)
src/overlays.svg            statische Überlagerungen für Maßnahmen (Tempo 30, Spurmarkierung, Halteverbot, Stopp Ost)
src/head.html               Titel, Fonts, CSS (Tokens für hell und dunkel)
src/body.html               Seitenaufbau, Bedienelemente, Modellannahmen; Platzhalter {{MAP}}
src/sim.js                  gesamte Simulation und Darstellung
tests/*.py                  Playwright-Prüfskripte (Headless Chromium)
legacy/                     frühere Einzelgrafiken (statische SVG und 5-Szenen-Animation)
```

Bauen: `python3 build.py`. Tests brauchen `pip install playwright` und `python3 -m playwright install chromium`.

Die Karte nutzt Pixelkoordinaten, Maßstab `PX = 15` Pixel pro Meter. Norden ist oben. Wichtige Geometrie:

- Südarm Fahrbahn x 280–490, Gegenrichtung südwärts x ≈ 326, nordwärts einspurig x ≈ 400, kurz vor der Kreuzung Linksabbieger x 381 und Geradeaus x 453.
- Nordarm x 310–445 (südwärts 344, nordwärts 412), Haltlinie y 252.
- Naumburger Straße y 300–420 (westwärts 330 bzw. 342 im Osten, ostwärts 392 bzw. 378 im Osten).
- Haltestelle Süd: Bucht x 462–490, Halteplatz y 760–1040, Sperrfläche y 560–690.
- Kreuzungsmitte für den Minikreisel `KC = (385, 360)`, Fahrradius `KR = 70`, Busradius `KRB = 44`.

## Simulation (src/sim.js)

**Netz** (`buildNet`): Je nach Grundform und Maßnahmen werden alle Fahrwege als SVG-Pfade erzeugt und alle 4 px abgetastet (`sample`: Lage, Richtung, Kurvenradius `rr`, Kurvenschneide-Profil `cut`). Daraus entstehen Querungszonen (`ZR`), Konfliktpunkte zwischen Fahrwegen (`CP`, gemeinsame Abschnitte werden ausgelassen), Haltelinien (`LINE`), Bushalt (`busStopS`) und Ampel-Haltepunkte (`AH`). Routen heißen nach Herkunft und Ziel, zum Beispiel `SW` = Süd nach West, `SNx` = geradeaus aus der Linksabbiegespur, `bSW` = Rad auf dem Radstreifen, `BSW` = Bus, `p…` = Fußgänger.

**Nachfrage** (`DEMAND`): Fahrzeuge pro Stunde je Route und Typ, Schätzwerte für eine Spitzenstunde. Spawnen mit Warteschlange und Mindestabstand.

**Fahrzeuge**
- Längsdynamik: Intelligent Driver Model (IDM) mit `s0 = 2 m`, Folgezeit `T`, Wunschgeschwindigkeit begrenzt durch Tempolimit, Kurvenradius (`v = √(a_lat · R)`, auf der Vorfahrt Süd ↔ West zügiger), Plateau und Kreisel.
- Hindernissuche entlang des eigenen Weges mit Fahrzeugkörpern als Kapseln (`segs`), Reaktionszeit gegenüber Fußgängern und Radfahrenden.
- Querversatz `lat`: In Kurven schneiden Fahrer die Spur, wenn kein Gegenverkehr in der Nähe ist.
- Lenkgeometrie: Vorderachse folgt dem Weg, Hinterachse läuft als Schleppkurve nach (`RIG`, `rigidUpdate`). Gelenkbus und Sattelzug mit Gelenk (`ART`, `artUpdate`), beim Bus Lenkunterstützung an zweiter und dritter Achse über die Anteile `k1` und `k2`.
- Vorfahrt: `mustYield` und `gapOK` je Grundform, Kreisel über `ringGapOK`, Ampel über den Zustand `SIG`.
- Überlappungsschutz `resolveOverlaps`: Wer sich in einen anderen hineinbewegt, wird zurückgesetzt. Gegen Verklemmungen gibt es `push` und kurzzeitig `ghost`.

**Fußgänger**: laufen feste Wege, warten an Zonen auf eine Lücke (Ungeduld, Fehleinschätzung schneller Autos, Abbiegespur wird oft für Abbieger gehalten), schwenkender Blickkegel.

**Fehlverhalten** (Regler): Anteil zu schnell (+15 km/h, dichter auf), Anteil versteht die Vorfahrt nicht (Nord übersieht Rad, Ost ignoriert rechts vor links, Kreisel-Einfahrt ohne Lücke, Geradeaus aus der Abbiegespur).

**Gefahrensituationen** (`event`): nötige Bremsung über 5,5 m/s² oder Abstand unter etwa 0,4 m, nur ab 20 km/h (Fuß und Rad ab 14 km/h). Kategorien: Fußgänger Nord, West, Ost, Radverkehr, unklare Vorfahrt, Bus oder Lkw, Engstelle Ost, sonstige.

**Darstellung**: `render` setzt SVG-Transformationen, Blinker und Handzeichen, `drawMeasures` zeichnet Maßnahmen dynamisch in `#dyn`, statische Teile werden über IDs ein- und ausgeblendet.

**Testzugang**: `window.__t` mit `set({...})`, `run(n)`, `agents()`, `step(dt)`, `counts` für die Playwright-Skripte.

## Stand der Ergebnisse

Eine Modellstunde, Werte schwanken deutlich von Lauf zu Lauf. Bestand etwa 110 bis 140 Gefahrensituationen, Minikreisel etwa 30 bis 50, Radstreifen mit Gehwegnasen etwa 40 bis 80. Das Modell ist nicht kalibriert und zeigt Muster, keine belastbaren Zahlen.

## Offene Punkte und nächste Schritte

1. **Code aufteilen**: `sim.js` in Module (Netz, Agenten, Regeln, Darstellung, Oberfläche) zerlegen, die Kartenerzeugung von exec auf ein echtes Python-Modul oder direkt auf JS umstellen.
2. **Verklemmungen**: `push` und `ghost` sind Notlösungen. Besser wäre eine Reservierung von Konfliktflächen mit fester Reihenfolge.
3. **Querversatz**: Die Spurschneide-Logik prüft nur grob auf Gegenverkehr. Seitliche Abstände zu Parkern und Radfahrenden fehlen.
4. **Kreisel**: Geometrie und Querungen vereinfacht, Bypass und Fahrbahnteiler fehlen.
5. **Kalibrierung**: Verkehrszählung und Unfalldaten der Polizei einpflegen, Nachfrage pro Tageszeit.
6. **Statistik**: mehrere Läufe mit festem Zufallsstartwert, Mittelwert und Streuung je Variante, Export als CSV.
7. **Export für die Petition**: Video oder GIF je Variante, Standbilder mit Legende.
8. **Barrierefreiheit**: Tastaturbedienung prüfen, Kontraste der Kartensymbole.

## Begleitmaterial im Gespräch

- Petitionstext für leipzig.de (Entwurf im Chat), Hinweis auf ausgesetzten Bürgerhaushalt 2027/28.
- `legacy/kreuzung_giesserstrasse.svg`: statische Skizze mit nummerierten Gefahrenstellen.
- `legacy/kreuzung_giesserstrasse_animation.svg`: SMIL-Animation mit fünf Szenen.
