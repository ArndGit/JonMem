# Projektplan: ADHS-optimierte Karteikarten-App (Kivy)

## Ziel
Eine klare, realistisch umsetzbare Konzeption als Grundlage für eine Python/Kivy-Implementierung, mit besonderem Fokus auf Eingabemethoden (Text, Stift, Sprache) unter Offline- und Lizenzbedingungen (LGPL/permissive Open Source).

## Leitlinien (aus dem Briefing abgeleitet)
- Kurze, begrenzte Sessions (max. 5 Minuten, max. 10 Vokabeln)
- Flaches Pyramiden-System (max. 4 Stufen, Fehler = -1 Stufe)
- Strikte Trennung: Neue Vokabeln vs. Wiederholung
- Feedback: sachlich, motivierend, ohne Druck
- Offline-first, keine kostenpflichtigen APIs, keine nicht-kompatiblen Lizenzen
- Updates duerfen Fortschritt nicht zerstoeren
- Backup und Import/Export als YAML-Datei moeglich

---

## Phase 1: Konzeption & Anforderungen

### 1.1 Lern- und Trainingslogik präzisieren
- Definiere die 4 Stufen der flachen Pyramide (z. B. S1–S4)
- Lege fest, wann eine Vokabel "neu" eingeführt wird
- Bestimme genaue Regeln für Auf-/Abstufung
- Lege fest, wie Sessions zeitlich/inhaltlich geschnitten werden

### 1.2 Trainingsformate
- Pyramiden-Trainingseinheit (5 Minuten, aktives Abrufen)
- Festlegen der Session-Struktur: Einstieg → Training → Feedback
- Zeit- und Item-Limits technisch definieren

### 1.3 Feedback-Logik
- Definition von Punkten/Sternen pro Tag
- Audio-Feedback-Design (kurz, sachlich)
- Wann und wie Eselsbrücken eingeblendet werden

### 1.4 Karten- und Datenstruktur
- Definition der Kartenfelder (Wort, Richtung, Eselsbrücke pro Richtung)
- Themenpakete als sprachspezifische Einheiten
- Startsprache: Englisch (Ausgangssprache Deutsch bleibt)
- Kombination mehrerer Themenpakete pro Session

---

## Phase 2: Eingabemethoden – Machbarkeit & Bewertung

### 2.1 Texteingabe
- Unterstützte Sonderzeichen (Umlaute, Akzente)
- Fehlertoleranz-Konzept (nahe richtig / Akzentfehler)
- Realistische UX in Kivy (virtuelle Tastatur + Custom Input)
- MVP: OS-Tastatur soll idealerweise die aktuelle Sprache unterstuetzen

### 2.2 Stifteingabe (Handschrift)
- Recherche nach Open-Source Handschrift-Erkennung (offline)
- Bewertung nach:
  - Lizenz (LGPL/permissive)
  - Offline-Tauglichkeit
  - Erkennungsqualität einzelner Wörter
  - Einbindung in Python/Kivy

### 2.3 Spracherkennung
- Recherche nach lokaler ASR (offline)
- Bewertung nach:
  - Lizenz
  - Modelle pro Sprache
  - Performance auf mobilen Geräten
  - Qualität bei Akzent/Kinderstimme

### 2.4 Realistische Empfehlung
- Entscheidung: Text als Standard, Stift/Sprache optional?
- Priorisierung für MVP
- Festlegung: Stift und Sprache als Features fuer spaeter


---

## Phase 3: UX-Konzept & Motivationslogik

### 3.1 Kalenderansicht
- Darstellung der absolvierten Sessions (Sterne/Marker)
- Keine negativen Markierungen
- Fokus auf Kontinuität

### 3.2 Flow-Design
- Nutzerführung ohne Überforderung
- Klare Trennung: Einführung vs. Wiederholung
- Minimalistisches Layout, ADHS-optimiert

---

## Phase 4: Ergebnisdokumentation

### 4.1 Konzeptdokument
- Zusammenfassung aller Lernregeln
- Beschreibung der Kartenstruktur
- Eingabemethoden-Bewertung mit Begründung
- Empfehlung für MVP (realistisch umsetzbar)

### 4.2 Technische Notizen für Kivy
- Hinweise zu möglichen Libraries (Text, ASR, Stift)
- Buildozer-Constraints & Plattform-Risiken

---

## Offene Entscheidungen (zu klaeren)

- Feinschliff der Fortschritts-/Backup-Architektur (update-sicher)

- Reihenfolge der Plattformziele (Android zuerst, iOS nachziehen)



---



## Prioritaeten / Umsetzungsschritte (konkret)
1. JonTrain-Kram entfernen oder umbauen; Projekt fuer GitHub (Android/iOS) lauffaehig machen und lokal als `uv`-Projekt betreiben
2. JonMem-Hauptmenue: Kalender + Training starten + Vokabeln eingeben
3.1 YAML-Seed im Projekt anlegen (Deutsch/Englisch, 20 Woerter, Thema "Uhrzeit", Eselsbruecken in beide Richtungen); wird installiert, aber nie ueberschrieben, falls auf Zielsystem schon vorhanden
3.2 Trainings-Session inkl. Eselsbruecken implementieren
3.3 Vokabel-Eingabe implementieren (Sprache/Neue-Sprache -> Thema/Neues-Thema -> Eingabe)
3.4 Trainingsprotokollierung und Fortschritt speichern (update-sicher), Backup-Konzept und Kalender-Ansicht ableiten
4. Hamburger-Menue: Lizenz, Support-Link (wie JonTrain: PayPal Planetarium) + Backup-Funktionen
5. Debugging: Wenn ein Import fehlschlaegt, Fehlerreport als kopierbarer Text (ohne ADB)
6. Doku, Logo, Splash-Screen
7. OS-Benachrichtigung, wenn Training > 24h her ist
