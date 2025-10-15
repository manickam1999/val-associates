"""
PDF Border Detection Module
Detects v2 format PDFs (with black border) without cropping
"""

import cv2
import numpy as np
import pdfplumber
from pathlib import Path


def detect_border(image_array):
    """
    Detect black rectangular border in image using OpenCV contour detection

    Args:
        image_array: numpy array of the image (BGR format)

    Returns:
        tuple: (x, y, width, height) of the inner content area, or None if no border detected
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)

    # Apply binary threshold to detect black areas
    # Black border should be close to 0 (black)
    _, binary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)

    # Find contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    # Find the largest contour (should be the border)
    largest_contour = max(contours, key=cv2.contourArea)

    # Get bounding rectangle of the largest contour
    x, y, w, h = cv2.boundingRect(largest_contour)

    # Check if this is likely a border (should be near the edges and large)
    img_height, img_width = gray.shape
    contour_area = w * h
    image_area = img_width * img_height

    # Border should cover at least 80% of the image
    if contour_area < 0.8 * image_area:
        return None

    # IMPORTANT: Real black borders (v2 format) start significantly inside the page
    # False positives (v1 format) start at page edges (x≈5, y≈5)
    # Real v2 border starts around x=64, y=64
    # Set minimum threshold to distinguish them
    MIN_BORDER_OFFSET = 30  # pixels from edge

    if x < MIN_BORDER_OFFSET or y < MIN_BORDER_OFFSET:
        # This is too close to the edge - likely a false positive (page edge detection)
        return None

    # Border should also not be too far from edges (sanity check)
    max_margin_threshold = 0.10  # 10% of page size
    if (x > img_width * max_margin_threshold or
        y > img_height * max_margin_threshold):
        return None

    # Approximate polygon to check if it's rectangular
    epsilon = 0.02 * cv2.arcLength(largest_contour, True)
    approx = cv2.approxPolyDP(largest_contour, epsilon, True)

    # Should have 4 corners (rectangle)
    if len(approx) < 4 or len(approx) > 6:  # Allow some tolerance
        return None

    # Return the bounding box coordinates
    return (x, y, w, h)


def detect_v2_border(input_pdf_path, dpi=150):
    """
    Detect if PDF has v2 black border format

    Args:
        input_pdf_path: Path to input PDF file
        dpi: DPI for border detection (default: 150)

    Returns:
        bool: True if v2 border detected, False otherwise
    """
    input_path = Path(input_pdf_path)

    if not input_path.exists():
        return False

    try:
        # Convert first page to image for border detection using pdfplumber
        with pdfplumber.open(str(input_path)) as pdf:
            if not pdf.pages:
                return False

            # Get first page and convert to image
            page = pdf.pages[0]
            pil_image = page.to_image(resolution=dpi).original

            # Convert PIL image to numpy array for OpenCV
            image_array = np.array(pil_image)

        # Detect border
        border_box = detect_border(image_array)

        if border_box is None:
            return False

        # Border detected
        return True

    except Exception as e:
        return False


def crop_pdf_if_needed(input_pdf_path, dpi=150):
    """
    Detect if PDF has v2 border (for backward compatibility)
    Returns original path and detection result

    Args:
        input_pdf_path: Path to input PDF file
        dpi: DPI for border detection (default: 150)

    Returns:
        tuple: (pdf_path, has_v2_border, None)
            - pdf_path: Original PDF path (no cropping)
            - has_v2_border: True if v2 border detected
            - None: No temp file (for compatibility)
    """
    has_border = detect_v2_border(input_pdf_path, dpi)
    return str(input_pdf_path), has_border, None


def cleanup_temp_file(temp_file_path):
    """
    Clean up temporary file (no-op for compatibility)

    Args:
        temp_file_path: Path to temporary file
    """
    pass  # No temp files created anymore
