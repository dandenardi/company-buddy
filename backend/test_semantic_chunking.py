import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Adiciona o diretório raiz ao path para encontrar o módulo 'app'
# Assumindo que o script está em backend/
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.semantic_chunker import SemanticChunker

def test_chunking():
    print("Testing Semantic Chunking...")
    # Use small min_chunk_size for small test data
    chunker = SemanticChunker(max_chunk_size=100, overlap_size=20, min_chunk_size=10)
    
    # Test case 1: Structure detection
    text = """TITLE
    
    This is a paragraph.
    
    SUBTITLE:
    This is another paragraph under subtitle.
    """
    
    # Debug: check sections
    sections = chunker._detect_sections(text)
    print(f"DEBUG: Detected sections: {len(sections)}")
    for s in sections:
        print(f"Title: {s['title']}")
        print(f"Text length: {len(s['text'])}")
        print(f"Text preview: {repr(s['text'][:50])}")
    
    chunks_with_metadata = chunker.chunk_text(text)
    print(f"Chunks generated: {len(chunks_with_metadata)}")
    
    for i, (chunk, meta) in enumerate(chunks_with_metadata):
        print(f"\nChunk {i+1}:")
        print(f"Metadata: {meta}")
        print("-" * 20)
        print(chunk)
        print("-" * 20)

    # Simple assertions (manual check via output for now, or basic checks)
    assert len(chunks_with_metadata) > 0, "Should generate chunks"
    
    # Test case 2: Overlap
    print("\nTesting Overlap...")
    # "This is sentence X. " is ~20 chars.
    # 10 sentences = ~200 chars. Max chunk=100.
    long_text = "This is sentence one. " * 10
    chunks = chunker.chunk_text(long_text)
    print(f"Long text chunks: {len(chunks)}")
    for i, (chunk, meta) in enumerate(chunks):
        print(f"Chunk {i} length: {len(chunk)}")
        print(f"Chunk {i} start: {chunk[:20]}...")
        print(f"Chunk {i} end: ...{chunk[-20:]}")

    if len(chunks) > 1:
        print("Overlap test passed (implicitly if chunks > 1 for long text)")
    else:
        print("Overlap test might have failed or text too short")

if __name__ == "__main__":
    test_chunking()
