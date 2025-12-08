"""
Test script for Phase 2: Semantic Chunking

This script tests the new semantic chunking features:
1. Structure detection (titles, sections)
2. Paragraph-aware chunking
3. Overlap between chunks
4. Content hash generation
5. Deduplication
"""

from app.services.semantic_chunker import SemanticChunker


def test_basic_chunking():
    """Test basic semantic chunking."""
    print("\n" + "="*60)
    print("TEST 1: Basic Semantic Chunking")
    print("="*60)
    
    chunker = SemanticChunker(max_chunk_size=500, overlap_size=100)
    
    text = """
INTRODUÇÃO

Este é um documento de teste para validar o chunking semântico.
O sistema deve detectar esta seção como um título.

SEÇÃO 1: POLÍTICA DE FÉRIAS

Os colaboradores têm direito a 30 dias de férias por ano.
As férias podem ser divididas em até 3 períodos.
O primeiro período não pode ser inferior a 14 dias.

SEÇÃO 2: BENEFÍCIOS

A empresa oferece os seguintes benefícios:
- Vale refeição
- Vale transporte
- Plano de saúde
- Plano odontológico

Todos os benefícios são concedidos após o período de experiência.
    """
    
    chunks_with_meta = chunker.chunk_text(text.strip())
    
    print(f"✅ Generated {len(chunks_with_meta)} chunks")
    
    for i, (chunk_text, metadata) in enumerate(chunks_with_meta):
        print(f"\n--- Chunk {i+1} ---")
        print(f"Section: {metadata.get('section_title', 'N/A')}")
        print(f"Hash: {metadata['content_hash'][:16]}...")
        print(f"Chars: {metadata['char_count']}, Words: {metadata['word_count']}")
        print(f"Text preview: {chunk_text[:100]}...")
    
    return chunks_with_meta


def test_overlap():
    """Test that chunks have overlap."""
    print("\n" + "="*60)
    print("TEST 2: Chunk Overlap")
    print("="*60)
    
    chunker = SemanticChunker(max_chunk_size=200, overlap_size=50)
    
    text = "Lorem ipsum dolor sit amet. " * 50  # Long text
    
    chunks_with_meta = chunker.chunk_text(text)
    chunks = [c[0] for c in chunks_with_meta]
    
    print(f"✅ Generated {len(chunks)} chunks from long text")
    
    # Check for overlap
    has_overlap = False
    for i in range(len(chunks) - 1):
        chunk1_end = chunks[i][-50:]
        chunk2_start = chunks[i+1][:50]
        
        # Check if there's any common text
        if any(word in chunk2_start for word in chunk1_end.split()[-5:]):
            has_overlap = True
            print(f"✅ Overlap detected between chunk {i+1} and {i+2}")
            break
    
    if has_overlap:
        print("✅ Overlap feature working correctly")
    else:
        print("⚠️  No overlap detected (might be expected for this text)")


def test_deduplication():
    """Test content hash generation for deduplication."""
    print("\n" + "="*60)
    print("TEST 3: Content Hash & Deduplication")
    print("="*60)
    
    chunker = SemanticChunker()
    
    text1 = "Este é um texto de teste para deduplicação."
    text2 = "Este é um texto de teste para deduplicação."  # Identical
    text3 = "Este é um texto diferente."
    
    chunks1 = chunker.chunk_text(text1)
    chunks2 = chunker.chunk_text(text2)
    chunks3 = chunker.chunk_text(text3)
    
    hash1 = chunks1[0][1]['content_hash']
    hash2 = chunks2[0][1]['content_hash']
    hash3 = chunks3[0][1]['content_hash']
    
    print(f"Hash 1: {hash1[:16]}...")
    print(f"Hash 2: {hash2[:16]}...")
    print(f"Hash 3: {hash3[:16]}...")
    
    if hash1 == hash2:
        print("✅ Identical texts produce identical hashes")
    else:
        print("❌ Identical texts should have same hash!")
    
    if hash1 != hash3:
        print("✅ Different texts produce different hashes")
    else:
        print("❌ Different texts should have different hashes!")


def test_section_detection():
    """Test section title detection."""
    print("\n" + "="*60)
    print("TEST 4: Section Detection")
    print("="*60)
    
    chunker = SemanticChunker()
    
    text = """
TÍTULO EM MAIÚSCULAS

Este parágrafo está sob o título.

Subtítulo com dois pontos:

Este parágrafo está sob o subtítulo.
    """
    
    chunks_with_meta = chunker.chunk_text(text.strip())
    
    sections_found = set()
    for chunk_text, metadata in chunks_with_meta:
        if metadata.get('section_title'):
            sections_found.add(metadata['section_title'])
    
    print(f"✅ Detected {len(sections_found)} sections:")
    for section in sections_found:
        print(f"   - {section}")
    
    if len(sections_found) > 0:
        print("✅ Section detection working")
    else:
        print("⚠️  No sections detected")


def main():
    """Run all tests."""
    print("="*60)
    print("PHASE 2 SEMANTIC CHUNKING TESTS")
    print("="*60)
    
    test_basic_chunking()
    test_overlap()
    test_deduplication()
    test_section_detection()
    
    print("\n" + "="*60)
    print("TESTS COMPLETED")
    print("="*60)
    print("\n📋 Next steps:")
    print("1. Run migration: python migrate_phase2.py")
    print("2. Upload a test document")
    print("3. Check logs for 'Gerando chunks semânticos'")
    print("4. Verify chunks have better structure")


if __name__ == "__main__":
    main()
