#!/usr/bin/env python3
"""
Script per tradurre le voci mancanti utilizzando l'API di quintaedizione.online
"""

import json
import re
import time
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("⚠️  Libreria 'requests' non installata. Installa con: pip install requests")

REPO_ROOT = Path(__file__).parent

# Rate limiting
REQUEST_DELAY = 0.5  # Secondi tra una richiesta e l'altra
MAX_RETRIES = 3

def normalize_to_slug(name: str) -> str:
    """Converte un nome inglese in uno slug per quintaedizione.online"""
    # Rimuovi caratteri speciali, converti in minuscolo
    slug = re.sub(r'[^\w\s-]', '', name.lower())
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')

def fetch_translation_from_api(item_type: str, english_name: str) -> Optional[str]:
    """
    Cerca la traduzione italiana su quintaedizione.online
    
    Args:
        item_type: 'spell', 'monster', 'item', 'class', 'class_feature', 'monster_feature'
        english_name: Nome inglese dell'elemento
    
    Returns:
        Nome italiano se trovato, None altrimenti
    """
    if not REQUESTS_AVAILABLE:
        return None
    
    # Mappa tipo -> endpoint base
    endpoint_map = {
        'spell': 'incantesimi',
        'monster': 'mostri',
        'item': 'equipaggiamenti',
        'equipment': 'equipaggiamenti',
        'class': 'classi',
        'class_feature': 'classi',
        'monster_feature': 'mostri',
    }
    
    base_slug = endpoint_map.get(item_type, 'incantesimi')
    item_slug = normalize_to_slug(english_name)
    
    # Prova diversi pattern di URL
    url_patterns = [
        f"https://quintaedizione.online/{base_slug}/{item_slug}",
        f"https://quintaedizione.online/api/{base_slug}/{item_slug}",
        f"https://quintaedizione.online/{base_slug}/{item_slug.replace('-', '_')}",
    ]
    
    for url in url_patterns:
        try:
            response = requests.get(url, timeout=10, allow_redirects=True)
            
            if response.status_code == 200:
                # Se è HTML, cerca il titolo
                if 'text/html' in response.headers.get('content-type', ''):
                    # Cerca pattern tipo <h1> o <title> con il nome italiano
                    title_pattern = r'<h1[^>]*>([^<]+)</h1>'
                    match = re.search(title_pattern, response.text, re.IGNORECASE)
                    if match:
                        italian_name = match.group(1).strip()
                        # Rimuovi eventuali tag HTML residui
                        italian_name = re.sub(r'<[^>]+>', '', italian_name)
                        if italian_name and len(italian_name) > 2:
                            return italian_name
                
                # Se è JSON
                elif 'application/json' in response.headers.get('content-type', ''):
                    data = response.json()
                    # Prova diversi campi comuni
                    for field in ['name', 'nome', 'title', 'titolo', 'italian_name']:
                        if field in data and data[field]:
                            return str(data[field])
            
            time.sleep(REQUEST_DELAY)
        except Exception as e:
            print(f"   ⚠️  Errore richiesta {url}: {e}")
            continue
    
    return None

def translate_spells24():
    """Traduce gli incantesimi mancanti in spells24"""
    print("\n=== TRADUZIONE SPELLS24 ===\n")
    
    json_file = REPO_ROOT / 'compendium/dnd5e.spells24.json'
    origin_dir = REPO_ROOT / 'origin/packs/_source/spells24'
    
    # Carica JSON esistente
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Trova incantesimi mancanti (quelli senza traduzione italiana)
    translated_ids = set()
    if 'entries' in data and isinstance(data['entries'], list):
        for entry in data['entries']:
            if isinstance(entry, dict) and 'id' in entry:
                translated_ids.add(entry['id'])
                # Controlla se il nome è italiano
                if 'name' in entry:
                    name = entry['name']
                    italian_chars = ['à', 'è', 'é', 'ì', 'ò', 'ù']
                    if any(c in name for c in italian_chars):
                        continue  # Già tradotto
    
    # Trova incantesimi originali non tradotti
    missing_spells = []
    if origin_dir.exists():
        for yml_file in sorted(origin_dir.rglob("*.yml")):
            if yml_file.name.startswith('_'):
                continue
            try:
                with open(yml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    id_match = re.search(r'^_id:\s*(.+)$', content, re.MULTILINE)
                    name_match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
                    if id_match and name_match:
                        spell_id = id_match.group(1).strip()
                        spell_name = name_match.group(1).strip()
                        
                        # Verifica se manca
                        if spell_id not in translated_ids:
                            missing_spells.append({'id': spell_id, 'name': spell_name, 'file': yml_file.name})
            except Exception as e:
                print(f"   ⚠️  Errore lettura {yml_file.name}: {e}")
    
    if not missing_spells:
        print("✅ Nessun incantesimo mancante!")
        return
    
    print(f"📋 Trovati {len(missing_spells)} incantesimi da tradurre\n")
    
    # Traduci
    translated_count = 0
    for spell in missing_spells:
        print(f"🔍 Cercando traduzione per: {spell['name']}")
        italian_name = fetch_translation_from_api('spell', spell['name'])
        
        if italian_name:
            # Aggiungi al JSON
            if 'entries' not in data:
                data['entries'] = []
            
            # Verifica se esiste già entry con questo ID
            entry_exists = False
            for entry in data['entries']:
                if isinstance(entry, dict) and entry.get('id') == spell['id']:
                    entry['name'] = italian_name
                    entry_exists = True
                    break
            
            if not entry_exists:
                data['entries'].append({
                    'id': spell['id'],
                    'name': italian_name
                })
            
            translated_count += 1
            print(f"   ✅ Tradotto: {italian_name}")
        else:
            print(f"   ❌ Traduzione non trovata")
    
    # Salva
    if translated_count > 0:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Salvati {translated_count} incantesimi tradotti in {json_file}")
    else:
        print("\n⚠️  Nessuna traduzione trovata")

def translate_classes24():
    """Traduce le classi/caratteristiche mancanti in classes24"""
    print("\n=== TRADUZIONE CLASSES24 ===\n")
    
    json_file = REPO_ROOT / 'compendium/dnd5e.classes24.json'
    origin_dir = REPO_ROOT / 'origin/packs/_source/classes24'
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'entries' not in data:
        print("❌ Struttura JSON non valida")
        return
    
    translated_keys = set(data['entries'].keys())
    
    # Trova voci mancanti
    missing_classes = []
    if origin_dir.exists():
        for yml_file in sorted(origin_dir.rglob("*.yml")):
            if yml_file.name.startswith('_'):
                continue
            try:
                with open(yml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    id_match = re.search(r'^_id:\s*(.+)$', content, re.MULTILINE)
                    name_match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
                    if id_match and name_match:
                        class_id = id_match.group(1).strip()
                        class_name = name_match.group(1).strip()
                        
                        # Usa ID o nome come chiave
                        key = class_id if class_id in translated_keys else class_name
                        if key not in translated_keys:
                            missing_classes.append({'id': class_id, 'name': class_name, 'key': key})
            except Exception as e:
                print(f"   ⚠️  Errore lettura {yml_file.name}: {e}")
    
    if not missing_classes:
        print("✅ Nessuna classe mancante!")
        return
    
    print(f"📋 Trovate {len(missing_classes)} voci da tradurre\n")
    
    translated_count = 0
    for cls in missing_classes:
        print(f"🔍 Cercando traduzione per: {cls['name']}")
        italian_name = fetch_translation_from_api('class_feature', cls['name'])
        
        if italian_name:
            # Aggiungi al JSON
            key = cls['key']
            data['entries'][key] = {
                'name': italian_name
            }
            translated_count += 1
            print(f"   ✅ Tradotto: {italian_name}")
        else:
            print(f"   ❌ Traduzione non trovata")
    
    if translated_count > 0:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Salvate {translated_count} traduzioni in {json_file}")

def translate_equipment24():
    """Traduce gli equipaggiamenti mancanti"""
    print("\n=== TRADUZIONE EQUIPMENT24 ===\n")
    
    json_file = REPO_ROOT / 'compendium/dnd5e.equipment24.json'
    origin_dir = REPO_ROOT / 'origin/packs/_source/equipment24'
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'entries' not in data:
        print("❌ Struttura JSON non valida")
        return
    
    translated_keys = set(data['entries'].keys())
    
    missing_items = []
    if origin_dir.exists():
        for yml_file in sorted(origin_dir.rglob("*.yml")):
            if yml_file.name.startswith('_'):
                continue
            try:
                with open(yml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    id_match = re.search(r'^_id:\s*(.+)$', content, re.MULTILINE)
                    name_match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
                    if id_match and name_match:
                        item_id = id_match.group(1).strip()
                        item_name = name_match.group(1).strip()
                        
                        key = item_id if item_id in translated_keys else item_name
                        if key not in translated_keys:
                            missing_items.append({'id': item_id, 'name': item_name, 'key': key})
            except Exception as e:
                print(f"   ⚠️  Errore lettura {yml_file.name}: {e}")
    
    if not missing_items:
        print("✅ Nessun equipaggiamento mancante!")
        return
    
    print(f"📋 Trovati {len(missing_items)} equipaggiamenti da tradurre\n")
    
    translated_count = 0
    for item in missing_items:
        print(f"🔍 Cercando traduzione per: {item['name']}")
        italian_name = fetch_translation_from_api('equipment', item['name'])
        
        if italian_name:
            key = item['key']
            data['entries'][key] = {
                'name': italian_name
            }
            translated_count += 1
            print(f"   ✅ Tradotto: {italian_name}")
        else:
            print(f"   ❌ Traduzione non trovata")
    
    if translated_count > 0:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Salvati {translated_count} equipaggiamenti tradotti")

def translate_monster_features():
    """Traduce le caratteristiche mostri mancanti"""
    print("\n=== TRADUZIONE MONSTER FEATURES ===\n")
    
    json_file = REPO_ROOT / 'compendium/dnd5e.monsterfeatures.json'
    origin_dir = REPO_ROOT / 'origin/packs/_source/monsterfeatures'
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'entries' not in data or not isinstance(data['entries'], list):
        print("❌ Struttura JSON non valida")
        return
    
    translated_ids = {entry.get('id') for entry in data['entries'] if isinstance(entry, dict) and 'id' in entry}
    
    missing_features = []
    if origin_dir.exists():
        for yml_file in sorted(origin_dir.rglob("*.yml")):
            if yml_file.name.startswith('_'):
                continue
            try:
                with open(yml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    id_match = re.search(r'^_id:\s*(.+)$', content, re.MULTILINE)
                    name_match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
                    if id_match and name_match:
                        feat_id = id_match.group(1).strip()
                        feat_name = name_match.group(1).strip()
                        
                        if feat_id not in translated_ids:
                            missing_features.append({'id': feat_id, 'name': feat_name})
            except Exception as e:
                print(f"   ⚠️  Errore lettura {yml_file.name}: {e}")
    
    if not missing_features:
        print("✅ Nessuna caratteristica mostro mancante!")
        return
    
    print(f"📋 Trovate {len(missing_features)} caratteristiche da tradurre\n")
    
    translated_count = 0
    for feat in missing_features:
        print(f"🔍 Cercando traduzione per: {feat['name']}")
        italian_name = fetch_translation_from_api('monster_feature', feat['name'])
        
        if italian_name:
            # Trova entry esistente o crea nuova
            entry_found = False
            for entry in data['entries']:
                if isinstance(entry, dict) and entry.get('id') == feat['id']:
                    entry['name'] = italian_name
                    entry_found = True
                    break
            
            if not entry_found:
                data['entries'].append({
                    'id': feat['id'],
                    'name': italian_name
                })
            
            translated_count += 1
            print(f"   ✅ Tradotto: {italian_name}")
        else:
            print(f"   ❌ Traduzione non trovata")
    
    if translated_count > 0:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Salvate {translated_count} caratteristiche tradotte")

def test_api_connection(item_type: str, english_name: str):
    """Testa la connessione API con un singolo elemento"""
    print(f"\n🧪 TEST API - {item_type}: {english_name}")
    print("-" * 70)
    
    italian_name = fetch_translation_from_api(item_type, english_name)
    
    if italian_name:
        print(f"✅ Traduzione trovata: {italian_name}")
        return True
    else:
        print(f"❌ Traduzione non trovata")
        print(f"\n💡 Suggerimenti:")
        print(f"   1. Verifica che quintaedizione.online sia raggiungibile")
        print(f"   2. Controlla manualmente: https://quintaedizione.online/incantesimi/{normalize_to_slug(english_name)}")
        print(f"   3. Potrebbe essere necessario adattare lo script all'API reale")
        return False

def main():
    """Esegue tutte le traduzioni"""
    print("=" * 70)
    print("🌐 TRADUZIONE VOCI MANCANTI VIA API")
    print("=" * 70)
    
    if not REQUESTS_AVAILABLE:
        print("\n❌ ERRORE: Libreria 'requests' non disponibile!")
        print("   Installa con: pip install requests")
        return
    
    # Menu interattivo
    print("\nCosa vuoi fare?")
    print("0. Test API (verifica connessione con un elemento di esempio)")
    print("1. Tutto (spells24, classes24, equipment24, monster_features)")
    print("2. Solo spells24 (10 incantesimi)")
    print("3. Solo classes24 (54 voci)")
    print("4. Solo equipment24 (90 voci)")
    print("5. Solo monster_features (36 voci)")
    
    choice = input("\nScelta (0-5): ").strip()
    
    if choice == '0':
        # Test con un incantesimo noto
        test_api_connection('spell', 'Shining Smite')
        test_api_connection('equipment', 'Lantern, Bullseye')
        test_api_connection('class_feature', 'Tactical Master')
        return
    
    if choice == '1' or choice == '2':
        translate_spells24()
    if choice == '1' or choice == '3':
        translate_classes24()
    if choice == '1' or choice == '4':
        translate_equipment24()
    if choice == '1' or choice == '5':
        translate_monster_features()
    
    print("\n" + "=" * 70)
    print("✅ TRADUZIONE COMPLETATA")
    print("=" * 70)

if __name__ == '__main__':
    main()
