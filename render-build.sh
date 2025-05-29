#!/usr/bin/env bash
# render-build.sh

set -o errexit  # exit on error

# Встановлюємо системні залежності
apt-get update
apt-get install -y \
    fonts-dejavu-core \
    fonts-liberation \
    fonts-noto \
    fontconfig \
    tesseract-ocr \
    tesseract-ocr-ukr \
    wkhtmltopdf

# Встановлюємо Python залежності
pip install --upgrade pip
pip install -r requirements.txt

# Створюємо папку для шрифтів
mkdir -p fonts

echo "✅ Всі залежності встановлено!"
