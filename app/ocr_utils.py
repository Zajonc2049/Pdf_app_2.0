import os
import tempfile
import subprocess
import shutil
from fpdf import FPDF
from PIL import Image
import pytesseract
import urllib.request
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def configure_tesseract_for_render():
    """Configure Tesseract for Render environment with comprehensive checks"""
    logger.info("🔍 Configuring Tesseract...")
    
    # 1. Спробуйте знайти tesseract за стандартними шляхами
    tesseract_paths = [
        '/usr/bin/tesseract',
        '/usr/local/bin/tesseract',
        shutil.which('tesseract') # Шукає в PATH
    ]
    
    # 2. Перевірте, чи встановлено TESSDATA_PREFIX як змінну середовища
    # Це може вказувати на шлях до tesseract, якщо він не в PATH
    tessdata_prefix_env = os.environ.get('TESSDATA_PREFIX')
    if tessdata_prefix_env:
        # Якщо TESSDATA_PREFIX встановлено, спробуйте знайти tesseract поруч
        # або припустити, що він у стандартному системному шляху
        logger.info(f"Using TESSDATA_PREFIX from environment: {tessdata_prefix_env}")
        # Додаємо потенційний шлях до tesseract, якщо він не в PATH
        # Зазвичай tesseract знаходиться в /usr/bin, який має бути в PATH
        # Але якщо ні, то це може допомогти.
        # Однак, якщо tesseract не в PATH, це системна проблема, а не pytesseract
        # Тому ми покладаємося на shutil.which('tesseract')
    else:
        logger.warning("⚠️ TESSDATA_PREFIX environment variable not set.")

    tesseract_cmd = None
    for path in tesseract_paths:
        if path and os.path.exists(path):
            tesseract_cmd = path
            logger.info(f"✅ Found Tesseract at: {path}")
            break
    
    if not tesseract_cmd:
        logger.error("❌ Tesseract executable not found! Please ensure it's installed and in PATH.")
        return False
    
    # Встановлюємо шлях до виконуваного файлу tesseract для pytesseract
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    
    # Тестуємо встановлення tesseract
    try:
        result = subprocess.run([tesseract_cmd, '--version'], 
                                 capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_info = result.stdout.strip()
            logger.info(f"✅ Tesseract version: {version_info.split()[1] if len(version_info.split()) > 1 else 'unknown'}")
        else:
            logger.error(f"❌ Tesseract version check failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("❌ Tesseract version check timed out")
        return False
    except Exception as e:
        logger.error(f"❌ Error checking Tesseract version: {e}")
        return False
    
    # Перевіряємо доступні мови
    try:
        languages = pytesseract.get_languages(config='')
        logger.info(f"📝 Available Tesseract languages: {languages}")
        
        required_langs = ['eng', 'ukr', 'rus'] # Додаємо 'rus'
        missing_langs = [lang for lang in required_langs if lang not in languages]
        
        if missing_langs:
            logger.warning(f"⚠️ Missing languages: {missing_langs}. OCR accuracy may be affected.")
            # Спробуйте продовжити з доступними мовами
        else:
            logger.info("✅ All required languages available")
            
    except Exception as e:
        logger.error(f"❌ Error checking languages: {e}")
        return False
    
    # Тестуємо OCR з простим зображенням
    try:
        test_img = Image.new('RGB', (200, 50), color='white')
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_img:
            test_img.save(tmp_img.name)
            
            test_text = pytesseract.image_to_string(tmp_img.name, lang='eng') # Використовуємо шлях до файлу
            logger.info(f"✅ Tesseract OCR test successful. Recognized text (first 20 chars): '{test_text[:20]}'")
            
            os.unlink(tmp_img.name) # Clean up
            
    except Exception as e:
        logger.error(f"❌ Tesseract OCR test failed: {e}")
        return False
    
    return True

def check_render_environment():
    """Check Render environment setup"""
    logger.info("🔍 Checking Render environment...")
    
    tessdata = os.environ.get('TESSDATA_PREFIX', 'not set')
    logger.info(f"TESSDATA_PREFIX: {tessdata}")
    
    if tessdata != 'not set' and os.path.exists(tessdata):
        logger.info(f"✅ TESSDATA directory exists: {tessdata}")
        try:
            lang_files = [f for f in os.listdir(tessdata) if f.endswith('.traineddata')]
            logger.info(f"📚 Available language files in TESSDATA_PREFIX: {lang_files}")
        except Exception as e:
            logger.warning(f"⚠️ Could not list tessdata files: {e}")
    else:
        logger.warning(f"⚠️ TESSDATA directory not found or TESSDATA_PREFIX not set correctly: {tessdata}")
    
    commands_to_test = ['tesseract', 'convert', 'python3']
    for cmd in commands_to_test:
        cmd_path = shutil.which(cmd)
        if cmd_path:
            logger.info(f"✅ {cmd} found at: {cmd_path}")
        else:
            logger.warning(f"⚠️ {cmd} not found in PATH")
    
    tesseract_ok = configure_tesseract_for_render()
    
    if tesseract_ok:
        logger.info("🎉 Environment setup complete!")
    else:
        logger.error("❌ Environment setup failed!")
    
    return tesseract_ok

class CyrillicPDF(FPDF):
    """Extended FPDF class with Cyrillic support"""
    
    def __init__(self):
        super().__init__()
        self.font_loaded = False
        self.cyrillic_supported = False
    
    def load_cyrillic_font(self):
        """Load font with Cyrillic support"""
        if self.font_loaded:
            return self.cyrillic_supported
            
        try:
            font_dir = Path("fonts")
            font_dir.mkdir(exist_ok=True)
            font_path = font_dir / "DejaVuSans.ttf"
            
            if not font_path.exists() or font_path.stat().st_size < 100000: # Перевірка розміру файлу
                logger.info("📥 Downloading DejaVu Sans font...")
                font_urls = [
                    "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf",
                    "https://github.com/google/fonts/raw/main/apache/opensans/OpenSans-Regular.ttf",
                    "https://www.fontsquirrel.com/fonts/download/dejavu-sans" # Додаткове джерело
                ]
                
                downloaded = False
                for url in font_urls:
                    try:
                        logger.info(f"Trying to download from {url[:50]}...")
                        urllib.request.urlretrieve(url, font_path)
                        if font_path.exists() and font_path.stat().st_size > 100000:
                            logger.info("✅ Font downloaded successfully!")
                            downloaded = True
                            break
                    except Exception as e:
                        logger.warning(f"Failed to download from {url[:30]}: {e}")
                        continue
                
                if not downloaded:
                    logger.error("❌ Failed to download any font. Cyrillic support may be limited.")
                    self.font_loaded = True
                    self.cyrillic_supported = False
                    return False

            if font_path.exists() and font_path.stat().st_size > 100000:
                try:
                    self.add_font('DejaVu', '', str(font_path), uni=True)
                    self.set_font('DejaVu', '', 12)
                    self.font_loaded = True
                    self.cyrillic_supported = True
                    logger.info("✅ DejaVu Sans font configured successfully!")
                    return True
                except Exception as e:
                    logger.error(f"Font configuration error with FPDF: {e}")
            
            logger.warning("⚠️ Using fallback font method for FPDF...")
            self.font_loaded = True
            self.cyrillic_supported = False
            return False
            
        except Exception as e:
            logger.error(f"General font loading error for FPDF: {e}")
            self.font_loaded = True
            self.cyrillic_supported = False
            return False

async def process_image_to_pdf(image_path):
    """Process image and create PDF with recognized text"""
    logger.info(f"🖼️ Processing image: {image_path}")
    
    try:
        if not os.path.exists(image_path):
            raise Exception(f"Image file not found: {image_path}")
        
        try:
            img = Image.open(image_path)
            logger.info(f"📐 Image size: {img.size}, mode: {img.mode}")
            
            if img.mode != 'RGB':
                img = img.convert('RGB')
                logger.info("🔄 Converted image to RGB")
                
        except Exception as e:
            raise Exception(f"Cannot open image file: {e}")
        
        try:
            logger.info("🔍 Starting OCR with ukr+eng+rus languages...")
            # Використовуємо config='--psm 3' для розпізнавання тексту на сторінці
            text = pytesseract.image_to_string(img, lang='ukr+eng+rus', config='--psm 3')
            
            if not text.strip():
                logger.info("🔍 OCR with ukr+eng+rus yielded no text. Trying fallback to eng only...")
                text = pytesseract.image_to_string(img, lang='eng', config='--psm 3')
                
            if not text.strip():
                logger.info("🔍 OCR with eng only yielded no text. Trying different PSM modes for eng...")
                for psm in [6, 7, 8, 13]: # Спробуємо різні режими PSM
                    try:
                        temp_text = pytesseract.image_to_string(img, lang='eng', config=f'--psm {psm}')
                        if temp_text.strip():
                            text = temp_text
                            logger.info(f"✅ Found text with PSM {psm}.")
                            break
                    except Exception as psm_e:
                        logger.warning(f"OCR with PSM {psm} failed: {psm_e}")
                        continue
                        
            logger.info(f"📝 OCR result length: {len(text)} characters")
            logger.info(f"📝 First 100 chars: {text[:100]}...")
            
        except pytesseract.TesseractNotFoundError as e:
            logger.error(f"Tesseract executable not found during OCR: {e}. Ensure Tesseract is installed and in PATH.")
            text = f"OCR Error: Tesseract not found. Please ensure it's installed and configured correctly."
        except Exception as e:
            logger.error(f"OCR failed: {e}", exc_info=True)
            text = f"OCR Error: {str(e)}\nPlease check if the image contains readable text or if Tesseract is configured."
        
        pdf_path = await create_text_pdf_with_cyrillic(text)
        
        try:
            os.unlink(image_path)
            logger.info("🗑️ Temporary image cleaned up")
        except Exception as e:
            logger.warning(f"Could not clean up temp image: {e}")
            
        return pdf_path
        
    except Exception as e:
        logger.error(f"❌ Image processing failed: {e}", exc_info=True)
        raise

async def create_text_pdf(text):
    """Create PDF file with text - main function"""
    return await create_text_pdf_with_cyrillic(text)

async def create_text_pdf_with_cyrillic(text):
    """Create PDF file with full Cyrillic support"""
    logger.info(f"📄 Creating PDF with text (length: {len(text)} chars)...")
    
    # Method 1: Try WeasyPrint (best for HTML->PDF with Unicode)
    try:
        return await create_pdf_weasyprint(text)
    except Exception as e:
        logger.warning(f"WeasyPrint failed: {e}")
    
    # Method 2: Try advanced ReportLab
    try:
        return await create_text_pdf_reportlab_advanced(text)
    except Exception as e:
        logger.warning(f"ReportLab advanced failed: {e}")
    
    # Method 3: Simple ReportLab
    try:
        return await create_text_pdf_reportlab_simple(text)
    except Exception as e:
        logger.warning(f"ReportLab simple failed: {e}")
    
    # Method 4: FPDF with custom font
    try:
        return await create_text_pdf_fpdf_unicode(text)
    except Exception as e:
        logger.warning(f"FPDF Unicode failed: {e}")
    
    # Last resort: Basic fallback with transliteration
    logger.warning("❌ All Unicode methods failed! Using transliteration fallback.")
    return await create_text_pdf_basic_fallback(text)

async def create_pdf_weasyprint(text):
    """Create PDF via WeasyPrint (best method)"""
    try:
        from weasyprint import HTML, CSS
        
        logger.info("🔥 Using WeasyPrint (best Unicode method)...")
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="uk">
        <head>
            <meta charset="UTF-8">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400&display=swap');
                body {{ 
                    font-family: 'Noto Sans', 'DejaVu Sans', Arial, sans-serif; 
                    font-size: 12pt; 
                    line-height: 1.4;
                    margin: 2cm;
                    color: #333;
                }}
                p {{ 
                    margin-bottom: 1em; 
                    text-align: justify;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 2em;
                    padding-bottom: 1em;
                    border-bottom: 1px solid #ccc;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>OCR Result</h2>
            </div>
        """
        
        lines = text.split('\n')
        for line in lines:
            if line.strip():
                escaped_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                html_content += f"<p>{escaped_line}</p>\n"
            else:
                html_content += "<p>&nbsp;</p>\n"
        
        html_content += "</body></html>"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf_path = tmp.name
        
        HTML(string=html_content).write_pdf(pdf_path)
        logger.info("✅ PDF created via WeasyPrint!")
        return pdf_path
        
    except ImportError:
        raise Exception("WeasyPrint not installed. Please add it to requirements.txt and ensure system dependencies are met.")
    except Exception as e:
        raise Exception(f"WeasyPrint error: {e}")

async def create_text_pdf_reportlab_advanced(text):
    """Advanced ReportLab with detailed configuration"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.utils import simpleSplit
        
        logger.info("📄 Using advanced ReportLab...")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf_path = tmp.name
        
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
        active_font = 'Helvetica' # Fallback to Helvetica
        
        for font_info in font_attempts:
            try:
                font_dir = Path("fonts")
                font_dir.mkdir(exist_ok=True)
                font_path = font_dir / f"{font_info['name']}.ttf"
                
                if not font_path.exists() or font_path.stat().st_size < 50000:
                    logger.info(f"Downloading {font_info['name']} for ReportLab...")
                    urllib.request.urlretrieve(font_info['url'], font_path)
                
                if font_path.exists() and font_path.stat().st_size > 50000:
                    pdfmetrics.registerFont(TTFont(font_info['name'], str(font_path)))
                    active_font = font_info['name']
                    font_loaded = True
                    logger.info(f"✅ Font {font_info['name']} loaded for ReportLab!")
                    break
                    
            except Exception as e:
                logger.warning(f"Error with {font_info['name']} for ReportLab: {e}")
                continue
        
        if not font_loaded:
            logger.warning("Could not load any Unicode font for ReportLab. Using Helvetica (limited Unicode).")
            # raise Exception("Could not load any Unicode font for ReportLab") # Don't raise, just warn and use fallback
            
        c = canvas.Canvas(pdf_path, pagesize=A4)
        width, height = A4
        c.setFont(active_font, 12)
        
        margin = 72  # 1 inch
        line_height = 16
        max_width = width - 2 * margin
        y_position = height - margin
        
        c.setFont(active_font, 16)
        c.drawString(margin, y_position, "OCR Result")
        y_position -= 30
        c.setFont(active_font, 12)
        
        lines = text.split('\n')
        
        for line in lines:
            if y_position < margin + 50:  # New page
                c.showPage()
                c.setFont(active_font, 12)
                y_position = height - margin
            
            if line.strip():
                wrapped_lines = simpleSplit(line, active_font, 12, max_width)
                for wrapped_line in wrapped_lines:
                    if y_position < margin + 50:
                        c.showPage()
                        c.setFont(active_font, 12)
                        y_position = height - margin
                    
                    c.drawString(margin, y_position, wrapped_line)
                    y_position -= line_height
            else:
                y_position -= line_height  # Empty line
        
        c.save()
        logger.info("✅ PDF created via advanced ReportLab!")
        return pdf_path
        
    except ImportError:
        raise Exception("ReportLab not installed. Please add it to requirements.txt.")
    except Exception as e:
        raise Exception(f"ReportLab advanced error: {e}")

async def create_text_pdf_reportlab_simple(text):
    """Simple ReportLab method"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        
        logger.info("📋 Using simple ReportLab...")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf_path = tmp.name
        
        c = canvas.Canvas(pdf_path, pagesize=A4)
        width, height = A4
        
        c.setFont("Helvetica", 12)
        
        y_position = height - 50
        lines = text.split('\n')
        
        for line in lines:
            if y_position < 50:
                c.showPage()
                c.setFont("Helvetica", 12)
                y_position = height - 50
            
            try:
                c.drawString(50, y_position, line)
            except:
                ascii_line = ''.join(char if ord(char) < 128 else '?' for char in line)
                c.drawString(50, y_position, ascii_line)
            
            y_position -= 15
        
        c.save()
        logger.info("⚠️ PDF created via simple ReportLab (possibly without Unicode)")
        return pdf_path
        
    except Exception as e:
        raise Exception(f"Simple ReportLab error: {e}")

async def create_text_pdf_fpdf_unicode(text):
    """FPDF with Unicode font"""
    try:
        logger.info("📝 Using FPDF with Unicode...")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf_path = tmp.name
        
        pdf = CyrillicPDF()
        cyrillic_loaded = pdf.load_cyrillic_font()
        
        if not cyrillic_loaded:
            # Не піднімаємо виняток, якщо шрифт не завантажився,
            # дозволяючи системі спробувати інші методи
            logger.warning("FPDF Unicode font could not be loaded. Trying other PDF methods.")
            raise Exception("FPDF Unicode font not available.")
            
        pdf.add_page()
        
        lines = text.split('\n')
        for line in lines:
            if pdf.get_y() + 10 > 280:
                pdf.add_page()
                pdf.set_font('DejaVu', '', 12)
                
            pdf.cell(0, 8, line, ln=True)
        
        pdf.output(pdf_path)
        logger.info("✅ PDF created via FPDF Unicode!")
        return pdf_path
        
    except Exception as e:
        raise Exception(f"FPDF Unicode error: {e}")

async def create_text_pdf_basic_fallback(text):
    """Last resort with transliteration"""
    try:
        logger.warning("❌ USING TRANSLITERATION FALLBACK!")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf_path = tmp.name
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', '', 12)
        
        pdf.cell(0, 10, "WARNING: Cyrillic text has been transliterated", ln=True)
        pdf.ln(5)
        
        lines = text.split('\n')
        for line in lines:
            transliterated = transliterate_cyrillic(line)
            pdf.cell(0, 10, transliterated, ln=True)
        
        pdf.output(pdf_path)
        logger.info("⚠️ Fallback PDF created with transliteration")
        return pdf_path
        
    except Exception as e:
        logger.error(f"Even fallback failed: {e}")
        raise

def transliterate_cyrillic(text):
    """Transliterate Cyrillic to Latin"""
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

# Backward compatibility
async def create_text_pdf_unicode(text):
    """Create PDF file with text using the best available method"""
    return await create_text_pdf_with_cyrillic(text)
