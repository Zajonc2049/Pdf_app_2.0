#!/bin/bash

# build.sh - Скрипт збірки для Render

echo "🚀 Початок збірки для Render..."

# Оновлюємо пакети
echo "📦 Оновлення системних пакетів..."
apt-get update

# Встановлюємо Tesseract OCR та мовні пакети
echo "🔤 Встановлення Tesseract OCR..."
apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-ukr \
    tesseract-ocr-eng \
    tesseract-ocr-rus \
    libtesseract-dev \
    libleptonica-dev \
    pkg-config

# Встановлюємо додаткові системні залежності для обробки зображень
echo "🖼️ Встановлення залежностей для зображень..."
apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0

# Очищуємо кеш APT
apt-get clean
rm -rf /var/lib/apt/lists/*

# Встановлюємо Python залежності
echo "🐍 Встановлення Python пакетів..."
pip install --upgrade pip
pip install -r requirements.txt

# Створюємо необхідні папки
echo "📁 Створення папок..."
mkdir -p temp fonts templates

# Перевіряємо встановлення Tesseract
echo "✅ Перевірка Tesseract..."
tesseract --version
tesseract --list-langs

echo "🎉 Збірка завершена успішно!"
