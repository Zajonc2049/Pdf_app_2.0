import os
import tempfile
from fpdf import FPDF
from PIL import Image
import pytesseract
import urllib.request
from pathlib import Path
import base64
import io

# Вбудований шрифт DejaVu Sans в base64 (частина шрифту для кирилиці)
DEJAVU_FONT_BASE64 = """
T1RUTwACAAgAAQAAQ0ZGIAhlgnQAABqcAAAAlkZGVE0BdgIgAAAcNAAAABxHREVGABkAFAAAHFAAAAAe
T1MvMmcbMHEAAACgAAAAYGNtYXCRjgVZAAABAAAAAGRnYXNwAAAAEAAAHDAAAAAIZ2x5ZouAFdgAAAJY
AAAVkmhlYWQWZDbmAAAX7AAAADZoaGVhBfQD7AAAGCQAAAAKAG1heHAAlwAAAAAYLAAAACBuYW1lEWLu
yAAAGEwAAANacG9zdP/uADEAABuoAAAAIAABAAAAAQAAztqNJF8PPPUACwPoAAAAANdFvVgAAAAA10W9
WAAAAAAAIAAgACAAIAAGAAwAGwAsAEYAWgBnAHoAlwCkALcAzwDlAPoBDwEqAUMBXAF5AZYBrwHGAd0B
+gIVAjICTwJs
"""

def configure_tesseract_for_render():
    """Налаштовує Tesseract для середовища Render"""
    try:
        # Перевіряємо наявність Tesseract
        import subprocess
        result = subprocess.run(['tesseract', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Tesseract знайдено: {result.stdout.split()[1] if len(result.stdout.split()) > 1 else 'невідома версія'}")
            return True
        else:
            print("❌ Tesseract не знайдено")
            return False
    except Exception as e:
        print(f"❌ Помилка перевірки Tesseract: {e}")
        return False

def check_render_environment():
    """Перевіряє середовище Render"""
    print("🔍 Перевірка середовища...")
    
    # Перевіряємо Tesseract
    tesseract_ok = configure_tesseract_for_render()
    
    # Перевіряємо змінні середовища
    tessdata = os.environ.get('TESSDATA_PREFIX', 'не встановлено')
    print(f"TESSDATA_PREFIX: {tessdata}")
    
    # Перевіряємо доступні мови Tesseract
    try:
        languages = pytesseract.get_languages()
        print(f"Доступні мови Tesseract: {languages}")
        
        if 'ukr' not in languages:
            print("⚠️ УВАГА: Українська мова не знайдена!")
        if 'eng' not in languages:
            print("⚠️ УВАГА: Англійська мова не знайдена!")
            
    except Exception as e:
        print(f"❌ Помилка перевірки мов: {e}")
    
    return tesseract_ok

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
            # Створюємо папку для шрифтів
            font_dir = Path("fonts")
            font_dir.mkdir(exist_ok=True)
            font_path = font_dir / "DejaVuSans.ttf"
            
            # Спочатку спробуємо завантажити з інтернету
            if not font_path.exists():
                print("Завантажуємо шрифт DejaVu Sans...")
                try:
                    # Список альтернативних URL для шрифту
                    font_urls = [
                        "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf",
                        "https://raw.githubusercontent.com/google/fonts/main/ofl/dejavusans/DejaVuSans.ttf",
                        "https://www.fontsquirrel.com/fonts/download/dejavu-sans"
                    ]
                    
                    for url in font_urls:
                        try:
                            print(f"Спроба завантаження з {url[:50]}...")
                            urllib.request.urlretrieve(url, font_path)
                            if font_path.exists() and font_path.stat().st_size > 100000:
                                print("Шрифт успішно завантажено!")
                                break
                        except Exception as e:
                            print(f"Помилка завантаження з {url[:30]}: {e}")
                            continue
                except Exception as e:
                    print(f"Помилка завантаження шрифту: {e}")
            
            # Перевіряємо, чи вдалося завантажити шрифт
            if font_path.exists() and font_path.stat().st_size > 100000:
                try:
                    # Додаємо шрифт до FPDF
                    self.add_font('DejaVu', '', str(font_path), uni=True)
                    self.set_font('DejaVu', '', 12)
                    self.font_loaded = True
                    self.cyrillic_supported = True
                    print("Шрифт DejaVu Sans успішно налаштовано!")
                    return True
                except Exception as e:
                    print(f"Помилка налаштування шрифту: {e}")
            
            # Якщо шрифт не завантажився, спробуємо вбудований варіант
            print("Використовуємо резервний метод...")
            self.font_loaded = True
            self.cyrillic_supported = False
            return False
            
        except Exception as e:
            print(f"Загальна помилка завантаження шрифту: {e}")
            self.font_loaded = True
            self.cyrillic_supported = False
            return False

async def process_image_to_pdf(image_path):
    """Обробляє зображення та створює PDF з розпізнаним текстом"""
    try:
        # OCR обробка з українською та англійською мовами
        text = pytesseract.image_to_string(Image.open(image_path), lang='ukr+eng')
        print(f"Розпізнаний текст: {text[:100]}...")
        
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
    print(f"Створюємо PDF з текстом: {text[:50]}...")
    
    # Метод 1: Спробуємо weasyprint (найкращий для HTML->PDF з Unicode)
    try:
        return await create_pdf_weasyprint(text)
    except Exception as e:
        print(f"WeasyPrint не працює: {e}")
    
    # Метод 2: Спробуємо reportlab з детальним налаштуванням
    try:
        return await create_text_pdf_reportlab_advanced(text)
    except Exception as e:
        print(f"Reportlab advanced не працює: {e}")
    
    # Метод 3: Простий reportlab
    try:
        return await create_text_pdf_reportlab_simple(text)
    except Exception as e:
        print(f"Reportlab simple не працює: {e}")
    
    # Метод 4: FPDF з кастомним шрифтом
    try:
        return await create_text_pdf_fpdf_unicode(text)
    except Exception as e:
        print(f"FPDF Unicode не працює: {e}")
    
    # Метод 5: HTML to PDF через wkhtmltopdf подібний підхід
    try:
        return await create_pdf_from_html(text)
    except Exception as e:
        print(f"HTML to PDF не працює: {e}")
        
    # В крайньому випадку використовуємо транслітерацію
    print("❌ УВАГА: Всі методи Unicode не працюють! Використовується транслітерація.")
    return await create_text_pdf_basic_fallback(text)

async def create_pdf_weasyprint(text):
    """Створює PDF через WeasyPrint (найкращий метод)"""
    try:
        from weasyprint import HTML, CSS
        
        print("🔥 Використовуємо WeasyPrint (найкращий метод для Unicode)...")
        
        # Створюємо HTML з правильним кодуванням
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400&display=swap');
                body {{ 
                    font-family: 'Noto Sans', 'DejaVu Sans', Arial, sans-serif; 
                    font-size: 12pt; 
                    line-height: 1.4;
                    margin: 2cm;
                }}
                p {{ margin-bottom: 1em; }}
            </style>
        </head>
        <body>
        """
        
        # Додаємо текст по параграфах
        lines = text.split('\n')
        for line in lines:
            if line.strip():
                html_content += f"<p>{line}</p>\n"
            else:
                html_content += "<p>&nbsp;</p>\n"
        
        html_content += "</body></html>"
        
        # Створюємо PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf_path = tmp.name
        
        HTML(string=html_content).write_pdf(pdf_path)
        print("✅ PDF створено через WeasyPrint!")
        return pdf_path
        
    except ImportError:
        raise Exception("WeasyPrint не встановлено")
    except Exception as e:
        raise Exception(f"WeasyPrint помилка: {e}")

async def create_text_pdf_reportlab_advanced(text):
    """Покращений reportlab з детальним налаштуванням"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.utils import simpleSplit
        
        print("📄 Використовуємо покращений ReportLab...")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf_path = tmp.name
        
        # Список шрифтів для спроби
        font_attempts = [
            {
                'name': 'DejaVuSans',
                'url': 'https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf'
            },
            {
                'name': 'NotoSans', 
                'url': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf'
            }
        ]
        
        font_loaded = False
        active_font = 'DejaVuSans'
        
        for font_info in font_attempts:
            try:
                font_dir = Path("fonts")
                font_dir.mkdir(exist_ok=True)
                font_path = font_dir / f"{font_info['name']}.ttf"
                
                if not font_path.exists():
                    print(f"Завантажуємо {font_info['name']}...")
                    urllib.request.urlretrieve(font_info['url'], font_path)
                
                if font_path.exists() and font_path.stat().st_size > 50000:
                    pdfmetrics.registerFont(TTFont(font_info['name'], str(font_path)))
                    active_font = font_info['name']
                    font_loaded = True
                    print(f"✅ Шрифт {font_info['name']} завантажено!")
                    break
                    
            except Exception as e:
                print(f"Помилка з {font_info['name']}: {e}")
                continue
        
        if not font_loaded:
            raise Exception("Не вдалося завантажити жоден Unicode шрифт")
        
        # Створюємо PDF
        c = canvas.Canvas(pdf_path, pagesize=A4)
        width, height = A4
        c.setFont(active_font, 12)
        
        # Налаштування для тексту
        margin = 72  # 1 inch
        line_height = 16
        max_width = width - 2 * margin
        y_position = height - margin
        
        lines = text.split('\n')
        
        for line in lines:
            if y_position < margin + 50:  # Нова сторінка
                c.showPage()
                c.setFont(active_font, 12)
                y_position = height - margin
            
            if line.strip():
                # Розбиваємо довгі рядки
                wrapped_lines = simpleSplit(line, active_font, 12, max_width)
                for wrapped_line in wrapped_lines:
                    if y_position < margin + 50:
                        c.showPage()
                        c.setFont(active_font, 12)
                        y_position = height - margin
                    
                    c.drawString(margin, y_position, wrapped_line)
                    y_position -= line_height
            else:
                y_position -= line_height  # Порожній рядок
        
        c.save()
        print("✅ PDF створено через покращений ReportLab!")
        return pdf_path
        
    except ImportError:
        raise Exception("ReportLab не встановлено")
    except Exception as e:
        raise Exception(f"ReportLab advanced помилка: {e}")

async def create_text_pdf_reportlab_simple(text):
    """Простий reportlab метод"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        
        print("📋 Використовуємо простий ReportLab...")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf_path = tmp.name
        
        c = canvas.Canvas(pdf_path, pagesize=A4)
        width, height = A4
        
        # Використовуємо стандартний шрифт з максимальною підтримкою
        c.setFont("Helvetica", 12)
        
        y_position = height - 50
        lines = text.split('\n')
        
        for line in lines:
            if y_position < 50:
                c.showPage()
                c.setFont("Helvetica", 12)
                y_position = height - 50
            
            # Конвертуємо в UTF-8, потім пробуємо вивести
            try:
                c.drawString(50, y_position, line)
            except:
                # Якщо не працює, залишаємо тільки ASCII символи
                ascii_line = ''.join(char if ord(char) < 128 else '?' for char in line)
                c.drawString(50, y_position, ascii_line)
            
            y_position -= 15
        
        c.save()
        print("⚠️ PDF створено через простий ReportLab (можливо без Unicode)")
        return pdf_path
        
    except Exception as e:
        raise Exception(f"Simple ReportLab помилка: {e}")

async def create_pdf_from_html(text):
    """Створення PDF через HTML"""
    try:
        import subprocess
        
        print("🌐 Спроба створення PDF через HTML...")
        
        # Створюємо HTML файл
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; font-size: 12pt; margin: 2cm; }}
                p {{ margin-bottom: 1em; }}
            </style>
        </head>
        <body>
        """
        
        lines = text.split('\n')
        for line in lines:
            if line.strip():
                html_content += f"<p>{line}</p>\n"
            else:
                html_content += "<p>&nbsp;</p>\n"
        
        html_content += "</body></html>"
        
        # Зберігаємо HTML файл
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".html", encoding='utf-8') as html_tmp:
            html_tmp.write(html_content)
            html_path = html_tmp.name
        
        # Створюємо PDF файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as pdf_tmp:
            pdf_path = pdf_tmp.name
        
        # Пробуємо різні утиліти для конвертації HTML в PDF
        commands = [
            ['wkhtmltopdf', html_path, pdf_path],
            ['weasyprint', html_path, pdf_path],
            ['prince', html_path, pdf_path]
        ]
        
        success = False
        for cmd in commands:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0 and os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 100:
                    success = True
                    print(f"✅ PDF створено через {cmd[0]}!")
                    break
            except Exception as e:
                print(f"Команда {cmd[0]} не працює: {e}")
                continue
        
        # Видаляємо тимчасовий HTML
        os.unlink(html_path)
        
        if success:
            return pdf_path
        else:
            os.unlink(pdf_path)
            raise Exception("Жодна HTML->PDF утиліта не працює")
            
    except Exception as e:
        raise Exception(f"HTML to PDF помилка: {e}")

async def create_text_pdf_fpdf_unicode(text):
    """FPDF з Unicode шрифтом"""
    try:
        print("📝 Використовуємо FPDF з Unicode...")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf_path = tmp.name
        
        pdf = CyrillicPDF()
        cyrillic_loaded = pdf.load_cyrillic_font()
        
        if not cyrillic_loaded:
            raise Exception("Не вдалося завантажити Unicode шрифт для FPDF")
        
        pdf.add_page()
        
        lines = text.split('\n')
        for line in lines:
            if pdf.get_y() + 10 > 280:
                pdf.add_page()
                pdf.set_font('DejaVu', '', 12)
            
            pdf.cell(0, 8, line, ln=True)
        
        pdf.output(pdf_path)
        print("✅ PDF створено через FPDF Unicode!")
        return pdf_path
        
    except Exception as e:
        raise Exception(f"FPDF Unicode помилка: {e}")

async def create_text_pdf_basic_fallback(text):
    """Останній варіант з транслітерацією"""
    try:
        print("❌ ВИКОРИСТОВУЄТЬСЯ ТРАНСЛІТЕРАЦІЯ!")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf_path = tmp.name
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', '', 12)
        
        lines = text.split('\n')
        for line in lines:
            transliterated = transliterate_cyrillic(line)
            pdf.cell(0, 10, transliterated, ln=True)
        
        pdf.output(pdf_path)
        return pdf_path
        
    except Exception as e:
        print(f"Навіть fallback не працює: {e}")
        raise

def transliterate_cyrillic(text):
    """Транслітерація кирилиці"""
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
    """Створює PDF файл з текстом використовуючи найкращий доступний метод"""
    return await create_text_pdf_with_cyrillic(text)
