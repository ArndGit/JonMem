# JonMem

ADHS-optimierte Karteikarten-App (Kivy) mit Spaced-Repetition und „Pyramiden“-Training.

## Features
- Vokabeln nach Sprache und Themen erfassen
- Einführen (neue Karten) und Wiederholen (gelernte Karten)
- Pyramiden-Training mit Stufen (Leitner-ähnlich)
- Themenfilter für Wiederholen (persistente Experten-Option)
- Export/Import der lokalen Datenbank (YAML)

## Datenformat (kurz)
- Karten haben immer:
  - `de`: Deutsch
  - `en`: Zielsprache (unabhängig vom Sprachcode)
  - `lang`: Zielsprachcode (z.B. `en`, `es`)
  - `topic`: Themen-ID
- Fortschritt wird pro Karte und pro Richtung gespeichert.

## Pyramiden-Training: exakte Regeln
**Konstanten (aktuell):**
- Max. Session-Länge: `SESSION_MAX_ITEMS = 10`
- Zeit pro Session: `SESSION_SECONDS = 300`
- Max. Stufe: `MAX_STAGE = 4`
- Einführen-Wiederholungen: `INTRODUCE_REPEAT_COUNT = 2`
- Pyramiden-Gewichte: `1:4, 2:3, 3:2, 4:1`

**Allgemein:**
- Fortschritt (`stage`) wird **pro Karte und pro Richtung** gespeichert.
- Stufe ist **nicht** abhängig von Themen-Kombinationen.
- Richtungen:
  - `de_to_en` (Deutsch → Zielsprache)
  - `en_to_de` (Zielsprache → Deutsch)

### Einführen (neue Karten)
1. Es werden nur Karten berücksichtigt, die **noch keinen Fortschritt** für die gewählte Richtung haben.
2. Pro Session wird eine begrenzte Anzahl **neuer** Karten ausgewählt:  
   `unique_limit = SESSION_MAX_ITEMS / INTRODUCE_REPEAT_COUNT`
3. Diese neuen Karten werden **innerhalb derselben Session wiederholt**:  
   Gesamtliste = `unique_cards * INTRODUCE_REPEAT_COUNT`.
4. Die Reihenfolge wird so gemischt, dass **die gleiche Karte nicht direkt hintereinander** erscheint.

### Wiederholen (gelernte Karten)
1. Es werden nur Karten berücksichtigt, die **bereits Fortschritt** für die gewählte Richtung haben.
2. **Themenfilter (optional):**
   - Standard: alle eingeführten Themen sind aktiv.
   - Expertenmodus: Nutzer kann Themen kombinieren. Auswahl wird **persistiert**.
   - Es werden **nur Themen mit eingeführten Karten** angeboten.
3. Pyramiden-Logik:
   - Karten werden nach Stufe in Pools 1–4 einsortiert.
   - Session wird nach Gewichten befüllt:  
     Stufe 1 häufiger als 2, häufiger als 3, häufiger als 4.
   - Danach wird die Session gemischt.

### Stufen-Update nach Antwort
- **Richtig:** Stufe +1 (max. 4)
- **Falsch:** Stufe -1 (min. 1)

## Antwortbewertung (Training)
- **Doppelte Leerzeichen** werden immer ignoriert.
- **EndgÃ¼ltig richtig** ist eine Antwort nur bei exakt richtiger Eingabe (GroÃ/Kleinschreibung, Akzente, Satzzeichen).
- **Zweite Chance:** Nur bei Level 1â€“3 und nur innerhalb der jeweiligen Fehlergrenze.
  - Titel des Hinweises: **Fast richtig....** (eigener Sound).

### Level-Regeln
- **Level 4:** Keine Ausnahmen, keine zweite Chance.
- **Level 3:** Max. 2 Buchstaben Fehler fÃ¼r eine zweite Chance.
  - Bei reinen GroÃ/Kleinschreibungsfehlern: Hinweis darauf.
  - Sonst: Hinweis, dass etwas nicht stimmt (ohne Anzahl).
- **Level 2:** Wie Level 3, aber bis 4 Buchstaben.
  - ZusÃ¤tzlich explizite Hinweise auf Akzente/Apostroph/Satzzeichen.
  - Bei Buchstabenfehlern **und** Akzent/Satzzeichen: Hinweis, dass es weitere Fehler gibt (mit Anzahl).
- **Level 1:** Wie Level 2, plus Hinweis, wenn ein ganzes Wort fehlt.

### AuflÃ¶sung
- Wenn die Antwort endgÃ¼ltig falsch ist (keine zweite Chance mehr), wird die eigene Eingabe **durchgestrichen** neben der richtigen LÃ¶sung angezeigt.

## Lokales Debugging (uv)
1. Abhängigkeiten installieren:
```bash
uv sync
```
2. App starten (mit Konsolen-Logs):
```bash
uv run python main.py
```

**Debug-Report in der App:**
- Im Menü gibt es **Debug report**, der aktuelle Fehler und die letzte Exception anzeigt.

## Seed-Datenbank
Die Seed-Datenbank liegt in `data/seed_vocab.yaml`.  
Sie wird beim ersten Start in das User-Data-Verzeichnis kopiert.
