from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os

def text_to_pdf(text_path, pdf_path):
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    y = height - 40

    with open(text_path, "r") as file:
        for line in file:
            c.drawString(40, y, line.strip())
            y -= 15
            if y < 40:
                c.showPage()
                y = height - 40

    c.save()

if __name__ == "__main__":
    os.makedirs("data/pdfs", exist_ok=True)

    text_files = [
        "data/sample_reports/report_2023.txt",
        "data/sample_reports/report_2024.txt",
        "data/sample_reports/lipid_2024.txt",
        "data/sample_reports/lipid_2023.txt",
        "data/sample_reports/glucose_2024.txt",
        "data/sample_reports/cbc_2024.txt"
    ]

    for txt in text_files:
        pdf_name = os.path.basename(txt).replace(".txt", ".pdf")
        text_to_pdf(txt, f"data/pdfs/{pdf_name}")
