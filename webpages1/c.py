from playwright.sync_api import sync_playwright
from PyPDF2 import PdfReader, PdfMerger
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os

html_files = [
    "Quick-Start.html", 
    "Production-Install.html", 
    "i2b2-Upgrade.html", 
    "i2b2-Admin-Module.html"
]
pdf_files = []
toc_entries = []  # List of tuples: (H1, [H2, ...], [h2_pages])
section_starts = {}  # Maps H1 -> starting page number in merged PDF (zero-based)

def convert_html_to_pdf(html_file, pdf_file):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f"file://{os.path.abspath(html_file)}", wait_until="networkidle")
        
        h1 = page.evaluate("""() => {
            let el = document.querySelector('h1');
            return el ? el.innerText : "Untitled Section";
        }""")
        
        h2s = page.evaluate("""() => {
            const result = [];
            document.querySelectorAll('h2').forEach((el) => {
                result.push(el.innerText);
            });
            return result;
        }""")
        
        # Updated CSS with blue background for shell code
        page.evaluate("""() => {
    const style = document.createElement('style');
    style.innerHTML = `
        body { 
            font-size: 13px !important; 
            margin: 10px !important; 
            padding: 10px !important; 
        }
        h1 { font-size: 20px !important; }
        h2 { font-size: 18px !important; }
        h3, p, li { font-size: 14px !important; }
        .sidebar, .header, .footer { display: none !important; }
        .content { margin: 0 auto !important; width: 90% !important; }

        pre.codehilite {
            background: rgb(0, 0, 0) !important; /* Force black background */
            color: black !important;
            padding: 5px !important;
            border-radius: 4px !important;
            font-family: monospace !important;
            font-size: 13px !important;
            line-height: 1.4;
            border: 10px !important;
            margin: 2px 0 !important;
            display: block !important;
            white-space: pre-wrap;
            overflow-x: auto !important;
        }
    `;
    document.head.appendChild(style);
}""")

        page.pdf(path=pdf_file, format="A4", margin={
            "top": "10mm",
            "bottom": "10mm",
            "left": "10mm",
            "right": "10mm"
        })
        browser.close()
        return h1, h2s

# Rest of the script remains the same...
# [Keep all subsequent code identical to your original version]

# Convert HTML to PDF and collect H2 page numbers
for html in html_files:
    pdf = html.replace(".html", ".pdf")
    h1, h2s = convert_html_to_pdf(html, pdf)
    
    # Find H2 pages in the generated PDF
    h2_pages = []
    with open(pdf, "rb") as f:
        reader = PdfReader(f)
        for h2_text in h2s:
            h2_clean = ' '.join(h2_text.split()).strip().lower()
            found_page = None
            for page_num, page in enumerate(reader.pages):
                text = ' '.join(page.extract_text().split()).strip().lower()
                if h2_clean in text:
                    found_page = page_num
                    break
            h2_pages.append(found_page if found_page is not None else 0)
    
    toc_entries.append((h1, h2s, h2_pages))
    pdf_files.append(pdf)

# Create TOC Page
toc_pdf = "TOC.pdf"
c = canvas.Canvas(toc_pdf, pagesize=A4)
c.setFont("Helvetica-Bold", 22)
c.drawString(170, 800, "i2b2 Documentation")
c.setFont("Helvetica-Bold", 16)
c.drawString(200, 770, "Table of Contents")
c.setFont("Helvetica", 12)

# Calculate section starts (zero-based, after TOC page)
offset = 1  # TOC is page 0, first section starts at page 1
for i, pdf in enumerate(pdf_files):
    with open(pdf, "rb") as f:
        reader = PdfReader(f)
        section_starts[toc_entries[i][0]] = offset
        offset += len(reader.pages)

# Write TOC entries (using 1-based page numbers for display)
y = 740
for i, (h1, h2s, _) in enumerate(toc_entries):
    display_page = section_starts[h1] + 1  # Convert to 1-based
    c.drawString(100, y, f"{i+1}. {h1} .......... {display_page}")
    y -= 20
    for h2 in h2s:
        c.drawString(120, y, f"  - {h2}")
        y -= 15
c.save()

# Merge PDFs
merger = PdfMerger()
merger.append(toc_pdf)
for pdf in pdf_files:
    merger.append(pdf)

# Add bookmarks with correct page numbers
for i, (h1, h2s, h2_pages) in enumerate(toc_entries):
    section_start = section_starts[h1]
    parent = merger.add_outline_item(h1, section_start)
    for h2, h2_page in zip(h2s, h2_pages):
        merged_page = section_start + h2_page
        merger.add_outline_item(h2, merged_page, parent)

output_pdf = "i2b2_documentation.pdf"
merger.write(output_pdf)
merger.close()

print("✅ PDF generated:", output_pdf, "with accurate H2 bookmarks")