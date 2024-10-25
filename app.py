from fastapi import FastAPI, HTTPException, Form
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import FileResponse
import yt_dlp
import os
import threading
import time
import re

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
async def home(request: Request):
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

            # Filtrar los formatos que sean MP4 y tengan un tamaño válido
            mp4_formats = [
                {
                    'format_id': fmt['format_id'],
                    'ext': fmt['ext'],
                    'format_note': fmt.get('format_note', ''),
                    'filesize': fmt.get('filesize'),
                    'quality': fmt.get('height', fmt.get('format_note', 'Video')),
                }
                for fmt in formats if fmt['ext'] == 'mp4' and fmt.get('vcodec') != 'none' and fmt.get('filesize')
            ]

            # Eliminar duplicados basados en la resolución (mayor tamaño primero)
            unique_formats = {}
            for fmt in mp4_formats:
                quality = fmt['quality']
                if quality not in unique_formats or fmt['filesize'] > unique_formats[quality]['filesize']:
                    unique_formats[quality] = fmt

            mp4_formats = list(unique_formats.values())

            available_mp3_qualities = {
                320: "320 kbps – Calidad de CD",
                192: "192 kbps – Sin pérdidas significativas",
                128: "128 kbps – Pérdidas ligeramente perceptibles",
                96: "96 kbps – Calidad similar a radio FM",
                32: "32 kbps – Similar a radio AM",
            }

            mp3_formats = [
                {
                    'quality': quality,
                    'description': description,
                }
                for quality, description in available_mp3_qualities.items()
            ]

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

def clean_title(title: str) -> str:
    """Función que limpia el título del video eliminando caracteres especiales y emojis."""
    title = re.sub(r'[^\w\s-]', '', title)  # Remover caracteres especiales
    title = re.sub(r'\s+', '_', title)  # Reemplazar espacios por guiones bajos
    return title.lower()

@app.post("/download/video/")
async def download_video(url: str = Form(...), format_id: str = Form(None)):
    try:
        with yt_dlp.YoutubeDL({'noplaylist': True}) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            video_title = info_dict.get('title', 'Video')
            clean_video_title = clean_title(video_title)

        if format_id:
            ydl_opts = {
                'format': format_id,
                'outtmpl': f'{DOWNLOAD_PATH}/{clean_video_title}.%(ext)s',
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            video_file = f"{DOWNLOAD_PATH}/{clean_video_title}.mp4"

            if not os.path.exists(video_file):
                raise HTTPException(status_code=404, detail="El archivo no se encontró después de la descarga.")

            response = FileResponse(video_file, media_type="video/mp4", filename=f"{video_title}.mp4")

            # Limpiar el archivo del servidor después de la descarga en un hilo separado
            threading.Thread(target=remove_file, args=(video_file,)).start()

            return response

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al descargar el video: {str(e)}")

@app.post("/download/audio/")
async def download_audio(url: str = Form(...), quality: int = Form(None)):
    try:
        with yt_dlp.YoutubeDL({'noplaylist': True}) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            video_title = info_dict.get('title', 'Video')
            clean_video_title = clean_title(video_title)

        if quality:
            if quality not in [320, 192, 128, 96, 32]:
                raise HTTPException(status_code=400, detail="Calidad de audio no válida.")

            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': str(quality),
                }],
                'outtmpl': f'{DOWNLOAD_PATH}/{clean_video_title}.%(ext)s',
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            audio_file = f"{DOWNLOAD_PATH}/{clean_video_title}.mp3"

            if not os.path.exists(audio_file):
                raise HTTPException(status_code=404, detail="El archivo no se encontró después de la descarga.")

            response = FileResponse(audio_file, media_type="audio/mpeg", filename=f"{video_title}.mp3")

            # Limpiar el archivo del servidor después de la descarga en un hilo separado
            threading.Thread(target=remove_file, args=(audio_file,)).start()

            return response

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al descargar el audio: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
