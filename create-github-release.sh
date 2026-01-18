#!/bin/bash

# Script per creare la release su GitHub
# Questo script:
# 1. Fa il push del codice e del tag
# 2. Crea la release su GitHub con il file ZIP

VERSION="2.4.0"
ZIP_NAME="module.zip"
REPO="mccoy88f/dnd5e-2024-it-translation-foundryVTT"

echo "🚀 Creazione release v$VERSION su GitHub..."

# Verifica che il file ZIP esista
if [ ! -f "$ZIP_NAME" ]; then
    echo "❌ Errore: file $ZIP_NAME non trovato!"
    echo "   Esegui prima: ./create-release.sh"
    exit 1
fi

# Verifica che il tag esista localmente
if ! git rev-parse "v$VERSION" >/dev/null 2>&1; then
    echo "❌ Errore: tag v$VERSION non trovato localmente!"
    echo "   Crea prima il tag: git tag -a v$VERSION -m 'Release v$VERSION'"
    exit 1
fi

# Push del branch principale (se necessario)
echo "📤 Push del branch principale..."
git push origin main 2>&1 || echo "⚠️  Push del branch fallito (potrebbe essere già aggiornato)"

# Push del tag
echo "📤 Push del tag v$VERSION..."
git push origin "v$VERSION" 2>&1 || echo "⚠️  Push del tag fallito"

# Crea la release su GitHub usando gh CLI
echo "🎉 Creazione release su GitHub..."
gh release create "v$VERSION" \
    "$ZIP_NAME" \
    "module.json" \
    --repo "$REPO" \
    --title "v$VERSION" \
    --notes "## Release v$VERSION

### ✨ Nuove Funzionalità
- ✅ **Script Traduzione API**: Aggiunto `translate_missing_via_api.py` per traduzioni automatiche da quintaedizione.online
- ✅ **Script Estrazione PDF**: Aggiunto `extract_translations_from_pdf.py` per estrarre traduzioni dai PDF SRD
- ✅ **Contenuto Regole**: Estratto contenuto completo (92 pagine) per `dnd5e.rules.json`

### 📖 Traduzioni Regole (dnd5e.rules)
- ✅ **Contenuto estratto**: 92 pagine con contenuto inglese completo (da file YAML originali)
- ✅ **Stato**: Contenuto pronto per traduzione (inglese → italiano)
- ⚠️  **Da fare**: Traduzione italiana del contenuto (90 pagine in inglese + 24 solo titolo)

### 🛠️ Strumenti Aggiunti
- 📄 `translate_missing_via_api.py`: Script per tradurre voci mancanti via API quintaedizione.online
- 📄 `extract_translations_from_pdf.py`: Script per estrarre traduzioni dai PDF SRD italiani
- 📄 `translate_rules.py`: Script per estrarre contenuto regole da file YAML originali

### 📊 Stato Traduzioni
- **Traduzioni complete**: ~1515/1819 voci (83.3%)
- **Da tradurre via API**: ~190 voci (spells24, classes24, equipment24, monsterfeatures)
- **Da tradurre PDF/manuale**: 114 pagine regole

### 🔧 Miglioramenti Tecnici
- ✅ Estrazione automatica contenuto regole da YAML originali
- ✅ Preparazione infrastruttura per traduzioni API
- ✅ Supporto estrazione traduzioni da PDF SRD italiano

### 📦 Installazione
Usa questo URL per installare il modulo in Foundry VTT:
\`\`\`
https://github.com/$REPO/releases/latest/download/module.json
\`\`\`

### 🔗 Link
- [Repository](https://github.com/$REPO)
- [Issues](https://github.com/$REPO/issues)" \
    --verify-tag

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Release v$VERSION creata con successo!"
    echo "🔗 URL release: https://github.com/$REPO/releases/tag/v$VERSION"
    echo "📦 File ZIP caricato: $ZIP_NAME"
else
    echo ""
    echo "❌ Errore durante la creazione della release"
    echo "💡 Prova a crearla manualmente su GitHub:"
    echo "   https://github.com/$REPO/releases/new"
    exit 1
fi
