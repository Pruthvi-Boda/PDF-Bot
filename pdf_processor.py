import PyPDF2
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai
import os
import hashlib
import pickle
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
import time
from pdf2image import convert_from_path
import pytesseract
import tempfile
from PIL import Image
import re

class PDFBot:
    def __init__(self, api_key):
        """Initialize PDFBot with Google API key."""
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        print("Initialized PDFBot with Gemini model")

    def extract_text_with_ocr(self, pdf_path: str) -> str:
        """Extract text from PDF using OCR if needed"""
        try:
            # First try normal text extraction
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                
                # If we got meaningful text, return it
                if len(text.strip()) > 100:
                    print("Successfully extracted text without OCR")
                    return text

            # If normal extraction didn't yield good results, try OCR
            print("Normal text extraction failed, attempting OCR...")
            
            # Convert PDF to images
            images = convert_from_path(
                pdf_path,
                poppler_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "poppler", "Library", "bin"),
                dpi=300  # Higher DPI for better quality
            )
            
            if not images:
                raise ValueError("Failed to convert PDF to images")
            
            # Process each page with OCR
            texts = []
            for i, image in enumerate(images):
                print(f"Processing page {i+1} with OCR...")
                # Improve image quality for better OCR results
                image = image.convert('L')  # Convert to grayscale
                text = pytesseract.image_to_string(image)
                texts.append(text)
            
            final_text = "\n\n".join(texts)
            if not final_text.strip():
                raise ValueError("OCR failed to extract any text")
                
            print("Successfully extracted text using OCR")
            return final_text
            
        except Exception as e:
            print(f"Error in OCR text extraction: {str(e)}")
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")

    def process_page(self, page) -> str:
        """Process a single page"""
        try:
            return page.extract_text() or ""
        except Exception:
            return ""

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file using parallel processing and OCR if needed"""
        try:
            # First try normal text extraction
            text = ""
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                if len(reader.pages) == 0:
                    raise ValueError("PDF file is empty")
                
                # Use ThreadPoolExecutor for parallel processing
                with ThreadPoolExecutor() as executor:
                    texts = list(executor.map(self.process_page, reader.pages))
                
                # Filter out empty strings and join
                text = " ".join(filter(None, texts)).strip()

            # If normal extraction didn't yield good results, try OCR
            if not text or len(text) < 100:
                print("Normal text extraction yielded insufficient results, attempting OCR...")
                text = self.extract_text_with_ocr(pdf_path)

            if not text:
                raise ValueError("No text could be extracted from the PDF")
            return text
            
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
            raise

    def get_cache_path(self, pdf_path: str) -> str:
        """Get cache file path for a PDF"""
        pdf_hash = hashlib.md5(open(pdf_path, 'rb').read()).hexdigest()
        return os.path.join("cache", f"{pdf_hash}.pkl")
            
    def process_pdf(self, pdf_path: str):
        """Process PDF and create vector store"""
        try:
            # Validate file exists
            if not os.path.exists(pdf_path):
                raise ValueError(f"PDF file not found: {pdf_path}")

            # Check file size
            file_size = os.path.getsize(pdf_path)
            if file_size == 0:
                raise ValueError("PDF file is empty")
            print(f"Processing PDF of size: {file_size} bytes")

            # Check if cached version exists
            cache_path = self.get_cache_path(pdf_path)
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, 'rb') as f:
                        self.vector_store = pickle.load(f)
                    print("Successfully loaded from cache")
                    return
                except Exception as e:
                    print(f"Failed to load from cache: {str(e)}")
                    # Continue with normal processing if cache load fails

            # Extract text from PDF
            try:
                text = self.extract_text_from_pdf(pdf_path)
                if not text:
                    raise ValueError("No text could be extracted from the PDF")
                print(f"Successfully extracted {len(text)} characters from PDF")
            except Exception as e:
                print(f"Error extracting text: {str(e)}")
                raise ValueError(f"Failed to extract text from PDF: {str(e)}")

            # Split text into smaller chunks
            try:
                chunk_size = 500
                overlap = 50
                texts = []
                
                # Create chunks with overlap
                for i in range(0, len(text), chunk_size - overlap):
                    chunk = text[i:i + chunk_size].strip()
                    if len(chunk) >= 100:  # Only keep chunks with substantial content
                        texts.append(chunk)

                if not texts:
                    raise ValueError("No valid text chunks could be created")
                print(f"Created {len(texts)} text chunks")
            except Exception as e:
                print(f"Error creating text chunks: {str(e)}")
                raise ValueError(f"Failed to process text chunks: {str(e)}")

            # Create embeddings in smaller batches
            try:
                batch_size = 5  # Reduced batch size
                self.vector_store = None

                for i in range(0, len(texts), batch_size):
                    print(f"Processing batch {i//batch_size + 1} of {(len(texts) + batch_size - 1)//batch_size}")
                    batch_texts = texts[i:i + batch_size]
                    batch_metadatas = [{"source": f"chunk_{j}"} for j in range(i, i + len(batch_texts))]
                    
                    try:
                        # Create vector store for this batch
                        batch_vectorstore = FAISS.from_texts(
                            batch_texts,
                            GoogleGenerativeAIEmbeddings(
                                google_api_key=api_key,
                                model="models/embedding-001"
                            ),
                            metadatas=batch_metadatas
                        )
                        
                        if not self.vector_store:
                            self.vector_store = batch_vectorstore
                        else:
                            self.vector_store.merge_from(batch_vectorstore)
                    except Exception as e:
                        print(f"Error processing batch {i//batch_size + 1}: {str(e)}")
                        raise

                if not self.vector_store:
                    raise ValueError("Failed to create vector store")
                print("Successfully created vector store")

                # Cache the vector store
                try:
                    with open(cache_path, 'wb') as f:
                        pickle.dump(self.vector_store, f)
                    print("Successfully cached vector store")
                except Exception as e:
                    print(f"Warning: Failed to cache vector store: {str(e)}")
                    # Continue even if caching fails

            except Exception as e:
                print(f"Error creating vector store: {str(e)}")
                raise ValueError(f"Failed to process PDF content: {str(e)}")

        except Exception as e:
            print(f"Error in process_pdf: {str(e)}")
            raise ValueError(str(e))

    def get_response(self, prompt):
        """Get a response from the LLM."""
        try:
            # Add better error handling and retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    print(f"Sending prompt to LLM (attempt {attempt + 1}/{max_retries})")
                    response = self.model.generate_content(prompt)
                    if response:
                        return response.text
                    print(f"Empty response received on attempt {attempt + 1}")
                except Exception as e:
                    print(f"Error on attempt {attempt + 1}: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(1)  # Wait before retrying
                    else:
                        raise
            
            return None
        except Exception as e:
            print(f"Error in get_response: {str(e)}")
            return None

    def get_key_insights(self, filepath):
        """Extract key insights from the PDF document."""
        try:
            text = self.extract_text_from_pdf(filepath)
            prompt = """Analyze this document and provide key insights in the following format. Use the exact formatting shown:

            # Highlights

            • 💻 **Tech Background**: [Describe technical expertise and focus areas]

            • 🎓 **Educational Profile**: [Describe educational background and qualifications]

            • 📚 **Research Experience**: [Describe any research or publication experience]

            • 🛠️ **Project Work**: [Describe significant projects and their impact]

            • 💡 **Core Skills**: [List primary technical and professional skills]

            • 🤝 **Professional Qualities**: [Describe soft skills and professional attributes]

            • 📊 **Domain Knowledge**: [List specialized knowledge areas and expertise]

            Format each point with:
            1. An emoji
            2. A bold header followed by a colon
            3. A clear, concise description
            4. Proper spacing between points

            Make each point informative and specific to the document content.
            Use professional language and maintain consistency in formatting.

            Document text:
            {text}
            """
            
            response = self.model.generate_content(prompt.format(text=text))
            if not response:
                print("No response received from get_key_insights")
                return None
                
            # Format the response
            formatted_response = response.text
            # Ensure proper spacing after bullet points
            formatted_response = formatted_response.replace('• ', '\n• ')
            # Add spacing between sections
            formatted_response = formatted_response.replace('# ', '\n# ')
            # Clean up any multiple newlines
            formatted_response = '\n'.join(line for line in formatted_response.splitlines() if line.strip())
            # Ensure consistent emoji spacing
            formatted_response = re.sub(r'([•] )([🛠️💻🎓📚💡🤝📊])', r'\1 \2', formatted_response)
            
            return formatted_response
            
        except Exception as e:
            print(f"Error getting key insights: {str(e)}")
            return None

    def get_summary(self, filepath):
        """Generate a concise summary of the PDF document."""
        try:
            text = self.extract_text_from_pdf(filepath)
            prompt = """Please provide a comprehensive summary of this document in the following format:

            **Executive Summary:**
            [A brief 2-3 sentence overview of the entire document]

            **Key Points:**
            • [First main point]
            • [Second main point]
            • [Continue with main points]

            **Important Details:**
            • [Detail 1]
            • [Detail 2]
            • [Continue with important details]

            **Conclusion:**
            [A brief conclusion summarizing the main takeaways]

            Make sure to format the response clearly with sections and bullet points.
            Be concise but informative in your summary.

            Document text:
            {text}
            """
            
            response = self.model.generate_content(prompt.format(text=text))
            if not response:
                print("No response received from get_summary")
                return None
                
            formatted_response = response.text.replace('•', '•').replace('*', '**')
            return formatted_response
            
        except Exception as e:
            print(f"Error generating summary: {str(e)}")
            return None

    def chat(self, filepath, message):
        """Chat about the PDF document."""
        try:
            text = self.extract_text_from_pdf(filepath)
            
            # Different prompts based on question type
            if any(keyword in message.lower() for keyword in ['summarize', 'summary', 'overview']):
                prompt = """Provide a well-formatted summary in the following structure:

                # Summary

                📝 **Overview**:
                [Provide a brief 2-3 sentence overview]

                🎯 **Key Points**:
                • [First main point]
                • [Second main point]
                • [Additional main points]

                💡 **Important Details**:
                • [Detail 1]
                • [Detail 2]
                • [Additional details]

                📊 **Conclusion**:
                [Brief conclusion with main takeaways]

                Question: {question}
                Document text: {text}
                """
            else:
                prompt = """Provide a well-formatted response in the following structure:

                # Response

                📌 **Answer**:
                [Direct answer to the question]

                🔍 **Supporting Details**:
                • [First supporting point]
                • [Second supporting point]
                • [Additional relevant points]

                📚 **Context**:
                [Relevant context from the document]

                💭 **Additional Notes**:
                • [Any additional relevant information]
                • [Related points or considerations]

                Make the response clear, specific, and well-organized.
                Use bullet points for lists and proper formatting.

                Question: {question}
                Document text: {text}
                """
            
            response = self.model.generate_content(prompt.format(question=message, text=text))
            if not response:
                print("No response received from chat")
                return None
                
            # Format the response
            formatted_response = response.text
            # Ensure proper spacing after bullet points
            formatted_response = formatted_response.replace('• ', '\n• ')
            # Add spacing between sections
            formatted_response = formatted_response.replace('# ', '\n# ')
            formatted_response = formatted_response.replace('**', '\n**')
            # Clean up any multiple newlines
            formatted_response = '\n'.join(line for line in formatted_response.splitlines() if line.strip())
            # Ensure consistent emoji spacing
            formatted_response = re.sub(r'([•] )([📌🔍📚💭📝🎯💡📊])', r'\1 \2', formatted_response)
            
            return formatted_response
            
        except Exception as e:
            print(f"Error in chat: {str(e)}")
            return None
