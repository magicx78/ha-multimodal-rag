# 🚀 Multimodal RAG für Home Assistant — INSTALLATION

## Schritt 1: Integration kopieren

Öffne ein Terminal und führe diesen Befehl aus:

```bash
cp -r ~/Documents/ha-multimodal-rag/custom_components/multimodal_rag \
      ~/.homeassistant/custom_components/
```

**Wobei:**
- `~/.homeassistant` = dein Home Assistant Konfigurationsordner
- Falls Home Assistant in Docker läuft, verwende stattdessen:
  ```bash
  cp -r ~/Documents/ha-multimodal-rag/custom_components/multimodal_rag \
        /home/homeassistant/.homeassistant/custom_components/
  ```

## Schritt 2: Home Assistant neustarten

Gehe zu:
- **Settings** → **System** → **Restart**

Oder terminal-Befehl:
```bash
docker restart homeassistant
```

## Schritt 3: Integration hinzufügen

Nach dem Neustart gehe zu:
- **Settings** → **Devices & Services**
- Klick **"Create Automation"** (oder "Create Integration")
- Suche nach **"Multimodal RAG"**
- Klick **"Install"**

Ein Assistent öffnet sich mit 4 Schritten.

## Schritt 4: API-Schlüssel hinzufügen

Du brauchst einen **Anthropic API Key** (Claude):

1. Gehe zu https://console.anthropic.com/
2. Erstelle einen Account (falls noch nicht vorhanden)
3. Kopiere deinen **API Key**
4. In Home Assistant öffne:
   - **Settings** → **Automations & Scenes** → **Edit YAML**
   - Füge hinzu:
   ```yaml
   anthropic_api_key: sk-ant-xxxxxxxxxxxxx  # Dein echter Key
   ```
5. Speichern

## Schritt 5: Fertig!

Die Integration ist jetzt aktiv. Du kannst Services nutzen:

### Dokument hochladen:
```yaml
service: multimodal_rag.upload_document
data:
  file_path: /config/documents/meine_rechnung.pdf
  collection: rechnungen
```

### Suchen:
```yaml
service: multimodal_rag.search
data:
  query: "Welche Rechnungen habe ich im März?"
  top_k: 5
response_variable: ergebnisse
```

### Reasoning (LLM-Analyse):
```yaml
service: multimodal_rag.reason
data:
  query: "Was ist auf diesem Foto?"
response_variable: antwort
```

---

## 🆘 Häufige Fehler

### "Integration nicht gefunden"
- Stelle sicher, dass die Datei in `~/.homeassistant/custom_components/multimodal_rag/` liegt
- Verzeichnis muss genau so heißen

### "API Key ungültig"
- Überprüfe dein secrets.yaml
- Key muss mit `sk-ant-` beginnen
- Keine Anführungszeichen nötig

### "Qdrant nicht erreichbar"
- Die Integration versucht automatisch **SQLite** zu nutzen
- Das sollte ohne weitere Installation funktionieren

---

## ✅ Prüfung

Nach der Installation solltest du in Home Assistant sehen:
- **Settings** → **Devices & Services** → "Multimodal RAG" (grün = aktiv)

Dann sind alle Dependencies automatisch installiert! 🎉
