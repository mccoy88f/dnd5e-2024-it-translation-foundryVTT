#!/bin/bash

# Script per creare il file ZIP per la release di Foundry VTT
# Esclude file non necessari come .git, origin/, foundry-translation/, etc.

VERSION="2.2.0"
ZIP_NAME="module.zip"
TEMP_DIR=$(mktemp -d)

echo "📦 Creazione file ZIP per versione $VERSION..."

# Crea la struttura del modulo nella directory temporanea
mkdir -p "$TEMP_DIR"

# Copia i file necessari, escludendo quelli non necessari
echo "📋 Copia file necessari..."

# File root
cp module.json "$TEMP_DIR/"
cp main.js "$TEMP_DIR/"
cp README.md "$TEMP_DIR/"

# Directory compendium (tutti i file JSON)
cp -r compendium "$TEMP_DIR/"

# Directory lang
cp -r lang "$TEMP_DIR/"

# Directory packs/macro (solo i file necessari, escludendo file di database)
mkdir -p "$TEMP_DIR/packs/macro"
# Copia solo se ci sono file macro validi (escludi .log, CURRENT, LOCK, LOG, MANIFEST-*)
if [ -d "packs/macro" ]; then
    find packs/macro -type f ! -name "*.log" ! -name "CURRENT" ! -name "LOCK" ! -name "LOG" ! -name "MANIFEST-*" -exec cp {} "$TEMP_DIR/packs/macro/" \;
fi

# Crea il file ZIP
echo "🗜️  Compressione in $ZIP_NAME..."
cd "$TEMP_DIR"
zip -r "$OLDPWD/$ZIP_NAME" . -q

# Pulisci
cd "$OLDPWD"
rm -rf "$TEMP_DIR"

echo "✅ File ZIP creato: $ZIP_NAME"
echo "📊 Dimensione: $(du -h $ZIP_NAME | cut -f1)"
