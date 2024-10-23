# YouTube Video Downloader

Este es un proyecto para descargar videos de YouTube a través de una aplicación web, utilizando **FastAPI** y **yt-dlp**. Los usuarios pueden proporcionar una URL de YouTube, seleccionar el formato de video que desean descargar, y recibir el archivo en su dispositivo. Los videos se descargan temporalmente en el servidor y luego se eliminan automáticamente tras la descarga.

## Características

- Descarga de videos desde YouTube en diferentes formatos.
- Uso de `yt-dlp` para la extracción y descarga de videos.
- FastAPI como backend para gestionar las solicitudes.
- Elimina automáticamente los videos del servidor después de la descarga.
- Soporte para múltiples formatos de video.
  
## Requisitos

Asegúrate de tener instaladas las siguientes herramientas en tu sistema:

- Python 3.7 o superior
- FastAPI
- yt-dlp
- Uvicorn

## Instalación

1. Clona este repositorio en tu máquina local:

   ```bash
   git clone https://github.com/tu-usuario/youtube-video-downloader.git
   cd youtube-video-downloader
