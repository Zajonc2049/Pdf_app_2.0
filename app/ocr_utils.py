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
        self.cyrillic_supported = False
    
    def load_cyrillic_font(self):
        """Завантажує шрифт з підтримкою кирилиці"""
        if self.font_loaded:
            return self.cyrillic_supported
            
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
            
            # Перевіряємо, чи файл шрифту існує та має правильний розмір
            if font_path.exists() and font_path.stat().st_size > 100000:  # Мінімум 100KB
                # Додаємо шрифт до FPDF
                self.add_font('DejaVu', '', str(font_path), uni=True)
                self.set_font('DejaVu', '', 12)
                self.font_loaded = True
                self.cyrillic_supported = True
                print("Шрифт DejaVu Sans успішно завантажено та налаштовано!")
                return True
            else:
                raise Exception("Файл шрифту пошкоджений або неповний")
            
        except Exception as e:
            print(f"Помилка завантаження шрифту DejaVu: {e}")
            self.font_loaded = True
            self.cyrillic_supported = False
            
            # Не встановлюємо fallback шрифт тут - буде обробляться в create_text_pdf
            return False

async def process_image_to_pdf(image_path):
    """Обробляє зображення та створює PDF з розпізнаним текстом"""
    try:
        # OCR обробка з українською та англійською мовами
        text = pytesseract.image_to_string(Image.open(image_path), lang='ukr+eng')
        print(f"Розпізнаний текст: {text[:100]}...")  # Для налагодження
        
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
    """Створює PDF файл з текстом - головна функція"""
    return await create_text_pdf_with_cyrillic(text)

async def create_text_pdf_with_cyrillic(text):
    """Створює PDF файл з повною підтримкою кирилиці"""
    print(f"Створюємо PDF з текстом: {text[:50]}...")  # Для налагодження
    
    # Спочатку спробуємо reportlab (найкраща підтримка Unicode)
    try:
        return await create_text_pdf_reportlab(text)
    except Exception as e:
        print(f"Reportlab не працює: {e}")
    
    # Потім спробуємо FPDF з кастомним шрифтом
    try:
        return await create_text_pdf_fpdf_unicode(text)
    except Exception as e:
        print(f"FPDF з Unicode не працює: {e}")
    
    # В крайньому випадку використовуємо транслітерацію
    print("УВАГА: Використовується транслітерація через проблеми зі шрифтами!")
    return await create_text_pdf_basic_fallback(text)

async def create_text_pdf_reportlab(text):
    """Створює PDF з використанням reportlab (кращий метод)"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph
        from reportlab.lib.units import inch
        
        print("Використовуємо reportlab для створення PDF...")
        
        # Створюємо тимчасовий файл для PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf_path = tmp.name
        
        # Завантажуємо та реєструємо шрифт
        font_dir = Path("fonts")
        font_dir.mkdir(exist_ok=True)
        font_path = font_dir / "DejaVuSans.ttf"
        
        if not font_path.exists():
            print("Завантажуємо шрифт для reportlab...")
            font_url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"
            urllib.request.urlretrieve(font_url, font_path)
            print("Шрифт завантажено!")
        
        # Реєструємо шрифт
        pdfmetrics.registerFont(TTFont('DejaVu', str(font_path)))
        
        # Створюємо документ
        doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Створюємо стиль з нашим шрифтом
        styles = getSampleStyleSheet()
        custom_style = styles['Normal']
        custom_style.fontName = 'DejaVu'
        custom_style.fontSize = 12
        custom_style.leading = 14
        
        # Створюємо контент
        story = []
        lines = text.split('\n')
        
        for line in lines:
            if line.strip():  # Якщо рядок не порожній
                para = Paragraph(line, custom_style)
                story.append(para)
            else:  # Додаємо порожній рядок
                para = Paragraph("&nbsp;", custom_style)
                story.append(para)
        
        # Будуємо документ
        doc.build(story)
        print("PDF створено успішно з reportlab!")
        
        return pdf_path
        
    except ImportError:
        print("Reportlab не встановлено")
        raise Exception("Reportlab не доступний")
    except Exception as e:
        print(f"Помилка створення PDF з reportlab: {e}")
        raise

async def create_text_pdf_fpdf_unicode(text):
    """Створює PDF з FPDF та Unicode шрифтом"""
    try:
        print("Використовуємо FPDF з Unicode шрифтом...")
        
        # Створюємо тимчасовий файл для PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf_path = tmp.name
        
        # Створюємо PDF з підтримкою кирилиці
        pdf = CyrillicPDF()
        cyrillic_loaded = pdf.load_cyrillic_font()
        
        if not cyrillic_loaded:
            raise Exception("Не вдалося завантажити шрифт з підтримкою кирилиці")
        
        pdf.add_page()
        
        # Розбиваємо текст на рядки та додаємо в PDF
        lines = text.split('\n')
        line_height = 8
        
        for line in lines:
            # Перевіряємо, чи потрібна нова сторінка
            if pdf.get_y() + line_height > 280:
                pdf.add_page()
                pdf.set_font('DejaVu', '', 12)  # Переналаштовуємо шрифт після нової сторінки
            
            # Обробляємо довгі рядки (розбиваємо їх)
            max_line_length = 90  # Символів на рядок
            if len(line) > max_line_length:
                words = line.split(' ')
                current_line = ""
                
                for word in words:
                    if len(current_line + word + " ") <= max_line_length:
                        current_line += word + " "
                    else:
                        if current_line:
                            pdf.cell(0, line_height, current_line.strip(), ln=True)
                            if pdf.get_y() + line_height > 280:
                                pdf.add_page()
                                pdf.set_font('DejaVu', '', 12)
                        current_line = word + " "
                
                if current_line:
                    pdf.cell(0, line_height, current_line.strip(), ln=True)
            else:
                pdf.cell(0, line_height, line, ln=True)
        
        # Зберігаємо PDF
        pdf.output(pdf_path)
        print("PDF створено успішно з FPDF!")
        
        return pdf_path
        
    except Exception as e:
        print(f"Помилка створення PDF з FPDF: {e}")
        raise

async def create_text_pdf_basic_fallback(text):
    """Базове рішення з транслітерацією (останній варіант)"""
    try:
        print("ВИКОРИСТОВУЄТЬСЯ ТРАНСЛІТЕРАЦІЯ! Кирилиця буде замінена на латиницю.")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf_path = tmp.name
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', '', 12)
        
        lines = text.split('\n')
        for line in lines:
            # Замінюємо кирилічні символи на латинські аналоги
            transliterated = transliterate_cyrillic(line)
            pdf.cell(0, 10, transliterated, ln=True)
        
        pdf.output(pdf_path)
        return pdf_path
        
    except Exception as e:
        print(f"Помилка створення базового PDF: {e}")
        raise

def transliterate_cyrillic(text):
    """Транслітерація кирилиці (використовується тільки як крайній засіб)"""
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

# Залишаємо для зворотної сумісності
async def create_text_pdf_unicode(text):
    """Створює PDF файл з текстом використовуючи reportlab для кращої підтримки Unicode"""
    return await create_text_pdf_reportlab(text)
