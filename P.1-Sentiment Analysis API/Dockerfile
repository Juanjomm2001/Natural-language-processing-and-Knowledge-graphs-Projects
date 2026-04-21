FROM python:3.11-alpine

WORKDIR /app

COPY main.py /app/main.py
COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]  


# FROM python:3.11-alpine: Aquí le estás diciendo a Docker: "Móntame de fondo un entorno Linux" (Alpine es el nombre de una versión ultra ligera de Linux para que no pese más de 200MB, tal y como pedía tu ejercicio) y "asegúrate de que venga con Python 3.11 pre-instalado".
# WORKDIR /app: Al crear ese micro-linux de fondo, Docker necesita una carpeta donde trabajar. Esto le dice: "Crea una carpeta llamada /app dentro de tu pequeño sistema operativo y haz todo lo siguiente ahí dentro". Da igual si la llamas /app, /proyecto o /src, pero /app es el estándar de la industria.
# COPY ... ...: Le dice a Docker que coja el archivo de tu PC (

# main.py
#  y 

# requirements.txt
# ) y lo copie a su carpeta /app interna de forma congelada dentro de la Imagen.
# RUN pip install ...: Docker abre su propia consola interna en Linux y ejecuta "pip" para descargar los módulos (FastAPI, httpx...) y empaquetarlos en esa receta.
# EXPOSE 8000: Una nota informativa de que esta app quiere comunicarse con el mundo externo usando la "puerta" 8000.
# CMD [...]: Comando final. Le dice al contenedor que, cuando alguien por fin ejecute la imagen (docker run) en el futuro, dispare la API y ponga el servidor a escuchar encendiéndolo.