# Guía de instalación del proyecto
Este documento es la guía para instalar todo lo necesario para hacer funcionar el chatbot.

## 1. Instalación del entorno virtual
- python -m venv venv
- source venv/bin/activate **# Linux/macOS**
- venv\Scripts\activate **# Windows**

## 2. Instalar dependencias
- pip install -r requirements.txt

## 3. Crear el .env
- touch .env

## 4. Aplicar migraciones
- python manage.py migrate

## 5. Crear superusuario para admin
- python manage.py createsuperuser

## 6. Cargar datos iniciales
- python manage.py cargar_datos_iniciales

## 7. Generar el modelo spaCy
- python manage.py generar_nlp
- python -m spacy init config config.cfg --lang es --pipeline ner,textcat_multilabel --optimize accuracy
- python -m spacy train ./entrenamiento/spacy/config.cfg --output ./modelo --paths.train ./entrenamiento/spacy/train.spacy --paths.dev ./entrenamiento/spacy/dev.spacy

## 8. Installar y configurar Ollama
- ollama pull llama3.2
- python manage.py generar_modelfiles
- python manage.py generar_modelfiles --crear

## 9. Arrancar el servidor de desarrollo
- python manage.py runserver