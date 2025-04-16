from playwright.sync_api import sync_playwright
import fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PyPDF2 import PdfReader, PdfWriter
import os

html_files = [
    "Quick-Start.html",
    "Production-Install.html",
    "i2b2-Upgrade.html",
    "i2b2-Admin-Module.html"
]

pdf_files = []
toc_entries = []  # (H1, [H2])
h2_locations = []  # [(h2_text, page_offset + page_index)]
page_lengths = []

def convert_html_to_pdf(html_file, pdf_file):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f"file://{os.path.abspath(html_file)}", wait_until="networkidle")

            # Inject styling
            page.evaluate("""() => {
                const style = document.createElement("style");
                style.innerHTML = `
                    body { font-size: 13px; margin: 15px; padding: 10px; }
                    h1 { font-size: 20px; }
                    h2 { font-size: 18px; }
                    h3, p, li { font-size: 14px; }
                    .sidebar, .header, .footer { display: none !important; }
                    .content { margin: 0 auto; width: 90%; }
                `;
                document.head.appendChild(style);
            }""")

            page.pdf(path=pdf_file, format="A4", margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"})
            h1 = page.evaluate("() => document.querySelector('h1')?.innerText || 'Untitled Section'")
            h2s = page.evaluate("() => Array.from(document.querySelectorAll('h2')).map(h => h.innerText)")
            browser.close()

        return h1.strip(), [h.strip() for h in h2s]
    except Exception as e:
        print(f"Error converting {html_file} to PDF: {e}")
        return "Error", []

# Step 1: Convert all HTML to PDFs
for html in html_files:
    pdf = html.replace(".html", ".pdf")
    h1, h2s = convert_html_to_pdf(html, pdf)
    if h1 != "Error":
        toc_entries.append((h1, h2s))
        pdf_files.append(pdf)

# Step 2: Detect exact H2 locations (improved with text dump)
page_offset = 1  # Page 1 will be TOC
for pdf_file, (h1, h2s) in zip(pdf_files, toc_entries):
    doc = fitz.open(pdf_file)
    found = []
    for page_index, page in enumerate(doc):
        text_dump = page.get_text("text")  # Extract entire page text
        for h2_text in h2s:
            if text_dump.find(h2_text) != -1:  # Search in text dump
                found.append((h2_text, page_offset + page_index))
                break  # Prevent duplicate h2 entries from the same page
            else:
                print(f"Warning: H2 '{h2_text}' not found in {pdf_file}, page {page_index + 1}")
    h2_locations.append(found)
    page_lengths.append(len(doc))
    page_offset += len(doc)

# Step 3: Create TOC Page
toc_pdf = "TOC.pdf"
c = canvas.Canvas(toc_pdf, pagesize=A4)
c.setFont("Helvetica-Bold", 22)
c.drawString(170, 800, "i2b2 Documentation")

c.setFont("Helvetica-Bold", 16)
c.drawString(200, 770, "Table of Contents")

c.setFont("Helvetica", 12)
y = 740
current_page = 2
toc_map = []
for idx, (h1, h2s) in enumerate(toc_entries):
    c.drawString(80, y, f"{idx+1}. {h1} .......... {current_page}")
    toc_map.append((h1, current_page))
    y -= 20
    for h2, h2_page in h2_locations[idx]:
        c.drawString(100, y, f"-- {h2} .......... {h2_page}")
        y -= 18
    if idx < len(page_lengths):
      current_page += page_lengths[idx]
c.save()

# Step 4: Merge PDFs
writer = PdfWriter()

# Add TOC
with open(toc_pdf, "rb") as f:
    writer.append(PdfReader(f))

# Add all PDFs
for pdf_file in pdf_files:
    with open(pdf_file, "rb") as f:
        writer.append(PdfReader(f))

# Step 5: Add Bookmarks
page_offset = 1
for idx, (h1, h2s) in enumerate(toc_entries):
    h1_page = 1 + page_offset - page_lengths[idx] if idx > 0 else 1
    parent = writer.add_outline_item(h1, h1_page)
    for h2, h2_page in h2_locations[idx]:
        writer.add_outline_item(h2, h2_page + 1, parent=parent)
    page_offset += page_lengths[idx]

# Step 6: Save
with open("i2b2_documentation.pdf", "wb") as f:
    writer.write(f)

print("✅ Final PDF: i2b2_documentation.pdf")