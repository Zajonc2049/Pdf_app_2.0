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

# Конфігурація для Render
def configure_tesseract_for_render():
    """Налаштовує Tesseract для роботи на Render"""
    # На Render Tesseract зазвичай встановлено в стандартному місці
    possible_paths = [
        '/usr/bin/tesseract',  # Стандартний шлях на Linux
        '/usr/local/bin/tesseract',
        '/opt/homebrew/bin/tesseract'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info(f"Tesseract знайдено: {path}")
            return True
    
    # Якщо не знайдено, використовуємо стандартну команду
    logger.info("Використовуємо стандартну команду tesseract")
    return True

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
            logger.error(f"❌ Проблема з Tesseract: {e}")
            # Спробуємо встановити змінну середовища
            os.environ['TESSDATA_PREFIX'] = '/usr/share/tesseract-ocr/5/tessdata/'
        
        # OCR обробка з послідовними спробами
        text = ""
        ocr_configs = [
            {'lang': 'ukr+eng', 'config': '--psm 6 -c preserve_interword_spaces=1'},
            {'lang': 'ukr+eng', 'config': '--psm 3'},
            {'lang': 'eng', 'config': '--psm 6'},
            {'lang': 'eng', 'config': '--psm 3'},
            {'lang': '', 'config': '--psm 6'}  # Без мови
        ]
        
        logger.info("🔤 Початок OCR обробки...")
        
        for i, ocr_config in enumerate(ocr_configs):
            try:
                logger.info(f"🔍 OCR спроба {i+1}: lang='{ocr_config['lang']}', config='{ocr_config['config']}'")
                
                if ocr_config['lang']:
                    text = pytesseract.image_to_string(
                        Image.open(image_path),
                        lang=ocr_config['lang'],
                        config=ocr_config['config']
                    )
                else:
                    text = pytesseract.image_to_string(
                        Image.open(image_path),
                        config=ocr_config['config']
                    )
                
                if text.strip():
                    logger.info(f"✅ OCR успішно: {len(text)} символів, перші 100: {text[:100]}")
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
        cleanup_files = [image_path, image_path + "_opt.jpg"]
        for file_path in cleanup_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.info(f"🗑️ Видалено: {file_path}")
            except Exception as e:
                logger.warning(f"⚠️ Не вдалося видалити {file_path}: {e}")
        
        return pdf_path
        
    except Exception as e:
        logger.error(f"❌ Критична помилка обробки зображення: {e}")
        
        # Очищення у разі помилки
        cleanup_files = [image_path, image_path + "_opt.jpg"]
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
        version = pytesseract.get_tesseract_version()
        logger.info(f"✅ Tesseract: {version}")
    except:
        logger.error("❌ Tesseract не знайдено")
    
    # Перевірка мов
    try:
        langs = pytesseract.get_languages()
        logger.info(f"✅ Мови: {langs}")
    except:
        logger.error("❌ Не вдалося отримати список мов")
    
    # Перевірка папок
    os.makedirs("temp", exist_ok=True)
    os.makedirs("fonts", exist_ok=True)
    logger.info("✅ Папки створено")
    
    return True
