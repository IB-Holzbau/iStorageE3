# Software für Verkehrssimulation und Verkehrsanalyse an einer innerstädtischen Kreuzung

Stand der Recherche Oktober 2026. Ziel ist die Abbildung des Ist-Zustands der Kreuzung Gießerstraße / Naumburger Straße und der Vergleich von Varianten (Spuraufteilung, Signalprogramme, Kreisverkehr, Radverkehrsführung, Fußgängerquerungen). Die Ergebnisse sollen für eine Bürgerkampagne verständlich aufbereitet werden. Gearbeitet wird in einem Linux-Container mit Python.

## 1. Kurzfazit

Für eine Bürgerinitiative ohne Lizenzbudget ist **Eclipse SUMO** das einzige Werkzeug, das alle Anforderungen gleichzeitig erfüllt. Es ist frei (EPL 2.0), läuft headless unter Linux, lässt sich per `pip install eclipse-sumo` installieren (auf PyPI aktuell Version 1.28.0), importiert OpenStreetMap und liefert mikroskopische Kennzahlen wie Wartezeit, Zeitverlust, Rückstaulänge und Durchsatz pro Fahrstreifen. HBS-Qualitätsstufen gibt SUMO nicht direkt aus. Sie lassen sich aber aus den simulierten mittleren Wartezeiten ableiten und sollten zusätzlich mit einer eigenen, transparenten Python-Umsetzung der HBS-Formblätter gegengerechnet werden.

Die Verkehrsmengen als wichtigste Eingangsgröße erhebt man am besten selbst per Videozählung (Ultralytics YOLO plus `supervision`, offline und datenschutzfreundlich) und ergänzt sie bei Bedarf durch einen Telraam-Sensor für Langzeitwerte. Für die Kampagne eignen sich Videos aus `sumo-gui`, Karten in QGIS oder Kepler.gl und Straßenquerschnitte aus Streetmix.

Kommerzielle Werkzeuge (PTV Vissim, Aimsun, LISA, KNOBEL/KNOSIMO) sind der fachliche Standard in Ingenieurbüros und Verwaltungen. Sie sind für die Initiative nur über Studierende mit Studentenlizenz nutzbar, und deren Lizenzen schließen nicht akademische Nutzung in der Regel aus. Sie dienen hier vor allem zur Einordnung, weil ein Gutachten der Stadt sehr wahrscheinlich mit einem dieser Programme erstellt wurde.

## 2. Bewertungsübersicht

Legende für Eignung ●●● sehr gut, ●● brauchbar, ● kaum geeignet.

| Werkzeug | Lizenz | Einstieg | Eignung Kreuzung | Linux / headless | Rolle im Projekt |
|---|---|---|---|---|---|
| Eclipse SUMO (netedit, netconvert, TraCI, sumolib) | EPL 2.0, frei | mittel | ●●● | ja, voll | Kernwerkzeug Simulation |
| sumo-web3d | EPL 2.0, frei | hoch | ● | ja, aber veraltet | nicht empfohlen |
| MATSim | GPL, frei | hoch | ● | ja (Java) | nicht passend, Netzmaßstab |
| CityFlow | Apache 2.0, frei | mittel | ● | ja (Docker, Python) | nur für KI-Ampelforschung |
| A/B Street | Apache 2.0, frei | niedrig | ●● (Anschauung) | eingeschränkt | optional für Laienvisualisierung |
| MovSim / traffic-simulation.de | Open Source (GPL) | niedrig | ● | ja (Java) bzw. Browser | Erklärgrafik, nicht für Analyse |
| PTV Vissim | proprietär, Studentenversion | hoch | ●●● | nein, Windows | Einordnung, Fachstandard |
| Aimsun Next | proprietär, Studentenversion | hoch | ●●● | eingeschränkt | Einordnung |
| LISA (Schlothauer & Wauer) | proprietär | mittel | ●●● (Signalplanung) | nein, Windows | Einordnung, Fachstandard LSA |
| KNOBEL / KNOSIMO / AMPEL / KREISEL (BPS) | proprietär | mittel | ●●● (HBS) | nein, Windows | Einordnung, Fachstandard HBS |
| Eigene HBS-Berechnung in Python | selbst, frei | mittel | ●●● (Kennzahlen) | ja | Plausibilisierung, QSV |
| Ultralytics YOLO + supervision | AGPL 3.0 bzw. MIT | mittel | ●●● (Zählung) | ja, auch ohne GPU (langsam) | Videozählung |
| OpenDataCam | MIT | mittel | ●● | ja, Docker mit NVIDIA GPU | Alternative Videozählung live |
| Telraam S2 | Hardware proprietär, Daten offen | niedrig | ●● (Querschnitt) | API nutzbar | Langzeitzählung je Arm |
| Streetmix | BSD 3, frei | sehr niedrig | ●●● (Querschnitt) | Webanwendung | Querschnitte Ist und Varianten |
| Kepler.gl | MIT | niedrig | ●● | ja (Python-Paket, Browser) | animierte Karten |
| QGIS | GPL, frei | mittel | ●●● (Karten) | ja, auch `qgis_process` headless | Lagepläne, Plakate |

## 3. Simulationswerkzeuge im Einzelnen

### 3.1 Eclipse SUMO

**Lizenz und Stand.** Eclipse Public License 2.0, entwickelt vom DLR unter dem Dach der Eclipse Foundation. Im Jahr 2026 erschienen die Versionen 1.26.0 (Januar, Schwerpunkt öffentlicher Verkehr und GTFS-Import) und 1.27.0 (Mai, geänderte Standardwerte für Einfahrgeschwindigkeit und Fahrstreifenwahl, was höhere Einspeiseraten ergibt). Auf PyPI steht inzwischen 1.28.0 bereit. Wichtig für die Praxis ist, dass sich Standardwerte zwischen Versionen ändern können, daher sollte die verwendete Version im Projekt fest notiert werden.

**Bestandteile.**
* `netconvert` erzeugt aus OSM-Daten ein simulierbares Netz mit Fahrstreifen, Abbiegebeziehungen und Lichtsignalanlagen. Mit den Skripten `osmGet.py` und `osmBuild.py` geht das komplett headless. Der `osmWebWizard.py` ist bequemer, braucht aber einen Browser.
* `netedit` ist der grafische Netzeditor. Damit korrigiert man Fahrstreifen, Haltlinien, Abbiegebeziehungen, Fußgängerüberwege, Radwege und Signalprogramme und baut auch einen Kreisverkehr. Netedit braucht eine grafische Oberfläche. Im Container geht das über X-Forwarding oder VNC, alternativ arbeitet man lokal am Rechner und legt die Dateien ins Repository. Fast alles lässt sich auch direkt in den XML-Dateien (plain XML von netconvert) bearbeiten, was für versionierte Varianten sogar besser ist.
* `sumo` (Kommandozeile) und `libsumo` simulieren ohne Oberfläche und sind schnell genug für viele Wiederholungen mit unterschiedlichen Zufallszahlen.
* `sumo-gui` zeigt die Simulation an und kann Bildschirmfotos und Bildfolgen für Videos speichern. Unter Linux headless funktioniert das mit `xvfb-run` und anschließendem Zusammenfügen per `ffmpeg`.
* TraCI und `sumolib` sind die Python-Schnittstellen. Damit lassen sich Ampeln während der Simulation steuern, Werte abgreifen und Ausgabedateien auswerten.
* Für die Nachfrage aus Zählwerten ist `routeSampler.py` das passende Werkzeug. Es erzeugt Fahrzeugrouten so, dass gezählte Abbiegeströme und Querschnittswerte möglichst genau getroffen werden. Alternativen sind `jtrrouter` (Abbiegewahrscheinlichkeiten) und `flowrouter.py`.

**Eignung für eine Kreuzung.** Sehr gut. SUMO bildet einzelne Fahrstreifen, Haltlinien, Abbiegekonflikte, Fußgänger auf Überwegen, Radverkehr auf eigenen Streifen und feste oder verkehrsabhängige Signalprogramme ab. Varianten wie geänderte Spuraufteilung, geschützte Linksabbieger, Rundum-Grün für Fußgänger oder ein Kreisverkehr sind modellierbar. Grenzen bestehen beim detaillierten Verhalten von Radfahrenden im Mischverkehr und bei Fußgängern abseits von Überwegen. Hier vereinfacht SUMO stärker als Vissim.

**Datenbedarf.** Netzgeometrie (OSM, vor Ort geprüft), Knotenstromzählung in der Spitzenstunde getrennt nach Kfz, Lkw, Rad und Fuß, Signalprogramm des Ist-Zustands (Umlaufzeit, Phasenfolge, Grünzeiten, idealerweise der Signalzeitenplan der Stadt, sonst per Video gestoppt), zulässige Geschwindigkeit und gegebenenfalls Straßenbahn- oder Busfahrpläne.

**Kennzahlen.** Über Ausgabedateien stehen unter anderem zur Verfügung
* `tripinfo-output` mit Wartezeit, Zeitverlust und Anzahl der Halte je Fahrzeug, Radfahrer und Fußgänger,
* `queue-output` sowie Detektoren vom Typ E2 (Fahrstreifenbereich) mit Rückstaulänge je Fahrstreifen und Zeitschritt,
* E1-Detektoren (Induktionsschleife) und `edgeData` bzw. `laneData` mit Durchsatz, Belegung und mittlerer Geschwindigkeit,
* E3-Detektoren für mittlere Durchfahrtszeiten zwischen definierten Punkten,
* Emissionsausgaben nach HBEFA und das SSM-Modul mit Ersatzmaßen für Verkehrssicherheit (Konfliktzählungen, Zeit bis zur Kollision).

**HBS-Bezug.** SUMO berechnet keine Qualitätsstufen. Man ordnet die simulierte mittlere Wartezeit je Fahrstreifen oder Strom den Grenzwerten des HBS zu (siehe Abschnitt 4). Das ist methodisch eine Näherung und ersetzt keinen formalen HBS-Nachweis, ist aber gut nachvollziehbar.

**Aufwand.** Für eine einzelne Kreuzung realistisch zwei bis vier Arbeitstage bis zu einem kalibrierten Ist-Modell, wenn Zähldaten vorliegen. Jede weitere Variante kostet dann wenige Stunden. Die Dokumentation und die Tutorials sind umfangreich.

Quellen
[SUMO Download](https://sumo.dlr.de/Download) ·
[SUMO Dokumentation](https://sumo.dlr.de/docs/) ·
[Tutorials](https://sumo.dlr.de/docs/Tutorials/index.html) ·
[OSM-Import](https://sumo.dlr.de/docs/Networks/Import/OpenStreetMap.html) ·
[netedit](https://sumo.dlr.de/docs/Netedit/index.html) ·
[routeSampler](https://sumo.dlr.de/docs/Tools/Turns.html#routesampler) ·
[Ausgabedateien](https://sumo.dlr.de/docs/Simulation/Output/index.html) ·
[TraCI](https://sumo.dlr.de/docs/TraCI.html) ·
[Changelog](https://sumo.dlr.de/docs/ChangeLog.html) ·
[eclipse-sumo auf PyPI](https://pypi.org/project/eclipse-sumo/) ·
[Eclipse Newsroom zu SUMO 1.25](https://newsroom.eclipse.org/node/43089) ·
[Wikipedia SUMO](https://en.wikipedia.org/wiki/Simulation_of_Urban_MObility)

### 3.2 sumo-web3d

Webbasierte 3D-Darstellung von SUMO-Simulationen über TraCI und three.js, ursprünglich von Sidewalk Labs. Lizenz EPL 2.0. Das Projekt wurde für SUMO 0.31 gebaut, die letzte Aktivität liegt Jahre zurück, und schon für SUMO 1.7 war die Kompatibilität unklar. Für 2026 ist das nicht mehr empfehlenswert. Besser sind Videos aus `sumo-gui` oder ein Export der Fahrzeugbahnen (`fcd-output`) nach Kepler.gl oder in eine eigene Web-Darstellung.

Quellen
[sumo-web3d auf GitHub](https://github.com/sidewalklabs/sumo-web3d) ·
[Hinweis zur Kompatibilität in der sumo-user Liste](https://www.eclipse.org/lists/sumo-user/msg03052.html)

### 3.3 MATSim

Agentenbasierte Verkehrsnachfragesimulation in Java, GPL-lizenziert, läuft unter Linux headless. MATSim modelliert ganze Städte mit Tagesplänen von Personen und einer stark vereinfachten Warteschlangenphysik. Fahrstreifen, Abbiegekonflikte und Signalphasen an einer einzelnen Kreuzung bildet es nicht im benötigten Detail ab. Für die Fragestellung der Initiative ist MATSim ungeeignet. Interessant wäre es höchstens, wenn man Verlagerungseffekte im ganzen Stadtteil abschätzen wollte, und das wäre ein eigenes, großes Projekt.

Quellen
[matsim.org](https://www.matsim.org/) ·
[MATSim auf GitHub](https://github.com/matsim-org/matsim-libs)

### 3.4 CityFlow

Schneller mikroskopischer Simulator in C++ mit Python-Schnittstelle, Apache 2.0, entwickelt für Forschung zu lernenden Ampelsteuerungen (Reinforcement Learning). Läuft unter Linux und per Docker. Das Repository ist nicht archiviert, die Aktivität ist aber gering. Geometrie, Fußgänger und Radverkehr sind stark vereinfacht, ein OSM-Import mit realistischer Spuraufteilung fehlt weitgehend, und Kennzahlen zur Verkehrsqualität nach HBS gibt es nicht. Nicht empfohlen.

Quellen
[CityFlow Dokumentation](https://cityflow.readthedocs.io/en/latest/introduction.html) ·
[CityFlow auf GitHub](https://github.com/cityflow-project/CityFlow) ·
[Projektmetadaten bei ecosyste.ms](https://ost.ecosyste.ms/projects/20143)

### 3.5 A/B Street

Spielerische Verkehrssimulation auf OSM-Basis in Rust, Apache 2.0, ausdrücklich für Bürgerbeteiligung gedacht. Man kann Fahrstreifen umwidmen, Ampeln ändern und sieht sofort die Wirkung. Der Hauptsimulator ist laut README im Jahr 2025 in einen Wartungsmodus übergegangen (letzte Version 0.3.49), die Entwickler konzentrieren sich auf Nachfolgewerkzeuge wie das Low-Traffic-Neighbourhood-Werkzeug und die Bibliothek osm2streets. Für Deutschland müssen Karten selbst importiert werden, die Nachfrage ist synthetisch und nicht an echte Zählwerte kalibriert, und belastbare Kennzahlen für eine Petition liefert A/B Street nicht. Headless-Betrieb ist nur eingeschränkt vorgesehen. Brauchbar als niedrigschwellige Anschauung in einer Veranstaltung, nicht als Analysegrundlage. Die Bibliothek osm2streets und der zugehörige Street Explorer sind nützlich, um die Fahrstreifen aus OSM schnell visuell zu prüfen.

Quellen
[A/B Street auf GitHub mit 2025 Update](https://github.com/a-b-street/abstreet) ·
[OSM-Wiki zu A/B Street](https://wiki.openstreetmap.org/wiki/AB_Street) ·
[Vortrag SotM 2021 zu A/B Street für Verkehrsaktivismus](https://pretalx.com/sotm2021/talk/JNVWZS/) ·
[osm2streets](https://github.com/a-b-street/osm2streets)

### 3.6 MovSim und traffic-simulation.de

MovSim ist ein fahrstreifenbasierter Forschungssimulator in Java mit XML-Konfiguration und CSV-Ausgabe, entwickelt im Umfeld der TU Dresden (Treiber, Kesting). Das Hauptprojekt ist kaum noch aktiv. Für reale Kreuzungsgeometrien und Signalprogramme fehlt die Werkzeugkette. Die verwandte Browser-Anwendung traffic-simulation.de ist aber hervorragend, um in der Kampagne grundlegende Effekte zu erklären, etwa Stauwellen oder die Wirkung einer Fahrstreifenreduktion. Für die eigentliche Analyse nicht geeignet.

Quellen
[MovSim auf GitHub](https://github.com/movsim/movsim) ·
[traffic-simulation.de Quellcode](https://github.com/movsim/traffic-simulation-de) ·
[traffic-simulation.de](https://traffic-simulation.de/) ·
[CIVITAS Werkzeugverzeichnis zu MovSim](https://civitas.eu/tool-inventory/movsim)

### 3.7 PTV Vissim (zur Einordnung)

Proprietärer Marktstandard für mikroskopische Simulation in Deutschland, Windows. Kommunale Gutachten zu innerstädtischen Knotenpunkten werden häufig mit Vissim erstellt, oft kombiniert mit einer HBS-konformen Auswertung. Die kostenlose Studentenversion ist auf Lehre und akademische Forschung beschränkt, auf ein Netz von etwa 1 km mal 1 km und auf 600 Sekunden Simulationszeit begrenzt und gilt laut PTV für ein Jahr (andere PTV-Seiten nennen sechs Monate). Eine einzelne Kreuzung passt in die Netzgröße, 600 Sekunden reichen aber nicht für eine Spitzenstunde. Die kommerzielle Testversion (30 Tage) ist für gewerbliche Interessenten gedacht. Für eine Bürgerinitiative ist Vissim daher praktisch nicht nutzbar. Gut zu wissen ist es trotzdem, weil man so die Methodik eines städtischen Gutachtens nachvollziehen und gezielt nachfragen kann.

Quellen
[PTV Vissim Studentenversion](https://www.ptvgroup.com/en/products/ptv-vissim/student-version) ·
[PTV Thesis-Lizenz](https://www.ptvgroup.com/en/about/academia/thesis-license) ·
[PTV Vissim Demo](https://www.ptvgroup.com/en-us/products/ptv-vissim/demo)

### 3.8 Aimsun Next (zur Einordnung)

Proprietäre Software für mikro, meso und makroskopische Modelle. Die Studentenversion hat den Funktionsumfang der Expert-Edition, ist auf 100 Knoten und 200 km Fahrstreifen begrenzt, an einen Rechner gebunden und nur für Lehrzwecke zugelassen. Einzelne Bachelorstudierende können sie nicht selbst beantragen, das läuft über Lehrende. Für Masterarbeiten und Promotionen gibt es eine Postgraduate-Edition. Eine kommerzielle oder politische Nutzung der Modelle schließen die Bedingungen aus. Für die Initiative also nur denkbar, wenn eine studentische Abschlussarbeit an der Kreuzung entsteht.

Quellen
[Aimsun Student Edition](https://www.aimsun.com/academic/student-edition/) ·
[Aimsun Studentenlizenzbedingungen](https://www.aimsun.com/student-license-terms-conditions/) ·
[Aimsun Postgraduate Edition](https://www.aimsun.com/aimsun-next/academic/postgraduate-edition/)

### 3.9 LISA (Signalplanung)

LISA von Schlothauer & Wauer ist in Deutschland ein verbreitetes Programm für die Planung von Lichtsignalanlagen. Es berechnet Zwischenzeiten nach RiLSA, erstellt Signalzeitenpläne und Phasenfolgen und bewertet die Verkehrsqualität nach HBS. Proprietär, Windows, kostenpflichtig. Eine freie Alternative mit gleichem Funktionsumfang gibt es nicht. Für die Initiative relevant ist vor allem, dass Signalzeitenpläne der Stadt häufig als LISA-Ausdruck vorliegen. Diese Pläne kann man über eine Anfrage nach Informationsfreiheits- oder Transparenzgesetz anfordern und dann in SUMO nachbauen. Zwischenzeiten für eigene Varianten sollte man nach RiLSA überschlägig selbst rechnen und als Annahme kennzeichnen.

Quellen
[Schlothauer & Wauer LISA](https://www.schlothauer.de/) (Herstellerseite war bei der Recherche nicht erreichbar, Angaben aus Fachkenntnis, bitte prüfen) ·
[FragDenStaat für Anfragen nach Signalzeitenplänen](https://fragdenstaat.de/)

### 3.10 HBS-Rechner für Knotenpunkte (KNOBEL, KNOSIMO, AMPEL, KREISEL, Excel)

Das maßgebliche Regelwerk ist das Handbuch für die Bemessung von Straßenverkehrsanlagen, Ausgabe 2015 (FGSV 299), Teil S für Stadtstraßen mit eigenen Kapiteln für Knotenpunkte mit Lichtsignalanlage, ohne Lichtsignalanlage und Kreisverkehre. Eine neue Gesamtausgabe konnte in der Recherche nicht belegt werden. Es gibt Forschung zur Neukalibrierung der LSA-Verfahren, daher sollte man vor einer Veröffentlichung beim FGSV-Verlag den aktuellen Stand prüfen.

* **KNOBEL** (Knotenpunkte ohne Lichtsignalanlage nach HBS), **KNOSIMO** (Simulation von Knotenpunkten ohne LSA), **KREISEL** (Kreisverkehre) und **AMPEL** (Knotenpunkte mit LSA) stammen von der BPS GmbH in Bochum. Sie sind proprietär, laufen unter Windows und sind bei Ingenieurbüros und Behörden verbreitet. Für eine Bürgerinitiative sind sie wegen der Kosten kaum erreichbar.
* **Excel-Formblätter.** Das HBS selbst enthält Formblätter für die Handrechnung. Viele Büros und Hochschulen nutzen eigene Excel-Umsetzungen, eine frei lizenzierte und gepflegte Version wurde in der Recherche nicht gefunden.
* **Empfehlung.** Eine kleine eigene Python-Umsetzung der benötigten HBS-Verfahren (Kapazität und mittlere Wartezeit je Fahrstreifen bei LSA, Kapazität von Nebenströmen bei Vorfahrtsregelung, Kapazität von Kreisverkehrszufahrten) ist mit dem HBS-Buch in einigen Tagen machbar und hat den Vorteil vollständiger Transparenz. Sie dient als zweite, unabhängige Säule neben der Simulation.

Quellen
[HBS 2015 Einführungsschreiben Bayern mit Inhaltsübersicht](https://www.mobilitaet.bayern.de/assets/stmi/vum/strasse/planung/49_hbs_2015.pdf) ·
[TRID Aktualisierung der Verfahren zur Bewertung der Verkehrsqualität an Knotenpunkten mit LSA](https://trid.trb.org/View/2573179) ·
[TRID Zur verkehrstechnischen Berechnung von Knotenpunkten mit LSA nach HBS 2015](https://trid.trb.org/View/1506180) ·
[Firmenprofil BPS GmbH Bochum](https://app.implisense.com/en/companies/bps-gmbh-bochum--DEB6KXIXZU68) ·
[FGSV Verlag](https://www.fgsv-verlag.de/)

## 4. Qualitätsstufen nach HBS aus Simulationsergebnissen ableiten

Das HBS bewertet Knotenpunkte über Qualitätsstufen des Verkehrsablaufs (QSV) von A bis F. Maßgebend ist für den Kfz-Verkehr die mittlere Wartezeit je Fahrstreifen oder Strom, Stufe F gilt zusätzlich immer dann, wenn die Nachfrage die Kapazität übersteigt (Auslastungsgrad über 1). Die folgende Tabelle gibt die nach unserem Kenntnisstand gültigen Grenzwerte des HBS 2015 für Stadtstraßen wieder. Vor einer Veröffentlichung müssen die Werte am Originaltext geprüft werden, ebenso die gesonderten Grenzwerte für Fuß und Radverkehr an Lichtsignalanlagen.

| QSV | Knotenpunkt mit LSA, Kfz, mittlere Wartezeit | Knotenpunkt ohne LSA und Kreisverkehr, mittlere Wartezeit |
|---|---|---|
| A | bis 20 s | bis 10 s |
| B | bis 35 s | bis 20 s |
| C | bis 50 s | bis 30 s |
| D | bis 70 s | bis 45 s |
| E | bis 100 s | über 45 s |
| F | über 100 s oder Auslastung über 1 | Auslastung über 1 |

Praktisches Vorgehen mit SUMO ist, die Wartezeit je Fahrzeug aus `tripinfo-output` den Zufahrtsfahrstreifen zuzuordnen (über die Route oder über E2-Detektoren je Fahrstreifen), über mehrere Simulationsläufe mit verschiedenen Zufallszahlen zu mitteln und erst dann einer Stufe zuzuordnen. Die SUMO-Größe `waitingTime` zählt nur echten Stillstand, `timeLoss` den gesamten Zeitverlust gegenüber freier Fahrt. Für den Vergleich mit dem HBS ist `timeLoss` meist die passendere Größe. Die Wahl sollte offen dokumentiert werden.

## 5. Verkehrszählung per Video und Sensor

### 5.1 Ultralytics YOLO mit supervision (empfohlen)

Ultralytics stellt aktuelle YOLO-Modelle zur Objekterkennung und Verfolgung bereit (Paket `ultralytics`, auf PyPI Version 8.4.x), Lizenz AGPL 3.0. Das Paket `supervision` von Roboflow (MIT, Version 0.31) liefert fertige Bausteine für Zähllinien und Zählzonen. Damit lassen sich aus einem Video der Kreuzung Abbiegeströme nach Fahrzeugklassen zählen, indem man für jede Zufahrt und Ausfahrt eine Linie definiert und die Wege der verfolgten Objekte zuordnet. Läuft unter Linux headless in Python, mit GPU deutlich schneller, auf CPU für eine Stunde Video aber in vertretbarer Zeit mit kleinen Modellen. Für die AGPL gilt, dass reine interne Nutzung unkritisch ist. Erst wer die Software als Dienst anbietet, muss den Quellcode offenlegen.

Hinweise zur Qualität. Eine erhöhte Kameraposition mit Blick auf die ganze Kreuzung ist entscheidend (etwa aus einem Fenster mit Einverständnis der Bewohner). Radfahrende und Fußgänger werden bei Verdeckung schlechter erkannt. Eine Stichprobe von 15 Minuten sollte von Hand nachgezählt werden, um die Fehlerquote anzugeben.

Datenschutz. Videoaufnahmen im öffentlichen Raum berühren die DSGVO. Empfehlenswert ist eine Aufnahme mit geringer Auflösung oder aus großer Höhe, Auswertung lokal, Löschen der Rohvideos nach der Zählung und Veröffentlichung nur aggregierter Zahlen.

Quellen
[Ultralytics Dokumentation](https://docs.ultralytics.com/) ·
[Ultralytics Objektzählung](https://docs.ultralytics.com/guides/object-counting/) ·
[ultralytics auf PyPI](https://pypi.org/project/ultralytics/) ·
[supervision Dokumentation](https://supervision.roboflow.com/) ·
[supervision auf PyPI](https://pypi.org/project/supervision/)

### 5.2 OpenDataCam

Offenes Werkzeug zum Zählen und Verfolgen von Objekten in Kamerabildern auf Basis von YOLO, ursprünglich vom moovel lab, MIT-Lizenz. Es bietet eine Weboberfläche zum Ziehen von Zähllinien und einen Datenexport per API. Installation per Docker, für akzeptable Geschwindigkeit wird eine NVIDIA-GPU mit CUDA oder ein Jetson-Gerät benötigt. Die mobile App ist archiviert, das Hauptprojekt besteht weiter (zuletzt Version 3.x). OpenDataCam passt gut für eine Live-Zählung vor Ort mit einem Jetson, im Container ohne GPU ist die Variante mit Ultralytics und supervision einfacher.

Quellen
[OpenDataCam auf GitHub](https://github.com/opendatacam/opendatacam) ·
[OpenDataCam 2.0 Projektseite](https://www.benedikt-gross.de/projects/opendatacam-2) ·
[opendatacam-mobile (archiviert)](https://github.com/opendatacam/opendatacam-mobile)

### 5.3 Telraam

Telraam ist ein Bürgerwissenschaftsprojekt aus Belgien. Der Sensor S2 wird innen an ein Fenster zur Straße geklebt, zählt und klassifiziert Fußgänger, Radfahrende, Pkw und Lkw per Kamera und KI-Chip und überträgt nur anonyme Zählwerte im 15-Minuten-Takt. Die Daten sind öffentlich auf einer Karte und über eine API abrufbar, in R gibt es das Paket `telraamStats`. Telraam zählt einen Straßenquerschnitt, keine Abbiegeströme. Ein Sensor je Zufahrt ergibt aber gute Langzeitwerte für Tagesganglinien, Wochentagsunterschiede und Spitzenstunden. In Berlin wurde das Verfahren 2023 im Projekt Berlin zählt Mobilität breit eingesetzt.

Quellen
[telraam.net](https://telraam.net/) ·
[Telraam API Dokumentation](https://telraam-api.net/) ·
[telraamStats in R](https://rdocumentation.org/packages/telraamStats/versions/1.1.2) ·
[TechCrunch zum Telraam-Sensor](https://techcrunch.com/?p=2543774)

### 5.4 Weitere Datenquellen

Manuelle Knotenstromzählung mit Strichliste oder einer Zähl-App bleibt der Goldstandard für die Kalibrierung und ist für eine Spitzenstunde mit drei bis vier Personen gut machbar. Vorhandene Zählungen, Signalzeitenpläne und Unfalldaten der Stadt lassen sich anfragen. Der Unfallatlas der statistischen Ämter zeigt polizeilich erfasste Unfälle mit Personenschaden und eignet sich als Sicherheitsargument.

Quellen
[Unfallatlas](https://unfallatlas.statistikportal.de/)

## 6. Visualisierung

### 6.1 Streetmix

Webanwendung zum Zeichnen von Straßenquerschnitten aus fertigen Bausteinen (Gehweg, Radweg, Fahrstreifen, Baumstreifen, Haltestelle), Open Source unter BSD-3. Ideal, um Ist-Zustand und Varianten für Laien vergleichbar zu machen, etwa vier Kfz-Streifen gegen zwei Kfz-Streifen plus geschützte Radwege. Läuft im Browser, Bilder lassen sich exportieren. Für die Kreuzung selbst (Draufsicht) ist Streetmix nicht gedacht, dafür QGIS oder ein Zeichenprogramm.

Quellen
[streetmix.net](https://streetmix.net/) ·
[Streetmix auf GitHub](https://github.com/streetmix/streetmix)

### 6.2 Kepler.gl

Werkzeug von Uber für große Geodaten im Browser, MIT-Lizenz, mit Python-Paket `keplergl` für Jupyter. Aus dem SUMO-Export `fcd-output` (Position aller Fahrzeuge je Zeitschritt) lässt sich mit `traceExporter.py` oder einem eigenen Skript GeoJSON erzeugen, das Kepler.gl als animierte Fahrzeugbewegung auf der Karte abspielt. Gut für eine eingebettete interaktive Karte auf der Kampagnenseite. Die HTML-Ausgabe kann headless erzeugt werden, angesehen wird sie im Browser.

Quellen
[kepler.gl](https://kepler.gl/) ·
[kepler.gl auf GitHub](https://github.com/keplergl/kepler.gl) ·
[SUMO traceExporter](https://sumo.dlr.de/docs/Tools/TraceExporter.html)

### 6.3 QGIS

Freies GIS unter GPL, läuft unter Linux, mit `qgis_process` und PyQGIS auch skriptbar ohne Oberfläche. SUMO-Netze und Ergebnisse lassen sich über `net2geojson.py` bzw. `edgeDataFromFlow` und eigene Skripte als GeoJSON exportieren und in QGIS als Lageplan mit farbigen Fahrstreifen nach Qualitätsstufe oder Rückstaulänge darstellen. Zusammen mit Luftbildern (etwa den offenen Digitalen Orthophotos des jeweiligen Landes) entstehen druckfähige Karten für Plakate und Flyer.

Quellen
[qgis.org](https://qgis.org/) ·
[qgis_process Dokumentation](https://docs.qgis.org/latest/en/docs/user_manual/processing/standalone.html) ·
[SUMO net2geojson](https://sumo.dlr.de/docs/Tools/Net.html#net2geojsonpy)

### 6.4 Weitere Bausteine

Diagramme der Kennzahlen (Wartezeit je Strom, Rückstau über die Zeit, Vergleich der Varianten) entstehen am einfachsten mit matplotlib oder Plotly in Python. Videos der Simulation nimmt man mit `sumo-gui` unter `xvfb-run` als Bildfolge auf und fügt sie mit `ffmpeg` zusammen. Für die Lage der Fahrstreifen aus OSM ist der Street Explorer von osm2streets eine schnelle Kontrolle.

Quellen
[SUMO Screenshots und Videos aus sumo-gui](https://sumo.dlr.de/docs/sumo-gui.html#screenshots) ·
[osm2streets Street Explorer](https://a-b-street.github.io/osm2streets/)

## 7. Empfohlener Workflow

1. **Bestand erfassen.** Vor Ort Fahrstreifen, Markierungen, Radwege, Überwege, Haltlinien und Signalgeber fotografieren und mit OSM abgleichen, Fehler direkt in OSM korrigieren. Signalprogramm per Video stoppen und parallel bei der Stadt den Signalzeitenplan anfragen.
2. **Verkehr zählen.** Knotenstromzählung für mindestens eine Morgen und eine Nachmittagsspitze per Video mit Ultralytics YOLO und supervision, Stichprobe von Hand prüfen. Optional je Zufahrt ein Telraam-Sensor für Langzeitwerte. Ergebnis als CSV mit Strömen je 15 Minuten nach Fahrzeugklasse.
3. **Netz bauen.** OSM-Ausschnitt mit `osmGet.py` laden, mit `netconvert` umwandeln, in `netedit` oder als plain XML nachbearbeiten. Das Ist-Netz kommt versioniert ins Repository.
4. **Nachfrage erzeugen.** Zählwerte mit `routeSampler.py` in Routen für Kfz und Rad übersetzen, Fußgängerströme separat definieren.
5. **Kalibrieren.** Simulierte Ströme und beobachtete Rückstaulängen mit der Zählung vergleichen (GEH-Wert, Abweichung je Strom), Fahrzeugparameter nur moderat anpassen und alle Annahmen dokumentieren.
6. **Varianten anlegen.** Jede Variante als eigener Ordner mit eigenem Netz bzw. eigener Signalprogrammdatei, etwa geänderte Spuraufteilung, angepasste Phasenfolge, Rundum-Grün für Fußgänger, geschützte Radwege, Kreisverkehr. Gleiche Nachfrage für alle Varianten, zusätzlich ein Szenario mit veränderter Nachfrage.
7. **Simulieren.** Headless mit `sumo`, je Variante mindestens zehn Läufe mit verschiedenen Zufallszahlen, Ausgaben `tripinfo`, `queue`, E2-Detektoren je Zufahrtsfahrstreifen, `edgeData`, Emissionen und optional SSM.
8. **Auswerten.** Python-Skripte mit pandas berechnen je Strom und Verkehrsart mittlere Wartezeit, Zeitverlust, Rückstau (Mittelwert und 95-Prozent-Wert), Durchsatz und daraus die QSV nach HBS. Parallel dazu eine eigene analytische HBS-Berechnung als Plausibilitätskontrolle.
9. **Visualisieren.** Videos aus `sumo-gui`, Kartenausschnitte in QGIS mit Qualitätsstufen je Fahrstreifen, animierte Karte in Kepler.gl, Querschnitte in Streetmix, einfache Balkendiagramme für den Variantenvergleich.
10. **Veröffentlichen.** Methodik, Annahmen, Zähldaten und Skripte offenlegen. Die Ergebnisse als fachlich begründete Abschätzung kennzeichnen und nicht als amtlichen HBS-Nachweis. Das erhöht die Glaubwürdigkeit gegenüber Verwaltung und Presse.

Grobe Struktur im Repository

```
verkehr-giesserstrasse/
  daten/          Zählungen, Fotos, Signalzeiten
  sumo/ist/       Netz, Routen, Detektoren, Konfiguration
  sumo/varianten/ je Variante ein Unterordner
  auswertung/     Python-Skripte, Ergebnistabellen
  grafiken/       Karten, Diagramme, Videos
  recherche/      diese und weitere Notizen
```

Installation im Container (Grundausstattung)

```
pip install eclipse-sumo sumolib traci pandas matplotlib ultralytics supervision keplergl
apt-get install xvfb ffmpeg qgis    # optional für Videos und Karten
```

## 8. Offene Punkte und Vorbehalte

* Grenzwerte und Verfahren des HBS am Original (FGSV 299, Teil S) prüfen und klären, ob inzwischen eine neue Fassung gilt.
* Den Signalzeitenplan der Stadt anfragen, weil ein geschätztes Ist-Signalprogramm die größte Unsicherheit im Modell ist.
* Datenschutz bei der Videozählung vorab klären und dokumentieren.
* Die Lizenzlage von LISA, KNOBEL und KNOSIMO beruht auf Fachkenntnis, die Herstellerseiten waren während der Recherche nicht abrufbar.
* SUMO-Standardwerte ändern sich zwischen Versionen (zuletzt in 1.27). Die verwendete Version deshalb im Projekt festschreiben.
