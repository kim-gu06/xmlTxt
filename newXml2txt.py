import xml.etree.ElementTree as ET
from pathlib import Path
import re
from datetime import datetime

# 配置路径
xml_path = Path("diary55Corrected.xml")
output_dir = Path("output_diary_by_date")
output_dir.mkdir(parents=True, exist_ok=True)


ns = {'tei': 'http://www.tei-c.org/ns/1.0'}


words_to_remove = ['[torn]', '[struck through]', '[strikethrough]', '[illegible]', '[crossed out]', '[Arabic]']


weekday_abbr = {
    'Monday': 'Mon', 'Tuesday': 'Tue', 'Wednesday': 'Wed', 'Thursday': 'Thu',
    'Friday': 'Fri', 'Saturday': 'Sat', 'Sunday': 'Sun',
    'Tuesd' : 'Tue', 'Thursd' : 'Thu',
    'Mond': 'Mon', 'Tues': 'Tue', 'Wedn': 'Wed', 'Thurs': 'Thu', 'Frid': 'Fri', 'Satur': 'Sat', 'Sund': 'Sun'
}
month_abbr = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

def remove_words(text, words):
    for word in words:
        text = text.replace(word, '')
    return text

def extract_margin_notes(root):
    margin_notes = {}
    current_e = None
    for elem in root.iter():
        if elem.tag.endswith('div') and elem.attrib.get("type") == "entry":
            current_e = elem.attrib.get("{http://www.w3.org/XML/1998/namespace}id")
        if elem.tag.endswith('note') and elem.attrib.get("place") == "margin":
            note_text = ''.join(elem.itertext()).strip()
            location = elem.attrib.get("target")
            if current_e:
                margin_notes[current_e] = (note_text, location)
    return margin_notes

def find_matches(root):
    margin_notes = extract_margin_notes(root)
    matched_notes = set()
    unmatched_notes = set()
    processed_entries = set()
    current_page_text = ""
    current_e = None

    for elem in root.iter():
        tag = elem.tag
        if tag.endswith('pb') and 'n' in elem.attrib:
            if current_e in margin_notes:
                note_text, _ = margin_notes[current_e]
                if note_text in current_page_text:
                    matched_notes.add((current_e, note_text))
                    processed_entries.add(current_e)
            current_page_text = ""
        if tag.endswith('div') and elem.attrib.get("type") == "entry":
            current_e = elem.attrib.get("{http://www.w3.org/XML/1998/namespace}id")
            entry_text = ''.join([t for t in elem.itertext() if t.strip()])
            current_page_text += ' ' + entry_text

    if current_e and current_e in margin_notes:
        note_text, _ = margin_notes[current_e]
        if note_text in current_page_text:
            matched_notes.add((current_e, note_text))
            processed_entries.add(current_e)

    for e, margin_text in margin_notes.items():
        if e not in processed_entries:
            unmatched_notes.add((e, margin_text))

    return matched_notes

def format_filename(entry_num, date_str, head_text):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        yyyy = dt.strftime("%Y")
        mmm = month_abbr[dt.month - 1]
        dd = dt.strftime("%d")
    except Exception:
        yyyy, mmm, dd = "unknown", "UNK", "00"

    weekday = next((weekday_abbr.get(w.strip(), w.strip()) for w in head_text.split() if w.strip() in weekday_abbr), "Day")
    return f"{entry_num}_{yyyy}_{mmm}_{dd}_{weekday}.txt"

def write_entries_by_date(root, matched_notes):
    entries = root.findall(".//tei:div[@type='entry']", ns)
    for idx, entry in enumerate(entries, start=1):
        entry_id = entry.attrib.get("{http://www.w3.org/XML/1998/namespace}id")
        date_elem = entry.find(".//tei:date", ns)
        head_elem = entry.find(".//tei:head", ns)
        if date_elem is None:
            continue
        date_str = date_elem.attrib.get("when")
        head_text = ''.join(head_elem.itertext()).strip() if head_elem is not None else ""

        lines = []

        def extract_text(elem):
            if elem.tag.endswith('div') and elem.attrib.get("type") == "entry_notes":
                for note in elem.findall('.//tei:note[@place]', ns):
                    text = note.text.strip() if note.text else ""
                    if (entry_id, text) in matched_notes:
                        return  # skip matched note
            if elem.text:
                lines.append(remove_words(elem.text, words_to_remove).strip())
            for child in elem:
                extract_text(child)
            if elem.tail:
                lines.append(remove_words(elem.tail, words_to_remove).strip())

        extract_text(entry)
        content = '\n'.join(filter(None, lines))
        filename = format_filename(idx, date_str, head_text)
        file_path = output_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)


tree = ET.parse(xml_path)
root = tree.getroot()
matched_notes = find_matches(root)
write_entries_by_date(root, matched_notes)

