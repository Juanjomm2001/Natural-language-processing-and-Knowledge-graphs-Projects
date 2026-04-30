# ─── Stage 1: Build environment ───────────────────────────────────────────────
# We start from a slim official Python image to keep the container small.
# "slim" removes many unused system packages that the full image includes.
FROM python:3.11-slim

# Set the working directory inside the container.
# All subsequent commands (COPY, RUN, CMD) operate relative to this path.
WORKDIR /app

# ─── Stage 2: Install dependencies ───────────────────────────────────────────
# We copy requirements.txt FIRST, before copying the app code.
# This is a Docker caching trick: if requirements.txt doesn't change,
# Docker reuses the cached layer and doesn't re-install packages on rebuild.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── Stage 3: Copy application source ────────────────────────────────────────
# Copia tanto app.py (producción) como app_gemini.py (pruebas)
COPY app.py app_gemini.py ./

# ─── Stage 4: Expose and run ─────────────────────────────────────────────────
EXPOSE 8000

# Arranca directamente app_gemini para que pruebes. 
CMD ["uvicorn", "app_gemini:app", "--host", "0.0.0.0", "--port", "8000"]
