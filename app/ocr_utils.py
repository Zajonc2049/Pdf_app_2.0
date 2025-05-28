import pytesseract
from PIL import Image
from fpdf import FPDF
import os
import tempfile

FONT_PATH = "./app/fonts/DejaVuSans.ttf"

async def process_image_to_pdf(img_path: str) -> str:
    img = Image.open(img_path)
    text = pytesseract.image_to_string(img, lang="ukr+eng")

    pdf = FPDF()
    pdf.add_page()

    if os.path.exists(FONT_PATH):
        pdf.add_font("DejaVu", "", FONT_PATH, uni=True)
        pdf.set_font("DejaVu", size=12)
    else:
        pdf.set_font("Arial", size=12)

    pdf.multi_cell(0, 10, text.strip() or "No text detected.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        pdf.output(tmp_pdf.name)
        return tmp_pdf.name

async def create_text_pdf(text: str) -> str:
   from fpdf import FPDF
import tempfile
import os

def get_font_path():
    return os.path.join(os.path.dirname(__file__), "DejaVuSans.ttf")

async def create_text_pdf(text: str) -> str:
    pdf = FPDF()
    pdf.add_page()

    # Додай шрифт, який підтримує UTF-8 (треба мати файл DejaVuSans.ttf у тому ж каталозі)
    font_path = get_font_path()
    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.set_font("DejaVu", size=12)

    # Додай текст
    pdf.multi_cell(0, 10, txt=text)

    # Зберігаємо у тимчасовий файл
    tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(tmp_pdf.name)
    return tmp_pdf.name
