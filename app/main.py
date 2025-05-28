from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import os
import tempfile
import uvicorn
from ocr_utils import process_image_to_pdf, create_text_pdf

app = FastAPI()

# Підключаємо статику, якщо є папка static
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Підключаємо шаблони Jinja2 (завжди, незалежно від наявності папки static)
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name
    
    pdf_path = await process_image_to_pdf(tmp_path)
    
    # Очищуємо тимчасовий файл
    os.unlink(tmp_path)
    
    return FileResponse(pdf_path, media_type='application/pdf', filename="ocr_result.pdf")

@app.post("/text/")
async def text_to_pdf(text: str = Form(...)):
    pdf_path = await create_text_pdf(text)
    return FileResponse(pdf_path, media_type='application/pdf', filename="text_to_pdf.pdf")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    # Отримуємо порт з змінної середовища (Render автоматично встановлює PORT)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
