import os
from typing import List, Dict
import PyPDF2
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Tuple

class PDFBot:
    def __init__(self):
        """Initialize the PDFBot with free models."""
        # Initialize sentence transformer for embeddings
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize T5 model for text generation
        model_name = "t5-base"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        
        # Store document chunks and their embeddings
        self.document_chunks = []
        self.document_embeddings = None
        self.chat_history = []

    def load_pdf(self, pdf_path: str) -> List[str]:
        """Load and process a PDF file."""
        text_chunks = []
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page in pdf_reader.pages:
                text = page.extract_text()
                # Split text into chunks of approximately 1000 characters
                chunks = [text[i:i+1000] for i in range(0, len(text), 800)]
                text_chunks.extend(chunks)
        
        self.document_chunks = text_chunks
        self.document_embeddings = self.embedding_model.encode(text_chunks)
        return text_chunks

    def _get_relevant_chunks(self, query: str, top_k: int = 3) -> List[str]:
        """Retrieve the most relevant chunks for a query using semantic search."""
        query_embedding = self.embedding_model.encode([query])[0]
        
        # Calculate similarities
        similarities = np.dot(self.document_embeddings, query_embedding)
        top_indices = np.argsort(similarities)[-top_k:]
        
        return [self.document_chunks[i] for i in reversed(top_indices)]

    def chat(self, query: str) -> Dict:
        """Chat with the PDF content using T5 model."""
        if not self.document_chunks:
            raise ValueError("Please process a PDF first using load_pdf()")
        
        # Get relevant chunks
        relevant_chunks = self._get_relevant_chunks(query)
        context = " ".join(relevant_chunks)
        
        # Prepare input for T5
        input_text = f"question: {query} context: {context}"
        
        # Generate response
        inputs = self.tokenizer(input_text, return_tensors="pt", max_length=512, truncation=True)
        outputs = self.model.generate(
            inputs.input_ids,
            max_length=150,
            min_length=40,
            num_beams=4,
            temperature=0.7
        )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Update chat history
        self.chat_history.append({"question": query, "answer": response})
        
        return {
            "answer": response,
            "source_chunks": relevant_chunks
        }

    def summarize(self) -> str:
        """Generate a summary of the PDF content."""
        if not self.document_chunks:
            raise ValueError("Please process a PDF first using load_pdf()")
        
        # Combine chunks and prepare for summarization
        text = " ".join(self.document_chunks)
        input_text = f"summarize: {text}"
        
        inputs = self.tokenizer(input_text, return_tensors="pt", max_length=512, truncation=True)
        outputs = self.model.generate(
            inputs.input_ids,
            max_length=150,
            min_length=40,
            num_beams=4,
            temperature=0.7
        )
        
        summary = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return summary

    def extract_key_points(self) -> List[str]:
        """Extract key points from the PDF content."""
        if not self.document_chunks:
            raise ValueError("Please process a PDF first using load_pdf()")
        
        # Combine chunks and prepare for key points extraction
        text = " ".join(self.document_chunks)
        input_text = f"extract key points: {text}"
        
        inputs = self.tokenizer(input_text, return_tensors="pt", max_length=512, truncation=True)
        outputs = self.model.generate(
            inputs.input_ids,
            max_length=200,
            min_length=50,
            num_beams=4,
            temperature=0.7
        )
        
        key_points = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        # Split into bullet points
        points = [point.strip() for point in key_points.split('.') if point.strip()]
        return points
