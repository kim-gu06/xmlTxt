# Author: Chelsea Lee
# The xml2txt converts TEI-XML files to TXT files
# It excludes certain structural tags in the TXT found in the XML
# Removes margin text when it is emphasized in main page text by entry
# Output: States all matched margin notes and its page number, confirms TXT file is generated, shows matched/unmatched margins
# To run this program, input your specific pathname for the XML and TXT file

import xml.etree.ElementTree as ET
from xml.etree.ElementTree import SubElement, ElementTree, tostring
ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
# Set desired XML, TXT using pathname
xml_file = '/Users/chelsea/Downloads/55test.xml' #REPLACE WITH OWN PATHNAME
modified_xml = '/Users/chelsea/Downloads/modified55test.xml' #REPLACE WITH OWN PATHNAME
txt_file = '/Users/chelsea/Downloads/55test.txt' #REPLACE WITH OWN PATHNAME 
words_to_remove = ['[torn]', '[struck through]', '[strikethrough]', '[illegible]', '[crossed out]', '[Arabic]'] # List of words to exclude in TXT
tree = ET.parse(xml_file)
root = tree.getroot()

# Finds margin texts from XML and organizes by their entry number
# Returns: margin_notes (dict)
    # Key: xml:id=e_ (entry number)
    # Values: margin text content
def extract_margin_notes(root, ns):
    margin_notes = {}
    current_e = None  # Tracks current entry

    for elem in root.iter():
        # Get entry number
        if elem.tag == '{http://www.tei-c.org/ns/1.0}div' and elem.attrib.get("type") == "entry":
            current_e = elem.attrib.get("{http://www.w3.org/XML/1998/namespace}id")
        # Get margin text, add to margin_notes
        if elem.tag == '{http://www.tei-c.org/ns/1.0}note' and elem.attrib.get("place") == "margin":
                note_text = ''.join(elem.itertext()).strip()
                location = elem.attrib.get("target")
                if current_e:
                    margin_notes[current_e] = (note_text, location)

    return margin_notes

def store_match(matched_notes, key, margin_text):
    matched_notes.add((key, margin_text))
def store_unmatched(unmatched_notes, key, margin_text):
    unmatched_notes.add((key, margin_text))

# Finds match/unmatch margin_notes in text content of entry
# Returns: matched_notes (matched margin notes), unmatched_notes (unmatched margin notes)
def find_matches(root, ns):
    margin_notes = extract_margin_notes(root, ns)
    matched_notes = set()
    processed_entries = set()
    unmatched_notes = set()
    current_page_text = ""
    current_e = None

    for elem in root.iter():
        # Checks for margin text matches of current page
        if elem.tag == '{http://www.tei-c.org/ns/1.0}pb' and 'n' in elem.attrib:
            if current_e in margin_notes:
                # margin_text = margin_notes[current_e]
                note_text, _ = margin_notes[current_e]
                if note_text in current_page_text:
                    print(f"Match found for entry xml:id={current_e}")
                    store_match(matched_notes, current_e, note_text)
                    processed_entries.add(current_e)

            # Reset for new page
            current_page_text = ""

        # Accumulates all text within the entry
        if elem.tag == '{http://www.tei-c.org/ns/1.0}div' and elem.attrib.get("type") == "entry":
            current_e = elem.attrib.get("{http://www.w3.org/XML/1998/namespace}id")
            entry_text = ''.join([t for t in elem.itertext() if t.strip()])
            current_page_text += ' ' + entry_text

    # Final check of last page
    if current_e and current_e in margin_notes:
        margin_text = ' '.join(margin_notes[current_e])
        if margin_text in current_page_text:
            store_match(matched_notes, current_e, margin_text)
            processed_entries.add(current_e)

    # Stores all unmatched margin texts by comparing margin_notes's n with processed_entries
    for e, margin_text in margin_notes.items():
        if e not in processed_entries:
            store_unmatched(unmatched_notes, e, margin_text)

    return matched_notes, unmatched_notes

matched_notes, _ = find_matches(root, ns)
_, unmatched_notes = find_matches(root, ns)

def insert_margin(unmatched_notes, root):
    current_e = None
    for e, (note_text, location) in unmatched_notes:
        page = str(location[1])
        for elem in root.iter():
            if elem.tag == '{http://www.tei-c.org/ns/1.0}div' and elem.attrib.get("type") == "entry":
                current_e = elem.attrib.get("{http://www.w3.org/XML/1998/namespace}id")
            if current_e == e and elem.tag == '{http://www.tei-c.org/ns/1.0}pb' and elem.attrib.get("n") == page:
                print("Inserting")
                margin_element = ET.Element("note", place="margin", target=location, xml_id="e1_n1")
                margin_element.text = note_text
                elem.insert(0, margin_element)
                # Now remove the old <note> tag if it exists
                for child_note in elem.findall('.//tei:note[@place="margin"]', ns):
                    if child_note.attrib.get('target') == location:
                        print("Removing old note")
                        elem.remove(child_note)

insert_margin(unmatched_notes, root)
tree.write(modified_xml)
print("Modified XML file created")

# Reads XML, extracts textual content, removes specified tags, and writes cleaned text to a new TXT file
# Output: TXT file containing cleaned and formatted textual content from XML
def xml_to_txt(modified_xml, txt_file, words_to_remove):
    try:
        # Parse the XML file
        tree = ET.parse(modified_xml)
        root = tree.getroot()
        
        # Helper method to exclude specific words found in XML from TXT and replace with empty string
        def remove_words(text, words_to_remove):
            for word in words_to_remove:
                text = text.replace(word, '')
            return text

        with open(txt_file, 'w') as file:
            entry_id = None

            # Recursively extracts text from XML and writes cleaned content to TXT
            def extract_text(element):
                global entry_id
                if element.tag == '{http://www.tei-c.org/ns/1.0}div' and element.attrib.get("type") == "entry":
                    entry_id = element.attrib.get("{http://www.w3.org/XML/1998/namespace}id")
                elif element.tag == '{http://www.tei-c.org/ns/1.0}div' and element.attrib.get("type") == "entry_notes":
                    place_notes = root.findall('.//tei:note[@place]', namespaces=ns)
                    for note in place_notes:
                        text = note.text.strip() if note.text else ""
                        if (entry_id, text) in matched_notes:
                            return #Skip writing this note because it is matched
                
                # Writes cleaned text content to TXT
                if element.text:
                    clean_text = remove_words(element.text, words_to_remove)
                    file.write(clean_text.strip() + '\n')
                for child in element:
                    extract_text(child)
                if element.tail:
                    cleaned_tail = remove_words(element.tail, words_to_remove)
                    file.write(cleaned_tail.strip() + '\n')
            
            extract_text(root)
    
    except ET.ParseError:
        print("Error: Failed to parse XML file.")
    except IOError as e:
        print(f"Error: {e}")

xml_to_txt(modified_xml, txt_file, words_to_remove)
print("Matched Notes:", matched_notes)
print("Unmatched Notes:", unmatched_notes)
print("TXT file created")