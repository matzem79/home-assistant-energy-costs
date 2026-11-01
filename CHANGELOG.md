# Änderungen

## 0.2.3 — lokal vorbereitet

- Eigenes Integrationsicon als transparente PNGs in 256/512 Pixeln unter `brand/`, für HA ab 2026.3.
- Bearbeitbare SVG-Quelle und reproduzierbare Icon-Erstellung ohne Zusatzpakete.
- README zu Iconanzeige und Bezugskosten ohne Grundgebühr ergänzt.
- MIT-Lizenz, Anleitung für GitHub-Push/Release und sauberer ZIP-Build ergänzt.
- Tag-Workflow prüft Version und Tests und erstellt einen GitHub-Release-Entwurf mit Installationspaket.
- Lokale macOS-Dateien und Build-Ausgaben von Git ausgeschlossen.
- Iconanzeige nach manueller Installation in HA bestätigt; Hinweise zu Browsercache und Update ohne Löschen der Integration dokumentiert.
- HTTPS-Remote und lokale GitHub-CLI-Anmeldung für den ersten Push vorbereitet; Anleitung zum Anlegen eines neuen, leeren GitHub-Repositories ergänzt.
- 67 isolierte Tests; kein GitHub-Push oder Release ausgeführt.

## 0.2.2 — lokal vorbereitet

- Eigenes optionales Startdatum für monatliche Einspeiseauszahlungen, unabhängig vom Abrechnungsjahr und Tarifbeginn.
- Abrechnungsjahr Januar und 10 EUR monatlich ab April ergeben bis November 80 EUR; die verdiente Jahresvergütung bleibt unabhängig davon.
- Anzahl und vollständige Tarifübersicht im Konfigurationsdialog.
- Abrechnungssensoren zeigen gespeicherte Tarife und die einzelnen berücksichtigten Zahlungstermine mit Betrag und Tarifdatum.
- 67 isolierte Tests erfolgreich; Live-HA-Test weiterhin offen.

## 0.2.1 — lokal vorbereitet

- Historischen Ausgangswert bis zu 31 Tage vor dem Abrechnungsbeginn suchen, statt nur zwei Stunden.
- Abstände zwischen kumulativen Statistikwerten erhalten die bekannte Gesamtmenge; ihre zeitliche Verteilung wird als geschätzt ausgewiesen.
- Geschätzten Anfangsstand am Abrechnungsbeginn ausdrücklich als unvollständig kennzeichnen.
- Diagnoseattribute zu fehlendem Anfangsstand, Preisen, Zahlungstarifen und Rücksprüngen ergänzen.
- Ältere Importe beim Update einmalig neu aufbauen; Neustarts zählen weiterhin keine Energie doppelt.
- 61 isolierte Tests erfolgreich, einschließlich einer mehrtägigen Lücke über dem 01.04.; Live-HA-Test weiterhin offen.

## 0.2.0 — lokal vorbereitet

- Optionaler Import historischer Energie aus Recorder-Langzeitstatistiken, getrennt ab Bezugs- und Einspeise-Abrechnungsbeginn.
- Stündliche resetbereinigte Energiesummen in kWh mit Übergang zum aktuellen Zählerstand.
- Getrennte persistente Erfassungsbeginne für Kosten, Grundgebühr, Monatszahlungen und Salden.
- Importstatus und Datenlücken als Sensorattribute; bisherige Live-Daten bleiben bei fehlender Statistik erhalten.
- Erfolgreiche vollständige Importe werden bei Neustart nicht wiederholt; Preise bleiben rückwirkend änderbar.
- 56 isolierte Tests erfolgreich; Live-HA-Test weiterhin offen.

## 0.1.0 — lokal vorbereitet

- Eigenständige Home-Assistant-Integration mit UI-Einrichtung.
- Netzbezug und Einspeisung unabhängig erfassen.
- Bezugspreis, Einspeisevergütung und monatliche Grundgebühr.
- Tarifverlauf mit optionalem Gültigkeitsdatum und Rückdatierung.
- Separate monatliche Abschläge bzw. ausgezahlte Einspeisegutschriften.
- Zwei unabhängige Jahresabrechnungszeiträume mit Saldo und Status.
- Optionale Anfangssalden für den Einstieg im laufenden Abrechnungsjahr.
- 26 Sensoren, persistente Daten und deutsche/englische Oberfläche.
- 44 isolierte Tests; Live-HA-Test noch offen.
