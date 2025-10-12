"""
STR PDF Data Extractor
Extracts data from STR PDFs using bounding box template approach
Based on reference/extract_str.py with Excel output capabilities
"""

import json
import re
import pdfplumber
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


class STRExtractor:
    def __init__(self, template_path="app/templates/template.json"):
        """Initialize extractor with template"""
        self.template_path = template_path
        self.load_template(template_path)

    def load_template(self, template_path):
        """Load template from file"""
        template_file = Path(template_path)
        if not template_file.exists():
            # Try looking in the project root
            template_file = Path(__file__).parent.parent / template_path

        if not template_file.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        with open(template_file, 'r', encoding='utf-8') as f:
            template = json.load(f)

        self.fields = template['fields']
        self.pdf_dimensions = template.get('pdf_dimensions', {})

    def detect_section_offset(self, page, header_field_name, page_count=1):
        """Detect Y-offset for a section by finding its header position

        Args:
            page: pdfplumber page object
            header_field_name: name of the header field (e.g., 'maklumat_waris_header')
            page_count: total number of pages in PDF (default: 1)

        Returns:
            Y-offset in pixels (positive = shifted down, negative = shifted up), or None if header not found
        """
        if header_field_name not in self.fields:
            return 0

        template_box = self.fields[header_field_name]
        template_y = template_box['y']
        template_x = template_box['x']
        template_w = template_box['width']

        # Expected header text keywords
        header_keywords = {
            'maklumat_pemohon_header': ['MAKLUMAT', 'PEMOHON'],
            'maklumat_pasangan_header': ['MAKLUMAT', 'PASANGAN'],
            'maklumat_anak_header': ['MAKLUMAT', 'ANAK'],
            'maklumat_waris_header': ['MAKLUMAT', 'WARIS']
        }

        keywords = header_keywords.get(header_field_name, ['MAKLUMAT'])

        # Use larger search range for waris section (variable position due to anak section)
        search_range = 200 if header_field_name == 'maklumat_waris_header' else 50

        try:
            # Get all words in the page
            words = page.extract_words()

            # For waris header, need to find both MAKLUMAT and WARIS nearby
            if header_field_name == 'maklumat_waris_header':
                # Find all MAKLUMAT words first
                maklumat_words = []
                waris_words = []

                for word in words:
                    word_text = word['text'].upper()
                    word_x = word['x0']
                    word_y = word['top']

                    # Look for keywords in expected X range
                    if template_x - 20 <= word_x <= template_x + template_w + 20:
                        # For multi-page PDFs: no Y constraint (waris can be anywhere)
                        # For single-page PDFs: use Y constraint for precision
                        if page_count > 1 or abs(word_y - template_y) <= search_range:
                            if 'MAKLUMAT' in word_text:
                                maklumat_words.append((word_y, word_x, word_text))
                            elif 'WARIS' in word_text:
                                waris_words.append((word_y, word_x, word_text))

                # Find MAKLUMAT and WARIS that are on the same line (within 5px vertically)
                for mak_y, mak_x, mak_text in maklumat_words:
                    for war_y, war_x, war_text in waris_words:
                        if abs(mak_y - war_y) <= 5:  # Same line
                            actual_y = mak_y
                            offset = int(actual_y - template_y)
                            return offset

                # WARIS header not found
                return None

            # For other headers, use original logic
            candidates = []
            for word in words:
                word_text = word['text'].upper()
                word_x = word['x0']
                word_y = word['top']

                # Check if word matches any keyword and is in correct X range
                if (any(kw in word_text for kw in keywords) and
                    template_x - 20 <= word_x <= template_x + template_w + 20 and
                    abs(word_y - template_y) <= search_range):
                    candidates.append((word_y, word_text))

            if candidates:
                # Use the first matching candidate (should be the header)
                actual_y = candidates[0][0]
                offset = int(actual_y - template_y)
                return offset

        except Exception as e:
            pass

        return 0  # No offset if header not found

    def extract_text_from_box(self, page, box, y_offset=0, tolerance=5):
        """Extract text using word filtering with section-based Y-offset and tolerance

        Args:
            page: pdfplumber page object
            box: dictionary with 'x', 'y', 'width', 'height' keys
            y_offset: Section-specific Y-offset in pixels
            tolerance: Y-axis tolerance in pixels (default: 5px for tight matching)

        Returns:
            Extracted text string
        """
        x, y, w, h = box['x'], box['y'], box['width'], box['height']

        # Apply section offset to Y coordinate
        y_adjusted = y + y_offset

        try:
            # Get all words on page with their coordinates
            words = page.extract_words()

            # Filter words within bounding box with Y-tolerance
            # Using tight tolerance since we already applied section offset
            field_words = [
                word for word in words
                if (x <= word['x0'] <= x + w) and
                   (y_adjusted - tolerance <= word['top'] <= y_adjusted + h + tolerance)
            ]

            if field_words:
                # Sort by position (top to bottom, left to right)
                field_words.sort(key=lambda w: (w['top'], w['x0']))
                # Join words preserving order
                text = ' '.join([w['text'] for w in field_words])
                # Clean up the text
                text = text.strip()
                # Replace multiple spaces with single space
                text = ' '.join(text.split())
                # Remove trailing punctuation (colons, semicolons, etc.)
                text = text.rstrip(':;,.')
                return text

            return ""

        except Exception as e:
            return ""

    def extract_anak_table(self, page):
        """Extract MAKLUMAT ANAK table using pdfplumber table detection"""
        try:
            # Extract all tables from the page
            tables = page.extract_tables()

            # Find the MAKLUMAT ANAK table (usually contains columns: NAMA, NO.MYKAD/MYKID, UMUR, STATUS)
            for table in tables:
                if not table or len(table) < 2:
                    continue

                # Check if this is the ANAK table by looking at headers
                header = table[0] if table else []
                header_text = ' '.join([str(cell or '').upper() for cell in header])

                if 'NAMA' in header_text and 'MYKAD' in header_text and 'UMUR' in header_text:
                    # Found the ANAK table
                    children = []
                    for row in table[1:]:  # Skip header row
                        if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                            continue  # Skip empty rows

                        # Extract child data (handle variable column positions)
                        child = {}
                        for i, cell in enumerate(row):
                            cell_value = str(cell).strip() if cell else ""
                            if i < len(header) and header[i]:
                                field_name = str(header[i]).strip().lower()
                                # Normalize field names
                                if 'nama' in field_name:
                                    child['nama'] = cell_value
                                elif 'mykad' in field_name or 'mykid' in field_name:
                                    child['no_mykad'] = cell_value
                                elif 'umur' in field_name:
                                    child['umur'] = cell_value
                                elif 'status' in field_name or 'hubungan' in field_name:
                                    child['status'] = cell_value

                        if child:  # Only add if we extracted something
                            children.append(child)

                    return children

            return []

        except Exception as e:
            return []

    def extract_waris_section(self, page):
        """Extract MAKLUMAT WARIS using header-based positioning"""
        try:
            # Find the "MAKLUMAT WARIS" header text
            text_objects = page.extract_words()

            waris_header_y = None
            for word in text_objects:
                text = word['text'].upper()
                if 'MAKLUMAT' in text and 'WARIS' in text:
                    waris_header_y = word['bottom']
                    break
                elif 'WARIS' in text:
                    # Check if MAKLUMAT is nearby
                    for other_word in text_objects:
                        if abs(other_word['top'] - word['top']) < 5 and 'MAKLUMAT' in other_word['text'].upper():
                            waris_header_y = max(word['bottom'], other_word['bottom'])
                            break
                    if waris_header_y:
                        break

            if not waris_header_y:
                return {}

            # Define approximate field positions relative to header
            field_labels = {
                'hubungan': 'Hubungan',
                'no_pengenalan': 'No Pengenalan',
                'nama': 'Nama',
                'no_telefon': 'No Telefon'
            }

            waris_data = {}

            # Extract text in the WARIS section (from header to bottom of page)
            waris_bbox = (0, waris_header_y, page.width, page.height)
            waris_section = page.within_bbox(waris_bbox)
            waris_words = waris_section.extract_words()

            # For each field, find the label and extract the value after it
            for field_key, label_text in field_labels.items():
                label_found = False
                for i, word in enumerate(waris_words):
                    if label_text.upper() in word['text'].upper():
                        label_found = True
                        # Find text on the same line or slightly below (within 10px)
                        label_y = word['top']
                        label_x_end = word['x1']

                        # Collect all text after the label on the same line
                        value_parts = []
                        for other_word in waris_words:
                            # Check if word is on the same line and to the right of label
                            if abs(other_word['top'] - label_y) < 10 and other_word['x0'] > label_x_end:
                                # Skip colons
                                if other_word['text'].strip() != ':':
                                    value_parts.append(other_word['text'])

                        if value_parts:
                            waris_data[field_key] = ' '.join(value_parts).strip()
                        else:
                            waris_data[field_key] = ""
                        break

                if not label_found:
                    waris_data[field_key] = ""

            return waris_data

        except Exception as e:
            return {}

    def extract_pasangan_section(self, page):
        """Extract MAKLUMAT PASANGAN using header-based positioning"""
        try:
            # Find the "MAKLUMAT PASANGAN" header text
            text_objects = page.extract_words()

            pasangan_header_y = None
            for word in text_objects:
                text = word['text'].upper()
                if 'MAKLUMAT' in text and 'PASANGAN' in text:
                    pasangan_header_y = word['bottom']
                    break
                elif 'PASANGAN' in text:
                    # Check if MAKLUMAT is nearby
                    for other_word in text_objects:
                        if abs(other_word['top'] - word['top']) < 5 and 'MAKLUMAT' in other_word['text'].upper():
                            pasangan_header_y = max(word['bottom'], other_word['bottom'])
                            break
                    if pasangan_header_y:
                        break

            if not pasangan_header_y:
                return {}

            # Find the next section header to limit extraction area
            next_section_y = page.height
            for word in text_objects:
                if word['top'] > pasangan_header_y:
                    text = word['text'].upper()
                    if 'MAKLUMAT' in text and ('ANAK' in text or 'WARIS' in text):
                        next_section_y = word['top']
                        break

            # Define field labels for PASANGAN
            field_labels = {
                'nama': 'Nama',
                'jenis_pengenalan': 'Jenis Pengenalan',
                'no_mykad': 'MyKAD',
                'negara_asal': 'Negara Asal',
                'no_telefon': 'No. Telefon',
                'jantina': 'Jantina',
                'pekerjaan': 'Pekerjaan',
                'nama_bank': 'Nama Bank Pasangan',
                'no_akaun_bank': 'No Akaun Bank Pasangan'
            }

            pasangan_data = {}

            # Extract text in the PASANGAN section (from header to next section)
            pasangan_bbox = (0, pasangan_header_y, page.width, next_section_y)
            pasangan_section = page.within_bbox(pasangan_bbox)
            pasangan_words = pasangan_section.extract_words()

            # For each field, find the label and extract the value after it
            for field_key, label_text in field_labels.items():
                label_found = False
                for i, word in enumerate(pasangan_words):
                    if label_text.upper() in word['text'].upper():
                        label_found = True
                        # Find text on the same line or slightly below (within 10px)
                        label_y = word['top']
                        label_x_end = word['x1']

                        # Collect all text after the label on the same line
                        value_parts = []
                        for other_word in pasangan_words:
                            # Check if word is on the same line and to the right of label
                            if abs(other_word['top'] - label_y) < 10 and other_word['x0'] > label_x_end:
                                # Skip colons and field labels
                                text = other_word['text'].strip()
                                if text != ':' and text.upper() not in label_text.upper():
                                    value_parts.append(text)

                        if value_parts:
                            pasangan_data[field_key] = ' '.join(value_parts).strip()
                        else:
                            pasangan_data[field_key] = ""
                        break

                if not label_found:
                    pasangan_data[field_key] = ""

            return pasangan_data

        except Exception as e:
            return {}

    def extract_from_pdf(self, pdf_path):
        """Extract all fields from a PDF with two-stage template selection"""
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]  # First page for main data

            # STAGE 1: Quick extraction of status_perkahwinan to determine template
            status_perkahwinan = ""
            if 'status_perkahwinan' in self.fields:
                status_box = self.fields['status_perkahwinan']
                status_perkahwinan = self.extract_text_from_box(page, status_box).upper()

            # Determine which template to use
            if 'KAHWIN' in status_perkahwinan:
                template_to_use = "app/templates/template_with_pasangan.json"
            else:
                template_to_use = "app/templates/template_without_pasangan.json"

            # STAGE 2: Reload appropriate template and extract all fields
            if template_to_use != self.template_path:
                self.load_template(template_to_use)

            # Get total page count for smart header detection
            page_count = len(pdf.pages)

            # Detect section offsets using header anchors
            pemohon_offset = self.detect_section_offset(page, 'maklumat_pemohon_header', page_count)
            pasangan_offset = self.detect_section_offset(page, 'maklumat_pasangan_header', page_count)
            anak_offset = self.detect_section_offset(page, 'maklumat_anak_header', page_count)
            waris_offset = self.detect_section_offset(page, 'maklumat_waris_header', page_count)

            # Check if WARIS section exists on page 1
            waris_exists = waris_offset is not None
            waris_page = page  # Default to page 1

            # If waris not found on page 1 and there's a page 2, check page 2
            if not waris_exists and page_count > 1:
                page_2 = pdf.pages[1]
                waris_offset_page2 = self.detect_section_offset(page_2, 'maklumat_waris_header', page_count)
                if waris_offset_page2 is not None:
                    waris_exists = True
                    waris_offset = waris_offset_page2
                    waris_page = page_2

            # Extract all fields from bounding boxes with section-specific offsets
            all_fields = {}
            pasangan_fields = {}
            waris_fields = {}

            for field_name, box in self.fields.items():
                # Skip header fields (not actual data)
                if field_name.endswith('_header'):
                    continue

                # Skip waris fields if waris section doesn't exist
                if field_name.startswith('waris_') and not waris_exists:
                    continue

                # Determine section-specific offset and page to extract from
                if field_name.startswith('waris_'):
                    offset = waris_offset if waris_offset is not None else 0
                    extract_page = waris_page
                elif field_name.startswith('pasangan_'):
                    offset = pasangan_offset
                    extract_page = page
                elif field_name.startswith('anak_'):
                    offset = anak_offset
                    extract_page = page
                else:
                    # Main applicant section (MAKLUMAT PEMOHON)
                    offset = pemohon_offset
                    extract_page = page

                # Determine field-specific tolerance (jantina needs tighter tolerance)
                tolerance = 3 if field_name == 'jantina' else 5

                # Extract with section offset and field-specific tolerance
                text = self.extract_text_from_box(extract_page, box, y_offset=offset, tolerance=tolerance)

                # Group fields by prefix
                if field_name.startswith('pasangan_'):
                    clean_name = field_name.replace('pasangan_', '')
                    pasangan_fields[clean_name] = text
                elif field_name.startswith('waris_'):
                    clean_name = field_name.replace('waris_', '')
                    waris_fields[clean_name] = text
                else:
                    all_fields[field_name] = text

            # Extract MAKLUMAT ANAK table (always on page 1)
            children = self.extract_anak_table(page)

            # Structure the data
            return self.structure_data(all_fields, pasangan_fields, waris_fields, children)

    def clean_age_field(self, age_text: str) -> str:
        """Clean age field by removing text after TAHUN

        Args:
            age_text: Raw age text (e.g., "51 TAHUN LELAKI")

        Returns:
            Cleaned age text (e.g., "51 TAHUN")
        """
        if not age_text:
            return ""

        # Extract only the number + TAHUN part using regex
        match = re.search(r'(\d+\s*TAHUN)', age_text.upper())
        if match:
            return match.group(1)

        return age_text

    def clean_remove_section_labels(self, text: str) -> str:
        """Remove section labels like 'Pemohon', 'Pasangan', 'Waris' from text

        Args:
            text: Raw text that may contain section labels

        Returns:
            Cleaned text with section labels removed
        """
        if not text:
            return ""

        # Remove "Pemohon" and everything after it (case-insensitive)
        # This handles cases like "W.P. KUALA LUMPUR Pemohon"
        cleaned = re.sub(r'\s*Pemohon.*$', '', text, flags=re.IGNORECASE)

        # Also remove other section labels
        cleaned = re.sub(r'\s*Pasangan.*$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*Waris.*$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*Anak.*$', '', cleaned, flags=re.IGNORECASE)

        # Clean up extra whitespace and commas
        cleaned = cleaned.strip().rstrip(',').strip()

        return cleaned

    def clean_postal_code(self, postal_text: str) -> str:
        """Extract only numbers from postal code field

        Args:
            postal_text: Raw postal code text that may contain alphabets

        Returns:
            Only numeric characters, empty string if no numbers found
        """
        if not postal_text:
            return ""

        # Extract only digits
        numbers_only = re.sub(r'[^\d]', '', postal_text)

        return numbers_only

    def clean_remove_numbers(self, text: str) -> str:
        """Remove all numbers from text

        Args:
            text: Raw text that may contain numbers

        Returns:
            Text with numbers removed, cleaned whitespace
        """
        if not text:
            return ""

        # Remove all digits
        no_numbers = re.sub(r'\d+', '', text)

        # Clean up extra whitespace
        cleaned = ' '.join(no_numbers.split()).strip()

        return cleaned

    def clean_remove_whitespace(self, text: str) -> str:
        """Remove all whitespace from text

        Args:
            text: Raw text that may contain spaces (e.g., "g mail.com")

        Returns:
            Text with all whitespace removed (e.g., "gmail.com")
        """
        if not text:
            return ""

        # Remove all whitespace characters
        no_spaces = re.sub(r'\s+', '', text)

        return no_spaces

    def clean_remove_trailing_rm(self, text: str) -> str:
        """Remove trailing 'RM' from text

        Args:
            text: Raw text that may have trailing "RM"

        Returns:
            Text with trailing "RM" removed
        """
        if not text:
            return ""

        # Remove trailing "RM" (case-insensitive)
        cleaned = re.sub(r'\s*RM\s*$', '', text, flags=re.IGNORECASE)

        return cleaned.strip()

    def clean_numbers_only(self, text: str) -> str:
        """Extract only numeric digits from text

        Args:
            text: Raw text that may contain non-numeric characters

        Returns:
            Only numeric characters
        """
        if not text:
            return ""

        # Extract only digits
        numbers_only = re.sub(r'[^\d]', '', text)

        return numbers_only

    def clean_jantina_field(self, jantina_text: str) -> str:
        """Extract only the gender word (LELAKI or PEREMPUAN) from jantina field

        Args:
            jantina_text: Raw jantina text (e.g., "PEREMPUAN TIDAK BEKERJA")

        Returns:
            Only the gender word (e.g., "PEREMPUAN")
        """
        if not jantina_text:
            return ""

        # Convert to uppercase for matching
        text_upper = jantina_text.upper()

        # Extract only LELAKI or PEREMPUAN (first occurrence)
        if 'PEREMPUAN' in text_upper:
            return 'PEREMPUAN'
        elif 'LELAKI' in text_upper:
            return 'LELAKI'

        # If neither found, remove numbers and return cleaned text
        letters_only = re.sub(r'[^a-zA-Z\s]', '', jantina_text)
        cleaned = ' '.join(letters_only.split()).strip()
        return cleaned

    def clean_alphabets_only(self, text: str) -> str:
        """Keep only alphabetic characters and spaces

        Args:
            text: Raw text that may contain numbers or special characters

        Returns:
            Only alphabetic characters with spaces
        """
        if not text:
            return ""

        # Remove all non-letter characters except spaces
        letters_only = re.sub(r'[^a-zA-Z\s]', '', text)

        # Clean up extra whitespace
        cleaned = ' '.join(letters_only.split()).strip()

        return cleaned

    def clean_mykad_number(self, mykad_text: str) -> str:
        """Clean MyKad number - keep only first 12 digits before whitespace

        Args:
            mykad_text: Raw MyKad text (e.g., "740307015359 51")

        Returns:
            Only first 12 digits (e.g., "740307015359")
        """
        if not mykad_text:
            return ""

        # Remove everything after whitespace
        text_before_space = mykad_text.split()[0] if mykad_text.split() else mykad_text

        # Extract only digits
        digits_only = re.sub(r'[^\d]', '', text_before_space)

        # Keep only first 12 digits
        if len(digits_only) >= 12:
            return digits_only[:12]

        return digits_only

    def structure_data(self, pemohon_fields: Dict[str, str], pasangan_fields: Dict[str, str],
                      waris_fields: Dict[str, str], children: List[Dict[str, str]]) -> Dict[str, Any]:
        """Structure the extracted data into logical groups"""

        # Construct complete address
        address_parts = []
        if pemohon_fields.get('alamat_surat'):
            address_parts.append(pemohon_fields['alamat_surat'])
        if pemohon_fields.get('poskod'):
            address_parts.append(pemohon_fields['poskod'])
        if pemohon_fields.get('bandar_daerah'):
            address_parts.append(pemohon_fields['bandar_daerah'])
        if pemohon_fields.get('negeri'):
            address_parts.append(pemohon_fields['negeri'])

        full_address = ', '.join(address_parts)
        # Clean "Pemohon" from the combined address
        full_address = self.clean_remove_section_labels(full_address)

        structured = {
            'document_info': {
                'type': 'Sumbangan Tunai Rahmah (STR)',
                'tarikh_cetak': pemohon_fields.get('tarikh_cetak', ''),
                'extraction_date': datetime.now().isoformat(),
                'extraction_version': 'v3.0-template-based'
            },
            'pemohon': {
                'nama': pemohon_fields.get('nama', ''),
                'no_mykad': self.clean_mykad_number(pemohon_fields.get('no_mykad', '')),
                'umur': self.clean_age_field(pemohon_fields.get('umur', '')),
                'jantina': self.clean_jantina_field(pemohon_fields.get('jantina', '')),
                'alamat': full_address,
                'poskod': self.clean_postal_code(pemohon_fields.get('poskod', '')),
                'bandar_daerah': self.clean_remove_numbers(pemohon_fields.get('bandar_daerah', '')),
                'negeri': self.clean_remove_section_labels(pemohon_fields.get('negeri', '')),
                'telefon_bimbit': pemohon_fields.get('no_telefon_bimbit', ''),
                'telefon_rumah': pemohon_fields.get('no_telefon_rumah', ''),
                'email': self.clean_remove_whitespace(pemohon_fields.get('alamat_emel', '')),
                'pekerjaan': self.clean_remove_trailing_rm(pemohon_fields.get('pekerjaan', '')),
                'pendapatan_bulanan': pemohon_fields.get('pendapatan_kasar', ''),
                'status_perkahwinan': pemohon_fields.get('status_perkahwinan', ''),
                'tarikh_perkahwinan': pemohon_fields.get('tarikh_perkahwinan', ''),
                'bank': {
                    'nama_bank': pemohon_fields.get('nama_bank', ''),
                    'no_akaun': pemohon_fields.get('no_akaun_bank', '')
                }
            },
            'pasangan': {
                'nama': pasangan_fields.get('nama', ''),
                'no_mykad': pasangan_fields.get('no_mykad', ''),
                'telefon': self.clean_numbers_only(pasangan_fields.get('no_telefon', '')),
                'jantina': self.clean_jantina_field(pasangan_fields.get('jantina', '')),
                'pekerjaan': self.clean_remove_section_labels(pasangan_fields.get('pekerjaan', '')),
                'bank': {
                    'nama_bank': pasangan_fields.get('nama_bank', ''),
                    'no_akaun': pasangan_fields.get('no_akaun_bank', '')
                }
            },
            'anak_anak': children,
            'waris': {
                'hubungan': self.clean_alphabets_only(waris_fields.get('hubungan', '')),
                'no_pengenalan': self.clean_numbers_only(waris_fields.get('no_pengenalan', '')),
                'nama': self.clean_alphabets_only(waris_fields.get('nama', '')),
                'telefon': self.clean_numbers_only(waris_fields.get('no_telefon', ''))
            }
        }

        return structured

    def flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
        """Flatten nested dictionary"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self.flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def format_details_column(self, data: Dict[str, Any]) -> str:
        """Format all data into a single multiline text column for Details"""
        lines = []

        # Get data sections
        pemohon = data.get('pemohon', {})
        pasangan = data.get('pasangan', {})
        waris = data.get('waris', {})

        # Section 1: Numbered minimal fields (1-13)
        lines.append(f"(1) NAME :- {pemohon.get('nama', '')}")
        lines.append(f"(2) IC :- {pemohon.get('no_mykad', '')}")
        lines.append(f"(3) PH1 :- {pemohon.get('telefon_bimbit', '')}")
        lines.append(f"(4) PH2 :- {pemohon.get('telefon_rumah', '')}")
        lines.append(f"(5) ADDRESS :- {pemohon.get('alamat', '')}")
        lines.append(f"(6) SPOUSE IC :- {pasangan.get('no_mykad', '')}")
        lines.append(f"(7) SPOUSE NAME :- {pasangan.get('nama', '')}")
        lines.append(f"(8) SPOUSE PH :- {pasangan.get('telefon', '')}")
        lines.append(f"(9) RELATION :- {waris.get('hubungan', '')}")
        lines.append(f"(10) REL-IC :- {waris.get('no_pengenalan', '')}")
        lines.append(f"(11) REL-NAME :- {waris.get('nama', '')}")
        lines.append(f"(12) REL-PH1 :- {waris.get('telefon', '')}")
        lines.append(f"(13) EMAIL :- {pemohon.get('email', '')}")
        lines.append("----------------------------")

        # Section 2: All pemohon fields with prefix
        if 'pemohon' in data:
            pemohon_flat = self.flatten_dict(data['pemohon'])
            for key, value in pemohon_flat.items():
                lines.append(f"pemohon_{key} :- {value}")
        lines.append("------------------")

        # Section 3: All pasangan fields with prefix
        if 'pasangan' in data:
            pasangan_flat = self.flatten_dict(data['pasangan'])
            for key, value in pasangan_flat.items():
                lines.append(f"pasangan_{key} :- {value}")
        lines.append("------------------")

        # Section 4: All waris fields with prefix
        if 'waris' in data:
            waris_flat = self.flatten_dict(data['waris'])
            for key, value in waris_flat.items():
                lines.append(f"waris_{key} :- {value}")
        lines.append("------------------")

        # Section 5: All anak fields
        if 'anak_anak' in data and data['anak_anak']:
            for i, child in enumerate(data['anak_anak'], 1):
                for key, value in child.items():
                    lines.append(f"anak_{i}_{key} :- {value}")

        return '\n'.join(lines)

    def to_excel_row(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert structured data to flat row for Excel"""
        row_data = {}

        # Add Card Number as empty column (will be positioned after pemohon_no_mykad)
        row_data['Card Number'] = ''

        # Add Details column with formatted multiline text
        row_data['Details'] = self.format_details_column(data)

        # Add pemohon data with prefix
        if 'pemohon' in data:
            pemohon_flat = self.flatten_dict(data['pemohon'])
            for key, value in pemohon_flat.items():
                row_data[f'pemohon_{key}'] = value

        # Add pasangan data with prefix
        if 'pasangan' in data:
            pasangan_flat = self.flatten_dict(data['pasangan'])
            for key, value in pasangan_flat.items():
                row_data[f'pasangan_{key}'] = value

        # Add waris data with prefix
        if 'waris' in data:
            waris_flat = self.flatten_dict(data['waris'])
            for key, value in waris_flat.items():
                row_data[f'waris_{key}'] = value

        # Add document_info data with prefix (exclude extraction_date and extraction_version)
        if 'document_info' in data:
            doc_flat = self.flatten_dict(data['document_info'])
            for key, value in doc_flat.items():
                if key not in ['extraction_date', 'extraction_version']:
                    row_data[f'document_{key}'] = value

        # Add children data with numbered columns (support up to 10 children)
        if 'anak_anak' in data and data['anak_anak']:
            for i, child in enumerate(data['anak_anak'][:10], 1):  # Limit to 10 children
                for key, value in child.items():
                    row_data[f'anak_{i}_{key}'] = value

        return row_data

    def to_excel_row_minimal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert structured data to minimal flat row with only essential fields"""
        pemohon = data.get('pemohon', {})
        pasangan = data.get('pasangan', {})
        waris = data.get('waris', {})

        return {
            'IC': pemohon.get('no_mykad', ''),
            'Card Number': '',
            'Details': self.format_details_column(data),
            'NAME': pemohon.get('nama', ''),
            'PH1': pemohon.get('telefon_bimbit', ''),
            'PH2': pemohon.get('telefon_rumah', ''),
            'ADDRESS': pemohon.get('alamat', ''),
            'SPOUSE IC': pasangan.get('no_mykad', ''),
            'SPOUSE NAME': pasangan.get('nama', ''),
            'SPOUSE PH': pasangan.get('telefon', ''),
            'RELATION': waris.get('hubungan', ''),
            'REL-IC': waris.get('no_pengenalan', ''),
            'REL-NAME': waris.get('nama', ''),
            'REL-PH1': waris.get('telefon', ''),
            'EMAIL': pemohon.get('email', '')
        }


# Legacy class name for backward compatibility
class STRExtractorV2(STRExtractor):
    """Backward compatibility alias"""
    pass
