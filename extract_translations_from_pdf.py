#!/usr/bin/env python3
"""
Script per estrarre traduzioni italiane dai PDF SRD e completare dnd5e.rules.json
"""

import re
import json
from pathlib import Path
from collections import OrderedDict

try:
    import PyPDF2
    PDF_AVAILABLE = True
    PDF_LIB = 'PyPDF2'
except ImportError:
    try:
        import pdfplumber
        PDF_AVAILABLE = True
        PDF_LIB = 'pdfplumber'
    except ImportError:
        PDF_AVAILABLE = False
        PDF_LIB = None

def extract_text_from_pdf(pdf_path):
    """Estrae tutto il testo da un PDF"""
    if not PDF_AVAILABLE:
        print("❌ Nessuna libreria PDF disponibile!")
        print("   Installa con: pip install PyPDF2 o pip install pdfplumber")
        return None
    
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            if PDF_LIB == 'pdfplumber':
                pdf = pdfplumber.open(file)
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
                pdf.close()
            else:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        
        return text
    except Exception as e:
        print(f"❌ Errore lettura PDF {pdf_path}: {e}")
        return None

def normalize_title_for_search(title):
    """Normalizza un titolo per la ricerca (rimuove punteggiatura, case-insensitive)"""
    if not title:
        return ""
    # Rimuovi punteggiatura e normalizza
    normalized = re.sub(r'[^\w\s]', '', title.lower())
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized

def find_page_content_directly(text, page_title):
    """Trova direttamente il contenuto di una pagina cercando il titolo nel testo completo"""
    if not page_title or len(page_title) < 3:
        return None
    
    # Normalizza il titolo per la ricerca
    title_norm = normalize_title_for_search(page_title)
    
    # Cerca il titolo nel testo (case-insensitive, flessibile)
    # Prima cerca esatto
    title_pos = -1
    for i in range(len(text) - len(page_title)):
        text_slice = text[i:i+len(page_title)]
        if normalize_title_for_search(text_slice) == title_norm:
            title_pos = i
            break
    
    # Se non trovato esatto, cerca case-insensitive
    if title_pos == -1:
        title_lower = page_title.lower()
        text_lower = text.lower()
        pos = text_lower.find(title_lower)
        if pos != -1:
            title_pos = pos
    
    if title_pos == -1:
        return None
    
    # Estrai contenuto dopo il titolo
    start_pos = title_pos + len(page_title)
    
    # Trova la fine: cerca prossimo titolo di sezione (riga che inizia con maiuscola seguita da testo)
    # o fine documento
    end_pos = min(start_pos + 3000, len(text))  # Max 3000 caratteri
    
    # Cerca pattern di fine sezione
    # Pattern: riga che inizia con maiuscola e sembra un titolo
    next_title_pattern = r'(?m)^([A-ZÀÈÉÌÒÙ][a-zàèéìòù]+(?:\s+[A-ZÀÈÉÌÒÙ][a-zàèéìòù]+){0,3})\s*$'
    next_match = re.search(next_title_pattern, text[start_pos:end_pos])
    
    if next_match:
        # Verifica che non sia troppo vicino (almeno 100 caratteri)
        if next_match.start() > 100:
            end_pos = start_pos + next_match.start()
    
    content = text[start_pos:end_pos].strip()
    
    # Pulisci il contenuto
    # Rimuovi spazi multipli ma mantieni struttura base
    content = re.sub(r'[ \t]+', ' ', content)  # Spazi multipli -> singolo spazio
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)  # Newline multipli -> doppio
    
    # Rimuovi caratteri di controllo strani
    content = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', content)
    
    if len(content) > 100:  # Almeno 100 caratteri
        return content
    
    return None

def extract_translations_from_pdf():
    """Estrae traduzioni italiane dal PDF e completa rules.json"""
    print("=== ESTRAZIONE TRADUZIONI DA PDF SRD ITALIANO ===\n")
    
    # Trova PDF italiano
    pdf_it = Path("IT_SRD_CC_v5.2.1.pdf")
    if not pdf_it.exists():
        print("❌ PDF italiano non trovato!")
        return
    
    print(f"📄 Leggendo PDF: {pdf_it.name} ({pdf_it.stat().st_size / (1024*1024):.1f} MB)")
    print("   ⏳ Estrazione testo (può richiedere alcuni secondi)...")
    
    pdf_text = extract_text_from_pdf(pdf_it)
    if not pdf_text:
        return
    
    print(f"✅ Testo estratto: {len(pdf_text)} caratteri")
    
    # Trova dove inizia il contenuto reale (dopo l'indice)
    # L'indice di solito contiene "Contents" o "Contenuti" e poi elenchi di pagine
    # Cerca il primo capitolo/sezione reale
    content_start_markers = [
        "Come si gioca",
        "Ritmo di gioco",
        "Le sei caratteristiche",
        "Creazione del personaggio",
        "Classi",
    ]
    
    content_start_pos = 0
    for marker in content_start_markers:
        pos = pdf_text.find(marker)
        if pos != -1 and pos < len(pdf_text) * 0.3:  # Nei primi 30% del documento
            content_start_pos = pos
            print(f"📖 Contenuto inizia a posizione: {pos} (dopo l'indice)")
            break
    
    # Usa solo il contenuto dopo l'indice
    if content_start_pos > 0:
        pdf_text = pdf_text[content_start_pos:]
        print(f"   Testo contenuto: {len(pdf_text)} caratteri\n")
    else:
        print("   ⚠️  Indice non trovato, uso tutto il testo\n")
    
    # Carica rules.json
    rules_file = Path("compendium/dnd5e.rules.json")
    with open(rules_file, 'r', encoding='utf-8') as f:
        data = json.load(f, object_pairs_hook=OrderedDict)
    
    entries = data.get('entries', {})
    
    # Mapping titoli pagine JSON -> titoli nel PDF italiano
    page_title_mapping = {
        # Chapter 7: Using Ability Scores
        'Usare i Punteggi di Abilità': ['Le sei caratteristiche', 'Sei caratteristiche', 'Caratteristiche'],
        'Punteggi di Abilità e Modificatori': ['Punteggi di Abilità', 'Modificatori'],
        'Vantaggio e Svantaggio': ['Vantaggio', 'Svantaggio', 'Vantaggio/svantaggio'],
        'Bonus di Competenza': ['Competenza'],
        'Prove di Abilità': ['Prove di caratteristica'],
        'Uso di Ciascuna Abilità': ['Uso di ciascuna abilità', 'Usare ciascuna abilità'],
        'Tiri Salvezza': ['Tiri salvezza'],
        
        # Chapter 9: Combat
        "L'Ordine di Combattimento": ["L'ordine di combattimento", 'Ordine di combattimento'],
        'Movimento e Posizione': ['Movimento e posizione'],
        'Azioni in Combattimento': ['Azioni', 'Azioni in combattimento'],
        'Attaccare': ['Effettuare un attacco', 'Attacco'],
        'Copertura': ['Copertura'],
        'Danno e Cura': ['Danni e guarigione', 'Danno e guarigione'],
        'Combattimento con Cavalcatura': ['Combattere in sella'],
        "Combattimento sott'Acqua": ["Combattere sott'acqua"],
        
        # Chapter 10: Spellcasting
        'Lanciare Incantesimi': ['Lanciare incantesimi', 'Incantesimi'],
        "Cos'è un Incantesimo?": ['Cos\'è un incantesimo', 'Cosa è un incantesimo'],
        'Lanciare un Incantesimo': ['Lanciare un incantesimo'],
        
        # Chapter 3: Classes
        'Barbaro': ['Barbaro'],
        'Bardo': ['Bardo'],
        'Chierico': ['Chierico'],
        'Druido': ['Druido'],
        'Guerriero': ['Guerriero'],
        'Monaco': ['Monaco'],
        'Paladino': ['Paladino'],
        'Ranger': ['Ranger'],
        'Ladro': ['Ladro'],
        'Stregone': ['Stregone'],
        'Warlock': ['Warlock'],
        'Mago': ['Mago'],
        
        # Chapter 4
        'Allineamento': ['Allineamento'],
        'Linguaggi': ['Linguaggi'],
        'Ispirazione': ['Ispirazione'],
        'Background': ['Background'],
        
        # Chapter 5
        'Equipaggiamento': ['Equipaggiamento'],
        'Vendere Tesori': ['Vendere tesori'],
        'Armature': ['Armature'],
        'Armi': ['Armi'],
        'Dotazioni da Avventuriero': ['Dotazioni', 'Dotazioni da avventuriero'],
        'Oggetti': ['Oggetti'],
        'Cavalcature e Veicoli': ['Cavalcature', 'Veicoli'],
        'Beni Commerciali': ['Beni commerciali'],
        'Spese': ['Spese'],
        
        # Chapter 8
        'Tempo': ['Tempo'],
        'Movimento': ['Movimento'],
        "L'Ambiente": ['Ambiente'],
        'Riposare': ['Riposo', 'Riposare'],
        'Tra le Avventure': ['Tra le avventure'],
        
        # Appendix A
        'Accecato': ['Accecato'],
        'Affascinato': ['Affascinato'],
        'Afferrato': ['Afferrato'],
        'Assordato': ['Assordato'],
        'Avvelenato': ['Avvelenato'],
        'Incapacitato': ['Incapacitato'],
        'Indebolimento': ['Indebolimento', 'Esaurimento'],
        'Invisibile': ['Invisibile'],
        'Paralizzato': ['Paralizzato'],
        'Pietrificato': ['Pietrificato'],
        'Privo di Sensi': ['Privo di sensi', 'Svenuto'],
        'Prono': ['Prono'],
        'Spaventato': ['Spaventato'],
        'Stordito': ['Stordito'],
        'Trattenuto': ['Trattenuto'],
    }
    
    total_pages_updated = 0
    
    # Processa ogni capitolo e le sue pagine
    for chapter_key, chapter_data in entries.items():
        print(f"📖 Processando: {chapter_data.get('name', chapter_key)}")
        
        # Processa le pagine del capitolo
        if 'pages' not in chapter_data:
            continue
        
        pages_updated = 0
        for page_key, page_data in chapter_data['pages'].items():
            if not isinstance(page_data, dict) or 'name' not in page_data:
                continue
            
            page_name = page_data['name']
            
            existing_text = page_data.get('text', '') or page_data.get('description', '')
            
            # Controlla se è già in italiano
            is_already_italian = False
            if existing_text:
                italian_chars = ['à', 'è', 'é', 'ì', 'ò', 'ù', 'À', 'È', 'É', 'Ì', 'Ò', 'Ù']
                is_already_italian = any(char in existing_text[:500] for char in italian_chars)
            
            # Se è già in italiano e ha contenuto significativo, salta
            if is_already_italian and len(existing_text) > 200:
                continue
            
            # Cerca direttamente il contenuto della pagina nel PDF
            page_content = find_page_content_directly(pdf_text, page_name)
            
            # Se non trovato, prova con le varianti del mapping
            if not page_content and page_name in page_title_mapping:
                for variant in page_title_mapping[page_name]:
                    page_content = find_page_content_directly(pdf_text, variant)
                    if page_content:
                        break
            
            if page_content and len(page_content) > 100:
                # Verifica se il contenuto è in italiano
                italian_chars_in_content = ['à', 'è', 'é', 'ì', 'ò', 'ù']
                is_content_italian = any(char in page_content[:500] for char in italian_chars_in_content)
                
                # Sostituisci se:
                # 1. Non c'è testo esistente, OPPURE
                # 2. Il contenuto trovato è in italiano e quello esistente è in inglese, OPPURE
                # 3. Il contenuto trovato è significativamente più lungo
                should_replace = False
                
                if not existing_text:
                    should_replace = True
                elif is_content_italian and not is_already_italian:
                    should_replace = True
                elif len(page_content) > len(existing_text) * 1.5:  # 50% più lungo
                    should_replace = True
                
                if should_replace:
                    # Formatta come HTML se necessario
                    if not page_content.startswith('<'):
                        page_content = f"<p>{page_content}</p>"
                    
                    page_data['text'] = page_content
                    pages_updated += 1
                    total_pages_updated += 1
        
        if pages_updated > 0:
            print(f"   ✅ Aggiornate {pages_updated} pagine")
        else:
            print(f"   ⏭️  Nessuna pagina aggiornata")
    
    # Salva file aggiornato
    with open(rules_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n📊 RIEPILOGO:")
    print(f"  ✅ Pagine aggiornate con traduzioni italiane: {total_pages_updated}")
    print(f"  💾 File salvato: {rules_file}")

if __name__ == '__main__':
    if not PDF_AVAILABLE:
        print("❌ ERRORE: Nessuna libreria PDF disponibile!")
        print("\nInstalla una delle seguenti librerie:")
        print("  pip install PyPDF2")
        print("  oppure")
        print("  pip install pdfplumber")
        exit(1)
    
    extract_translations_from_pdf()
