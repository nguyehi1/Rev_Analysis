"""
PDF text extraction utility using pdfplumber with enhanced error handling and validation
"""
import pdfplumber
from typing import Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Constants
MAX_PAGES_TO_PROCESS = 20
MIN_TEXT_LENGTH = 50
MAX_FILE_SIZE_MB = 50


def validate_pdf_file(pdf_path: str) -> None:
    """Validate PDF file before processing."""
    path_obj = Path(pdf_path)
    
    if not path_obj.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    if not path_obj.is_file():
        raise ValueError(f"Path is not a file: {pdf_path}")
    
    if path_obj.suffix.lower() != '.pdf':
        raise ValueError(f"File is not a PDF: {pdf_path}")
    
    # Check file size (in bytes)
    file_size_mb = path_obj.stat().st_size / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(f"PDF file too large: {file_size_mb:.1f}MB (max: {MAX_FILE_SIZE_MB}MB)")


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text content from a PDF file with enhanced error handling.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text as a string
        
    Raises:
        FileNotFoundError: If PDF file doesn't exist
        ValueError: If file is invalid or text extraction fails
        Exception: For other PDF processing errors
    """
    validate_pdf_file(pdf_path)
    
    try:
        logger.info(f"Extracting text from PDF: {pdf_path}")
        text_content = []
        pages_processed = 0
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            # Limit to first N pages to improve performance
            max_pages = min(total_pages, MAX_PAGES_TO_PROCESS)
            logger.info(f"Processing {max_pages} pages (total: {total_pages})")
            
            for page_num in range(max_pages):
                try:
                    page = pdf.pages[page_num]
                    # Extract text from page
                    page_text = page.extract_text()
                    
                    if page_text and page_text.strip():
                        text_content.append(page_text.strip())
                        pages_processed += 1
                        logger.debug(f"Page {page_num + 1}: extracted {len(page_text)} characters")
                    else:
                        logger.debug(f"Page {page_num + 1}: no text extracted")
                        
                except Exception as e:
                    logger.warning(f"Error processing page {page_num + 1}: {str(e)}")
                    continue  # Skip problematic pages
        
        if not text_content:
            logger.error("No text extracted from any page")
            raise ValueError(
                "No text could be extracted from the PDF. "
                "This may be a scanned document or image-based PDF that requires OCR."
            )
        
        full_text = "\n\n".join(text_content)
        
        if len(full_text.strip()) < MIN_TEXT_LENGTH:
            logger.warning(f"Very little text extracted: {len(full_text)} characters")
            raise ValueError(
                f"Insufficient text extracted ({len(full_text)} characters). "
                "Document may be primarily images or poorly formatted."
            )
        
        logger.info(f"✓ Extraction complete: {len(full_text)} total characters from {pages_processed} pages")
        return full_text
        
    except Exception as e:
        if isinstance(e, (FileNotFoundError, ValueError)):
            raise  # Re-raise validation errors as-is
        
        logger.error(f"Unexpected error extracting text: {str(e)}")
        raise Exception(f"Failed to extract text from PDF: {str(e)}")