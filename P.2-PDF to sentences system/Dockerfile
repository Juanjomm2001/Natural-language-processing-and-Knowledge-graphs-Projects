# Partimos de una imagen ligera oficial de python
FROM python:3.10-slim

WORKDIR /app

# Copiamos nuestro instalador de dependencias
COPY requirements.txt .

# Instalamos las librerías evitando cache para reducir la imagen al máximo.
RUN pip install --no-cache-dir -r requirements.txt

# Descargamos los modelos pre-entrenados para la función sent_tokenize de NLTK
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"

# Copiamos nuestra aplicación
COPY main.py .

# Exponemos el puerto que exige el proyecto
EXPOSE 8000

# Orden de arranque por defecto del contenedor
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
