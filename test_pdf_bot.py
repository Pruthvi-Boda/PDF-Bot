from pdf_processor import PDFBot
import time

def print_separator():
    print("\n" + "="*50 + "\n")

def main():
    # Initialize the PDF-Bot
    print("Initializing PDF-Bot...")
    pdf_bot = PDFBot()
    
    # Load the sample PDF
    print("Loading sample.pdf...")
    pdf_bot.load_pdf("sample.pdf")
    print("PDF loaded successfully!")
    print_separator()
    
    # Test 1: Ask about the main topic
    question = "What are the main topics covered in this document?"
    print(f"Question: {question}")
    response = pdf_bot.chat(question)
    print("Answer:", response["answer"])
    print_separator()
    
    # Test 2: Ask about AI applications
    question = "What are some applications of computer vision mentioned in the document?"
    print(f"Question: {question}")
    response = pdf_bot.chat(question)
    print("Answer:", response["answer"])
    print_separator()
    
    # Test 3: Generate a summary
    print("Generating document summary...")
    summary = pdf_bot.summarize()
    print("Summary:", summary)
    print_separator()
    
    # Test 4: Extract key points
    print("Extracting key points...")
    key_points = pdf_bot.extract_key_points()
    print("Key Points:", key_points)

if __name__ == "__main__":
    main()
