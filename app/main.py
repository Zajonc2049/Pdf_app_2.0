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
from pathlib import Path
from app.ocr_utils import process_image_to_pdf, create_text_pdf

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
templates = Jinja2Templates(directory="templates")

# Створюємо необхідні папки
os.makedirs("temp", exist_ok=True)
os.makedirs("fonts", exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    try:
        logger.info(f"Отримано файл: {file.filename}, тип: {file.content_type}")
        
        # Перевіряємо тип файлу
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/bmp", "image/tiff"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"Непідтримуваний тип файлу: {file.content_type}")
        
        # Визначаємо розширення файлу
        file_extension = Path(file.filename).suffix.lower()
        if not file_extension:
            file_extension = ".jpg"  # За замовчуванням
        
        # Створюємо тимчасовий файл з правильним розширенням
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension, dir="temp") as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name
        
        logger.info(f"Тимчасовий файл створено: {tmp_path}")
        
        # Перевіряємо, чи файл створено правильно
        if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
            raise HTTPException(status_code=400, detail="Не вдалося створити тимчасовий файл")
        
        # Обробляємо зображення
        pdf_path = await process_image_to_pdf(tmp_path)
        
        logger.info(f"PDF створено: {pdf_path}")
        
        # Перевіряємо, чи PDF створено
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=500, detail="Не вдалося створити PDF файл")
        
        return FileResponse(
            pdf_path, 
            media_type='application/pdf', 
            filename="ocr_result.pdf"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Помилка обробки файлу: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Помилка обробки файлу: {str(e)}")

@app.post("/text/")
async def text_to_pdf(text: str = Form(...)):
    try:
        logger.info(f"Створення PDF з тексту: {text[:50]}...")
        pdf_path = await create_text_pdf(text)
        
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=500, detail="Не вдалося створити PDF файл")
        
        return FileResponse(pdf_path, media_type='application/pdf', filename="text_to_pdf.pdf")
    except Exception as e:
        logger.error(f"Помилка створення PDF з тексту: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Помилка створення PDF: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# API ендпоінти для React
@app.post("/api/upload/")
async def api_upload_file(file: UploadFile = File(...)):
    try:
        logger.info(f"API: Отримано файл: {file.filename}, тип: {file.content_type}")
        
        # Перевіряємо тип файлу
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/bmp", "image/tiff"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"Непідтримуваний тип файлу: {file.content_type}")
        
        # Визначаємо розширення файлу
        file_extension = Path(file.filename).suffix.lower()
        if not file_extension:
            file_extension = ".jpg"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension, dir="temp") as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name
        
        logger.info(f"API: Тимчасовий файл створено: {tmp_path}")
        
        if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
            raise HTTPException(status_code=400, detail="Не вдалося створити тимчасовий файл")
        
        pdf_path = await process_image_to_pdf(tmp_path)
        
        logger.info(f"API: PDF створено: {pdf_path}")
        
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=500, detail="Не вдалося створити PDF файл")
        
        return FileResponse(
            pdf_path, 
            media_type='application/pdf', 
            filename="ocr_result.pdf"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API помилка обробки файлу: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Помилка обробки файлу: {str(e)}")

@app.post("/api/text/")
async def api_text_to_pdf(text: str = Form(...)):
    try:
        logger.info(f"API: Створення PDF з тексту: {text[:50]}...")
        pdf_path = await create_text_pdf(text)
        
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=500, detail="Не вдалося створити PDF файл")
        
        return FileResponse(pdf_path, media_type='application/pdf', filename="text_to_pdf.pdf")
    except Exception as e:
        logger.error(f"API помилка створення PDF з тексту: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Помилка створення PDF: {str(e)}")

if __name__ == "__main__":
    # Отримуємо порт з змінної середовища (Render автоматично встановлює PORT)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
