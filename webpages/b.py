from playwright.sync_api import sync_playwright
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os

# List of HTML files
html_files = ["Quick-Start.html", "Production-Install.html", "i2b2-Upgrade.html", "i2b2-Admin-Module.html"]
pdf_files = []
toc_entries = []  # Stores TOC titles and corresponding page numbers

def convert_html_to_pdf(html_file, pdf_file):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        # Open the local HTML file
        page.goto(f"file://{os.path.abspath(html_file)}", wait_until="networkidle")
        
        # Extract the H1 title for TOC
        title = page.evaluate("""() => {
            let h1 = document.querySelector('h1');
            return h1 ? h1.innerText : "Untitled Section";
        }""")
        
        # Apply CSS to adjust font size & margins
        page.evaluate("""() => {
            let style = document.createElement('style');
            style.innerHTML = `
                body {
                    font-size: 13px !important;
                    margin: 15px !important;
                    padding: 10px !important;
                }
                h1 { font-size: 20px !important; }
                h2 { font-size: 18px !important; }
                h3, p, li { font-size: 14px !important; }
                .sidebar, .header, .footer {
                    display: none !important;
                }
                .content {
                    margin: 0 auto !important;
                    width: 85% !important;
                }
            `;
            document.head.appendChild(style);
        }""")

        # Save the rendered page as PDF
        page.pdf(path=pdf_file, format="A4", margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"})
        
        browser.close()
    
    return title  # Return the extracted title

# Convert HTML files to PDF and collect TOC entries
for html in html_files:
    pdf = html.replace(".html", ".pdf")
    title = convert_html_to_pdf(html, pdf)
    pdf_files.append(pdf)
    toc_entries.append(title)

# Generate TOC Page with Main Title
toc_pdf = "TOC.pdf"
toc_writer = PdfWriter()

# Create a TOC page
toc_canvas = canvas.Canvas(toc_pdf, pagesize=A4)

# Add Main Title: "i2b2 Documentation"
toc_canvas.setFont("Helvetica-Bold", 22)  
toc_canvas.drawString(170, 800, "i2b2 Documentation")  

# Add TOC Header Below
toc_canvas.setFont("Helvetica-Bold", 16)
toc_canvas.drawString(200, 770, "Table of Contents")

# Add TOC Entries
toc_canvas.setFont("Helvetica", 12)
y_position = 740
current_page = 2  # TOC is on page 1, sections start from page 2
toc_links = []  # Store TOC links for bookmarks

for i, title in enumerate(toc_entries):
    toc_canvas.drawString(100, y_position, f"{i+1}. {title}  .......... {current_page}")  
    toc_links.append((title, current_page))  # Store TOC title & target page
    y_position -= 20
    with open(pdf_files[i], "rb") as f:
        pdf_reader = PdfReader(f)
        current_page += len(pdf_reader.pages)

toc_canvas.save()

# Merge PDFs with TOC and create clickable bookmarks
merged_pdf = "i2b2_documentation.pdf"
writer = PdfWriter()

# Append TOC first
with open(toc_pdf, "rb") as f:
    writer.append(PdfReader(f))

# Append section PDFs
page_number_map = {}  # Store correct page numbers for bookmarks
current_page = 1  # Start from page 1 (TOC)

for i, pdf in enumerate(pdf_files):
    with open(pdf, "rb") as f:
        pdf_reader = PdfReader(f)
        writer.append(pdf_reader)
        page_number_map[toc_entries[i]] = current_page  # Map TOC entry to correct page
        current_page += len(pdf_reader.pages)

# Add clickable bookmarks
for title, page_number in page_number_map.items():
    writer.add_outline_item(title, page_number, parent=None)

# Save the final PDF
with open(merged_pdf, "wb") as output_pdf:
    writer.write(output_pdf)

print(f"PDF generated: {merged_pdf}")