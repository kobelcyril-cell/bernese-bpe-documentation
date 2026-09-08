# Release-Paket: Bernese-BPE-Manual auf Linux

Dieses Paket enthält den fertigen Manual-Ersteller update_manual.py. Die bisherigen GPSUSER waren nur Testdaten und sind nicht enthalten. Der Upload dieses Release-Pakets fragt niemals nach GPSUSER-Pfaden.

## Dateien und Berechtigungen

| Datei/Ordner | Zweck | Berechtigung |
|---|---|---|
| update_manual.py | Analysiert PCF/, SCRIPT/ und OPT/ einer GPSUSER und erzeugt HTML-Dokumentation. | Nur du bearbeiten/ausführen |
| manual_config.json | Linux-spezifische Standardwerte für die Abfragen und Pfade. | Nur du bearbeiten |
| publish_manual_linux.sh | Prüft site/ und commitet/pusht das fertige Manual nach GitHub. | Nur du ausführen/bearbeiten |
| manual_additions/handbook/ | Eigene zusätzliche Handbuchseiten als Markdown. | Nur du bearbeiten |
| manual_additions/comments/ | Kommentare und Anmerkungen zum Manual. | Nur du bearbeiten |
| manual_additions/history/ | Änderungsverlauf des Handbuchteils. | Nur der Builder beschreiben |
| manual_additions/import/ | Optionaler lokaler Importbereich für zusätzliche Markdown-Handbuchquellen. | Nur du bearbeiten |
| .github/workflows/deploy-pages.yml | GitHub-Workflow zur Veröffentlichung von site/. | Nur du bearbeiten |
| site/ | Erzeugte Website. Wird vom Builder erstellt. | Nicht manuell bearbeiten |
| output/ | Optionale lokale Zwischenergebnisse. | Nicht manuell bearbeiten |

Bei einem privaten GitHub-Repository können nur du und ausdrücklich berechtigte Personen die Quelldateien sehen. Bei einem öffentlichen Repository sind auch update_manual.py, Workflow und Zusatztexte öffentlich. Die Pages-Seite kann separat öffentlich sein.

## Konfiguration der Standardwerte

Die Datei manual_config.json enthält die Linux-spezifischen Standardwerte. Sie kann nach dem Übertragen auf Linux mit einem Editor angepasst werden. update_manual.py muss dafür nicht geändert werden.

    {
      "default_user": "Cyril Kobel",
      "default_action": "a",
      "output_dir": "site",
      "source_list_file": "manual_sources.txt",
      "default_comment_title": "Zusätzliche Notiz",
      "handbook_import_dir": "manual_additions/import",
      "handbook_full_top_levels": [],
      "handbook_group_descriptions": {}
    }

Bedeutung der Werte:

- default_user: Vorgabename für den Änderungsverlauf.
- default_action: Vorgabe im Startmenü. a baut das Manual ohne Zusatzaktion.
- output_dir: Standardordner für die erzeugten HTML-Dateien.
- source_list_file: Datei mit konfigurierten GPSUSER-Pfaden, sofern der Builder ohne --source-dir gestartet wird.
- default_comment_title: Titel, wenn bei einem neuen Kommentar kein Titel eingegeben wird.
- handbook_import_dir: optionaler Importbereich für zusätzliche Markdown-Seiten.
- handbook_full_top_levels: Handbook-Kategorien, die standardmäßig vollständig angezeigt werden.
- handbook_group_descriptions: Beschreibungstexte für Handbook-Kategorien als JSON-Objekt.

Beispiel zum Anpassen:

    nano manual_config.json

## 1. Linux vorbereiten

    sudo apt update
    sudo apt install -y git python3
    git --version
    python3 --version

In den Release-Ordner wechseln:

    cd /PFAD/ZU/Documentation_builder_linux_release
    chmod 700 publish_manual_linux.sh
    chmod 700 update_manual.py
    chmod 700 manual_additions

Git konfigurieren:

    git config --global user.name "DEIN NAME"
    git config --global user.email "DEINE_GITHUB_EMAIL"

## 2. GitHub-Zugang einrichten

    ssh-keygen -t ed25519 -C "DEINE_GITHUB_EMAIL"
    cat ~/.ssh/id_ed25519.pub

Den ausgegebenen Schlüssel in GitHub unter Settings -> SSH and GPG keys -> New SSH key eintragen und testen:

    ssh -T git@github.com

## 3. Leeres GitHub-Repository erstellen

Auf GitHub ein neues Repository erstellen, zum Beispiel bernese-bpe-manual.

Beim Erstellen möglichst kein README, keine Lizenz und kein automatisch erzeugtes .gitignore hinzufügen.

Die SSH-Adresse notieren:

    git@github.com:DEIN_GITHUB_NAME/bernese-bpe-manual.git

## 4. Eigene GPSUSER vorbereiten

Jede GPSUSER-Installation muss diese Struktur besitzen:

    GPSUSER/
    ├── PCF/
    ├── SCRIPT/
    └── OPT/

Prüfen:

    find /PFAD/ZUR/GPSUSER -maxdepth 2 -type d | sort
    test -d /PFAD/ZUR/GPSUSER/PCF
    test -d /PFAD/ZUR/GPSUSER/SCRIPT
    test -d /PFAD/ZUR/GPSUSER/OPT

Die GPSUSER bleibt an ihrem normalen Linux-Ort. Sie muss nicht in dieses Release-Paket kopiert werden.

## 5. Eigene Handbuchseiten hinzufügen

Eine zusätzliche Handbuchseite erstellen:

    nano manual_additions/handbook/00_Start.md

Beispielinhalt:

    # Start

    Beschreibe hier die allgemeinen Voraussetzungen und den ersten Arbeitsschritt.

    ## Ablauf

    1. Erster Schritt
    2. Zweiter Schritt
    3. Dritter Schritt

Weitere Seiten mit sortierten Dateinamen anlegen:

    nano manual_additions/handbook/01_System_Overview.md
    nano manual_additions/handbook/02_Operation.md

## 6. Fertiges Manual nach GitHub hochladen

Der Release-Ordner fragt niemals nach GPSUSER-Pfaden. Vor dem Upload muss ein fertiges site/-Verzeichnis mit site/index.html vorhanden sein.

    ./publish_manual_linux.sh

Dieses Skript prüft nur site/index.html, richtet beim ersten Lauf das lokale Git-Repository ein und führt dann aus:

    git add -A
    git commit -m "Build and publish manual"
    git push -u origin HEAD:main

Beim ersten Lauf fragt publish_manual_linux.sh zusätzlich nur nach der GitHub-Repository-URL.

## 7. GitHub Pages aktivieren

Nach dem ersten Push im GitHub-Repository öffnen:

    Settings -> Pages -> Build and deployment -> Source -> GitHub Actions

Unter Actions muss der Workflow Deploy manual site erfolgreich laufen. Danach ist die Seite normalerweise unter dieser Adresse erreichbar:

    https://DEIN_GITHUB_NAME.github.io/bernese-bpe-manual/

## 8. Nur lokal bauen

    python3 update_manual.py \
      --source-dir /PFAD/ZUR/GPSUSER \
      --output-dir ./site \
      --no-prompts

Lokalen Webserver starten:

    python3 -m http.server 8000 --directory site

Im Browser öffnen:

    http://localhost:8000/

Webserver beenden:

    Strg+C

## 9. Kommentare und Handbuchseiten bearbeiten

Eine Handbuchseite interaktiv hinzufügen:

    python3 update_manual.py \
      --source-dir /PFAD/ZUR/GPSUSER \
      --output-dir ./site \
      --add-handbook-entry

Eine Handbuchseite bearbeiten:

    python3 update_manual.py \
      --source-dir /PFAD/ZUR/GPSUSER \
      --output-dir ./site \
      --edit-handbook-entry

Einen Kommentar hinzufügen:

    python3 update_manual.py \
      --source-dir /PFAD/ZUR/GPSUSER \
      --output-dir ./site \
      --add-comment

Danach die erzeugte Website hochladen:

    git add -A
    git commit -m "Update manual content"
    git push origin main

## 10. Kontrolle und Fehlerbehebung

    git status
    git remote -v
    git branch --show-current
    git log --oneline -5
    test -f site/index.html

Wenn GitHub Pages eine alte Version zeigt, unter Actions den Lauf Deploy manual site prüfen. Nur ein erfolgreicher Workflow veröffentlicht die neue Version. Im Browser anschließend Strg+F5 drücken.

Wenn die GPSUSER-Prüfung fehlschlägt, müssen genau diese Ordner vorhanden sein:

    /PFAD/ZUR/GPSUSER/PCF
    /PFAD/ZUR/GPSUSER/SCRIPT
    /PFAD/ZUR/GPSUSER/OPT
