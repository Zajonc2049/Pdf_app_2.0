import os
import tempfile
from fpdf import FPDF
from PIL import Image
import pytesseract
import urllib.request
from pathlib import Path
import base64
import io
import logging

# Налаштування логування
logger = logging.getLogger(__name__)

class UTF8FPDF(FPDF):
    """FPDF клас з підтримкою Unicode"""
    
    def __init__(self):
        super().__init__()
        self.font_loaded = False
        self.current_font = None
    
    def load_unicode_font(self):
        """Завантажуємо шрифт з підтримкою кирилиці"""
        if self.font_loaded:
            return
            
        try:
            # Спробуємо завантажити шрифт DejaVu (є в більшості Linux систем)
            font_paths = [
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                '/System/Library/Fonts/Helvetica.ttc',  # macOS
                'C:/Windows/Fonts/arial.ttf'  # Windows
            ]
            
            font_loaded = False
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        self.add_font('DejaVu', '', font_path, uni=True)
                        self.set_font('DejaVu', '', 12)
                        self.current_font = 'DejaVu'
                        font_loaded = True
                        logger.info(f"✅ Завантажено шрифт: {font_path}")
                        break
                    except Exception as e:
                        logger.warning(f"⚠️ Не вдалося завантажити {font_path}: {e}")
                        continue
            
            if not font_loaded:
                # Якщо не знайшли шрифт, використовуємо стандартний
                logger.warning("⚠️ Не знайдено Unicode шрифт, використовуємо стандартний")
                try:
                    self.set_font('Arial', '', 12)
                    self.current_font = 'Arial'
                except:
                    # Якщо Arial недоступний, використовуємо будь-який доступний
                    self.set_font('Helvetica', '', 12)
                    self.current_font = 'Helvetica'
            
            self.font_loaded = True
            
        except Exception as e:
            logger.error(f"❌ Помилка завантаження шрифту: {e}")
            try:
                self.set_font('Helvetica', '', 12)
                self.current_font = 'Helvetica'
            except:
                pass
            self.font_loaded = True

    def set_font_size(self, size):
        """Встановлює розмір шрифту"""
        self.load_unicode_font()  # Переконуємося, що шрифт завантажено
        if self.current_font:
            self.set_font(self.current_font, '', size)
        else:
            super().set_font_size(size)

    def add_utf8_text(self, text):
        """Додає текст з підтримкою UTF-8"""
        self.load_unicode_font()
        
        # Розбиваємо текст на рядки
        lines = text.split('\n')
        
        for line in lines:
            # Перевіряємо, чи поміститься рядок на сторінці
            if self.get_y() > 250:  # Якщо близько до кінця сторінки
                self.add_page()
                self.load_unicode_font()  # Відновлюємо шрифт після нової сторінки
            
            try:
                # Спробуємо додати рядок як є
                self.cell(0, 10, line, ln=True)
            except Exception as e:
                logger.warning(f"⚠️ Помилка з рядком '{line[:50]}...': {e}")
                try:
                    # Якщо не вийшло, спробуємо закодувати
                    encoded_line = line.encode('latin1', 'ignore').decode('latin1')
                    self.cell(0, 10, encoded_line, ln=True)
                except:
                    # В крайньому випадку, пропускаємо рядок
                    self.cell(0, 10, '[Text encoding error]', ln=True)

# Конфігурація для Render
def configure_tesseract_for_render():
    """Налаштовує Tesseract для роботи на Render"""
    # На Render Tesseract зазвичай встановлено в стандартному місці
    possible_paths = [
        '/usr/bin/tesseract',  # Стандартний шлях на Linux
        '/usr/local/bin/tesseract',
        '/opt/homebrew/bin/tesseract',
        'tesseract'  # Системний PATH
    ]
    
    for path in possible_paths:
        if path == 'tesseract' or os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info(f"Tesseract знайдено: {path}")
            return True
    
    logger.warning("⚠️ Tesseract не знайдено в стандартних місцях")
    return False

async def create_text_pdf_with_cyrillic(text):
    """Створює PDF з тексту з підтримкою кирилиці"""
    try:
        logger.info("📄 Створення PDF з кирилицею...")
        
        # Створюємо PDF з Unicode підтримкою
        pdf = UTF8FPDF()
        pdf.add_page()
        
        # Завантажуємо шрифт спочатку
        pdf.load_unicode_font()
        
        # Додаємо заголовок
        pdf.set_font_size(16)
        pdf.cell(0, 10, 'Розпізнаний текст', ln=True, align='C')
        pdf.ln(10)
        
        # Додаємо основний текст
        pdf.set_font_size(12)
        pdf.add_utf8_text(text)
        
        # Зберігаємо в тимчасовий файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            pdf_path = tmp_file.name
            pdf.output(pdf_path)
        
        logger.info(f"✅ PDF створено: {pdf_path}")
        return pdf_path
        
    except Exception as e:
        logger.error(f"❌ Помилка створення PDF: {e}")
        
        # Якщо основний метод не спрацював, спробуємо простіший підхід
        try:
            logger.info("🔄 Спроба створення простого PDF...")
            simple_pdf = FPDF()
            simple_pdf.add_page()
            simple_pdf.set_font('Arial', '', 12)
            
            # Конвертуємо кирилицю в латиницю для простого PDF
            import unicodedata
            ascii_text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
            
            simple_pdf.cell(0, 10, 'Recognized Text (ASCII)', ln=True)
            simple_pdf.ln(5)
            
            lines = ascii_text.split('\n')
            for line in lines:
                if simple_pdf.get_y() > 250:
                    simple_pdf.add_page()
                    simple_pdf.set_font('Arial', '', 12)
                simple_pdf.cell(0, 8, line[:80], ln=True)  # Обмежуємо довжину рядка
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                pdf_path = tmp_file.name
                simple_pdf.output(pdf_path)
            
            logger.info(f"✅ Простий PDF створено: {pdf_path}")
            return pdf_path
            
        except Exception as simple_error:
            logger.error(f"❌ Помилка створення простого PDF: {simple_error}")
            raise Exception(f"Не вдалося створити PDF: {str(e)} | Простий PDF: {str(simple_error)}")

async def create_text_pdf(text):
    """Створює PDF з тексту (загальна функція)"""
    return await create_text_pdf_with_cyrillic(text)

async def process_image_to_pdf(image_path):
    """Обробляє зображення та створює PDF з розпізнаним текстом (оптимізовано для Render)"""
    try:
        logger.info(f"🔍 Render: Початок обробки зображення: {image_path}")
        
        # Налаштовуємо Tesseract
        configure_tesseract_for_render()
        
        # Перевіряємо, чи існує файл
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Файл не знайдено: {image_path}")
        
        file_size = os.path.getsize(image_path)
        if file_size == 0:
            raise ValueError("Файл порожній")
        
        logger.info(f"📏 Розмір файлу: {file_size} байт")
        
        # Відкриваємо та обробляємо зображення
        try:
            with Image.open(image_path) as img:
                logger.info(f"🖼️ Зображення відкрито: {img.format}, розмір: {img.size}, режим: {img.mode}")
                
                # Оптимізація зображення для OCR
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                    logger.info("🔄 Конвертовано в RGB")
                
                # Якщо зображення дуже велике, зменшуємо його
                max_size = 2000
                if img.width > max_size or img.height > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                    logger.info(f"📉 Зображення зменшено до: {img.size}")
                
                # Зберігаємо оптимізоване зображення
                optimized_path = image_path + "_opt.jpg"
                img.save(optimized_path, 'JPEG', quality=95)
                image_path = optimized_path
                
        except Exception as e:
            logger.error(f"❌ Помилка відкриття зображення: {e}")
            raise ValueError(f"Не вдалося відкрити зображення: {e}")
        
        # Тестуємо Tesseract
        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"✅ Tesseract версія: {version}")
        except Exception as e:
            logger.warning(f"⚠️ Проблема з Tesseract: {e}")
            # Спробуємо встановити змінну середовища
            os.environ['TESSDATA_PREFIX'] = '/usr/share/tesseract-ocr/5/tessdata/'
        
        # OCR обробка з послідовними спробами
        text = ""
        ocr_configs = [
            {'lang': 'ukr+eng', 'config': '--psm 6 -c preserve_interword_spaces=1'},
            {'lang': 'ukr+eng', 'config': '--psm 3'},
            {'lang': 'ukr', 'config': '--psm 6'},
            {'lang': 'eng', 'config': '--psm 6'},
            {'lang': 'eng', 'config': '--psm 3'},
            {'lang': '', 'config': '--psm 6'}  # Без мови
        ]
        
        logger.info("🔤 Початок OCR обробки...")
        
        for i, ocr_config in enumerate(ocr_configs):
            try:
                logger.info(f"🔍 OCR спроба {i+1}: lang='{ocr_config['lang']}', config='{ocr_config['config']}'")
                
                with Image.open(image_path) as ocr_img:
                    if ocr_config['lang']:
                        text = pytesseract.image_to_string(
                            ocr_img,
                            lang=ocr_config['lang'],
                            config=ocr_config['config']
                        )
                    else:
                        text = pytesseract.image_to_string(
                            ocr_img,
                            config=ocr_config['config']
                        )
                
                if text.strip():
                    logger.info(f"✅ OCR успішно: {len(text)} символів")
                    logger.info(f"📝 Перші 100 символів: {text[:100]}")
                    break
                else:
                    logger.warning(f"⚠️ OCR повернув порожній результат")
                    
            except Exception as e:
                logger.warning(f"❌ OCR спроба {i+1} провалилася: {e}")
                continue
        
        # Якщо текст не розпізнано
        if not text.strip():
            text = """Текст не розпізнано.

Можливі причини:
• Зображення не містить тексту
• Якість зображення недостатня
• Текст написаний нечітким шрифтом
• Потрібно покращити освітлення зображення

Спробуйте:
• Зробити більш чітке фото
• Покращити освітлення
• Використати контрастніше зображення"""
            logger.warning("⚠️ OCR не розпізнав текст, використовуємо повідомлення за замовчуванням")
        
        # Створюємо PDF
        logger.info("📄 Створення PDF...")
        pdf_path = await create_text_pdf_with_cyrillic(text)
        
        if not os.path.exists(pdf_path):
            raise Exception("PDF файл не створено")
        
        logger.info(f"✅ PDF успішно створено: {pdf_path}")
        
        # Очищення тимчасових файлів
        cleanup_files = [image_path]
        if image_path.endswith("_opt.jpg"):
            cleanup_files.append(image_path.replace("_opt.jpg", ""))
        
        for file_path in cleanup_files:
            try:
                if os.path.exists(file_path) and file_path != pdf_path:
                    os.unlink(file_path)
                    logger.info(f"🗑️ Видалено: {file_path}")
            except Exception as e:
                logger.warning(f"⚠️ Не вдалося видалити {file_path}: {e}")
        
        return pdf_path
        
    except Exception as e:
        logger.error(f"❌ Критична помилка обробки зображення: {e}")
        
        # Очищення у разі помилки
        cleanup_files = [image_path]
        if image_path.endswith("_opt.jpg"):
            cleanup_files.append(image_path.replace("_opt.jpg", ""))
            
        for file_path in cleanup_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except:
                pass
        
        raise Exception(f"Помилка обробки зображення: {str(e)}")

# Функція для перевірки системи на Render
def check_render_environment():
    """Перевіряє середовище Render"""
    logger.info("🔍 Перевірка середовища Render...")
    
    # Перевірка Tesseract
    try:
        configure_tesseract_for_render()
        version = pytesseract.get_tesseract_version()
        logger.info(f"✅ Tesseract: {version}")
    except Exception as e:
        logger.error(f"❌ Tesseract проблема: {e}")
    
    # Перевірка мов
    try:
        langs = pytesseract.get_languages()
        logger.info(f"✅ Доступні мови: {langs}")
        
        # Перевіряємо наявність української мови
        if 'ukr' in langs:
            logger.info("✅ Українська мова доступна")
        else:
            logger.warning("⚠️ Українська мова недоступна")
            
    except Exception as e:
        logger.error(f"❌ Не вдалося отримати список мов: {e}")
    
    # Перевірка папок
    try:
        os.makedirs("temp", exist_ok=True)
        logger.info("✅ Папка temp створена")
    except Exception as e:
        logger.error(f"❌ Не вдалося створити папку temp: {e}")
    
    # Перевірка PIL
    try:
        from PIL import Image
        logger.info("✅ PIL доступний")
    except Exception as e:
        logger.error(f"❌ PIL проблема: {e}")
    
    # Перевірка шрифтів
    logger.info("🔤 Перевірка доступних шрифтів...")
    font_paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        '/System/Library/Fonts/Helvetica.ttc',
        'C:/Windows/Fonts/arial.ttf'
    ]
    
    found_fonts = []
    for font_path in font_paths:
        if os.path.exists(font_path):
            found_fonts.append(font_path)
            logger.info(f"✅ Знайдено шрифт: {font_path}")
    
    if not found_fonts:
        logger.warning("⚠️ Не знайдено жодного TTF шрифту")
    
    # Перевірка створення простого PDF
    try:
        test_pdf = FPDF()
        test_pdf.add_page()
        test_pdf.set_font('Arial', '', 12)
        test_pdf.cell(0, 10, 'Test', ln=True)
        
        with tempfile.NamedTemporaryFile(delete=True, suffix='.pdf') as tmp_file:
            test_pdf.output(tmp_file.name)
            logger.info("✅ Тестовий PDF створено успішно")
            
    except Exception as e:
        logger.error(f"❌ Не вдалося створити тестовий PDF: {e}")
    
    return True
