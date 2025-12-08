"""
Semantic Chunking Service for Phase 2

This service provides intelligent text chunking that:
- Respects document structure (paragraphs, sections, titles)
- Includes configurable overlap between chunks
- Detects and preserves semantic boundaries
- Generates content hashes for deduplication
"""

import hashlib
import re
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class SemanticChunker:
    """
    Intelligent chunking that respects document structure.
    """
    
    def __init__(
        self,
        max_chunk_size: int = 1000,
        overlap_size: int = 200,
        min_chunk_size: int = 100,
    ):
        """
        Initialize semantic chunker.
        
        Args:
            max_chunk_size: Maximum characters per chunk
            overlap_size: Number of characters to overlap between chunks
            min_chunk_size: Minimum chunk size (avoid tiny chunks)
        """
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        self.min_chunk_size = min_chunk_size
    
    def chunk_text(
        self,
        text: str,
        document_metadata: Dict[str, Any] = None,
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Chunk text semantically with overlap and metadata.
        
        Returns:
            List of (chunk_text, chunk_metadata) tuples
        """
        if not text or not text.strip():
            return []
        
        metadata = document_metadata or {}
        
        # 1. Detect document structure
        sections = self._detect_sections(text)
        
        # 2. Chunk each section with overlap
        all_chunks = []
        
        for section in sections:
            section_chunks = self._chunk_section(
                section["text"],
                section_title=section.get("title"),
            )
            
            for chunk_text in section_chunks:
                chunk_metadata = {
                    "section_title": section.get("title"),
                    "content_hash": self._generate_hash(chunk_text),
                    "char_count": len(chunk_text),
                    "word_count": len(chunk_text.split()),
                }
                all_chunks.append((chunk_text, chunk_metadata))
        
        logger.info(
            f"[SEMANTIC_CHUNKING] Generated {len(all_chunks)} chunks "
            f"from {len(sections)} sections"
        )
        
        return all_chunks
    
    def _detect_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect sections in the document based on structure.
        
        Heuristics:
        - Lines in ALL CAPS = titles
        - Lines ending with : = subtitles
        - Double newlines = paragraph breaks
        """
        lines = text.split("\n")
        sections = []
        current_section = {"title": None, "text": ""}
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                continue
            
            # Heuristic 1: ALL CAPS and short = title
            if (
                stripped.isupper()
                and len(stripped) < 100
                and len(stripped) > 3
            ):
                # Save previous section
                if current_section["text"].strip():
                    sections.append(current_section)
                
                # Start new section
                current_section = {
                    "title": stripped,
                    "text": "",
                }
                continue
            
            # Heuristic 2: Ends with : and short = subtitle
            if (
                stripped.endswith(":")
                and len(stripped) < 100
                and not current_section["title"]
            ):
                current_section["title"] = stripped[:-1]
                continue
            
            # Add line to current section
            current_section["text"] += line + "\n"
        
        # Add last section
        if current_section["text"].strip():
            sections.append(current_section)
        
        # If no sections detected, treat entire text as one section
        if not sections:
            sections = [{"title": None, "text": text}]
        
        return sections
    
    def _chunk_section(
        self,
        text: str,
        section_title: str = None,
    ) -> List[str]:
        """
        Chunk a section with overlap, respecting paragraph boundaries.
        """
        if not text.strip():
            return []
        
        # Split by paragraphs (double newline or single newline)
        paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        # Add section title to first chunk if present
        if section_title:
            current_chunk.append(f"## {section_title}\n")
            current_size = len(section_title) + 4
        
        for paragraph in paragraphs:
            para_size = len(paragraph)
            
            # If single paragraph is too large, split it
            if para_size > self.max_chunk_size:
                # Save current chunk if not empty
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                # Split large paragraph by sentences
                sentences = self._split_by_sentences(paragraph)
                for sentence in sentences:
                    if current_size + len(sentence) > self.max_chunk_size:
                        if current_chunk:
                            chunks.append("\n\n".join(current_chunk))
                        current_chunk = [sentence]
                        current_size = len(sentence)
                    else:
                        current_chunk.append(sentence)
                        current_size += len(sentence)
                continue
            
            # Check if adding this paragraph exceeds max size
            if current_size + para_size > self.max_chunk_size:
                # Save current chunk
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap(current_chunk)
                current_chunk = [overlap_text, paragraph] if overlap_text else [paragraph]
                current_size = len(overlap_text) + para_size if overlap_text else para_size
            else:
                # Add paragraph to current chunk
                current_chunk.append(paragraph)
                current_size += para_size
        
        # Add final chunk
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            # Only add if meets minimum size
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(chunk_text)
        
        return chunks
    
    def _split_by_sentences(self, text: str) -> List[str]:
        """Split text by sentences for large paragraphs."""
        # Simple sentence splitting by period, exclamation, question mark
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_overlap(self, current_chunk: List[str]) -> str:
        """
        Get overlap text from current chunk.
        Returns last N characters from current chunk.
        """
        if not current_chunk:
            return ""
        
        full_text = "\n\n".join(current_chunk)
        
        if len(full_text) <= self.overlap_size:
            return full_text
        
        # Get last overlap_size characters, but try to break at word boundary
        overlap_text = full_text[-self.overlap_size:]
        
        # Find first space to avoid cutting words
        first_space = overlap_text.find(" ")
        if first_space > 0:
            overlap_text = overlap_text[first_space:].strip()
        
        return overlap_text
    
    def _generate_hash(self, text: str) -> str:
        """Generate SHA256 hash of text for deduplication."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()


# Singleton instance
_chunker_instance = None


def get_semantic_chunker(
    max_chunk_size: int = 1000,
    overlap_size: int = 200,
) -> SemanticChunker:
    """Get or create semantic chunker instance."""
    global _chunker_instance
    if _chunker_instance is None:
        _chunker_instance = SemanticChunker(
            max_chunk_size=max_chunk_size,
            overlap_size=overlap_size,
        )
    return _chunker_instance
