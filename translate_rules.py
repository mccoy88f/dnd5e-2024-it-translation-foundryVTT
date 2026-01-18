#!/usr/bin/env python3
"""
Script per completare le traduzioni delle regole (dnd5e.rules)
Estrae contenuto dai file YAML originali e lo aggiunge alle pagine mancanti
"""

import re
import json
from pathlib import Path
from collections import OrderedDict

def read_yaml_file(yml_file):
    """Legge un file YAML delle regole e estrae le pagine usando regex"""
    try:
        with open(yml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        pages = {}
        
        # Estrai nome del journal
        journal_name_match = re.search(r'^name:\s*[\'"]?([^\'"\n]+)[\'"]?$', content, re.MULTILINE)
        journal_name = journal_name_match.group(1).strip() if journal_name_match else None
        
        # Pattern semplificato: trova ogni pagina dividendo per "name:" e poi cercando "content: >-"
        # Divide il contenuto in sezioni per pagina
        page_sections = re.split(r'^\s*-\s+name:\s*', content, flags=re.MULTILINE)
        
        for section in page_sections[1:]:  # Salta la prima (intestazione)
            # Estrai nome pagina (prima riga)
            first_line = section.split('\n')[0].strip()
            page_name = first_line.strip("'\"")
            
            # Cerca "content: >-" in questa sezione
            content_match = re.search(r'content:\s*>\-\s*\n((?:\s+.*\n?)+?)(?=^\s+name:|^\s+_id:|^[a-zA-Z_]+:|$)', section, re.MULTILINE | re.DOTALL)
            
            if content_match:
                page_text_raw = content_match.group(1)
                
                # Rimuovi indentazione comune
                lines = [line for line in page_text_raw.split('\n') if line.strip()]
                if lines:
                    indent_levels = [len(line) - len(line.lstrip()) for line in lines]
                    if indent_levels:
                        min_indent = min(indent_levels)
                        page_text = '\n'.join(line[min_indent:] if len(line) > min_indent else line for line in lines).strip()
                    else:
                        page_text = '\n'.join(lines).strip()
                    
                    if page_text and page_name:
                        pages[page_name] = {
                            'name': page_name,
                            'text': page_text
                        }
        
        return {
            'name': journal_name,
            'pages': pages
        }
    except Exception as e:
        print(f"Errore lettura {yml_file}: {e}")
        import traceback
        traceback.print_exc()
        return None

def normalize_page_name(name):
    """Normalizza il nome della pagina per matching"""
    if not name:
        return ""
    # Rimuovi caratteri speciali e normalizza
    return name.strip().lower().replace(' ', '').replace('-', '').replace("'", "").replace(',', '').replace(':', '').replace('.', '')

def find_page_match(page_name, existing_pages):
    """Trova corrispondenza tra nome pagina originale e esistente"""
    page_norm = normalize_page_name(page_name)
    
    for existing_key, existing_value in existing_pages.items():
        existing_name = existing_value.get('name', existing_key) if isinstance(existing_value, dict) else existing_key
        existing_norm = normalize_page_name(existing_name)
        
        # Matching esatto
        if page_norm == existing_norm:
            return existing_key
        
        # Matching parziale
        if page_norm in existing_norm or existing_norm in page_norm:
            if len(page_name) > 3:
                return existing_key
    
    return None

# Mapping file YAML -> capitolo in JSON
FILE_TO_CHAPTER = {
    'chapter-1-beyond-1st-level.yml': 'Chapter 1: Beyond 1st Level',
    'chapter-2-races.yml': 'Chapter 2: Races',
    'chapter-3-classes.yml': 'Chapter 3: Classes',
    'chapter-4-personality-and-background.yml': 'Chapter 4: Personality and Background',
    'chapter-5-equipment.yml': 'Chapter 5: Equipment',
    'chapter-6-customization-options.yml': 'Chapter 6: Customization Options',
    'chapter-7-using-ability-scores.yml': 'Chapter 7: Using Ability Scores',
    'chapter-8-adventuring.yml': 'Chapter 8: Adventuring',
    'chapter-9-combat.yml': 'Chapter 9: Combat',
    'chapter-10-spellcasting.yml': 'Chapter 10: Spellcasting',
    'chapter-11-dm-tools.yml': 'Chapter 11: DM Tools',
    'appendix-a-conditions.yml': 'Appendix A: Conditions',
    'appendix-b-gods-and-the-multiverse.yml': 'Appendix B: Gods and the Multiverse',
    'appendix-c-creatures.yml': 'Appendix C: Creatures',
    'appendix-d-senses-and-speeds.yml': 'Appendix D: Senses and Speeds',
    'appendix-e-rules.yml': 'Appendix E: Rules',
}

def translate_rules():
    """Completa le traduzioni delle regole"""
    print("=== TRADUZIONE REGOLE (dnd5e.rules) ===\n")
    
    # Carica file rules.json esistente
    rules_file = Path("compendium/dnd5e.rules.json")
    with open(rules_file, 'r', encoding='utf-8') as f:
        data = json.load(f, object_pairs_hook=OrderedDict)
    
    # Leggi file originali
    origin_dir = Path("origin/packs/_source/rules")
    if not origin_dir.exists():
        print("❌ Directory rules non trovata!")
        return
    
    yml_files = list(origin_dir.glob("*.yml"))
    print(f"✅ Trovati {len(yml_files)} file originali\n")
    
    entries = data.get('entries', {})
    total_pages_added = 0
    total_pages_skipped = 0
    
    # Processa ogni file YAML
    for yml_file in sorted(yml_files):
        file_name = yml_file.name
        
        # Trova il capitolo corrispondente
        chapter_key = None
        for yml_key, chapter_name in FILE_TO_CHAPTER.items():
            if yml_key in file_name:
                # Cerca il capitolo nel JSON
                for key in entries.keys():
                    if chapter_name in key or normalize_page_name(chapter_name) == normalize_page_name(key):
                        chapter_key = key
                        break
                break
        
        if not chapter_key:
            print(f"⚠️  Nessun capitolo corrispondente per: {file_name}")
            continue
        
        print(f"📖 Processando: {file_name} → {chapter_key}")
        
        # Leggi contenuto YAML
        yaml_data = read_yaml_file(yml_file)
        if not yaml_data or 'pages' not in yaml_data:
            print(f"   ⚠️  Nessuna pagina trovata in {file_name}")
            continue
        
        # Aggiungi contenuto alle pagine mancanti
        chapter_data = entries[chapter_key]
        if 'pages' not in chapter_data:
            chapter_data['pages'] = OrderedDict()
        
        chapter_pages = chapter_data['pages']
        pages_added = 0
        
        for page_name_orig, page_data_orig in yaml_data['pages'].items():
            # Trova corrispondenza nella struttura esistente
            page_key = find_page_match(page_name_orig, chapter_pages)
            
            if not page_key:
                # Crea nuova pagina
                page_key = page_name_orig
                chapter_pages[page_key] = OrderedDict({
                    'name': page_name_orig  # Sarà tradotto dopo
                })
            
            # Aggiungi contenuto se manca
            page_data = chapter_pages[page_key]
            if isinstance(page_data, dict):
                if 'text' not in page_data and 'description' not in page_data and 'content' not in page_data:
                    # Aggiungi contenuto (testo originale, da tradurre manualmente o via API)
                    page_data['text'] = page_data_orig.get('text', '')
                    if page_data['text']:
                        pages_added += 1
                        total_pages_added += 1
                else:
                    total_pages_skipped += 1
        
        if pages_added > 0:
            print(f"   ✅ Aggiunto contenuto a {pages_added} pagine")
        else:
            print(f"   ⚠️  Nessuna pagina aggiornata (già presente o senza contenuto)")
    
    # Salva file aggiornato
    with open(rules_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n📊 RIEPILOGO:")
    print(f"  ✅ Pagine con contenuto aggiunto: {total_pages_added}")
    print(f"  ⏭️  Pagine saltate (già con contenuto): {total_pages_skipped}")
    print(f"  💾 File salvato: {rules_file}")

if __name__ == '__main__':
    translate_rules()
