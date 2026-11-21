"""Policy intelligence services — modular document processing pipeline.

Architecture:
  file_validator.py   → Validate uploads (type, size, magic bytes)
  text_extractor.py   → Extract text from PDF/DOCX/URL
  document_chunker.py → Split large documents into processable chunks
  gemini_extractor.py → Send text to Gemini, extract structured policy data
  output_validator.py → Validate and normalize Gemini output
  questionnaire.py    → Mode 3: build policy from 5-question answers
"""
