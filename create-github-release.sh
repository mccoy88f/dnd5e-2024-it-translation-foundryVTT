#!/bin/bash

# Script per creare la release su GitHub
# Questo script:
# 1. Fa il push del codice e del tag
# 2. Crea la release su GitHub con il file ZIP

VERSION="2.3.0"
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

### ✨ Nuove Traduzioni
- ✅ **Mostri 2024** (actors24): 388 mostri tradotti (100%)
- ✅ **Classi 2024** (classes24): 228 classi/caratteristiche tradotte (80.9%)
- ✅ **Incantesimi 2024** (spells24): 341 incantesimi tradotti (100%)
- ✅ **Equipaggiamento 2024** (equipment24): 503 oggetti tradotti (84.8%)
- ✅ **Talenti 2024** (feats24): 17 talenti tradotti (100%)
- ✅ **Caratteristiche Mostri** (monsterfeatures): traduzioni completate
- ✅ **Caratteristiche Classe** (classfeatures): traduzioni completate

### 🔧 Miglioramenti
- ✅ Riutilizzate traduzioni 2014 (SRD) per caratteristiche comuni tra 2014 e 2024
- ✅ Migliorato matching automatico delle traduzioni esistenti
- ✅ Aggiunto supporto per tutti i compendium 2024

### 📊 Statistiche
- **Totale voci tradotte automaticamente**: ~3800+ voci
- **Compendium completati**: 20/20
- **Metodo**: Riutilizzo intelligente delle traduzioni 2014 + dizionari comuni

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
