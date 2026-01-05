
# --- 4. ORCHESTRATOR (Parallel Processing) ---
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional, Callable
from src.extract import analyze_chunk_with_gemini
from src.pdf_split import split_pdf


def process_chunk(args):
    """
    Worker function to process a single chunk.
    
    Args:
        args: Tuple of (chunk_path, chunk_index)
    
    Returns:
        Tuple of (chunk_index, data, chunk_path)
    """
    chunk_path, chunk_index = args
    try:
        data = analyze_chunk_with_gemini(chunk_path, chunk_index)
        return (chunk_index, data, chunk_path)
    except Exception as e:
        print(f"[Chunk {chunk_index}] Error: {e}")
        return (chunk_index, {"transactions": []}, chunk_path)


def process_statement(
    pdf_path: str, 
    max_workers: int = 8, 
    pages_per_chunk: int = 2,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> Dict[str, Any]:
    """
    Process a bank statement PDF and extract transactions.
    
    This is the main function to be called from Streamlit or CLI.
    
    Args:
        pdf_path: Path to the PDF file
        max_workers: Maximum number of parallel workers
        pages_per_chunk: Number of pages per chunk
        progress_callback: Optional callback(current, total, message) for progress updates
    
    Returns:
        Dict with meta, summary, and transactions
    """
    start_time = time.time()
    
    def log(msg: str):
        print(msg)
    
    def update_progress(current: int, total: int, message: str):
        if progress_callback:
            progress_callback(current, total, message)
        log(message)
    
    update_progress(0, 100, f"📄 Processing: {pdf_path}")
    
    # Step 1: Split PDF into chunks
    update_progress(5, 100, "📑 Splitting PDF into chunks...")
    chunks = split_pdf(pdf_path, pages_per_chunk=pages_per_chunk)
    total_chunks = len(chunks)
    update_progress(10, 100, f"   Created {total_chunks} chunks")
    
    # Prepare chunk arguments (path, index)
    chunk_args = [(chunk, idx) for idx, chunk in enumerate(chunks)]
    
    all_results = []
    master_metadata = {}
    
    # Step 2: Process chunks in parallel
    update_progress(15, 100, "🚀 Processing chunks in parallel...")
    
    completed = 0
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_chunk = {
                executor.submit(process_chunk, args): args[1] 
                for args in chunk_args
            }
            
            for future in as_completed(future_to_chunk):
                chunk_idx = future_to_chunk[future]
                try:
                    result = future.result()
                    all_results.append(result)
                    completed += 1
                    progress = 15 + int((completed / total_chunks) * 70)
                    update_progress(progress, 100, f"   ✓ Chunk {completed}/{total_chunks} processed")
                except Exception as e:
                    print(f"[Chunk {chunk_idx}] Processing failed: {e}")
                    all_results.append((chunk_idx, {"transactions": []}, chunks[chunk_idx]))
                    completed += 1
    
    except KeyboardInterrupt:
        log("⚠️  Processing interrupted by user")
    
    # Step 3: Sort results by chunk index to maintain order
    all_results.sort(key=lambda x: x[0])
    
    # Step 4: Merge results
    update_progress(85, 100, "📊 Merging results...")
    all_transactions = []
    
    for chunk_idx, data, chunk_path in all_results:
        # Get metadata from first valid chunk
        if not master_metadata:
            holder = data.get("account_holder")
            period = data.get("statement_period")
            if holder and holder not in ["CONTINUED", None, ""]:
                master_metadata = {
                    "holder": holder,
                    "period": period
                }
        
        # Merge transactions
        transactions = data.get("transactions", [])
        all_transactions.extend(transactions)
        
        # Cleanup temp file
        try:
            os.remove(chunk_path)
        except:
            pass
    
    # Step 5: Deduplicate transactions
    update_progress(90, 100, "🔄 Deduplicating transactions...")
    seen = set()
    unique_transactions = []
    for txn in all_transactions:
        key = (
            txn.get("transaction_date"),
            txn.get("amount"),
            txn.get("description", "")[:50]
        )
        if key not in seen:
            seen.add(key)
            unique_transactions.append(txn)
    
    duplicates_removed = len(all_transactions) - len(unique_transactions)
    
    # Step 6: Sort transactions by date
    unique_transactions.sort(key=lambda x: x.get("transaction_date", ""))
    
    # Step 7: Calculate statistics
    update_progress(95, 100, "📈 Calculating statistics...")
    total_credit = sum(
        t.get("amount", 0) for t in unique_transactions 
        if t.get("direction") == "CREDIT"
    )
    total_debit = sum(
        t.get("amount", 0) for t in unique_transactions 
        if t.get("direction") == "DEBIT"
    )
    
    category_summary = {}
    for txn in unique_transactions:
        cat = txn.get("category", "UNCATEGORIZED")
        if cat not in category_summary:
            category_summary[cat] = {"count": 0, "total": 0.0}
        category_summary[cat]["count"] += 1
        category_summary[cat]["total"] += txn.get("amount", 0)
    
    # Step 8: Build final output
    elapsed_time = time.time() - start_time
    
    final_output = {
        "meta": {
            **master_metadata,
            "processing_time_seconds": round(elapsed_time, 2),
            "chunks_processed": len(chunks),
            "duplicates_removed": duplicates_removed
        },
        "summary": {
            "total_transactions": len(unique_transactions),
            "total_credit": round(total_credit, 2),
            "total_debit": round(total_debit, 2),
            "net_flow": round(total_credit - total_debit, 2),
            "category_breakdown": category_summary
        },
        "transactions": unique_transactions
    }
    
    update_progress(100, 100, f"✅ Done! Extracted {len(unique_transactions)} transactions in {elapsed_time:.1f}s")
    
    return final_output


# Legacy function for backward compatibility
def main(full_pdf_path: str, max_workers: int = 8, pages_per_chunk: int = 2):
    """
    Legacy main function. Use process_statement() instead.
    """
    result = process_statement(full_pdf_path, max_workers, pages_per_chunk)
    
    # Save output
    output_file = "output.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"✅ PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"   📁 Output saved to: {output_file}")
    print(f"   ⏱️  Total time: {result['meta']['processing_time_seconds']:.2f} seconds")
    print(f"   📊 Transactions extracted: {result['summary']['total_transactions']}")
    print(f"   💰 Total Credit: ₹{result['summary']['total_credit']:,.2f}")
    print(f"   💸 Total Debit: ₹{result['summary']['total_debit']:,.2f}")
    print(f"   📈 Net Flow: ₹{result['summary']['net_flow']:,.2f}")
    print(f"{'='*60}\n")
    
    return result


# Execute
if __name__ == "__main__":
    main(
        "DOC-20260102-WA0001..pdf",
        max_workers=4,
        pages_per_chunk=3
    )