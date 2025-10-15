"""
Text cleaning utilities for PDF extraction
Consolidates common text cleaning operations
"""

import re
from typing import Optional
from ..config.constants import GENDER_KEYWORDS, STATE_VARIATIONS


def clean_age_field(age_text: str) -> str:
    """Clean age field by removing text after TAHUN

    Args:
        age_text: Raw age text (e.g., "51 TAHUN LELAKI")

    Returns:
        Cleaned age text (e.g., "51 TAHUN")
    """
    if not age_text:
        return ""

    match = re.search(r'(\d+\s*TAHUN)', age_text.upper())
    if match:
        return match.group(1)

    return age_text


def remove_section_labels(text: str) -> str:
    """Remove section labels like 'Pemohon', 'Pasangan', 'Waris' from text

    Args:
        text: Raw text that may contain section labels

    Returns:
        Cleaned text with section labels removed
    """
    if not text:
        return ""

    # Remove section labels (case-insensitive)
    for label in ['Pemohon', 'Pasangan', 'Waris', 'Anak']:
        text = re.sub(rf'\s*{label}.*$', '', text, flags=re.IGNORECASE)

    # Clean up extra whitespace and commas
    text = text.strip().rstrip(',').strip()

    return text


def extract_postal_code(postal_text: str) -> str:
    """Extract only numbers from postal code field

    Args:
        postal_text: Raw postal code text that may contain alphabets

    Returns:
        Only numeric characters, empty string if no numbers found
    """
    if not postal_text:
        return ""

    return re.sub(r'[^\d]', '', postal_text)


def remove_numbers(text: str) -> str:
    """Remove all numbers from text

    Args:
        text: Raw text that may contain numbers

    Returns:
        Text with numbers removed, cleaned whitespace
    """
    if not text:
        return ""

    no_numbers = re.sub(r'\d+', '', text)
    return ' '.join(no_numbers.split()).strip()


def remove_whitespace(text: str) -> str:
    """Remove all whitespace from text

    Args:
        text: Raw text that may contain spaces (e.g., "g mail.com")

    Returns:
        Text with all whitespace removed (e.g., "gmail.com")
    """
    if not text:
        return ""

    return re.sub(r'\s+', '', text)


def remove_trailing_rm(text: str) -> str:
    """Remove trailing 'RM' from text

    Args:
        text: Raw text that may have trailing "RM"

    Returns:
        Text with trailing "RM" removed
    """
    if not text:
        return ""

    cleaned = re.sub(r'\s*RM\s*$', '', text, flags=re.IGNORECASE)
    return cleaned.strip()


def extract_numbers_only(text: str) -> str:
    """Extract only numeric digits from text

    Args:
        text: Raw text that may contain non-numeric characters

    Returns:
        Only numeric characters
    """
    if not text:
        return ""

    return re.sub(r'[^\d]', '', text)


def clean_jantina_field(jantina_text: str) -> str:
    """Extract only the gender word (LELAKI or PEREMPUAN) from jantina field

    Args:
        jantina_text: Raw jantina text (e.g., "PEREMPUAN TIDAK BEKERJA")

    Returns:
        Only the gender word (e.g., "PEREMPUAN")
    """
    if not jantina_text:
        return ""

    text_upper = jantina_text.upper()

    # Check for known gender keywords
    if 'PEREMPUAN' in text_upper:
        return GENDER_KEYWORDS['PEREMPUAN']
    elif 'LELAKI' in text_upper:
        return GENDER_KEYWORDS['LELAKI']

    # Fallback: remove numbers and return cleaned text
    letters_only = re.sub(r'[^a-zA-Z\s]', '', jantina_text)
    return ' '.join(letters_only.split()).strip()


def extract_alphabets_only(text: str) -> str:
    """Keep only alphabetic characters and spaces

    Args:
        text: Raw text that may contain numbers or special characters

    Returns:
        Only alphabetic characters with spaces
    """
    if not text:
        return ""

    letters_only = re.sub(r'[^a-zA-Z\s]', '', text)
    return ' '.join(letters_only.split()).strip()


def clean_mykad_number(mykad_text: str) -> str:
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


def is_state_in_address(state: str, address: str) -> bool:
    """Check if a state (or its variations) is already in the address

    Args:
        state: State name to check
        address: Address string to search in

    Returns:
        True if state or any variation is found in address
    """
    if not state or not address:
        return False

    state_normalized = ' '.join(state.upper().split())
    address_upper = ' '.join(address.upper().split())

    # Direct match
    if state_normalized in address_upper:
        return True

    # Check variations
    for state_key, variations in STATE_VARIATIONS.items():
        if any(keyword in state_normalized for keyword in [state_key]):
            if any(var in address_upper for var in variations):
                return True

    # Check word overlap
    state_words = set(state_normalized.split())
    address_words = set(address_upper.split())
    overlap = len(state_words & address_words)

    return overlap >= len(state_words) * 0.5
