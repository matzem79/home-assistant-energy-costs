# GitHub-Veröffentlichung

Vorgesehenes Repository: `matzem79/home-assistant-energy-costs`.
Der Stand 0.2.3 ist lokal vorbereitet. Als `origin` ist
`git@github.com:matzem79/home-assistant-energy-costs.git` vorgesehen.
Diese Vorbereitung erstellt weder ein GitHub-Repository noch einen Release.
Quellcode und eigenes Icon stehen unter der MIT-Lizenz in `LICENSE`.

## Lokal prüfen und paketieren

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q custom_components scripts
python3 scripts/build_release.py
git diff --check
git status --short
```

Das Installationspaket liegt unter `dist/energy-costs-0.2.3.zip`. Es enthält den
Integrationsordner einschließlich `brand/`, README, Changelog und Lizenz.
Lokale CSV-Dateien, ZIPs, Editor-Dateien, Python-Caches und Tests werden nicht
in das Installationspaket übernommen. ZIPs und lokale Umgebungen sind per
`.gitignore` von Git ausgeschlossen.

Die Tests verwenden HA-Testdoubles. Sie ersetzen keinen vollständigen
Home-Assistant-/hassfest-Lauf. Vor einem öffentlichen Release insbesondere
Einrichtung, Optionen, Neustart, Historienimport und Iconanzeige in HA prüfen.
Lokale Brand-Icons benötigen HA 2026.3 oder neuer; die übrige Integration setzt
HA 2026.1 oder neuer voraus.

## Ersten Push ausführen

Der vorbereitete Stand ist lokal committed. Vor dem Push Remote und Status prüfen:

```sh
git remote -v
git status --short
git log -1 --oneline
```

Wenn das Zielrepository noch nicht existiert, kann es mit GitHub CLI angelegt
werden. Der folgende Befehl legt es **öffentlich** an. `origin` ist lokal bereits
vorbereitet und wird dabei nicht erneut angelegt:

```sh
gh repo create matzem79/home-assistant-energy-costs --public --description "Independent import and export electricity cost accounting for Home Assistant"
git push -u origin main
```

Existiert das Repository bereits, reicht:

```sh
git push -u origin main
```

Nur einen der beiden Wege verwenden. Das Ziel von `origin` vor dem Push prüfen. Die vorhandene Tests-Action läuft
bei Push und Pull Request.

## Release vorbereiten

Nach erfolgreichem CI-Lauf und manuellem HA-Test:

```sh
git tag -a v0.2.3 -m "Energy Costs 0.2.3"
git push origin v0.2.3
```

Der Tag-Workflow prüft Version und Tests, baut das ZIP und legt einen
**Release-Entwurf** mit Installationspaket auf GitHub an. Der Release wird erst
durch anschließendes Veröffentlichen des Entwurfs öffentlich sichtbar.
Ein Tag, der nicht zur Version in `manifest.json` passt, wird abgewiesen.

## HACS

Nach Veröffentlichung lässt sich die Repository-URL in HACS als benutzerdefiniertes
Repository vom Typ **Integration** hinzufügen. `hacs.json` und die Struktur
`custom_components/energy_costs` sind dafür vorhanden. Eine Aufnahme in die
HACS-Standardliste ist ein separater Schritt; das Projekt ist dort nicht gelistet.
