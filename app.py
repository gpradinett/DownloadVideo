from fastapi import FastAPI, HTTPException, Form
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import FileResponse
import yt_dlp
import os
import threading
import time

app = FastAPI()

# Directorio de plantillas HTML
templates = Jinja2Templates(directory="templates")

# Ruta de descarga temporal
DOWNLOAD_PATH = "./downloads"
if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)

def remove_file(filepath: str):
    """Función que elimina el archivo del servidor después de un tiempo."""
    time.sleep(5)  # Esperar 5 segundos antes de eliminar
    if os.path.exists(filepath):
        os.remove(filepath)
        print(f"Archivo {filepath} eliminado del servidor")

@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("youtube.html", {"request": request})

@app.post("/video_info/")
async def get_video_info(url: str = Form(...)):
    try:
        ydl_opts = {'noplaylist': True}

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            video_title = info_dict.get('title', 'Video')
            thumbnail_url = info_dict.get('thumbnail')
            formats = info_dict.get('formats')

            # Filtrar los formatos que sean MP4
            mp4_formats = [
                {
                    'format_id': fmt['format_id'],
                    'ext': fmt['ext'],
                    'format_note': fmt.get('format_note', ''),
                    'filesize': fmt.get('filesize'),
                    'quality': fmt.get('height', fmt.get('format_note', 'Audio only')),  # Obtén la altura o el formato
                }
                for fmt in formats if fmt['ext'] == 'mp4' and fmt.get('vcodec') != 'none'
            ]

            # Filtrar los formatos que sean MP3 o M4A
            mp3_formats = [
                {
                    'format_id': fmt['format_id'],
                    'ext': fmt['ext'],
                    'format_note': fmt.get('format_note', ''),
                    'filesize': fmt.get('filesize'),
                    'quality': fmt.get('abr', fmt.get('format_note', 'Audio only')),  # Obtén el bitrate o el formato
                }
                for fmt in formats if fmt['ext'] in ['mp3', 'm4a']  # Agregar m4a si es necesario
            ]

            # Asignar nombres de calidad para los formatos de video
            for fmt in mp4_formats:
                if fmt['quality'] is None:
                    fmt['quality'] = 'N/A'
                elif 'p' in str(fmt['quality']):
                    fmt['quality'] = str(fmt['quality']) + 'p'
                else:
                    fmt['quality'] = fmt.get('format_note', fmt['quality'])

            return {
                "title": video_title,
                "thumbnail": thumbnail_url,
                "mp4_formats": mp4_formats,
                "mp3_formats": mp3_formats,
            }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al obtener la información del video: {str(e)}")



@app.post("/download/")
async def download_video(url: str = Form(...), format_id: str = Form(...)):
    try:
        # Configuramos las opciones de descarga
        ydl_opts = {
            'format': format_id,
            'outtmpl': f'{DOWNLOAD_PATH}/%(title)s.%(ext)s'
        }

        # Descargamos el video en el formato seleccionado
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_title = info_dict.get('title', 'Video')
            file_ext = info_dict.get('ext', 'mp4')
            video_file = f"{DOWNLOAD_PATH}/{video_title}.{file_ext}"

            # Verificamos si el archivo se descargó correctamente
            if not os.path.exists(video_file):
                raise HTTPException(status_code=404, detail="El video no se encontró después de la descarga.")

        # Preparamos la respuesta con el archivo descargado
        response = FileResponse(video_file, media_type=f"video/{file_ext}", filename=f"{video_title}.{file_ext}")

        # Limpiar el archivo del servidor después de la descarga en un hilo separado
        threading.Thread(target=remove_file, args=(video_file,)).start()

        return response

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al descargar el video: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
