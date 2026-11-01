# GitHub-Veröffentlichung

Vorgesehenes Repository: `matzem79/home-assistant-energy-costs`.
Der Stand 0.2.3 ist lokal vorbereitet. `origin` ist auf HTTPS eingerichtet:
`https://github.com/matzem79/home-assistant-energy-costs.git`.
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

## Anmeldung und aktueller Stand

- Branch: `main`, Änderungen lokal committed.
- GitHub-Konto: `matzem79`; die GitHub CLI war bei der letzten Prüfung gültig angemeldet.
- Der SSH-Push scheiterte mit `Permission denied (publickey)`.
- `origin` wurde deshalb auf HTTPS umgestellt. Dieses lokale Repository verwendet
  die GitHub CLI als Credential-Helper; Tokens stehen nicht in Remote-URL oder Dateien.
- Das Zielrepository war bei der letzten Prüfung unter diesem Konto nicht auffindbar.
- Noch kein erfolgreicher Push, kein Versionstag und kein GitHub-Release.

Alle folgenden Befehle im lokalen Projektordner `energy-costs` ausführen.
Zuerst prüfen:

```sh
gh auth status
git remote -v
git status --short
git log -1 --oneline
```

Falls die Anmeldung fehlt oder abgelaufen ist:

```sh
gh auth login --hostname github.com --git-protocol https --web
```

Auf einem weiteren Rechner lassen sich HTTPS-Remote und der Credential-Helper
für dieses Repository so einrichten (auf dem vorbereiteten Rechner bereits erledigt):

```sh
git remote set-url origin https://github.com/matzem79/home-assistant-energy-costs.git
git config --local --replace-all credential.https://github.com.helper ''
git config --local --add credential.https://github.com.helper '!gh auth git-credential'
```

## Neues GitHub-Repository anlegen und erster Push

Der fehlende Schritt vor dem ersten Push ist das Anlegen des Zielrepositories.
Zunächst **privat** anlegen; die Sichtbarkeit kann später in GitHub geändert werden:

```sh
gh repo create matzem79/home-assistant-energy-costs --private --description "Independent import and export electricity cost accounting for Home Assistant"
git push -u origin main
```

Soll das Repository direkt **öffentlich** sein, beim Erstellen `--public` statt
`--private` verwenden. Nur eine der Varianten ausführen. Ein normaler Push legt
ein fehlendes GitHub-Repository nicht automatisch an.

Alternativ das Repository auf der GitHub-Webseite mit Owner `matzem79` und Namen
`home-assistant-energy-costs` **leer** anlegen: dort weder README noch Lizenz noch
`.gitignore` erzeugen lassen, da diese Dateien bereits lokal committed sind.
Danach reicht `git push -u origin main`. `origin` nicht erneut hinzufügen.

Existiert das Repository inzwischen bereits, vor dem Push prüfen:

```sh
gh repo view matzem79/home-assistant-energy-costs --json nameWithOwner,url,isPrivate
```

Nach erfolgreichem Push:

```sh
git status -sb
gh run list --limit 5
```

Die Tests-Action läuft bei Push und Pull Request. Ein Push von `main` allein
erstellt keinen Release. Bis hierhin muss kein Tag angelegt werden.

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
