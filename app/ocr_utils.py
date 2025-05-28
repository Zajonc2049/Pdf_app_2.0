import os
import tempfile
from fpdf import FPDF
from PIL import Image
import pytesseract

async def process_image_to_pdf(image_path):
    """Обробляє зображення та створює PDF з розпізнаним текстом"""
    try:
        # OCR обробка
        text = pytesseract.image_to_string(Image.open(image_path), lang='ukr+eng')
        
        # Створюємо PDF з розпізнаним текстом
        pdf_path = await create_text_pdf(text)
        
        # Видаляємо тимчасове зображення
        if os.path.exists(image_path):
            os.unlink(image_path)
            
        return pdf_path
    except Exception as e:
        print(f"Помилка обробки зображення: {e}")
        raise

async def create_text_pdf(text):
    """Створює PDF файл з текстом"""
    try:
        # Створюємо тимчасовий файл для PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf_path = tmp.name
        
        # Створюємо PDF
        pdf = FPDF()
        pdf.add_page()
        
        # Використовуємо вбудований шрифт, який підтримує Unicode
        try:
            # Спробуємо використати Arial Unicode (якщо доступний)
            pdf.set_font('Arial', '', 12)
        except:
            # Якщо Arial недоступний, використовуємо базовий шрифт
            pdf.set_font('Times', '', 12)
        
        # Розбиваємо текст на рядки та додаємо в PDF
        lines = text.split('\n')
        for line in lines:
            # Кодуємо текст для правильного відображення
            try:
                # Спробуємо використати latin-1 кодування
                encoded_line = line.encode('latin-1', 'ignore').decode('latin-1')
                pdf.cell(0, 10, encoded_line, ln=True)
            except:
                # Якщо не вдається кодувати, використовуємо ASCII
                ascii_line = line.encode('ascii', 'ignore').decode('ascii')
                pdf.cell(0, 10, ascii_line, ln=True)
        
        # Зберігаємо PDF
        pdf.output(pdf_path)
        
        return pdf_path
        
    except Exception as e:
        print(f"Помилка створення PDF: {e}")
        raise

# Альтернативна версія з підтримкою Unicode через reportlab
async def create_text_pdf_unicode(text):
    """Створює PDF файл з текстом використовуючи reportlab для кращої підтримки Unicode"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        # Створюємо тимчасовий файл для PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf_path = tmp.name
        
        # Створюємо PDF
        c = canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter
        
        # Налаштовуємо шрифт
        c.setFont("Helvetica", 12)
        
        # Розбиваємо текст на рядки
        lines = text.split('\n')
        y_position = height - 50
        
        for line in lines:
            if y_position < 50:  # Нова сторінка, якщо місце закінчилось
                c.showPage()
                y_position = height - 50
                c.setFont("Helvetica", 12)
            
            # Додаємо рядок
            try:
                c.drawString(50, y_position, line)
            except:
                # Якщо є проблеми з кодуванням, використовуємо ASCII
                ascii_line = line.encode('ascii', 'ignore').decode('ascii')
                c.drawString(50, y_position, ascii_line)
            
            y_position -= 15
        
        c.save()
        return pdf_path
        
    except ImportError:
        # Якщо reportlab недоступний, використовуємо стандартну версію
        return await create_text_pdf(text)
    except Exception as e:
        print(f"Помилка створення PDF з reportlab: {e}")
        # Fallback до стандартної версії
        return await create_text_pdf(text)
