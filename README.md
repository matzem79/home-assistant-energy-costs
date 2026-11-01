# Energy Costs für Home Assistant

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
oder das mitgelieferte ZIP. In HACS wäre später ein eigener Custom-Repository-
Eintrag möglich.

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
| Gültig ab | Optionales Datum für diese Preise, Grundgebühr und Monatszahlungen; leer bedeutet heute |
| Beginn Abrechnungsjahr Bezug | Eigener jährlicher Abrechnungsbeginn für den Liefervertrag |
| Beginn Abrechnungsjahr Einspeisung | Eigener jährlicher Abrechnungsbeginn für die Einspeiseabrechnung |
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

- Ohne Datum: gültig ab heute, **00:00 Uhr** in der HA-Zeitzone.
- Zukünftiges Datum: Die bisherigen Preise gelten bis einschließlich Vortag.
- Rückwirkendes Datum: Die gespeicherten täglichen Energiemengen werden ab
  diesem Datum mit den neuen Preisen neu bewertet.

Es erfolgt keine Umrechnung historischer Tage mit einem beliebig späteren
Tarif. Ein rückdatierter Preis kann aber nur bereits **erfasste** Energiemengen
neu bewerten. Die Integration importiert keine früheren Zählerdaten aus dem
Recorder. Frühere Recorder-Statistiken werden nicht umgeschrieben; die neu
berechneten aktuellen Perioden-/Gesamtwerte können deshalb von alten Graphen
abweichen.

Alle Angaben eines Tarifeintrags teilen sich das Gültigkeitsdatum, einschließlich
Monatsabschlag und Einspeisegutschrift. Die Währung wird beim Einrichten aus HA
übernommen und bleibt für diesen Eintrag erhalten; keine automatische Währungs-
umrechnung. Negative kWh-Preise sind möglich, negative Grundgebühren oder
Monatszahlungen nicht.

## Sensoren

Es werden 26 Sensoren an einem gemeinsamen Gerät angelegt:

- Netzbezug in kWh: heute, Monat, Bezugs-Abrechnungsjahr, gesamt.
- Einspeisung in kWh: heute, Monat, Einspeise-Abrechnungsjahr, gesamt.
- Bezugskosten: heute, Monat, Bezugs-Abrechnungsjahr, gesamt.
- Einspeisevergütung: heute, Monat, Einspeise-Abrechnungsjahr, gesamt.
- Aufgelaufene Grundgebühr: heute, Monat, Bezugs-Abrechnungsjahr, gesamt.
- Jeweils bezogen auf das eigene Abrechnungsjahr: Abschläge/Gutschriften,
  Saldo und Abrechnungsstatus für Bezug und Einspeisung.

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

44 lokale Tests erfolgreich: Einheiten, Bezug/Einspeisung, Tarifänderungen,
Rückdatierung, Grundgebühr, Monats-/Jahresgrenzen, Schaltjahr/Zeitumstellung,
Neustart, Zählerreset, getrennte Abrechnungsjahre, Abschläge, Saldenvorzeichen,
Anfangssaldo sowie Aufbau und Speichern der Konfigurationsdialoge.
Die HA-Grenzen sind in den Tests durch kleine Testdoubles ersetzt. Noch kein
Live-Test dieser neuen Integration, kein vollständiger HA-/hassfest-Lauf.

Das Projekt liegt wegen der aktuellen Schreibgrenze vorläufig unter
`AI/50five/energy-costs`. Nach Abschluss in einem normalen Terminal nach
`AI/energy-costs` verschieben. Es ist ein eigenes Projekt und gehört nicht zum
50five-Fork. Keine Zugangsdaten enthalten, keine GitHub-Veröffentlichung erfolgt.

Referenzen:
[HA Config Flow](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/),
[HA Options Flow](https://developers.home-assistant.io/docs/config_entries_options_flow_handler/),
[HA Sensoren](https://developers.home-assistant.io/docs/core/entity/sensor/).
