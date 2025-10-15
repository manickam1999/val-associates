"""
STR PDF Data Extractor
Extracts data from STR PDFs using bounding box template approach
Based on reference/extract_str.py with Excel output capabilities
"""

import json
import re
import copy
import pdfplumber
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from .pdf_cropper import crop_pdf_if_needed
from .config.constants import (
    V2_OFFSET_X, V2_OFFSET_Y, TOLERANCE_DEFAULT, TOLERANCE_TIGHT, TOLERANCE_LABEL,
    SECTION_HEADERS, SEARCH_RANGE_DEFAULT, SEARCH_RANGE_WARIS,
    WARIS_FIELD_LABELS, PASANGAN_FIELD_LABELS, SAME_LINE_THRESHOLD,
    DOCUMENT_TYPE, EXTRACTION_VERSION, EXCEL_SHEET_NAME, MAX_CHILDREN
)
from .utils.text_cleaners import (
    clean_age_field, remove_section_labels, extract_postal_code, remove_numbers,
    remove_whitespace, remove_trailing_rm, extract_numbers_only, clean_jantina_field,
    extract_alphabets_only, clean_mykad_number, is_state_in_address
)


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

        keywords = SECTION_HEADERS.get(header_field_name, ['MAKLUMAT'])

        # Use larger search range for waris section (variable position due to anak section)
        search_range = SEARCH_RANGE_WARIS if header_field_name == 'maklumat_waris_header' else SEARCH_RANGE_DEFAULT

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

                # Find MAKLUMAT and WARIS that are on the same line
                for mak_y, mak_x, mak_text in maklumat_words:
                    for war_y, war_x, war_text in waris_words:
                        if abs(mak_y - war_y) <= SAME_LINE_THRESHOLD:
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

    def extract_text_from_box(self, page, box, y_offset=0, tolerance=TOLERANCE_DEFAULT):
        """Extract text using word filtering with section-based Y-offset and tolerance

        Args:
            page: pdfplumber page object
            box: dictionary with 'x', 'y', 'width', 'height' keys
            y_offset: Section-specific Y-offset in pixels
            tolerance: Y-axis tolerance in pixels

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

    def _extract_section_by_header(self, page, header_keywords: List[str],
                                    field_labels: Dict[str, str],
                                    next_section_keywords: Optional[List[str]] = None) -> Dict[str, str]:
        """Generic method to extract a section using header-based positioning

        Args:
            page: pdfplumber page object
            header_keywords: Keywords to find section header (e.g., ['MAKLUMAT', 'WARIS'])
            field_labels: Dict mapping field keys to label text
            next_section_keywords: Keywords for next section to limit extraction (optional)

        Returns:
            Dict of extracted field values
        """
        try:
            # Find the section header text
            text_objects = page.extract_words()

            header_y = None
            for word in text_objects:
                text = word['text'].upper()
                if all(kw in ' '.join([w['text'].upper() for w in text_objects
                                       if abs(w['top'] - word['top']) < SAME_LINE_THRESHOLD])
                       for kw in header_keywords):
                    header_y = word['bottom']
                    break

            if not header_y:
                return {}

            # Find the next section header to limit extraction area
            next_section_y = page.height
            if next_section_keywords:
                for word in text_objects:
                    if word['top'] > header_y:
                        text = word['text'].upper()
                        if any(kw in text for kw in next_section_keywords):
                            next_section_y = word['top']
                            break

            # Extract text in the section
            section_bbox = (0, header_y, page.width, next_section_y)
            section = page.within_bbox(section_bbox)
            section_words = section.extract_words()

            # Extract field values
            extracted_data = {}
            for field_key, label_text in field_labels.items():
                for i, word in enumerate(section_words):
                    if label_text.upper() in word['text'].upper():
                        label_y = word['top']
                        label_x_end = word['x1']

                        # Collect all text after the label on the same line
                        value_parts = []
                        for other_word in section_words:
                            if (abs(other_word['top'] - label_y) < TOLERANCE_LABEL and
                                other_word['x0'] > label_x_end and
                                other_word['text'].strip() != ':'):
                                value_parts.append(other_word['text'])

                        extracted_data[field_key] = ' '.join(value_parts).strip() if value_parts else ""
                        break

                if field_key not in extracted_data:
                    extracted_data[field_key] = ""

            return extracted_data

        except Exception as e:
            return {}

    def extract_waris_section(self, page):
        """Extract MAKLUMAT WARIS using header-based positioning"""
        return self._extract_section_by_header(
            page,
            header_keywords=['MAKLUMAT', 'WARIS'],
            field_labels=WARIS_FIELD_LABELS,
            next_section_keywords=None
        )

    def extract_pasangan_section(self, page):
        """Extract MAKLUMAT PASANGAN using header-based positioning"""
        return self._extract_section_by_header(
            page,
            header_keywords=['MAKLUMAT', 'PASANGAN'],
            field_labels=PASANGAN_FIELD_LABELS,
            next_section_keywords=['ANAK', 'WARIS']
        )


    def _load_template_by_status(self, page, working_fields: Dict, has_v2_border: bool) -> Dict:
        """Load appropriate template based on status_perkahwinan

        Returns:
            Updated working_fields dict
        """
        # Quick extraction of status_perkahwinan to determine template
        status_perkahwinan = ""
        if 'status_perkahwinan' in working_fields:
            status_box = working_fields['status_perkahwinan']
            status_perkahwinan = self.extract_text_from_box(page, status_box).upper()

        # Determine which template to use
        if 'KAHWIN' in status_perkahwinan:
            template_to_use = "app/templates/template_with_pasangan.json"
        else:
            template_to_use = "app/templates/template_without_pasangan.json"

        # Reload appropriate template if different
        if template_to_use != self.template_path:
            self.load_template(template_to_use)
            # Re-create working copy with new template
            working_fields = copy.deepcopy(self.fields)
            # Re-apply v2 offset to new template if needed
            if has_v2_border:
                for field_name, box in working_fields.items():
                    box['x'] += V2_OFFSET_X
                    box['y'] += V2_OFFSET_Y

        return working_fields

    def _calculate_section_offsets(self, pdf, page, has_v2_border: bool) -> Tuple[Dict[str, int], Any, bool]:
        """Calculate section offsets and determine waris page

        Returns:
            Tuple of (offsets_dict, waris_page, waris_exists)
        """
        page_count = len(pdf.pages)

        # For v2 format, skip auto-offset detection (use fixed offset already applied)
        # Exception: WARIS needs dynamic offset due to variable ANAK section length
        # For v1 format, use auto-offset detection
        if has_v2_border:
            # For waris in v2: detected offset includes v2 border shift, so subtract it
            # to avoid double-counting (detected offset - v2_offset = additional offset for variable ANAK content)
            waris_detected_offset = self.detect_section_offset(page, 'maklumat_waris_header', page_count)

            # Only apply adjustment if header was actually found (distinguish None from 0)
            if waris_detected_offset is not None:
                waris_adjusted_offset = waris_detected_offset - int(V2_OFFSET_Y)
            else:
                waris_adjusted_offset = None  # Header not found on page 1

            offsets = {
                'pemohon': 0,
                'pasangan': 0,
                'anak': 0,
                'waris': waris_adjusted_offset
            }
        else:
            # Detect section offsets using header anchors (v1 format only)
            offsets = {
                'pemohon': self.detect_section_offset(page, 'maklumat_pemohon_header', page_count),
                'pasangan': self.detect_section_offset(page, 'maklumat_pasangan_header', page_count),
                'anak': self.detect_section_offset(page, 'maklumat_anak_header', page_count),
                'waris': self.detect_section_offset(page, 'maklumat_waris_header', page_count)
            }

        # Check if WARIS section exists on page 1
        waris_exists = offsets['waris'] is not None
        waris_page = page  # Default to page 1

        # If waris not found on page 1 and there's a page 2, check page 2
        if not waris_exists and page_count > 1:
            page_2 = pdf.pages[1]
            waris_offset_page2 = self.detect_section_offset(page_2, 'maklumat_waris_header', page_count)
            if waris_offset_page2 is not None:
                waris_exists = True
                # Apply v2 adjustment (same logic as page 1 WARIS)
                if has_v2_border:
                    offsets['waris'] = waris_offset_page2 - int(V2_OFFSET_Y)
                else:
                    offsets['waris'] = waris_offset_page2
                waris_page = page_2

        return offsets, waris_page, waris_exists

    def _extract_all_fields(self, working_fields: Dict, page, offsets: Dict,
                           waris_page, waris_exists: bool) -> Tuple[Dict, Dict, Dict]:
        """Extract all fields from bounding boxes with section-specific offsets

        Returns:
            Tuple of (all_fields, pasangan_fields, waris_fields)
        """
        all_fields = {}
        pasangan_fields = {}
        waris_fields = {}

        for field_name, box in working_fields.items():
            # Skip header fields (not actual data)
            if field_name.endswith('_header'):
                continue

            # Skip waris fields if waris section doesn't exist
            if field_name.startswith('waris_') and not waris_exists:
                continue

            # Determine section-specific offset and page to extract from
            if field_name.startswith('waris_'):
                offset = offsets['waris'] if offsets['waris'] is not None else 0
                extract_page = waris_page
            elif field_name.startswith('pasangan_'):
                offset = offsets['pasangan']
                extract_page = page
            elif field_name.startswith('anak_'):
                offset = offsets['anak']
                extract_page = page
            else:
                # Main applicant section (MAKLUMAT PEMOHON)
                offset = offsets['pemohon']
                extract_page = page

            # Determine field-specific tolerance (jantina needs tighter tolerance)
            tolerance = TOLERANCE_TIGHT if field_name == 'jantina' else TOLERANCE_DEFAULT

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

        return all_fields, pasangan_fields, waris_fields

    def extract_from_pdf(self, pdf_path):
        """Extract all fields from a PDF with two-stage template selection"""
        # Detect if this is v2 format (with black border)
        working_pdf_path, has_v2_border, temp_file = crop_pdf_if_needed(pdf_path, dpi=150)

        try:
            with pdfplumber.open(working_pdf_path) as pdf:
                page = pdf.pages[0]  # First page for main data

                # Create a working copy of fields to avoid mutating the original template
                working_fields = copy.deepcopy(self.fields)

                # If v2 format, apply offset to working copy
                if has_v2_border:
                    for field_name, box in working_fields.items():
                        box['x'] += V2_OFFSET_X
                        box['y'] += V2_OFFSET_Y

                # STAGE 1: Load appropriate template based on status_perkahwinan
                working_fields = self._load_template_by_status(page, working_fields, has_v2_border)

                # STAGE 2: Calculate section offsets
                offsets, waris_page, waris_exists = self._calculate_section_offsets(pdf, page, has_v2_border)

                # STAGE 3: Extract all fields
                all_fields, pasangan_fields, waris_fields = self._extract_all_fields(
                    working_fields, page, offsets, waris_page, waris_exists
                )

                # Extract MAKLUMAT ANAK table (always on page 1)
                children = self.extract_anak_table(page)

                # Structure the data
                structured_data = self.structure_data(all_fields, pasangan_fields, waris_fields, children)

                # Add metadata about v2 format detection
                structured_data['document_info']['v2_format_detected'] = has_v2_border

                return structured_data
        finally:
            pass  # No cleanup needed anymore


    def smart_combine_address(self, alamat_surat: str, poskod: str,
                             bandar_daerah: str, negeri: str) -> str:
        """Smart address combination that avoids duplicating information

        Args:
            alamat_surat: Main address field (may contain complete or partial address)
            poskod: Postal code
            bandar_daerah: District/city
            negeri: State

        Returns:
            Combined address with no duplication
        """
        if not alamat_surat:
            alamat_surat = ""

        # Normalize for comparison
        alamat_upper = ' '.join(alamat_surat.upper().split())

        # Clean individual components
        poskod_clean = extract_postal_code(poskod) if poskod else ""
        bandar_clean = remove_numbers(bandar_daerah) if bandar_daerah else ""
        negeri_clean = remove_section_labels(negeri) if negeri else ""

        # Components to potentially add
        parts_to_add = []

        # Check if postal code is already in alamat_surat
        if poskod_clean and poskod_clean not in alamat_upper:
            parts_to_add.append(poskod_clean)

        # Check if district is already in alamat_surat
        if bandar_clean:
            bandar_normalized = ' '.join(bandar_clean.upper().split())
            if bandar_normalized not in alamat_upper:
                bandar_words = set(bandar_normalized.split())
                alamat_words = set(alamat_upper.split())
                if len(bandar_words & alamat_words) < len(bandar_words) * 0.5:
                    parts_to_add.append(bandar_clean)

        # Check if state is already in alamat_surat using utility function
        if negeri_clean and not is_state_in_address(negeri_clean, alamat_surat):
            parts_to_add.append(negeri_clean)

        # Combine: start with alamat_surat, then add missing parts
        result_parts = [alamat_surat] if alamat_surat else []
        result_parts.extend(parts_to_add)

        # Join with comma and clean up
        combined = ', '.join(part for part in result_parts if part)

        # Final cleanup
        combined = remove_section_labels(combined)
        combined = re.sub(r',\s*,+', ',', combined)
        combined = re.sub(r'\s+', ' ', combined).strip()
        combined = combined.strip(',').strip()

        return combined

    def structure_data(self, pemohon_fields: Dict[str, str], pasangan_fields: Dict[str, str],
                      waris_fields: Dict[str, str], children: List[Dict[str, str]]) -> Dict[str, Any]:
        """Structure the extracted data into logical groups"""

        # Smart address combination - avoids duplication
        full_address = self.smart_combine_address(
            alamat_surat=pemohon_fields.get('alamat_surat', ''),
            poskod=pemohon_fields.get('poskod', ''),
            bandar_daerah=pemohon_fields.get('bandar_daerah', ''),
            negeri=pemohon_fields.get('negeri', '')
        )

        structured = {
            'document_info': {
                'type': DOCUMENT_TYPE,
                'tarikh_cetak': pemohon_fields.get('tarikh_cetak', ''),
                'extraction_date': datetime.now().isoformat(),
                'extraction_version': EXTRACTION_VERSION
            },
            'pemohon': {
                'nama': pemohon_fields.get('nama', ''),
                'no_mykad': clean_mykad_number(pemohon_fields.get('no_mykad', '')),
                'umur': clean_age_field(pemohon_fields.get('umur', '')),
                'jantina': clean_jantina_field(pemohon_fields.get('jantina', '')),
                'alamat': full_address,
                'poskod': extract_postal_code(pemohon_fields.get('poskod', '')),
                'bandar_daerah': remove_numbers(pemohon_fields.get('bandar_daerah', '')),
                'negeri': remove_section_labels(pemohon_fields.get('negeri', '')),
                'telefon_bimbit': pemohon_fields.get('no_telefon_bimbit', ''),
                'telefon_rumah': pemohon_fields.get('no_telefon_rumah', ''),
                'email': remove_whitespace(pemohon_fields.get('alamat_emel', '')),
                'pekerjaan': remove_trailing_rm(pemohon_fields.get('pekerjaan', '')),
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
                'telefon': extract_numbers_only(pasangan_fields.get('no_telefon', '')),
                'jantina': clean_jantina_field(pasangan_fields.get('jantina', '')),
                'pekerjaan': remove_section_labels(pasangan_fields.get('pekerjaan', '')),
                'bank': {
                    'nama_bank': pasangan_fields.get('nama_bank', ''),
                    'no_akaun': pasangan_fields.get('no_akaun_bank', '')
                }
            },
            'anak_anak': children,
            'waris': {
                'hubungan': extract_alphabets_only(waris_fields.get('hubungan', '')),
                'no_pengenalan': extract_numbers_only(waris_fields.get('no_pengenalan', '')),
                'nama': extract_alphabets_only(waris_fields.get('nama', '')),
                'telefon': extract_numbers_only(waris_fields.get('no_telefon', ''))
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

    def _format_details(self, data: Dict[str, Any], include_full_data: bool = True) -> str:
        """Format data into multiline text column

        Args:
            data: Structured data dictionary
            include_full_data: If True, include all sections; if False, only numbered fields (1-13)

        Returns:
            Formatted multiline string
        """
        lines = []

        # Get data sections
        pemohon = data.get('pemohon', {})
        pasangan = data.get('pasangan', {})
        waris = data.get('waris', {})

        # Section 1: Numbered minimal fields (1-13) - always included
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

        # Only add full data sections if requested
        if include_full_data:
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

    def format_details_column(self, data: Dict[str, Any]) -> str:
        """Format all data into a single multiline text column for Details"""
        return self._format_details(data, include_full_data=True)

    def format_minimal_details_column(self, data: Dict[str, Any]) -> str:
        """Format only the first 13 numbered items for Minimal Detail column"""
        return self._format_details(data, include_full_data=False)

    def to_excel_row(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert structured data to flat row for Excel"""
        row_data = {}

        # Add Card Number as empty column (will be positioned after pemohon_no_mykad)
        row_data['Card Number'] = ''

        # Add Minimal Detail column with only top 13 items
        row_data['Minimal Detail'] = self.format_minimal_details_column(data)

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
