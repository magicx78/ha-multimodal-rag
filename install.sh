#!/bin/bash

# 🚀 Multimodal RAG für Home Assistant — AUTOMATISCHE INSTALLATION

set -e  # Stoppe bei Fehler

echo "📦 Multimodal RAG Installer"
echo "═══════════════════════════════════════"
echo ""

# Schritt 1: Home Assistant Pfad herausfinden
if [ -z "$HA_CONFIG_PATH" ]; then
    HA_CONFIG_PATH=~/.homeassistant
fi

echo "🔍 Home Assistant Pfad: $HA_CONFIG_PATH"

# Prüfe ob Pfad existiert
if [ ! -d "$HA_CONFIG_PATH" ]; then
    echo "❌ Fehler: Home Assistant Konfiguration nicht gefunden!"
    echo ""
    echo "Bitte setze die Umgebungsvariable:"
    echo "  export HA_CONFIG_PATH=/path/to/homeassistant"
    echo ""
    echo "Oder gib den Pfad ein:"
    read -p "Home Assistant Pfad: " HA_CONFIG_PATH
fi

# Schritt 2: Integration kopieren
echo ""
echo "📂 Kopiere Integration..."

DEST="$HA_CONFIG_PATH/custom_components/multimodal_rag"

# Backup falls Integration bereits existiert
if [ -d "$DEST" ]; then
    BACKUP="$DEST.backup.$(date +%s)"
    echo "⚠️  Integration existiert bereits. Backup: $BACKUP"
    mv "$DEST" "$BACKUP"
fi

# Kopieren
cp -r "$(dirname "$0")/custom_components/multimodal_rag" "$DEST"
chmod -R 755 "$DEST"

echo "✅ Integration kopiert zu: $DEST"
echo ""

# Schritt 3: Zusammenfassung
echo "═══════════════════════════════════════"
echo "✨ Installation abgeschlossen!"
echo ""
echo "📋 Nächste Schritte:"
echo ""
echo "1️⃣  Home Assistant neustarten:"
echo "    • Settings → System → Restart"
echo ""
echo "2️⃣  Integration hinzufügen:"
echo "    • Settings → Devices & Services"
echo "    • Suche: 'Multimodal RAG'"
echo ""
echo "3️⃣  API Key hinzufügen:"
echo "    • secrets.yaml: anthropic_api_key: sk-ant-..."
echo ""
echo "4️⃣  Services nutzen:"
echo "    • multimodal_rag.upload_document"
echo "    • multimodal_rag.search"
echo "    • multimodal_rag.reason"
echo ""
echo "📖 Mehr Infos: INSTALLATION_DE.md"
echo "═══════════════════════════════════════"
