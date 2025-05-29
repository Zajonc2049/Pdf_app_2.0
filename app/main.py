from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
import os
import tempfile
import uvicorn
import logging
import traceback
from app.ocr_utils import process_image_to_pdf, create_text_pdf, check_render_environment

# Enhanced logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="PDF OCR Service", description="Convert images and text to PDF with OCR support")

# Add CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify concrete domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files if directory exists
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates
if os.path.isdir("templates"):
    templates = Jinja2Templates(directory="templates")
else:
    templates = None

# Додано функцію on_event для перевірки оточення при запуску
@app.on_event("startup")
async def startup_event():
    logger.info("Application startup event triggered.")
    # Виконайте перевірку середовища Render та Tesseract при запуску
    if not check_render_environment():
        logger.error("Failed to configure Tesseract or environment check failed. OCR functionality may be limited.")
        # Можливо, варто викликати HTTPException або вийти, якщо це критично
        # raise HTTPException(status_code=500, detail="Server startup failed: Tesseract not configured.")
    else:
        logger.info("Environment and Tesseract configured successfully.")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    return HTMLResponse("<h1>PDF OCR Service</h1><p>Upload a text or image to convert to PDF.</p>")

@app.post("/convert/text")
async def convert_text_to_pdf(text: str = Form(...)):
    try:
        pdf_path = await create_text_pdf(text)
        return FileResponse(path=pdf_path, media_type="application/pdf", filename="converted_text.pdf")
    except Exception as e:
        logger.error(f"Error converting text to PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to convert text to PDF: {e}")

@app.post("/convert/image")
async def convert_image_to_pdf(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed.")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as tmp_file:
            contents = await file.read()
            tmp_file.write(contents)
            tmp_image_path = tmp_file.name

        pdf_path = await process_image_to_pdf(tmp_image_path)
        return FileResponse(path=pdf_path, media_type="application/pdf", filename="converted_image.pdf")
    except Exception as e:
        logger.error(f"Error converting image to PDF: {e}", exc_info=True)
        # Додайте більш детальну інформацію в лог, щоб зрозуміти, чому OCR не спрацював
        # наприклад, print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to convert image to PDF: {e}")

if __name__ == "__main__":
    # Цей блок зазвичай не запускається на Render напряму, оскільки Render використовує команду uvicorn
    # однак він корисний для локального тестування.
    logger.info("Running application locally with uvicorn.")
    uvicorn.run(app, host="0.0.0.0", port=10000)
