from fastapi import FastAPI, HTTPException, Form, File
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import FileResponse
import yt_dlp
import os
import threading
import time
import re
from fastapi import UploadFile


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

@app.get("/tiktok")
async def tiktok_home(request: Request):
    return templates.TemplateResponse("tiktok.html", {"request": request})

@app.get("/instagram")
async def instagram_home(request: Request):
    return templates.TemplateResponse("instagram.html", {"request": request})

@app.post("/video_info/")
async def get_video_info(url: str = Form(...)):
    try:
        ydl_opts = {'noplaylist': True}

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            #print(json.dumps(ydl.sanitize_info(info_dict)))
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


def clean_title(title):
    # Limitar el título a 100 caracteres para evitar errores de longitud
    title = title[:100]
    # Reemplazar "#" por "_"
    title = title.replace("#", "_")
    # Eliminar emojis y caracteres especiales adicionales
    title = re.sub(r'[^\w\s-]', '', title)
    # Reemplazar espacios y guiones múltiples por "_"
    return re.sub(r'[\s-]+', '_', title)



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

@app.post("/download/tiktok/")
async def download_tiktok_video(url: str = Form(...)):
    try:
        print(f"URL recibida para descarga: {url}")  # Log de URL en el servidor

        with yt_dlp.YoutubeDL({'noplaylist': True}) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            video_title = info_dict.get('title', 'TikTok Video')
            clean_video_title = clean_title(video_title)
            print(f"Título limpio del video: {clean_video_title}")

        ydl_opts = {
            'format': 'best',
            'outtmpl': f'{DOWNLOAD_PATH}/{clean_video_title}.%(ext)s',
            'geo_bypass': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            video_file = f"{DOWNLOAD_PATH}/{clean_video_title}.mp4"
            print(f"Video descargado como: {video_file}")

        if not os.path.isfile(video_file):
            print("Error: archivo no encontrado después de la descarga")
            raise HTTPException(status_code=404, detail="El archivo no se encontró después de la descarga.")

        print("Preparando respuesta para enviar el archivo al cliente")
        response = FileResponse(video_file, media_type="video/mp4", filename=f"{clean_video_title}.mp4")

        threading.Thread(target=remove_file, args=(video_file,)).start()
        print("Hilo para eliminación del archivo creado")

        return response

    except Exception as e:
        print(f"Error durante la descarga o envío: {str(e)}")  # Log de error en el servidor
        raise HTTPException(status_code=400, detail=f"Error al descargar el video de TikTok: {str(e)}")

@app.post("/download/instagram/")
async def download_instagram_video(url: str = Form(...)):
    try:
        print(f"URL recibida para descarga de Instagram: {url}")

        # Ruta al archivo de cookies en el servidor
        cookies_file_path = f"{DOWNLOAD_PATH}/cookies.txt"

        # Verificar que el archivo de cookies exista y tenga contenido
        if not os.path.isfile(cookies_file_path):
            raise HTTPException(status_code=404, detail="El archivo de cookies no se encontró.")

        # Configuración para yt-dlp
        ydl_opts = {
            'format': 'best',
            'outtmpl': f'{DOWNLOAD_PATH}/%(title)s.%(ext)s',
            'geo_bypass': True,
            'cookiefile': cookies_file_path,  # Asegúrate de que este archivo es accesible
        }

        # Extraer información del video
        with yt_dlp.YoutubeDL({'noplaylist': True}) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            video_title = info_dict.get('title', 'Instagram Video')
            clean_video_title = clean_title(video_title)
            print(f"Título limpio del video: {clean_video_title}")

        # Actualizar la plantilla de salida con el título limpio
        ydl_opts['outtmpl'] = f'{DOWNLOAD_PATH}/{clean_video_title}.%(ext)s'

        # Descargar el video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            video_file = f"{DOWNLOAD_PATH}/{clean_video_title}.mp4"
            print(f"Video descargado como: {video_file}")

        # Verificar si el archivo fue creado
        if not os.path.isfile(video_file):
            print("Error: archivo no encontrado después de la descarga")
            raise HTTPException(status_code=404, detail="El archivo no se encontró después de la descarga.")

        print("Preparando respuesta para enviar el archivo al cliente")
        response = FileResponse(video_file, media_type="video/mp4", filename=f"{clean_video_title}.mp4")

        # Crear un hilo para eliminar el archivo después de enviarlo
        threading.Thread(target=remove_file, args=(video_file,)).start()
        print("Hilo para eliminación del archivo creado")

        return response

    except Exception as e:
        print(f"Error durante la descarga o envío: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error al descargar el video de Instagram: {str(e)}")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

