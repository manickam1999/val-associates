"""
Batch PDF Processor
Handles processing multiple PDFs and combining into single Excel file.
"""

import asyncio
import zipfile
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Callable
from .str_extractor import STRExtractor


class BatchProcessor:
    def __init__(self):
        self.extractor = STRExtractor()

    async def extract_zip(self, zip_path: str, extract_dir: str) -> List[str]:
        """Extract PDFs from ZIP file."""
        pdf_files = []
        extract_path = Path(extract_dir)
        extract_path.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file_info in zip_ref.namelist():
                if file_info.lower().endswith('.pdf'):
                    zip_ref.extract(file_info, extract_dir)
                    pdf_files.append(str(extract_path / file_info))

        return pdf_files

    async def process_pdfs(
        self,
        pdf_files: List[str],
        progress_callback: Callable[[int, int, str, str], None] = None
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
        """Process multiple PDF files with progress tracking.

        Returns:
            Tuple of (all_data, failed_files) where failed_files contains error details
        """
        all_data = []
        failed_files = []
        total = len(pdf_files)

        for idx, pdf_path in enumerate(pdf_files, 1):
            pdf_name = Path(pdf_path).name

            if progress_callback:
                await progress_callback(idx, total, f"Processing {pdf_name}", "processing")

            try:
                # Run blocking PDF extraction in thread pool to avoid blocking event loop
                data = await asyncio.to_thread(self.extractor.extract_from_pdf, pdf_path)
                data['_source_file'] = pdf_name
                all_data.append(data)

                if progress_callback:
                    await progress_callback(idx, total, f"Completed {pdf_name}", "success")
            except Exception as e:
                error_msg = str(e)
                failed_files.append({
                    'filename': pdf_name,
                    'error': error_msg
                })

                if progress_callback:
                    await progress_callback(idx, total, f"Failed: {pdf_name} - {error_msg}", "error")
                # Continue processing other files
                continue

        return all_data, failed_files

    def combine_to_excel(self, all_data: List[Dict[str, Any]], output_path: str, mode: str = 'everything'):
        """Combine all extracted data into single Excel file."""
        rows = []

        for data in all_data:
            # Use appropriate row method based on mode
            if mode == 'minimal':
                row = self.extractor.to_excel_row_minimal(data)
            else:
                row = self.extractor.to_excel_row(data)

            # Add source file column
            row['source_file'] = data.get('_source_file', '')
            rows.append(row)

        # Create DataFrame
        df = pd.DataFrame(rows)

        # Reorder columns based on mode
        all_columns = df.columns.tolist()

        if mode == 'minimal':
            # For minimal mode: IC, Card Number, Details, then rest of columns
            first_cols = ['IC', 'Card Number', 'Details']
            other_cols = [col for col in all_columns if col not in first_cols]
            ordered_columns = first_cols + other_cols
        else:
            # For everything mode: pemohon_no_mykad, Card Number, Minimal Detail, Details, then other data columns, then document columns, then source_file
            document_cols = [col for col in all_columns if col.startswith('document_')]
            source_file_col = ['source_file'] if 'source_file' in all_columns else []

            # Ensure pemohon_no_mykad, Card Number, Minimal Detail, and Details are first
            first_cols = []
            if 'pemohon_no_mykad' in all_columns:
                first_cols.append('pemohon_no_mykad')
            if 'Card Number' in all_columns:
                first_cols.append('Card Number')
            if 'Minimal Detail' in all_columns:
                first_cols.append('Minimal Detail')
            if 'Details' in all_columns:
                first_cols.append('Details')

            # Get remaining data columns (exclude document_, source_file, and first_cols)
            data_cols = [col for col in all_columns
                        if col not in document_cols
                        and col != 'source_file'
                        and col not in first_cols]

            # Reorder: pemohon_no_mykad + Card Number + Minimal Detail + Details + other data columns + document columns + source_file
            ordered_columns = first_cols + data_cols + document_cols + source_file_col

        df = df[ordered_columns]

        # Convert numeric-looking text columns to string to prevent Excel auto-formatting
        string_column_patterns = [
            'IC', 'PH', 'no_mykad', 'no_mykid', 'telefon',
            'poskod', 'no_akaun', 'no_pengenalan'
        ]

        for col in df.columns:
            # Check if column name matches any pattern
            if any(pattern in col for pattern in string_column_patterns):
                # Convert to string and replace 'nan' with empty string
                df[col] = df[col].fillna('').astype(str)
                df[col] = df[col].replace('nan', '')

        # Save to Excel
        df.to_excel(output_path, sheet_name='STR_Data', index=False, engine='openpyxl')

        return len(rows)