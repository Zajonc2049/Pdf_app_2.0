from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
import os
import tempfile
import uvicorn
import logging
from app.ocr_utils import process_image_to_pdf, create_text_pdf, check_render_environment

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Додаємо CORS для React фронтенду
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # У продакшені вкажіть конкретні домени
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Підключаємо статику, якщо є папка static
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Підключаємо шаблони Jinja2 (завжди, незалежно від наявності папки static)
if os.path.isdir("templates"):
    templates = Jinja2Templates(directory="templates")
else:
    templates = None

@app.on_event("startup")
async def startup_event():
    """Ініціалізація при запуску"""
    logger.info("🚀 Запуск сервісу...")
    check_render_environment()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    else:
        return HTMLResponse("""
        <html>
            <body>
                <h1>PDF Service</h1>
                <p>Use /upload/ for image to PDF or /text/ for text to PDF</p>
            </body>
        </html>
        """)

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    logger.info(f"📤 Отримано файл: {file.filename}, тип: {file.content_type}, розмір: {file.size}")
    
    try:
        # Перевіряємо тип файлу
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Файл повинен бути зображенням")
        
        # Визначаємо розширення файлу
        file_extension = ".jpg"
        if file.filename:
            if file.filename.lower().endswith(('.png', '.gif', '.bmp', '.tiff')):
                file_extension = os.path.splitext(file.filename)[1].lower()
        
        # Створюємо тимчасовий файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
            contents = await file.read()
            if not contents:
                raise HTTPException(status_code=400, detail="Файл порожній")
            
            tmp.write(contents)
            tmp_path = tmp.name
            logger.info(f"💾 Збережено в: {tmp_path}, розмір: {len(contents)} байт")
        
        # Обробляємо зображення
        pdf_path = await process_image_to_pdf(tmp_path)
        
        # Перевіряємо, чи створився PDF
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=500, detail="Не вдалося створити PDF")
        
        logger.info(f"✅ PDF створено: {pdf_path}")
        
        return FileResponse(
            pdf_path, 
            media_type='application/pdf', 
            filename="ocr_result.pdf",
            headers={"Content-Disposition": "attachment; filename=ocr_result.pdf"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Помилка обробки файлу: {e}")
        raise HTTPException(status_code=500, detail=f"Помилка обробки файлу: {str(e)}")

@app.post("/text/")
async def text_to_pdf(text: str = Form(...)):
    try:
        if not text.strip():
            raise HTTPException(status_code=400, detail="Текст не може бути порожнім")
        
        logger.info(f"📝 Створення PDF з тексту, довжина: {len(text)} символів")
        pdf_path = await create_text_pdf(text)
        
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=500, detail="Не вдалося створити PDF")
        
        return FileResponse(
            pdf_path, 
            media_type='application/pdf', 
            filename="text_to_pdf.pdf",
            headers={"Content-Disposition": "attachment; filename=text_to_pdf.pdf"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Помилка створення PDF з тексту: {e}")
        raise HTTPException(status_code=500, detail=f"Помилка створення PDF: {str(e)}")

@app.get("/health")
async def health_check():
    """Перевірка здоров'я сервісу"""
    try:
        # Перевіряємо наявність Tesseract
        from app.ocr_utils import configure_tesseract_for_render
        tesseract_ok = configure_tesseract_for_render()
        
        return {
            "status": "healthy",
            "tesseract": "ok" if tesseract_ok else "error",
            "timestamp": os.environ.get("RENDER_SERVICE_NAME", "local")
        }
    except Exception as e:
        return {
            "status": "error", 
            "error": str(e)
        }

# API ендпоінти для React
@app.post("/api/upload/")
async def api_upload_file(file: UploadFile = File(...)):
    return await upload_file(file)

@app.post("/api/text/")
async def api_text_to_pdf(text: str = Form(...)):
    return await text_to_pdf(text)

# Додаткові ендпоінти для діагностики
@app.get("/debug/tesseract")
async def debug_tesseract():
    """Діагностика Tesseract"""
    try:
        import pytesseract
        from PIL import Image
        
        # Перевіряємо версію
        version = pytesseract.get_tesseract_version()
        
        # Перевіряємо мови
        languages = pytesseract.get_languages()
        
        # Перевіряємо шлях
        tesseract_path = pytesseract.pytesseract.tesseract_cmd
        
        return {
            "tesseract_version": str(version),
            "available_languages": languages,
            "tesseract_path": tesseract_path,
            "tesseract_exists": os.path.exists(tesseract_path) if tesseract_path != 'tesseract' else "using system PATH"
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Отримуємо порт з змінної середовища (Render автоматично встановлює PORT)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
