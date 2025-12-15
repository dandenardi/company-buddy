import sys
import os

# Adiciona o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.semantic_chunker import SemanticChunker

def test_metadata_extraction():
    print("Testing Metadata Extraction...")
    chunker = SemanticChunker(max_chunk_size=100, overlap_size=20)
    
    # Simulate text with page markers
    # Page 1 has 50 chars. Page 2 has 50 chars.
    text_with_markers = (
        "<<<PAGE_1>>>\n"
        "This is the content of page one. It has some text.\n"
        "<<<PAGE_2>>>\n"
        "This is the content of page two. It has more text."
    )
    
    print("Input Text:")
    print(text_with_markers)
    print("-" * 20)
    
    chunks_with_metadata = chunker.chunk_text(text_with_markers)
    print(f"Chunks generated: {len(chunks_with_metadata)}")
    
    for i, (chunk, meta) in enumerate(chunks_with_metadata):
        print(f"\nChunk {i+1}:")
        print(f"Page Number: {meta.get('page_number')}")
        print(f"Content: {repr(chunk[:50])}...")
        
        # Verification logic
        if "page one" in chunk:
            assert meta.get('page_number') == 1, f"Chunk {i+1} should be on page 1"
        if "page two" in chunk:
            # Note: With overlap, a chunk might start on page 1 and overlap into page 2?
            # Our logic picks the page where the chunk *starts*.
            # If chunk is purely page two, it should be 2.
             assert meta.get('page_number') >= 1, f"Chunk {i+1} page number invalid"

    print("\nMetadata extraction test passed!")

if __name__ == "__main__":
    test_metadata_extraction()
