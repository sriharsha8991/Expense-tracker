
# --- 2. PDF SPLITTER (Optimized Batching Strategy) ---
import os
import tempfile

def split_pdf(input_path: str, pages_per_chunk: int = 5, output_dir: str = None) -> list[str]:
    """
    Splits a large PDF into smaller temporary chunks for parallel processing.
    
    Args:
        input_path: Path to the input PDF file
        pages_per_chunk: Number of pages per chunk (3-5 recommended for accuracy)
        output_dir: Directory for temp files (uses system temp if None)
    
    Returns:
        List of paths to chunk PDF files
    
    Notes:
        - Smaller chunks (3-5 pages) give better extraction accuracy
        - Larger chunks reduce API calls but may hit output token limits
        - Chunks are created in temp directory for easy cleanup
    """
    import fitz  # PyMuPDF
    
    # Use temp directory if not specified
    if output_dir is None:
        output_dir = tempfile.gettempdir()
    
    doc = fitz.open(input_path)
    chunk_paths = []
    total_pages = len(doc)
    
    print(f"   Total pages: {total_pages}")
    print(f"   Pages per chunk: {pages_per_chunk}")
    
    for i in range(0, total_pages, pages_per_chunk):
        chunk_doc = fitz.open()
        end_page = min(i + pages_per_chunk, total_pages)
        chunk_doc.insert_pdf(doc, from_page=i, to_page=end_page - 1)
        
        # Create unique chunk filename with timestamp
        chunk_name = os.path.join(
            output_dir, 
            f"chunk_{i:04d}_{end_page:04d}_{os.getpid()}.pdf"
        )
        chunk_doc.save(chunk_name)
        chunk_paths.append(chunk_name)
        chunk_doc.close()
    
    doc.close()
    return chunk_paths


def get_pdf_page_count(input_path: str) -> int:
    """Get the total number of pages in a PDF."""
    import fitz
    doc = fitz.open(input_path)
    count = len(doc)
    doc.close()
    return count


def estimate_processing_time(input_path: str, pages_per_chunk: int = 3, seconds_per_chunk: float = 5.0) -> float:
    """
    Estimate processing time based on page count.
    
    Args:
        input_path: Path to PDF
        pages_per_chunk: Chunk size
        seconds_per_chunk: Estimated seconds per chunk (API call time)
    
    Returns:
        Estimated processing time in seconds
    """
    total_pages = get_pdf_page_count(input_path)
    num_chunks = (total_pages + pages_per_chunk - 1) // pages_per_chunk
    return num_chunks * seconds_per_chunk
