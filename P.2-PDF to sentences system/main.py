import os
import xml.etree.ElementTree as ET
import httpx
import nltk
from fastapi import FastAPI, UploadFile, File, HTTPException

app = FastAPI(title="PDF to Sentences Web Service")

# Buscamos la variable en el entorno, si no está cogemos localhost por defecto
GROBID_URL = os.environ.get("GROBID_URL", "http://localhost:8070")

@app.post("/v1/extract-sentences")
async def extract_sentences(pdf_file: UploadFile = File(...)):
    if not pdf_file.filename.endswith('.pdf'):
         raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # 1. Leemos el archivo en crudo (bytes)
    pdf_bytes = await pdf_file.read()
    
    # 2. Hacemos la peticion HTTP asíncrona hacia el contenedor de GROBID
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            files = {"input": (pdf_file.filename, pdf_bytes, "application/pdf")}
            response = await client.post(f"{GROBID_URL}/api/processFulltextDocument", files=files)
            response.raise_for_status() # Lanza excepción si el código no es 2xx
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Error conectando a GROBID: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=502, detail=f"GROBID devolvió un error: {exc}")
    
    # 3. Analizar la respuesta XML (TEI) provista por GROBID
    tei_xml = response.text
    full_text = ""
    try:
        # GROBID usa el namespace "tei" oficial en sus nodos
        ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
        root = ET.fromstring(tei_xml)
        
        # Buscamos y guardamos solamente los textos que vivan dentro de la etiqueta <p> (párrafos) del <body>
        body_parts = root.findall('.//tei:body//tei:p', ns)
        for p in body_parts:
            # Concatenamos todo el contenido de texto dentro del párrafo
            text_content = "".join(p.itertext())
            if text_content:
                full_text += text_content + " "
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Error parseando el XML de GROBID: {e}")

    # 4. Tokenizar de Texto a Oraciones (Sentences) utilizando NLTK
    try:
        # Esto partirá el texto gigante en una lista de cadenas, donde cada cadena es una frase gramatical
        sentences = nltk.sent_tokenize(full_text)
        # Limpiamos los espacios sobrantes en cada frase
        sentences = [s.strip() for s in sentences if s.strip()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error separando el texto en oraciones: {e}")
        
    return {"sentences": sentences}
