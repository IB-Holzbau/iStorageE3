# Kreuzung Gießerstraße / Naumburger Straße

Stand der Recherche 17.10.2026

Kennzeichnung im Text
**[V]** verifiziert durch mindestens eine belastbare Quelle (Stadt Leipzig, Leipzig-Lexikon, Ratsdokument, Presse mit Quellenangabe)
**[U]** unsicher, nur aus Sekundärquellen, Aggregatoren oder eigener Ortskenntnis, vor Verwendung prüfen
**[O]** offen, konnte in dieser Sitzung nicht ermittelt werden

## 0 Wichtiger Hinweis zur Datenlage dieser Sitzung

Aus der Arbeitsumgebung waren overpass-api.de, openstreetmap.org, nominatim, leipzig.de und alle übrigen Datenserver gesperrt (Proxy antwortet mit 403). Das Abrufen ganzer Webseiten war ebenfalls nicht möglich, Firecrawl hatte kein Guthaben mehr. Verfügbar war nur eine Websuche mit Kurzauszügen. Deshalb gilt

* Die Datei `daten/osm_kreuzung.json` und die `.osm` Datei konnten **nicht** erzeugt werden.
* Stattdessen liegen die fertige Abfrage `daten/osm_abfrage.overpassql` und das Skript `daten/osm_abfrage.sh` bereit. Auf einem Rechner mit normalem Internetzugang erzeugt `bash daten/osm_abfrage.sh` beide Dateien und gibt eine lesbare Tag-Übersicht aus.
* Alle Angaben unten zur Spurführung und Beschilderung, die nicht aus Presse oder Stadtdokumenten stammen, sind deshalb als [U] oder [O] markiert.

## 1 In welcher Stadt liegt die Kreuzung

**Ergebnis Leipzig, Ortsteil Plagwitz (PLZ 04229), Stadtbezirk Alt-West.** [V]

* Laut Leipzig-Lexikon verläuft die Gießerstraße von der Endersstraße in Lindenau über die Karl-Heine-, Weißenfelser und Naumburger Straße nach Kleinzschocher bis zur Rolf-Axen-Straße, Gesamtlänge rund 1.744 m. An der Antonienstraße wechselt sie nach Kleinzschocher. [V] ([Leipzig-Lexikon Gießerstraße](https://www.leipzig-lexikon.de/STRASSEN/06021.htm), [Straßen in Plagwitz](https://www.leipzig-lexikon.de/STRASSEN/Plagwitz.htm))
* Beide Straßen stehen im amtlichen Straßennamenverzeichnis der Stadt Leipzig. [V] ([Gießerstraße](https://www.leipzig.de/buergerservice-und-verwaltung/unsere-stadt/gebietsgliederung-und-strassennamen/strassennamen/strassennamenverzeichnis/strasse/strassen-details/giesserstrasse), [Naumburger Straße](https://www.leipzig.de/buergerservice-und-verwaltung/unsere-stadt/gebietsgliederung-und-strassennamen/strassennamen/strassennamenverzeichnis/strasse/strassen-details/naumburger-strasse))
* Die Stadt selbst spricht in einer Pressemitteilung von der städtischen Grünfläche „an der Kreuzung Naumburger Straße/Gießerstraße“ (Wagenburg, um 2012). [V] ([leipzig.de](https://www.leipzig.de/newsarchiv/news/bergangslsung-fr-wagenburg-gefunden))
* Andere Städte. Eine Naumburger Straße gibt es laut strassen-in-deutschland.de in rund 57 Orten, darunter Jena, Weißenfels, Merseburg (B 181). In Chemnitz gibt es eine Gießerstraße. Eine Kreuzung beider Namen außerhalb Leipzigs wurde in der Websuche nicht gefunden. [U] Der Ort ist vom Koordinator vor Ort bestätigt, die Städtesuche wurde daher beendet. Die Abfrage für eine bundesweite Prüfung steht in Abschnitt 6.

## 2 Was über die Kreuzung bekannt ist

### 2.1 Netz und Funktion

* Die Gießerstraße ist im Hauptnetz der Stadt als Erschließungsstraße eingestuft, Breite zwischen den Hauswänden im Südabschnitt nur etwa 12 m. [V] ([L-IZ 2017, ADFC-Kritik](https://www.l-iz.de/politik/brennpunkt/2017/09/adfc-kritisiert-die-leipziger-verkehrsplaner-fuer-ihre-strassenverengungspolitik-192974))
* Ausbau Gießerstraße Südabschnitt Antonienstraße bis Rolf-Axen-Straße, 487 m, mittlere Gesamtbreite 11,80 m, keine eigenen Radverkehrsanlagen (Mischverkehr auf der Fahrbahn), Kosten rund 1,26 Mio. Euro. Liegt **südlich** der hier betrachteten Kreuzung. [V] (Quelle wie oben) Ob genau so gebaut wurde [O].
* Sanierung Gießerstraße Nordabschnitt Karl-Heine-Straße bis Endersstraße, rund 260 m, 2020 im Zuge des Grundschulneubaus, Ampel an Karl-Heine-/Gießerstraße vorgesehen. Liegt **nördlich** der Kreuzung. [V] ([L-IZ 2019](https://www.l-iz.de/melder/verkehrsmelder/2019/07/Giesserstrasse-wird-waehrend-des-Neubaus-der-Grundschule-saniert-284918))
* Die Naumburger Straße verbindet die Gießerstraße nach Westen mit Engertstraße und Zollschuppenstraße und nach Osten mit der Zschocherschen Straße. Der Ostteil (Gießer- bis Zschochersche Straße) hat laut Mobilitäts- und Tiefbauamt deutlich weniger Verkehr als der Westteil. [V] ([L-IZ Okt. 2024](https://www.l-iz.de/politik/brennpunkt/2024/10/naumburger-strasse-tempo-30-westteil-607248), [Einwohneranfrage VIII-EF-00180 als PDF](https://l-iz.de/wp-content/uploads/2024/10/2024-10-15-VIII-EF-00180-AW-01-Naumburger-Strasse_-T-VO.pdf))
* Historisch fuhr 1942 bis 1972 der Obus durch Gießer-, Naumburger, Engert- und Karl-Heine-Straße, die Kreuzung war also Abbiegepunkt einer Linie. [V] ([Leipzig-Lexikon](https://www.leipzig-lexikon.de/STRASSEN/06021.htm))

### 2.2 Geschwindigkeit

* **Tempo 30 auf der Naumburger Straße zwischen Engertstraße und Gießerstraße**, angeordnet im November 2025, beschildert ab 1. Dezember 2025, Kosten rund 3.100 Euro. Begründung Lärmbrennpunkt über 65 dB(A) tags und 55 dB(A) nachts. [V] ([Stadt Leipzig, 20.11.2025](https://www.leipzig.de/newsarchiv/news/stadt-ordnet-tempo-30-auf-abschnitt-der-naumburger-strasse-an), [L-IZ](https://www.l-iz.de/melder/verkehrsmelder/2025/11/stadt-ordnet-tempo-30-auf-abschnitt-der-naumburger-strasse-an-639609))
* Ostteil Naumburger Straße (Gießer- bis Zschochersche Straße) laut Stadt Oktober 2024 ohne Voraussetzungen für Tempo 30, also vermutlich weiter 50 km/h. [U] für den heutigen Stand.
* Lärmaktionsplan, 3. Fortschreibung, beschlossen 26.06.2025. Unter Nr. 5 der zehn neuen Tempo-30-Abschnitte bis 2027 steht „Naumburger Straße, Gießerstraße, Zollschuppenstraße“. Ob auch die Gießerstraße selbst an der Kreuzung Tempo 30 hat [O]. ([L-IZ Juli 2025](https://www.l-iz.de/politik/leipzig/2025/07/beschlossener-larmaktionsplan-okolowe-schnellere-umsetzung-tempo-30-hauptstrassen-628564), [Ökolöwe Dez. 2025](https://www.l-iz.de/wirtschaft/mobilitaet/2025/12/okolowe-kritisiert-schneckentempo-im-larmaktionsplan-erst-17-65-tempo-30-strecken-umgesetzt-641392))
* Hinweis zum Widerspruch in den Quellen. Der Entwurf 2024 nennt den Brennpunkt westlich „Gießer- bis Zollschuppenstraße“, die Anordnung 2025 „Engert- bis Gießerstraße“. Vermutlich ist derselbe Westast gemeint (Engertstraße liegt zwischen beiden), genaue Grenze laut Anordnung prüfen. [U]

### 2.3 Spurführung, Vorfahrt, Signalanlage

**Abgleich mit den Ortsangaben des Koordinators** (Stand 17.10.2026, Quelle Ortskenntnis bzw. Luftbild, nicht online belegt)

| Merkmal laut Koordinator | Online-Beleg | Bewertung |
|---|---|---|
| Einmündung (T-Knoten), Arme Nord und Süd Gießerstraße, West Naumburger Straße | Leipzig-Lexikon nennt die Naumburger Straße als Querstraße der Gießerstraße. Die Buslinie 60 fährt laut Fahrplanportalen von der Siemensstraße über die Haltestelle Naumburger Straße zur Zollschuppenstraße, biegt also hier von Süd nach West ab | passt [U] |
| Abknickende Vorfahrt Süd ↔ West auf der Gießerstraße | kein Online-Beleg, aber plausibel, weil die Hauptachse (früher Obus, heute Bus 60) genau diese Beziehung fährt | [U], in OSM als `highway=give_way`/`stop` am Nordarm und Zeichen 306 mit Zusatz 1002 prüfen |
| Gießerstraße Tempo 50 | Lärmaktionsplan nennt die Gießerstraße unter den Tempo-30-Abschnitten bis 2027, Umsetzung bisher nicht belegt | passt zum heutigen Stand [U] |
| Naumburger Straße beidseitig Tempo 30 | Tempo 30 zwischen Engert- und Gießerstraße seit 1.12.2025 [V] | West passt [V]. „Beidseitig“ bedeutet hier vermutlich beide Fahrtrichtungen. Für den **Ostteil** Gießer- bis Zschochersche Straße hat die Stadt im Oktober 2024 Tempo 30 abgelehnt. Wenn der Ostteil an einem anderen Punkt der Gießerstraße beginnt (versetzter Knoten), ist das kein Widerspruch zum T-Knoten. Klären! |
| Stoppschild (Zeichen 206) am Nordarm | kein Online-Beleg | [O] |
| Bushaltestelle Süd mit Gelenkbussen | Haltestelle „Naumburger Straße“, Linie 60, laut Anbieter barrierefrei [U] | Linie 60 [U], Gelenkbus und Lage am Südarm [O] |
| Kiosk Südwestecke | kein Online-Beleg | [O] |
| Parkende Autos Ostseite | kein Online-Beleg | [O] |

* Fahrstreifenzahl, Abbiegestreifen, Markierungen [O]. Beide Straßen sind nach Breite und Funktion vermutlich je ein Fahrstreifen pro Richtung ohne eigene Abbiegestreifen. [U]
* Lichtsignalanlage an der Kreuzung [O]. In keiner gefundenen Quelle erwähnt, passt zur Angabe Stoppschild statt Ampel. Die nächste gesicherte Ampel ist Karl-Heine-/Gießerstraße (geplant 2019/20). An Antonien-/Gießerstraße gibt es eine Ampel, die am 28.09.2026 wegen Wartung abgeschaltet war, als dort ein Transporter nach Zusammenstoß umkippte (sechs Leichtverletzte). Das ist **nicht** diese Kreuzung, aber der nächste südliche Knoten. [V] ([ms-aktuell](https://ms-aktuell.de/?p=162452))
* Vorfahrtregelung (Zeichen 306 / 205, rechts vor links) [O].
* Radverkehr. Im Südabschnitt Mischverkehr auf der Fahrbahn [V]. An der Kreuzung selbst [O].
* Straßenbahn. Keine Straßenbahn in Gießer- oder Naumburger Straße bekannt. [U]

### 2.4 ÖPNV

* **Buslinie 60 der LVB** (Lipsiusstraße bzw. Lindenauer Hafen ↔ Lindenau Bushof) bedient die Haltestelle „Naumburger Str.“, laut Fahrplanportalen zwischen Siemensstraße und Zollschuppenstraße, also mit Abbiegen Süd ↔ West an diesem Knoten. Die Haltestelle wird als barrierefrei beschrieben. [U] Mehrere Drittanbieter stimmen überein ([fahrplan-bus-bahn.de](https://fahrplan-bus-bahn.de/sachsen/leipzig/haltestelle/naumburger_str_leipzig-9580693), [bus-bahn-fahrplan.de](https://bus-bahn-fahrplan.de/fahrplan-leipzig/20-958069/bus-60-lindenau-bushof-leipzig-naumburger-strasse), [Gründungsküche Anfahrt](https://gruendungskueche.de/anfahrt/), [Moovit](https://moovitapp.com/index/en/public_transit-line-60-Dresden-5796-3764189-196821436-0)).
* Eine Variante 60E wird mit der Folge Antonien-/Gießerstraße, Naumburger Straße, Karl-Heine-/Gießerstraße angegeben, also geradeaus Süd ↔ Nord. [U] ([findit.city 60E](https://findit.city/en/germany/leipzig/transport/bus/60E))
* Weitere Linien an dieser Haltestelle nicht gefunden [O]. Bestätigung über die LVB-Fahrplanauskunft (l.de) oder den GTFS-Datensatz des MDV/DELFI nötig.

### 2.5 Umfeld

* Grundschule Gießerstraße (seit 2020, rund 500 Kinder) am Nordende der Straße, Elterntaxi-Probleme, beleuchteter Zebrastreifen in der Gießerstraße (rund 10 m breit, 2023) und in der Endersstraße. Liegt einige hundert Meter nördlich. [V] ([L-IZ 2023 Zebrastreifen](https://www.l-iz.de/politik/brennpunkt/2023/08/grundschule-in-lindenau-breitester-zebrastreifen-leipzigs-giesserstrasse-551154), [L-IZ 2023 Stadtrat](https://www.l-iz.de/politik/brennpunkt/2023/04/der-stadtrat-tagte-losung-verkehrschaos-grundschule-giesserstrasse-529173))
* Elterninitiative fordert 2025 eine Schulstraße und sichere Querungen am Jahrtausendfeld. [V] ([L-IZ Juni 2025](https://www.l-iz.de/politik/brennpunkt/2025/06/bauplane-fur-das-jahrtausendfeld-eltern-kinder-grundschule-giesserstrasse-offener-brief-626012))
* Städtische Grünfläche direkt an der Kreuzung (früher Wagenplatz). [V] ([leipzig.de](https://www.leipzig.de/newsarchiv/news/bergangslsung-fr-wagenburg-gefunden))

### 2.6 Unfälle

* Kein Pressebericht zu einem Unfall genau an Gießer-/Naumburger Straße gefunden. [O]
* Auswertung im Unfallatlas muss manuell erfolgen (siehe 3.3).

## 3 Freie Datenquellen und wie man sie nutzt

### 3.1 OpenStreetMap

* Abfrage und Skript liegen in `daten/` (siehe Abschnitt 6). Die Abfrage sucht den gemeinsamen Knoten beider Straßen in Leipzig und lädt alles im Umkreis 150 m (Straßen, Fahrstreifen, turn:lanes, maxspeed, Radwege, Parkstreifen, Ampeln, Überwege, Verkehrszeichen, Abbiegeverbote, Bus und Tram mit Routenrelationen).
* Für SUMO erzeugt das Skript zusätzlich `osm_kreuzung.osm`. Import zum Beispiel mit `netconvert --osm-files osm_kreuzung.osm --tls.guess-signals --junctions.join -o kreuzung.net.xml`.
* Ansicht im Browser über [openstreetmap.org](https://www.openstreetmap.org/search?query=Gie%C3%9Ferstra%C3%9Fe%20Naumburger%20Stra%C3%9Fe%20Leipzig) oder [overpass-turbo.eu](https://overpass-turbo.eu) (Abfrage hineinkopieren).

### 3.2 Amtliche Geodaten

| Quelle | Inhalt | Zugang | Status |
|---|---|---|---|
| Geoportal / Stadtplan Leipzig | Stadtplan, Luftbilder, Bebauungspläne | [stadtplan.leipzig.de](https://stadtplan.leipzig.de), [geoportal.leipzig.de](https://geoportal.leipzig.de) | [U] URLs nicht abrufbar gewesen |
| Open Data Leipzig | Verkehrszählungen, Geodaten | [opendata.leipzig.de](https://opendata.leipzig.de) | [U] |
| Dauerzählstellen Kfz | 24 Induktionsschleifen mit Dashboard, nicht an dieser Kreuzung bekannt | [leipzig.de/verkehrszaehlungen](https://www.leipzig.de/verkehrszaehlungen) | [V] laut [L-IZ 2022](https://www.l-iz.de/wirtschaft/mobilitaet/2022/02/verkehr-in-24-leipziger-strassen-auch-daten-der-zaehlstellen-zum-kfz-verkehr-sind-jetzt-online-einsehbar-434950) |
| GeoSN Luftbilder DOP20 | Orthophotos 20 cm, Sachsen | WMS vermutlich `https://geodienste.sachsen.de/wms_geosn_dop-rgb/guest`, Portal [geoportal.sachsen.de](https://geoportal.sachsen.de) | [U] URL und Lizenz (vermutlich dl-de/by-2-0) prüfen |
| Lärmkarten / Lärmaktionsplan | Lärmbrennpunkte, Tempo-30-Liste | leipzig.de Stichwort Lärmaktionsplan | [V] Inhalt laut Presse, Dokument nicht geöffnet |
| Radverkehrsentwicklungsplan | Netzeinstufung Rad | leipzig.de Stichwort Radverkehrsentwicklungsplan | [O] für diese Kreuzung |

### 3.3 Unfallatlas

* [unfallatlas.statistikportal.de](https://unfallatlas.statistikportal.de) zeigt Unfälle mit Personenschaden ab 2016 punktgenau mit Jahr, Unfallart, Unfalltyp, Beteiligten und Lichtverhältnis. Die Rohdaten gibt es als CSV/Shape je Jahr zum Download. Filter auf einen Kreis von etwa 30 m um den Knoten ergibt die Unfallliste. [O] Ergebnis, da die Seite nicht abrufbar war. Eine Auswertung für genau diesen Knoten ist im Netz nicht veröffentlicht.
* Open Data Leipzig bietet den Datensatz „Unfälle mit Radbeteiligung“ 2016 bis 2021 (aus dem Unfallatlas) als CSV. [V] ([opendata.leipzig.de](https://opendata.leipzig.de/dataset/unfaelle-mit-radbeteiligung))
* Unfallhäufungsstellen benennt die Verkehrsunfallkommission der Stadt, deren Unterlagen sind im Musterantrag mit abgefragt.
* Presse 2026 in der Nähe, aber nicht an diesem Knoten Antonien-/Gießerstraße 28.09.2026 (Ampel abgeschaltet, sechs Leichtverletzte, etwa 50.000 Euro Schaden), Haltestelle Adler Zschochersche Straße Januar 2026 (Fußgänger leicht verletzt). [V] ([ms-aktuell](https://ms-aktuell.de/?p=162452), [L-IZ Januar 2026](https://www.l-iz.de/melder/polizeimelder/2026/01/polizeibericht-20-januar-dachstuhlbrand-in-gruenau-zeugen-zu-unfall-in-plagwitz-gesucht-blindgaenger-verletzt-polizeibeamte-644831))

### 3.4 Straßenbilder zur Beschilderung

* [Mapillary](https://www.mapillary.com) und [Panoramax](https://panoramax.fr) bzw. [panoramax.openstreetmap.fr](https://panoramax.openstreetmap.fr) an der Kreuzung öffnen, Verkehrszeichen-Erkennung bei Mapillary zeigt erkannte Schilder als Kartenebene. [O] ob Bilder vorhanden sind und wie aktuell.
* Wichtig, weil Tempo 30 erst seit 12/2025 gilt. Ältere Bilder zeigen noch den alten Zustand.

### 3.5 Ratsinformationssystem und Politik

* Allris Leipzig ([ratsinformation.leipzig.de](https://ratsinformation.leipzig.de/allris_leipzig_public/)) mit Volltextsuche nach „Gießerstraße“ und „Naumburger Straße“. Bekannt sind
  * Einwohneranfrage VIII-EF-00180 zu Tempo 30 Naumburger Straße, Antwort Oktober 2024 [V] ([PDF](https://l-iz.de/wp-content/uploads/2024/10/2024-10-15-VIII-EF-00180-AW-01-Naumburger-Strasse_-T-VO.pdf))
  * Antrag Stadtbezirksbeirat Alt-West zur Schulwegsicherheit Grundschule Gießerstraße (2021 bis 2023) [V] (siehe 2.5)
  * Lärmaktionsplan 3. Fortschreibung, Beschluss 26.06.2025 [V]

### 3.6 Presse

* Leipziger Zeitung (l-iz.de) ist die ergiebigste Quelle, Artikel siehe oben. LVZ-Artikel sind meist hinter Bezahlschranke, keine gefunden. [O]

## 4 Amtliche Ampelpläne, Markierungs- und Beschilderungspläne

Zuständig ist das **Mobilitäts- und Tiefbauamt der Stadt Leipzig** (früher Verkehrs- und Tiefbauamt, VTA). Es betreibt rund 430 Lichtsignalanlagen und erlässt als Straßenverkehrsbehörde die verkehrsrechtlichen Anordnungen. [V] ([L-IZ 2023](https://www.l-iz.de/politik/brennpunkt/2023/07/der-stadtrat-tagte-fehlende-ampel-40-unbesetzte-planerstellen-video-544345))

Rechtsgrundlagen für eine Anfrage

* **Informationsfreiheitssatzung der Stadt Leipzig** (gilt seit 2012). Leipzig hat sich dem Sächsischen Transparenzgesetz (in Kraft seit 1.1.2023) noch **nicht** per Satzung unterworfen, eine Transparenzsatzung ist nicht vor 2028 zu erwarten. Anfragen laufen also über die Informationsfreiheitssatzung, mit Gebühren. [V] ([L-IZ Okt. 2025](https://www.l-iz.de/politik/leipzig/2025/10/der-stadtrat-tagte-vor-2028-leipzig-keine-transparenzsatzung-635458))
* **Sächsisches Umweltinformationsgesetz (SächsUIG)**. Gilt unmittelbar auch für Kommunen. Verkehrsregelungen, die Lärm und Luftschadstoffe beeinflussen (Tempo 30 aus dem Lärmaktionsplan, Signalprogramme), sind gut als Umweltinformation begründbar. Einfache Auskünfte sind meist gebührenfrei. [U] rechtliche Einschätzung, keine Rechtsberatung.
* Verkehrsrechtliche Anordnungen sind Allgemeinverfügungen, die durch die Schilder bekanntgegeben werden. Die zugehörigen Anordnungsunterlagen (Verkehrszeichenplan, Markierungsplan) sind Akten der Behörde und damit zugänglich, soweit keine Ausnahmen (Sicherheit, Urheberrecht von Planungsbüros) greifen. Signalzeitenpläne werden erfahrungsgemäß in vielen Städten herausgegeben, teils mit Schwärzungen. [U]
* Weg über [FragDenStaat](https://fragdenstaat.de) (Behörde „Stadt Leipzig“ bzw. „Mobilitäts- und Tiefbauamt Leipzig“ auswählen, als Rechtsgrundlage UIG Sachsen bzw. Informationsfreiheitssatzung). Eine frühere Anfrage zu Leipziger Signalzeitenplänen wurde nicht gefunden. [O]

### Musterantrag

> An die Stadt Leipzig, Mobilitäts- und Tiefbauamt, 04092 Leipzig
>
> **Antrag auf Zugang zu Umweltinformationen nach § 4 SächsUIG, hilfsweise nach der Informationsfreiheitssatzung der Stadt Leipzig**
>
> Sehr geehrte Damen und Herren,
>
> bitte übersenden Sie mir folgende Unterlagen zum Knotenpunkt Gießerstraße / Naumburger Straße in 04229 Leipzig-Plagwitz einschließlich der angrenzenden Abschnitte bis je etwa 150 m
>
> 1. die gültigen verkehrsrechtlichen Anordnungen mit Verkehrszeichen- und Markierungsplänen, insbesondere die Anordnung von Tempo 30 auf der Naumburger Straße zwischen Engertstraße und Gießerstraße vom November 2025,
> 2. sofern eine Lichtsignalanlage vorhanden ist, den aktuellen Signallageplan, die Signalzeitenpläne aller Programme mit Gültigkeitszeiten sowie die Zwischenzeitenmatrix, andernfalls eine kurze Mitteilung, dass keine Anlage besteht,
> 3. vorhandene Verkehrszählungen (Knotenstromzählungen, DTV) für diesen Knotenpunkt aus den letzten zehn Jahren,
> 4. vorhandene Unterlagen der Unfallkommission zu diesem Knotenpunkt.
>
> Es handelt sich um Umweltinformationen im Sinne von § 3 Abs. 2 SächsUIG, da die Maßnahmen Lärm und Luftschadstoffe beeinflussen und teilweise auf dem Lärmaktionsplan beruhen. Ich bitte um Übersendung in elektronischer Form (PDF, Zählungen gern als CSV oder XLSX). Sollten Gebühren anfallen, bitte ich vorab um Mitteilung, falls diese 20 Euro übersteigen. Sollten Teile nicht herausgegeben werden können, bitte ich um Herausgabe der übrigen Teile und um Begründung der Ablehnung.
>
> Mit freundlichen Grüßen
> [Name, Anschrift, E-Mail]

## 5 Offene Punkte für die nächste Sitzung

1. `bash daten/osm_abfrage.sh` mit freiem Internet ausführen und die Tag-Übersicht hier ergänzen. Gezielt prüfen `highway=stop` am Nordarm, `priority_road`/Zeichen 306 mit Zusatz 1002 (abknickende Vorfahrt), `maxspeed` je Arm, `highway=bus_stop` am Südarm, `parking:right`/`parking:left` auf der Ostseite, `shop=kiosk` an der Südwestecke.
2. Unfallatlas für 2016 bis 2025 im Radius 50 m auswerten.
3. Mapillary/Panoramax Bilder sichten, Schilder fotografisch dokumentieren, besser noch eigene Begehung.
4. Buslinie und Haltestellenlage über l.de bestätigen.
5. Allris Volltextsuche, besonders Lärmaktionsplan-Anlage mit der genauen Abgrenzung der Tempo-30-Abschnitte.

## 6 Dateien

* `daten/osm_abfrage.overpassql` Overpass-Abfrage, Umkreis 150 m um den gemeinsamen Knoten beider Straßen
* `daten/osm_abfrage.sh` lädt `osm_kreuzung.json` und `osm_kreuzung.osm` und druckt eine Tag-Zusammenfassung
* Für die bundesweite Prüfung auf weitere Städte mit dieser Kreuzung in overpass-turbo

```
[out:json][timeout:180];
area["ISO3166-1"="DE"]->.de;
way["highway"]["name"~"^Gie(ß|ss)erstra(ß|ss)e$"](area.de)->.g;
way["highway"]["name"~"^Naumburger Stra(ß|ss)e$"](area.de)->.n;
node(w.g)->.gn; node(w.n)->.nn;
node.gn.nn; out;
```
