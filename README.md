[Metadata Source Plugin] Perrypedia - Version 1.8.0 - 07-12-2023

[English version follows]

Dieses Plugin verwendet die Perrypedia als Metadatenquelle. Es lädt Metadaten und Cover herunter.
Die Perrypedia (https://www.perrypedia.de/) ist ein Fanprojekt zur Erstellung eines kostenlosen Nachschlagewerks für die Perry Rhodan SF-Serie.
Epubs aus dem offiziellen Verlagsshop enthalten wenig Informationen, das Titelfeld enthält nicht nur den Titel, sondern auch die Serien- und Ausgabenummer ("PR 3082 - Ein kalkuliertes Risiko").

Haupteigenschaften:
-------------------
Dieses Plugin unterstützt das Abrufen von Titeln, Autoren, Tags, Veröffentlichungsdatum, Verlag, Kommentaren, Serien, Serienindex und Cover.
Titel, Autoren, Veröffentlichungsdatum, Herausgeber, Serie, Serienindex und Cover werden in den entsprechenden Metadatenfeldern gespeichert.
Das Tag-Feld wird gefüllt mit dem Inhalt der Rubriken "Zyklus", "Hauptpersonen", "Handlungszeitraum", "Handlungsort" und "Glossar".
Der erste Teil des Kommentarfeldes wird mit der Übersichtstabelle einer Standard-Perrypedia-Publikationsseite gefüllt.

Da die meisten "Bücher" in der Perry Rhodan-Reihe keine Kennung wie ISBN oder ISSN haben, definiert das Plugin eine "PPID", die aus Perrypedia-Kennungen stammt (z. B. "PR1000" für Ausgabe 1000 der Perry Rhodan-Heftserie) ).
Eine Liste der Produkte mit ihren Namen und IDs finden Sie hier: https://www.perrypedia.de/wiki/Produkte
Hinweis: Wenn die Perrypedia-Buchseite eine ISBN enthält (für Hardcover und Taschenbücher), wird die Nummer dem Feld IDs hinzugefügt.
Am Ende des Kommentarfelds wird eine separate Zeile mit einem Link zur Perrypedia-Buchseite eingefügt.

Die Suche nach Perrypedia-Ressourcen erfolgt in drei Schritten:
1. Das Plugin überprüft das Feld IDs auf eine PPID und wechselt, falls vorhanden, zur zugehörigen Buchseite, um Metadaten abzugreifen.
2. Wenn keine PPID angegeben ist, sucht das Plugin im Titelfeld nach Token (Serien, Unterreihen, Ausgabenummer), um die PPID zu erstellen (mit regulären Ausdrücken und Tabellen, daher ist dies wartungsintensiv im Falle neuer Produkte - die Konfiguration durch den Benutzer ist geplant ).
3. Wenn der PPID-Build fehlschlägt, verwendet das Plugin die Wikimedia API, um nach dem Titel zu suchen.

Geplante Funktionen:
--------------------
- Suchen nach Identifikationsdaten in (physischen) Büchern, wenn Identifikatoren oder Titel nicht ausreichen (da Metadatenplugins nicht auf Buchdateien zugreifen können, ist ein separates GUI-Plugin namens "PerrypediaTools" geplant).
- Herunterladen von anderen Perrypedia-Buchseitenabschnitten (nicht in allen Fällen vorhanden)
- Automatisches Erkennen neuer Mini-Serien und Zyklen

Einschränkungen:
----------------
- Wenn das Veröffentlichungsdatum nur das Jahr enthält, wird das Veröffentlichungsdatum auf den 1. Januar dieses Jahres festgelegt. Wenn nur Monat und Jahr angegeben sind, wird es auf den 1. des Monats festgelegt. Wenn ein Link auf die Seite "Veröffentlichu7ngen" (https://www.perrypedia.de/wiki/Ver%C3%B6ffentlichungen_<jahr>) gesetzt ist, wird als Erscheinungsdatum das dort angegebene letztmögliche eingesetzt. Hinweis: Das genaue Erscheinungsdatum kann optional aus der ISFDB ermittelt werden.
- Da ein Metadaten-Plugin keine benutzerdefinierten Felder füllen kann, werden die Kandidaten für diese Felder, z. B. Unterreihen ("Zyklus"), zeilenweise im Feld "Kommentare" gespeichert.
- Die Handlung ist der zweite Teil des Kommentarfeldes.
- Im Moment führt die Titelsuche nur eine exakte Zeichenfolgenübereinstimmung durch.
- Wenn ein Buch mehr als ein Titelbild enthält, wird beim Massen-Download das erste ausgewählt. In den meisten Fällen handelt es sich um das Original-Cover (bei der Suche nach einzelnen Metadaten werden jedoch alle zur Auswahl angezeigt).

Versionsgeschichte:
-------------------
Version 1.8.0 - 07-12-2023
- Wenn in der Perrypedia nur das Veröffentlichungsjahr angegeben ist, kann das genaue Veröffentlichungsdatum aus der ISFDB bezogen werden.
Version 1.7.0 - 06-29-2023
- Neuer Regex-String (neue Dateinamenstruktur von Bücher-Walther: 'Perry-Rhodan-3225-Der-Mann-aus-Glas.epub')
- Optional: Bewertungen aus https://forum.perry-rhodan.net/ (siehe auch https://pr.mapfa.de/)
Version 1.6.2 - 12-16-2022
- Patch für 'Werkstattband'
Version 1.6.1 - 12-05-2022
- Patch für die Identifikation von Hörbüchern
Version 1.6.0 - 11-30-2022
- Daten für PR-Jahrbücher holen
Version 1.5.0 - 09-28-2022
- Einbeziehung von Kommentaren aus dem "kreis-archiv.de" (jetzt in archive.org) (optional)
Version 1.4.1 - 08-26-2022
- Erweiterung der Regulären Ausdrücke (PR-Storys u. a.)
Version 1.4.0 - 07-12-2022
- Option zum Setzen von ignore_ssl_errors
- Neue Mini-Serie: Atlantis
- Anpassungen für Stellaris Buch-Packete
- Kompatibel mit Calibre 6.0
Version 1.3.0 11-01-2021
- Erweiterte Konfiguration
- Unterstützung weiterer der unter https://www.perrypedia.de/wiki/Produkte aufgeführten Produkte
- Überarbeitung Regex-Zeichenketten
- Aktualisierte Übersetzungen
Version 1.2.0 05-17-2021
- Konfiguration über Calibre-Oberfläche
- Verbesserte Behandlung von mehrdeutigen Titeln
- Unterstützung weiterer der unter https://www.perrypedia.de/wiki/Produkte aufgeführten Produkte
- Beseitigung von Code-Dopplungen
- Aktualisierte Übersetzungen 
- Weiteres Serienformat: "Leihbuch"
- Überarbeitung Regex-Zeichenketten
- Handlungsebene in Übersicht eingefügt
- Ermittlung von Serien-Codes verfeinert (Atlas Traversan, Obsidian)
- Bereinigung des "publisher"-Feldes
- Verfeinerte Ermittlung des Erscheinungsdatums
- Fehler beim Parsen des deutschen Datums behoben (dayfirst)
- Behandlung von nicht serienbezogenen Büchern (Weltraumatlas, Risszeichnungen, ...)
Version 1.1.0 01-19-2021
- Titelsuche (mit Behandlung von mehrdeutigen Titeln)
- Nutzung der Wikimedia API
- Unterstützung für die meisten der unter https://www.perrypedia.de/wiki/Produkte aufgeführten Produkte
- Aktualisierte Übersetzungen 
Version 1.0.0 11-30-2020
- Optimierte Bildersuche
- HTML-Ausgabe des Kommentars
- Kleiner Fehlerkorrekturen und Verbesserungen
Version 0.1.0 11-14-2020
- Erstveröffentlichung

Installation:
-------------
Laden Sie die angehängte Zip-Datei herunter und installieren Sie das Plugin wie im sticky thread "Introduction to plugins" beschrieben.

So melden Sie Fehler und Vorschläge:
-----------------------------------
Wenn Sie Fehler finden oder Vorschläge haben, melden Sie diese bitte in diesem Thread.

---

[Metadata Source Plugin] Perrypedia - Version 1.8.0 - 07-12-2023

This plugin uses Perrypedia as metadata source. It downloads metadata and covers. 
Perrypedia (https://www.perrypedia.de/) is a fan project for the creation of a free reference work for the Perry Rhodan SF series.
Epubs from the official publisher's shop contains little information, the title field contains not only the title, but also the series and issue number ("PR 3082 - Ein kalkuliertes Risiko").

Main features:
--------------
This plugin supports retrieval of title, authors, tags, publication date, publisher, comments, series, series index and cover.
Title, authors, publication date, publisher, series, series index and cover are saved in the appropriate metadata fields.
The tag field is filled with the content of the categories "Cycle" (Zyklus), "Main Characters" (Hauptpersonen), "action time" (Handlungszeitraum), "scene of action" (Handlungsort) and "Glossary" (Glossar).
The first part of the comment field is filled with the summary table of a standard Perrypedia publication page.

Since most of the "books" in the Perry Rhodan series do not have an identifier such as ISBN or ISSN, the plugin defines a "PPID" which is taken from Perrypedia identifiers (e.g. "PR1000" for issue 1000 of the Perry Rhodan booklet series).
A list of products with their names and IDs can be found here: https://www.perrypedia.de/wiki/Produkte
Note: If the Perrypedia book page contains an ISBN (for the hardcovers and paperbacks) the number is added to the IDs field.
At the end of the comments field a seperate line with a link to the Perrypedia book page is inserted.

The search for Perrypedia resources is a three step:
1. The plugin checks the IDs field for a PPID and, if present, goes to the associated book page for scraping metadata
2. If no PPID is given, the plugin looks for tokens (series, subseries, issue number) in the title field to create the PPID (with regular expressions and tables, so this is a matter of maintenance - configuration by the user is planned). 
3. If the PPID build fails, the plugin will use the Wikimedia search API for a title search.

Planned Features:
-----------------
- Search for identification data in (physical) books if identifiers or title are not sufficient (since metadataplugins cannot access book files, a seperate GUI plugin named "PerrypediaTools" is planned)
- Downloading from other Perrypedia book page sections (not present in all cases)

Limitations:
------------
- If the returned publication date contains only the year, the publish date is set to january, 1 of that year. If only month and year are given, it will be set to the 1st of the month. If there is a link to the "Publications" page (https://www.perrypedia.de/wiki/Ver%C3%B6ffentlichungen_<jahr>), the latest possible publication date is used as the publication date. Note: The exact release date can optionally be determined from the ISFDB.
- Since a metadata plugin cannot fill userdefined fields, the candidates for those fields, for example subseries ("Zyklus"), are saved in the Comments field, line by line.
- The plot ("Handlung") will be the second part of the comments field.
- At the moment the title search does only a exact string matching
- If a book has more than one cover image, the bulk download selects the first on - in most cases this is the original cover (the single metadata search however presents all for selection).

Version History:
----------------
Version 1.8.0 - 07-12-2023
- If Perrypedia has only the publishing year, get the complete date from isfdb.org, if configured
Version 1.7.0 - 06-29-2023
- New regex string (new file name structure of Walther publishing: 'Perry-Rhodan-3225-Der-Mann-aus-Glas.epub')
- Optional rating from https://forum.perry-rhodan.net/ (see also https://pr.mapfa.de/)
Version 1.6.2 - 12-16-2022
- Patch for 'Werkstattband'
Version 1.6.1 - 12-05-2022
- Patch for identifying audio books
Version 1.6.0 - 11-30-2022
- Find data for PR-Jahrbuch
- Updated translations
Version 1.5.0 - 09-28-2022
- Inklusion of comments from "kreis-archiv.de" (now from archive.org) (optional)
Version 1.4.1 - 08-26-2022
- Extended Regular Expressions (PR-Storys etc.)
Version 1.4.0 - 07-12-2022
- Option to set ignore_ssl_errors
- New Mini serie: Atlantis
- Special page handling for Stellaris book packets
- Compatible with Calibre 6.0
Version 1.3.0 - 11-01-2021
- Advanced configuration
- Support of other products listed under https://www.perrypedia.de/wiki/Produkte
- Revision of regex strings
- Updated translations
Version 1.2.0 - 05-17-2021
- Configuration via calibre GUI
- Improved handling of ambiguous titles
- Support of other products listed under https://www.perrypedia.de/wiki/Produkte
- Elimination of code duplication
- Updated translations
- Another series format: "Leihbuch"
- Revision of regex strings
- Action level added to overview
- Refined determination of serial codes (Atlan Traversan, Obsidian)
- Adjustment of the "publisher" field
- Refined determination of the publishing date
- Fixed bug when parsing the German date (dayfirst)
- Treatment of books not related to series (Weltraumatlas, Risszeichnungen, ...)
Version 1.1.0 - 01-19-2021
- Search for title (with handling of ambiguous titles)
- Using of Wikimedia API
- support for most of the products listed on https://www.perrypedia.de/wiki/Produkte
- Updated translations
Version 1.0.0 11-30-2020
- better cover search
- HTML-Output for comments-Field
- Minor bugfixes and enhancements
Version 0.1.0 - 11-14-2020
- Initial release

Installation:
-------------
Download the attached zip file and install the plugin as described in the Introduction to plugins thread.

How to report Bugs and suggestions:
-----------------------------------
If you find any issues or have suggestions please report them in this thread.
