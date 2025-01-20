from pdf_processor import PDFBot
import time

def print_separator():
    print("\n" + "="*50 + "\n")

def main():
    # Initialize the PDF-Bot
    print("Initializing PDF-Bot...")
    pdf_bot = PDFBot()
    
    # Specify the path to your PDF file
    pdf_path = "sample.pdf"  # Replace with your PDF file path
    
    try:
        # Load and process the PDF
        print(f"Loading PDF from: {pdf_path}")
        pdf_bot.load_pdf(pdf_path)
        print("PDF processed successfully!")
        print_separator()
        
        # Example 1: Chat with the PDF
        question = "What is the main topic of this document?"
        print(f"Question: {question}")
        response = pdf_bot.chat(question)
        print("Answer:", response["answer"])
        print("\nRelevant text chunks used:")
        for i, chunk in enumerate(response["source_chunks"], 1):
            print(f"\nChunk {i}:")
            print(chunk[:200] + "..." if len(chunk) > 200 else chunk)
        print_separator()
        
        # Example 2: Generate a summary
        print("Generating document summary...")
        summary = pdf_bot.summarize()
        print("Summary:", summary)
        print_separator()
        
        # Example 3: Extract key points
        print("Extracting key points...")
        key_points = pdf_bot.extract_key_points()
        print("Key Points:", key_points)
        
    except FileNotFoundError:
        print(f"Error: Could not find the PDF file at {pdf_path}")
        print("Please make sure to update the pdf_path variable with your PDF file location.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
