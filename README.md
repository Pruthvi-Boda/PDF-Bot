# PDF-Bot

PDF-Bot is an intelligent document analysis tool that helps you interact with PDF documents using natural language. It can analyze PDFs, generate summaries, extract key points, and engage in conversations about the document content.

## Features

- PDF document processing and analysis
- Interactive chat with PDF content
- Document summarization
- Key points extraction
- Powered by free and open-source models:
  - T5 for text generation and summarization
  - Sentence Transformers for semantic search
  - No API keys required!

## Installation

1. Clone this repository
2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

```python
from pdf_processor import PDFBot

# Initialize the bot (no API key needed!)
pdf_bot = PDFBot()

# Load and process a PDF file
pdf_bot.load_pdf("path/to/your/document.pdf")

# Chat with the PDF content
response = pdf_bot.chat("What is this document about?")
print(response["answer"])

# Generate a summary
summary = pdf_bot.summarize()
print(summary)

# Extract key points
key_points = pdf_bot.extract_key_points()
print(key_points)
```

## How it Works

1. **Document Processing**: The PDF is loaded and split into manageable chunks
2. **Semantic Search**: Uses Sentence Transformers to find relevant parts of the document
3. **Text Generation**: Uses T5 model for generating responses, summaries, and key points
4. **No External APIs**: Everything runs locally on your machine!

## Requirements

- Python 3.7+
- PyTorch
- Transformers
- Sentence Transformers
- Dependencies listed in requirements.txt
