"""
Constants and configuration values for PDF extraction
"""

# PDF Format Offsets
V2_OFFSET_X = 28.34
V2_OFFSET_Y = 28.34

# DPI Settings
DEFAULT_DPI = 150
BORDER_DETECTION_DPI = 150

# Border Detection Parameters
MIN_BORDER_OFFSET = 30  # pixels from edge
BORDER_AREA_THRESHOLD = 0.8  # 80% of image area
MAX_MARGIN_THRESHOLD = 0.10  # 10% of page size
BORDER_THRESHOLD_VALUE = 50  # Binary threshold for black detection

# Extraction Tolerances
TOLERANCE_DEFAULT = 5  # Default Y-axis tolerance in pixels
TOLERANCE_TIGHT = 3  # Tight tolerance for specific fields (e.g., jantina)
TOLERANCE_LABEL = 10  # Tolerance for label detection

# Section Header Keywords
SECTION_HEADERS = {
    'maklumat_pemohon_header': ['MAKLUMAT', 'PEMOHON'],
    'maklumat_pasangan_header': ['MAKLUMAT', 'PASANGAN'],
    'maklumat_anak_header': ['MAKLUMAT', 'ANAK'],
    'maklumat_waris_header': ['MAKLUMAT', 'WARIS']
}

# Search Ranges for Header Detection
SEARCH_RANGE_DEFAULT = 50
SEARCH_RANGE_WARIS = 200  # Larger range for waris (variable position)

# Field Labels for Section Extraction
WARIS_FIELD_LABELS = {
    'hubungan': 'Hubungan',
    'no_pengenalan': 'No Pengenalan',
    'nama': 'Nama',
    'no_telefon': 'No Telefon'
}

PASANGAN_FIELD_LABELS = {
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

# Malaysian State Variations (for address deduplication)
STATE_VARIATIONS = {
    'W.P.': ['WILAYAH PERSEKUTUAN', 'WP', 'W.P.', 'W.P'],
    'WILAYAH PERSEKUTUAN': ['W.P.', 'WP', 'WILAYAH PERSEKUTUAN'],
    'KUALA LUMPUR': ['KL', 'K.L.', 'KUALA LUMPUR'],
    'SELANGOR': ['SELANGOR', 'SEL'],
    'PULAU PINANG': ['PULAU PINANG', 'PENANG', 'P.PINANG'],
    'JOHOR': ['JOHOR', 'JHR'],
    'MELAKA': ['MELAKA', 'MALACCA', 'MLK'],
}

# Excel Column Patterns (for string formatting)
STRING_COLUMN_PATTERNS = [
    'IC', 'PH', 'no_mykad', 'no_mykid', 'telefon',
    'poskod', 'no_akaun', 'no_pengenalan'
]

# Gender Keywords
GENDER_KEYWORDS = {
    'PEREMPUAN': 'PEREMPUAN',
    'LELAKI': 'LELAKI'
}

# Document Info
DOCUMENT_TYPE = 'Sumbangan Tunai Rahmah (STR)'
EXTRACTION_VERSION = 'v3.0-template-based'

# Excel Sheet Name
EXCEL_SHEET_NAME = 'STR_Data'

# Maximum Children Supported
MAX_CHILDREN = 10

# Same Line Threshold (pixels)
SAME_LINE_THRESHOLD = 5
