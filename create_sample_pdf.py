from fpdf import FPDF
import textwrap
import random

def create_sample_pdf():
    # Initialize PDF object
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Create multiple chapters with repeated content for larger file size
    chapters = ["Introduction", "Basic Concepts", "Advanced Topics", "Case Studies", 
                "Research Papers", "Industry Applications", "Future Trends"]
    
    for chapter_num, chapter in enumerate(chapters, 1):
        pdf.add_page()
        
        # Add chapter title
        pdf.set_font("Arial", "B", 24)
        pdf.cell(0, 10, f"Chapter {chapter_num}: {chapter}", ln=True, align="C")
        pdf.ln(10)
        
        # Add multiple sections per chapter
        for section_num in range(1, 6):
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, f"Section {section_num}: Advanced AI Topics", ln=True)
            pdf.ln(5)
            
            # Add paragraphs of content
            pdf.set_font("Arial", size=12)
            for _ in range(10):  # Multiple paragraphs per section
                # Generate a paragraph with technical content
                paragraph = generate_technical_paragraph()
                wrapped_text = textwrap.fill(paragraph, width=85)
                for line in wrapped_text.split('\n'):
                    pdf.multi_cell(0, 10, line)
                pdf.ln(5)
            
            # Add some statistics or data
            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "Key Statistics:", ln=True)
            pdf.set_font("Arial", size=12)
            for _ in range(5):
                stat = generate_statistic()
                pdf.cell(0, 10, f"- {stat}", ln=True)
            pdf.ln(10)

    # Save the PDF
    pdf.output("sample.pdf")

def generate_technical_paragraph():
    topics = [
        "artificial intelligence", "machine learning", "deep learning", "neural networks",
        "computer vision", "natural language processing", "reinforcement learning",
        "data science", "big data", "cloud computing", "edge computing", "IoT"
    ]
    
    verbs = [
        "revolutionizes", "transforms", "enhances", "optimizes", "accelerates",
        "improves", "modernizes", "streamlines", "augments", "facilitates"
    ]
    
    domains = [
        "healthcare", "finance", "manufacturing", "retail", "education",
        "transportation", "agriculture", "energy", "telecommunications", "security"
    ]
    
    benefits = [
        "increased efficiency", "cost reduction", "improved accuracy",
        "better decision-making", "enhanced productivity", "risk mitigation",
        "resource optimization", "competitive advantage", "scalability", "sustainability"
    ]
    
    # Generate a technical paragraph
    paragraph = f"""
    Recent advances in {random.choice(topics)} {random.choice(verbs)} the way organizations approach 
    {random.choice(domains)}. By leveraging sophisticated algorithms and state-of-the-art technology, 
    companies can achieve {random.choice(benefits)} and {random.choice(benefits)}. The integration of 
    {random.choice(topics)} with {random.choice(topics)} creates powerful synergies that enable 
    {random.choice(benefits)}. This technological convergence has led to unprecedented opportunities in 
    {random.choice(domains)}, where {random.choice(topics)} plays a crucial role in driving innovation 
    and {random.choice(benefits)}. Furthermore, the combination of {random.choice(topics)} and 
    {random.choice(topics)} has shown remarkable results in {random.choice(domains)}, particularly in 
    applications focused on {random.choice(benefits)}. As organizations continue to invest in these 
    technologies, we expect to see even more dramatic improvements in {random.choice(benefits)} and 
    {random.choice(benefits)}.
    """
    return paragraph.strip()

def generate_statistic():
    metrics = [
        "accuracy improvement", "cost reduction", "productivity increase",
        "efficiency gain", "error rate reduction", "processing speed improvement",
        "customer satisfaction increase", "revenue growth", "time savings",
        "resource optimization"
    ]
    
    percentages = [random.randint(20, 95) for _ in range(10)]
    years = [2023 + i for i in range(5)]
    
    return f"{random.choice(metrics)}: {random.choice(percentages)}% ({random.choice(years)} projection)"

if __name__ == "__main__":
    create_sample_pdf()
