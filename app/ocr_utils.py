import os
import tempfile
from fpdf import FPDF
from PIL import Image
import pytesseract
import urllib.request
from pathlib import Path

class CyrillicPDF(FPDF):
    """Розширений клас FPDF з підтримкою кирилиці"""
    
    def __init__(self):
        super().__init__()
        self.font_loaded = False
    
    def load_cyrillic_font(self):
        """Завантажує шрифт з підтримкою кирилиці"""
        if self.font_loaded:
            return
            
        try:
            # Шлях до шрифту
            font_dir = Path("fonts")
            font_dir.mkdir(exist_ok=True)
            font_path = font_dir / "DejaVuSans.ttf"
            
            # Завантажуємо шрифт, якщо його немає
            if not font_path.exists():
                print("Завантажуємо шрифт DejaVu Sans...")
                font_url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"
                urllib.request.urlretrieve(font_url, font_path)
                print("Шрифт завантажено успішно!")
            
            # Додаємо шрифт до FPDF
            self.add_font('DejaVu', '', str(font_path), uni=True)
            self.set_font('DejaVu', '', 12)
            self.font_loaded = True
            
        except Exception as e:
            print(f"Помилка завантаження шрифту: {e}")
            # Fallback до базового шрифту
            try:
                self.set_font('Arial', '', 12)
            except:
                self.set_font('Times', '', 12)

async def process_image_to_pdf(image_path):
    """Обробляє зображення та створює PDF з розпізнаним текстом"""
    try:
        # OCR обробка з українською та англійською мовами
        text = pytesseract.image_to_string(Image.open(image_path), lang='ukr+eng')
        
        # Створюємо PDF з розпізнаним текстом
        pdf_path = await create_text_pdf_with_cyrillic(text)
        
        # Видаляємо тимчасове зображення
        if os.path.exists(image_path):
            os.unlink(image_path)
            
        return pdf_path
    except Exception as e:
        print(f"Помилка обробки зображення: {e}")
        raise

async def create_text_pdf(text):
    """Створює PDF файл з текстом (стара версія без кирилиці)"""
    return await create_text_pdf_with_cyrillic(text)

async def create_text_pdf_with_cyrillic(text):
    """Створює PDF файл з повною підтримкою кирилиці"""
    try:
        # Створюємо тимчасовий файл для PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf_path = tmp.name
        
        # Створюємо PDF з підтримкою кирилиці
        pdf = CyrillicPDF()
        pdf.load_cyrillic_font()
        pdf.add_page()
        
        # Розбиваємо текст на рядки та додаємо в PDF
        lines = text.split('\n')
        line_height = 8
        
        for line in lines:
            # Перевіряємо, чи потрібна нова сторінка
            if pdf.get_y() + line_height > 280:
                pdf.add_page()
            
            # Обробляємо довгі рядки (розбиваємо їх)
            if len(line) > 80:  # Якщо рядок занадто довгий
                words = line.split(' ')
                current_line = ""
                
                for word in words:
                    if len(current_line + word) < 80:
                        current_line += word + " "
                    else:
                        if current_line:
                            pdf.cell(0, line_height, current_line.strip(), ln=True)
                            if pdf.get_y() + line_height > 280:
                                pdf.add_page()
                        current_line = word + " "
                
                if current_line:
                    pdf.cell(0, line_height, current_line.strip(), ln=True)
            else:
                pdf.cell(0, line_height, line, ln=True)
        
        # Зберігаємо PDF
        pdf.output(pdf_path)
        
        return pdf_path
        
    except Exception as e:
        print(f"Помилка створення PDF: {e}")
        # Fallback до reportlab
        return await create_text_pdf_reportlab(text)

async def create_text_pdf_reportlab(text):
    """Створює PDF з використанням reportlab (альтернативний метод)"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.utils import ImageReader
        import urllib.request
        from pathlib import Path
        
        # Створюємо тимчасовий файл для PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf_path = tmp.name
        
        # Завантажуємо шрифт для reportlab
        font_dir = Path("fonts")
        font_dir.mkdir(exist_ok=True)
        font_path = font_dir / "DejaVuSans.ttf"
        
        if not font_path.exists():
            print("Завантажуємо шрифт для reportlab...")
            font_url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"
            urllib.request.urlretrieve(font_url, font_path)
        
        # Реєструємо шрифт
        pdfmetrics.registerFont(TTFont('DejaVu', str(font_path)))
        
        # Створюємо PDF
        c = canvas.Canvas(pdf_path, pagesize=A4)
        width, height = A4
        c.setFont("DejaVu", 12)
        
        # Розбиваємо текст на рядки
        lines = text.split('\n')
        y_position = height - 50
        line_height = 15
        
        for line in lines:
            # Перевіряємо, чи потрібна нова сторінка
            if y_position < 50:
                c.showPage()
                y_position = height - 50
                c.setFont("DejaVu", 12)
            
            # Обробляємо довгі рядки
            if len(line) > 80:
                words = line.split(' ')
                current_line = ""
                
                for word in words:
                    if len(current_line + word) < 80:
                        current_line += word + " "
                    else:
                        if current_line:
                            c.drawString(50, y_position, current_line.strip())
                            y_position -= line_height
                            if y_position < 50:
                                c.showPage()
                                y_position = height - 50
                                c.setFont("DejaVu", 12)
                        current_line = word + " "
                
                if current_line:
                    c.drawString(50, y_position, current_line.strip())
                    y_position -= line_height
            else:
                c.drawString(50, y_position, line)
                y_position -= line_height
        
        c.save()
        return pdf_path
        
    except ImportError:
        print("Reportlab не встановлено, використовуємо базове рішення")
        return await create_text_pdf_basic_fallback(text)
    except Exception as e:
        print(f"Помилка створення PDF з reportlab: {e}")
        return await create_text_pdf_basic_fallback(text)

async def create_text_pdf_basic_fallback(text):
    """Базове рішення без додаткових шрифтів"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf_path = tmp.name
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', '', 12)
        
        lines = text.split('\n')
        for line in lines:
            # Замінюємо кирилічні символи на латинські аналоги для відображення
            transliterated = transliterate_cyrillic(line)
            pdf.cell(0, 10, transliterated, ln=True)
        
        pdf.output(pdf_path)
        return pdf_path
        
    except Exception as e:
        print(f"Помилка створення базового PDF: {e}")
        raise

def transliterate_cyrillic(text):
    """Транслітерація кирилиці для відображення у випадку проблем зі шрифтами"""
    cyrillic_to_latin = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'є': 'ye',
        'ж': 'zh', 'з': 'z', 'и': 'y', 'і': 'i', 'ї': 'yi', 'й': 'y', 'к': 'k',
        'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's',
        'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh',
        'щ': 'shch', 'ь': '', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Є': 'YE',
        'Ж': 'ZH', 'З': 'Z', 'И': 'Y', 'І': 'I', 'Ї': 'YI', 'Й': 'Y', 'К': 'K',
        'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S',
        'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'KH', 'Ц': 'TS', 'Ч': 'CH', 'Ш': 'SH',
        'Щ': 'SHCH', 'Ь': '', 'Ю': 'YU', 'Я': 'YA'
    }
    
    result = ""
    for char in text:
        result += cyrillic_to_latin.get(char, char)
    
    return result

# Альтернативна версія з підтримкою Unicode через reportlab (залишається для сумісності)
async def create_text_pdf_unicode(text):
    """Створює PDF файл з текстом використовуючи reportlab для кращої підтримки Unicode"""
    return await create_text_pdf_reportlab(text)
