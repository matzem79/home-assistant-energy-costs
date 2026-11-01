# Energy Costs für Home Assistant

<img src="custom_components/energy_costs/brand/icon.png" alt="Energy Costs" width="96" height="96">

Eine eigenständige Custom Integration für die Stromkosten eines Haushalts.
Netzbezug und Einspeisung bleiben vollständig getrennt. Keine Abhängigkeit von
50five, Tibber oder einem bestimmten Zählerhersteller.

## Einrichtung

1. Den Ordner `custom_components/energy_costs` nach
   `/config/custom_components/energy_costs` kopieren.
2. Home Assistant neu starten.
3. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach
   **Energy Costs** suchen.
4. Die Eingaben für deine Zähler und Tarife ausfüllen.

Benötigt Home Assistant 2026.1 oder neuer. Die GitHub-Links im Manifest sind für
`matzem79/home-assistant-energy-costs` vorbereitet; das Repository wurde noch
nicht veröffentlicht. Installation zunächst manuell über den Integrationsordner
oder das mitgelieferte ZIP. Beim Entpacken den enthaltenen Ordner
`custom_components/energy_costs` vollständig übernehmen, einschließlich `brand/`. In HACS wäre später ein eigener Custom-Repository-
Eintrag möglich.

## Icon

Ein eigenes Blitz-/Münzsymbol wird mit der Integration unter `brand/` ausgeliefert:
`icon.png` (256 × 256) und `icon@2x.png` (512 × 512), mit transparenten Ecken.
Es ist für helle und dunkle Oberflächen geeignet. Home Assistant zeigt lokale
Brand-Icons **ab Version 2026.3** an; auf 2026.1/2026.2 bleibt die Integration
nutzbar, das eigene Icon erscheint dort jedoch nicht automatisch.
Nach einem Update HA neu starten und bei Bedarf die Browseransicht vollständig
neu laden (am Mac **⌘⇧R**) oder ein privates Browserfenster verwenden.
Die Integration muss für das Icon-Update **nicht gelöscht** werden. Fehlt das
Icon weiter, HA-Core-Version und den Pfad
`/config/custom_components/energy_costs/brand/icon.png` prüfen.
Die Iconanzeige wurde nach manueller Installation in HA bestätigt.

Die bearbeitbare Vektorquelle liegt unter [docs/icon.svg](docs/icon.svg).
Mit `python3 scripts/build_brand.py` werden SVG und PNGs ohne Zusatzpakete aus
denselben Formen erzeugt. Sie stehen wie der Code unter der MIT-Lizenz.
Siehe [HA-Dokumentation für Brand-Icons](https://contributors.home-assistant.io/core/integrations/brands/).

## Konfiguration

| Eingabe | Bedeutung |
| --- | --- |
| Zähler Netzbezug | Kumulativer Energiezähler in Wh oder kWh, z. B. Netzbezug/1.8.0 |
| Zähler Einspeisung | Separater kumulativer Zähler in Wh oder kWh, z. B. Einspeisung/2.8.0; optional ohne Einspeisung |
| Bezugspreis je kWh | Preis in HA-Währung/kWh, z. B. `0.30` für 30 ct bei EUR |
| Einspeisevergütung je kWh | Vergütung in HA-Währung/kWh, z. B. `0.08` für 8 ct |
| Monatliche Grundgebühr | Fester monatlicher Betrag, nur auf der Bezugsseite |
| Monatlicher Abschlag Netzbezug | Planmäßige monatliche Zahlung an den Stromlieferanten |
| Monatliche Gutschrift Einspeisung | Planmäßige monatliche Auszahlung vom Netzbetreiber/Vergüter |
| Monatliche Einspeisegutschriften zählen ab | Optional: frühester berücksichtigter monatlicher Auszahlungstermin, unabhängig vom Abrechnungsjahr |
| Gültig ab | Optionales Datum für diese Preise, Grundgebühr und Monatszahlungen; leer bedeutet heute |
| Beginn Abrechnungsjahr Bezug | Eigener jährlicher Abrechnungsbeginn für den Liefervertrag |
| Beginn Abrechnungsjahr Einspeisung | Eigener jährlicher Abrechnungsbeginn für die Einspeiseabrechnung |
| Historische Zählerdaten ab Abrechnungsbeginn importieren | Optional: Langzeitstatistiken beider Quellen ab ihrem jeweiligen Startdatum übernehmen |
| Anfangssaldo Bezug/Einspeisung | Optional: bereits bekannter Saldo zum Zeitpunkt des erstmaligen Erfassungsbeginns |

Die beiden Zähler dürfen nicht dieselbe Entität sein. Benötigt werden echte
Zählersummen, keine Leistungswerte in W, kein täglich zurückgesetzter Verbrauch
und kein saldierender Bezug-minus-Einspeisung-Zähler. PV-Eigenverbrauch gehört
nicht zum Netzbezug. ESPHome, Shelly, Modbus oder MQTT sind als Quellen geeignet,
wenn sie passende HA-Sensoren bereitstellen. Keine der Hardwarevarianten wurde
mit dieser neuen Integration bisher live geprüft.

## Preisänderungen und Tarifverlauf

**Energy Costs → Konfigurieren** öffnet die Eingaben erneut. Neue Werte und ein
optionales Datum speichern einen weiteren Eintrag im Tarifverlauf. Ein Eintrag
am gleichen Gültigkeitsdatum wird ersetzt; andere Einträge bleiben erhalten.
Im Konfigurationsdialog stehen Anzahl und Tabelle aller gespeicherten Tarife
mit Gültigkeitsdatum und sämtlichen Preisen/Monatsbeträgen.

- Ohne Datum: gültig ab heute, **00:00 Uhr** in der HA-Zeitzone.
- Zukünftiges Datum: Die bisherigen Preise gelten bis einschließlich Vortag.
- Rückwirkendes Datum: Die gespeicherten täglichen Energiemengen werden ab
  diesem Datum mit den neuen Preisen neu bewertet.

Es erfolgt keine Umrechnung historischer Tage mit einem beliebig späteren
Tarif. Ein rückdatierter Preis kann aber nur bereits **erfasste** Energiemengen
neu bewerten. Mit dem optionalen Historienimport können frühere Zählerdaten aus
den Recorder-Langzeitstatistiken übernommen werden. Frühere Recorder-Statistiken werden nicht umgeschrieben; die neu
berechneten aktuellen Perioden-/Gesamtwerte können deshalb von alten Graphen
abweichen.

Alle Angaben eines Tarifeintrags teilen sich das Gültigkeitsdatum, einschließlich
Monatsabschlag und Einspeisegutschrift. Die Währung wird beim Einrichten aus HA
übernommen und bleibt für diesen Eintrag erhalten; keine automatische Währungs-
umrechnung. Negative kWh-Preise sind möglich, negative Grundgebühren oder
Monatszahlungen nicht.

### Rückwirkender Einstieg mit historischen Zählerdaten

Ab Version 0.2.0 kann unter **Konfigurieren** die Option **Historische Zählerdaten
ab Abrechnungsbeginn importieren** aktiviert werden. Beispiel:

1. Beginn Abrechnungsjahr Bezug: **26.10.2026**.
2. Beginn Abrechnungsjahr Einspeisung: **01.04.2026**.
3. Bezugspreis, Einspeisevergütung, Grundgebühr und Monatszahlungen eintragen.
4. **Gültig ab: 01.04.2026**, wenn diese Werte seitdem unverändert gelten.
   Bezugskosten und Grundgebühr beginnen trotzdem erst am 26.10.2026.
   Bei zwischenzeitlichen Änderungen weitere Tarife mit dem jeweiligen Datum speichern.
5. Historienimport aktivieren und speichern.

Voraussetzung sind **Langzeitstatistiken mit einer Energiesumme** für die
gewählten Entitäten. Ein aktueller Zählerstand oder ein sichtbarer kurzer
Zustandsverlauf allein reicht nicht. Unter **Entwicklerwerkzeuge → Statistik**
lässt sich prüfen, ob die Quellen Statistikdaten führen. Recorder muss aktiv
sein; reine Zustandsverläufe ohne Langzeitstatistiken werden nicht importiert.

Pro Richtung werden die gespeicherten Energiemengen durch die Rekonstruktion ab
dem eingetragenen Startdatum ersetzt. Der Import verwendet stündliche,
resetbereinigte Summendifferenzen in kWh; ein Wert aus der Stunde vor dem
Startdatum dient als Ausgangsbasis. Der Rest bis zum aktuellen Zählerstand wird
ergänzt. Für den Ausgangswert werden bis zu 31 Tage vor dem Start durchsucht.
Tagesgrenzen werden in der HA-Zeitzone berücksichtigt. Stundenwerte und
der Übergang zum aktuellen Stand sind zeitliche Näherungen.

Ein erfolgreicher vollständiger Import wird gespeichert und bei Neustarts oder
reinen Preisänderungen nicht wiederholt. Änderungen an Quelle oder Startdatum
lösen einen neuen Import aus. Beim Update auf 0.2.1 werden ältere Importe einmalig neu berechnet.
Fehlgeschlagene oder unvollständige Importe werden
beim erneuten Laden erneut versucht. Ohne nutzbare Statistik bleibt die bisherige
Live-Erfassung erhalten. Abstände zwischen kumulativen Statistikwerten allein
machen die bekannte Gesamtmenge nicht unvollständig: Sie wird zeitanteilig
verteilt und mit `distribution_estimated` gekennzeichnet. Auch ein langer
Übergang zum aktuellen Zählerstand wird so ausgewiesen.

Fehlt ein Ausgangswert vor dem Start, fehlt ein Teil des Zeitraums. Liegt ein
Wertepaar über dem Abrechnungsbeginn, wird dessen Menge anteilig aufgeteilt;
der Anfangsstand ist dann geschätzt. In beiden Fällen bleibt der Import als
unvollständig markiert. Ein Rücksprung beim Übergang zum Live-Zähler oder eine
fallende Statistiksumme führen ebenfalls zu dieser Markierung. `statistics_gaps`
und `longest_gap_seconds` beschreiben die zeitliche Auflösung. Das Attribut
`incomplete_reasons` erklärt den Status der Abrechnung:

- `estimated_start_boundary`: Anfangsstand am Abrechnungsbeginn geschätzt.
- `missing_start_baseline` / `missing_period_start`: Anfang des Zeitraums fehlt.
- `decreasing_sum_or_counter_reset`: Fallende Summe bzw. Rücksprung beim Live-Übergang.
- `missing_tariff`: Preis oder Grundgebühr für erfasste Mengen/Zeiten fehlt.
- `missing_payment_tariff`: Tarif für einen planmäßigen Zahlungstermin fehlt.
- `history_unavailable_or_incomplete`: Historienimport nicht verfügbar oder fehlgeschlagen.

Die Attribute `history_import`, `tracking_since` und
`period_complete` bzw. `complete` zeigen den Stand getrennt je Richtung.

Bei vollständig importiertem Abrechnungszeitraum wird kein Anfangssaldo
angerechnet. Grundgebühr und planmäßige Monatszahlungen werden dann ebenfalls
ab dem jeweiligen Erfassungsbeginn rückwirkend berechnet. Bei einem Teilimport
bezieht sich ein etwaiger Anfangssaldo auf dessen tatsächlichen Erfassungsbeginn;
einen zuvor für die Live-Einrichtung eingetragenen Saldo entsprechend prüfen.

## Sensoren

Es werden 26 Sensoren an einem gemeinsamen Gerät angelegt:

- Netzbezug in kWh: heute, Monat, Bezugs-Abrechnungsjahr, gesamt.
- Einspeisung in kWh: heute, Monat, Einspeise-Abrechnungsjahr, gesamt.
- Bezugskosten: heute, Monat, Bezugs-Abrechnungsjahr, gesamt.
- Einspeisevergütung: heute, Monat, Einspeise-Abrechnungsjahr, gesamt.
- Aufgelaufene Grundgebühr: heute, Monat, Bezugs-Abrechnungsjahr, gesamt.
- Jeweils bezogen auf das eigene Abrechnungsjahr: Abschläge/Gutschriften,
  Saldo und Abrechnungsstatus für Bezug und Einspeisung.

**Bezugskosten enthalten nur die Energiepreise** (Netzbezug × kWh-Preis),
auch bei „gesamt“ und „Abrechnungsjahr“. Die Grundgebühr steht separat in den
Sensoren „Aufgelaufene Grundgebühr“. Im Bezugssaldo werden Bezugskosten und
Grundgebühr gemeinsam von den Abschlägen abgezogen.

**Gesamt** bedeutet seit Erfassungsbeginn, nicht der historische Lebenszeitwert
des physischen Zählers. Der erste Zählerstand ist die Ausgangsbasis und wird
nicht als neuer Verbrauch berechnet. Unverfügbare Werte werden nicht zu null.
Bei einem Rücksprung wird eine neue Zählerbasis gesetzt; unbekannte Energie
während eines Zählerwechsels/Resets wird nicht geschätzt.

Tages-/Monatswechsel sowie Jahresabrechnungswechsel berücksichtigen die
HA-Zeitzone. Ein Timer aktualisiert zeitabhängige Werte auch ohne Zählerimpuls.
Kontostände und Energiemengen werden getrennt von der Entitätsanzeige in HA
`.storage` gespeichert und nach Neustarts wiederhergestellt. Normaler Neustart
und Entladen speichern explizit; bei abruptem Stromausfall können bis zu fünf
Sekunden noch nicht geschriebene Daten fehlen.

## Grundgebühr und planmäßige Monatszahlungen

Die Grundgebühr läuft **zeitanteilig** auf: Monatsbetrag geteilt durch die
Kalendertage des Monats und anteilig für den aktuellen Tag. Ein vollständig
erfasster Monat ergibt genau den Monatsbetrag, auch im Februar/Schaltjahr oder
bei einer Zeitumstellung. Nach erstmaliger Einrichtung fallen Grundgebühren
nur ab diesem Zeitpunkt an.

Abschläge und Einspeisegutschriften werden dagegen **als voller Monatsbetrag**
gebucht, jeweils am Monatstag des zugehörigen Abrechnungsbeginns. Beispiel:
Beginn am 15. April → planmäßige Zahlungen am 15. jedes Monats. Bei einem Tag,
den der Monat nicht hat, wird der letzte Monatstag verwendet. Die Jahressumme
umfasst maximal zwölf Monatszahlungen.

Mit **Monatliche Einspeisegutschriften zählen ab** lässt sich die erste
berücksichtigte Auszahlung unabhängig vom Abrechnungsjahr begrenzen. Beispiel:
Abrechnungsbeginn **01.01.2026**, Monatsgutschrift **10 EUR**, Zahlungen zählen ab
**01.04.2026** → bis einschließlich November **80 EUR** statt 110 EUR.
Tarife vor April können dabei unverändert bleiben. Das Datum ist eine Untergrenze
für die bisherigen Zahlungstermine; es verschiebt deren Monatstag nicht.
Es gilt unabhängig vom „Gültig ab“-Datum des neu gespeicherten Tarifeintrags.
Leer bedeutet das bisherige Verhalten. Das Feld verändert weder Energiemengen
noch die verdiente Vergütung oder den Abrechnungsbeginn. Eine bereits erfolgte
Zwischenabrechnung wird damit nicht als separate Zahlung verbucht.

Die Abrechnungssensoren zeigen zusätzlich `tariff_count`, `tariffs`,
`payment_start` und `payment_schedule`. Letzteres listet jeden angesetzten
Monatstermin mit Betrag und dem dafür verwendeten Tarifdatum. Sichtbar unter
**Entwicklerwerkzeuge → Zustände** beim jeweiligen Abrechnungssensor.

**Es wird angenommen, dass diese Zahlungen tatsächlich erfolgen.** Keine
Bankanbindung, keine Erkennung ausgefallener Überweisungen und keine Eingabe
einzelner Sonderzahlungen. Der Sensorwert ist eine Berechnung nach Zahlungsplan.

## Zwei getrennte Salden

```text
Bezugssaldo = Anfangssaldo + gezahlte Abschläge − Bezugskosten − Grundgebühr
Einspeisesaldo = Anfangssaldo + verdiente Einspeisevergütung − ausgezahlte Monatsgutschriften
```

| Saldo | Bezug | Einspeisung |
| --- | --- | --- |
| Positiv | Guthaben für dich | Noch auszuzahlende Gutschrift für dich |
| Negativ | Voraussichtliche Nachzahlung | Voraussichtliche Rückzahlung überzahlter Gutschriften |
| Nahe null | Ausgeglichen | Ausgeglichen |

Der jeweilige Status benennt das Ergebnis. Die Integration prognostiziert keinen
künftigen Verbrauch: Der Saldo gilt für bisher erfasste Kosten/Vergütungen und
bis heute planmäßig gezahlte Beträge, nicht als Jahresendprognose.

Die beiden Abrechnungsjahre können unabhängig beginnen, z. B. Bezug am 1. April
und Einspeisung am 1. Januar. Sie wechseln jährlich automatisch. Ein Anfangssaldo
gilt nur für das erste, bereits laufende Abrechnungsjahr. Er wird nach dem
Jahreswechsel nicht weitergetragen: Die Vorjahresabrechnung wird als separat
verrechnet angenommen. Die Integration führt keine Zahlung aus.

### Einstieg während eines laufenden Abrechnungsjahres

Ohne Anfangssaldo fehlen die vorherigen Kosten und Zahlungen. Der Zahlenwert
zeigt dann nur den bekannten Teil, und der Status lautet **Zeitraum unvollständig**.
Bei vorhandenem Anfangssaldo werden frühere Zahlungen nicht nochmals addiert;
es zählen nur Zahlungszeitpunkte ab dem Erfassungsbeginn. Das Vorzeichen ist
für beide Anfangssalden aus deiner Sicht: Guthaben positiv, Schuld negativ.

Beispiel: Bei Beginn der Erfassung hast du auf der Bezugsseite 50 EUR Guthaben.
`Anfangssaldo Bezug = 50`. Ab jetzt kommen neue Abschläge hinzu und neue Kosten
gehen ab. Dies rekonstruiert keinen früheren Bruttoverbrauch; die alten
Energiemengen und Kosten bleiben in den Verbrauchssensoren unbekannt.

## Genauigkeit und Grenzen

Zwischen zwei unterschiedlichen Zählerständen wird die Energiemenge zeitanteilig
auf lokale Tage aufgeteilt. Späte/seltener gelieferte Werte über Mitternacht
sind deshalb eine Schätzung; schnelle kumulative Zählerupdates verbessern die
Genauigkeit. Fehlende Preiszeiträume werden über `unpriced_energy_kwh` bzw.
`unpriced_days` und `cost_complete: false` sichtbar. `period_complete` zeigt,
ob der gesamte betrachtete Zeitabschnitt seit seinem Beginn erfasst wurde.
Abrechnungssensoren haben zusätzlich `complete`, `cycle_start` und die getrennten
Beträge `actual`, `advances`, `opening_balance` als Attribute.

Ein Stromlieferant kann andere Rundungen, Stichtage, Abschlagspläne oder
Abrechnungsregeln verwenden. Das ist eine laufende Übersicht, keine verbindliche
Rechnung. Die Integration verändert keine Quellentitäten und führt keine
Überweisungen oder physischen Aktionen aus.

## Tests und Projektstand

```sh
python3 -m unittest discover -s tests -v
```

67 lokale Tests erfolgreich: Einheiten, Bezug/Einspeisung, Tarifänderungen,
Rückdatierung, Grundgebühr, Monats-/Jahresgrenzen, Schaltjahr/Zeitumstellung,
Neustart, Zählerreset, getrennte Abrechnungsjahre, Abschläge, Saldenvorzeichen,
Anfangssaldo sowie Aufbau und Speichern der Konfigurationsdialoge, Historienimport,
Statistiklücken, Übergang zur Live-Erfassung und Import-Persistenz ohne Doppelzählung.
Die HA-Grenzen sind in den Tests durch kleine Testdoubles ersetzt. Erste manuelle
Rückmeldungen aus HA liegen vor; ein vollständiger HA-/hassfest-Lauf steht aus.

Das Projekt liegt unter `AI/energy-costs`. Es ist ein eigenes Projekt und gehört nicht zum
50five-Fork. Keine Zugangsdaten enthalten, keine GitHub-Veröffentlichung erfolgt.

## Entwicklung und Veröffentlichung

Code und eigenes Icon stehen unter der [MIT-Lizenz](LICENSE).
Der aktuelle Stand ist **0.2.3**. Die GitHub-Actions führen die lokalen Tests bei
Push und Pull Request aus. Ein gepushter Versionstag erstellt einen
Release-Entwurf mit Installations-ZIP.

[Veröffentlichungsanleitung](docs/PUBLISHING.md): lokale Prüfungen,
ZIP-Erstellung, HTTPS-Anmeldung, Anlegen des neuen GitHub-Repositories,
erster Push und Release. `origin` ist auf
`https://github.com/matzem79/home-assistant-energy-costs.git` eingerichtet und
nutzt die vorhandene GitHub-CLI-Anmeldung. Das Zielrepository muss vor dem
ersten Push noch auf GitHub angelegt werden; ein Push erstellt es nicht selbst.
Die lokale Vorbereitung veröffentlicht nichts auf GitHub.

```sh
python3 scripts/build_release.py
```

Erstellt `dist/energy-costs-0.2.3.zip` mit Integration, Icon und Dokumentation.

Referenzen:
[HA Config Flow](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/),
[HA Options Flow](https://developers.home-assistant.io/docs/config_entries_options_flow_handler/),
[HA Sensoren](https://developers.home-assistant.io/docs/core/entity/sensor/).
