# app.py - YouTube Downloader PRO (Flask + yt-dlp)
import os
import uuid
import logging
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
import yt_dlp
from datetime import datetime
from threading import Thread
import time

# ===================== CONFIGURACIÓN =====================
app = Flask(__name__)
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB máx por request
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'mp3', 'webm', 'm4a'}

# Crear carpetas
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

# Logging profesional
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("downloader.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===================== YT-DLP CONFIGS =====================
COMMON_OPTS = {
    'quiet': False,
    'no_warnings': False,
    'merge_output_format': 'mp4',
    'outtmpl': os.path.join(app.config['DOWNLOAD_FOLDER'], '%(id)s_%(title).100s.%(ext)s'),
    'restrict_filenames': True,
    'geo_bypass': True,
    'nocheckcertificate': True,
}

VIDEO_OPTS = COMMON_OPTS.copy()
VIDEO_OPTS.update({
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'postprocessors': [{
        'key': 'FFmpegVideoConvertor',
        'preferedformat': 'mp4',
    }],
    'noplaylist': True,  # Por defecto: solo 1 video
})

AUDIO_OPTS = COMMON_OPTS.copy()
AUDIO_OPTS.update({
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'postprocessor_args': ['-ar', '44100'],
    'noplaylist': True,  # Por defecto: solo 1 audio
})

# ===================== UTILS =====================
def sanitize_filename(filename):
    return secure_filename(filename) or f"file_{uuid.uuid4().hex}"

def validate_youtube_url(url: str) -> bool:
    return any(domain in url for domain in ['youtube.com', 'youtu.be', 'music.youtube.com'])

def get_ydl_opts(download_type: str, is_playlist: bool = False):
    base_opts = VIDEO_OPTS if download_type == 'video' else AUDIO_OPTS
    opts = base_opts.copy()
    
    # CONTROL EXPLÍCITO DE PLAYLIST
    if is_playlist:
        opts.pop('noplaylist', None)      # Eliminar noplaylist
        opts['yes_playlist'] = True       # Forzar descarga de toda la playlist
    else:
        opts['noplaylist'] = True         # Solo un video
        opts.pop('yes_playlist', None)    # Asegurar no haya conflicto
    
    return opts

def async_download(url, download_type, is_playlist, task_id):
    success, message = False, "Error desconocido"
    try:
        opts = get_ydl_opts(download_type, is_playlist)
        opts['progress_hooks'] = [lambda d: progress_hook(d, task_id)]
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            count = len(info.get('entries', [info])) if 'entries' in info else 1
            logger.info(f"[{task_id}] Iniciando descarga: {count} elementos - {title}")

            ydl.download([url])
        
        success, message = True, f"{'Playlist' if is_playlist else 'Contenido'} descargado: {count} archivos"
        logger.info(f"[{task_id}] {message}")
    
    except Exception as e:
        message = f"Error: {str(e)}"
        logger.error(f"[{task_id}] {message}")
    
    finally:
        TASKS[task_id] = {
            'status': 'completed' if success else 'failed',
            'message': message,
            'finished_at': datetime.now().isoformat()
        }

def progress_hook(d, task_id):
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '0%').strip()
        speed = d.get('_speed_str', '?').strip()
        eta = d.get('_eta_str', '?').strip()
        TASKS[task_id]['progress'] = {
            'percent': percent,
            'speed': speed,
            'eta': eta
        }

# ===================== TASK MANAGER =====================
TASKS = {}

def start_download_task(url, download_type, is_playlist):
    task_id = uuid.uuid4().hex[:8]
    TASKS[task_id] = {
        'status': 'running',
        'progress': {'percent': '0%', 'speed': '0', 'eta': '?'},
        'started_at': datetime.now().isoformat(),
        'url': url,
        'type': download_type,
        'is_playlist': is_playlist
    }
    thread = Thread(target=async_download, args=(url, download_type, is_playlist, task_id))
    thread.daemon = True
    thread.start()
    return task_id

# ===================== RUTAS =====================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()
    download_type = data.get('type', 'video')
    is_playlist = data.get('is_playlist', False)

    if not url:
        return jsonify({'success': False, 'message': 'URL requerida'}), 400

    if not validate_youtube_url(url):
        return jsonify({'success': False, 'message': 'Solo URLs de YouTube permitidas'}), 400

    if download_type not in ['video', 'audio']:
        return jsonify({'success': False, 'message': 'Tipo inválido: video o audio'}), 400

    task_id = start_download_task(url, download_type, is_playlist)
    return jsonify({
        'success': True,
        'task_id': task_id,
        'message': 'Descarga iniciada en segundo plano'
    }), 202

@app.route('/status/<task_id>')
def get_status(task_id):
    task = TASKS.get(task_id)
    if not task:
        return jsonify({'success': False, 'message': 'Tarea no encontrada'}), 404
    return jsonify({'success': True, 'data': task})

@app.route('/api/info', methods=['POST'])
def get_video_info():
    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()

    if not url or not validate_youtube_url(url):
        return jsonify({'success': False, 'message': 'URL de YouTube inválida'}), 400

    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
            info = ydl.extract_info(url, download=False)

            entries = info.get('entries')
            is_playlist = entries is not None
            videos = list(entries) if is_playlist else [info]

            response = {
                'title': info.get('title', 'Sin título'),
                'uploader': info.get('uploader', 'Desconocido'),
                'duration': info.get('duration'),
                'view_count': info.get('view_count', 0),
                'thumbnail': info.get('thumbnail'),
                'is_playlist': is_playlist,
                'video_count': len(videos) if is_playlist else 1,
                'videos': [
                    {
                        'title': v.get('title'),
                        'duration': v.get('duration'),
                        'id': v.get('id')
                    } for v in videos[:10]
                ] if is_playlist else None
            }
            return jsonify({'success': True, 'data': response})

    except Exception as e:
        logger.error(f"Error obteniendo info: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/files')
def list_files():
    files = []
    for f in os.listdir(app.config['DOWNLOAD_FOLDER']):
        path = os.path.join(app.config['DOWNLOAD_FOLDER'], f)
        if os.path.isfile(path):
            files.append({
                'name': f,
                'size': os.path.getsize(path),
                'mtime': datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
            })
    files.sort(key=lambda x: x['mtime'], reverse=True)
    return jsonify({'success': True, 'files': files})

@app.route('/download_file/<filename>')
def download_file(filename):
    safe_filename = secure_filename(filename)
    if not safe_filename:
        return "Archivo no válido", 400
    try:
        return send_from_directory(app.config['DOWNLOAD_FOLDER'], safe_filename, as_attachment=True)
    except FileNotFoundError:
        return "Archivo no encontrado", 404

# ===================== LIMPIEZA AUTOMÁTICA =====================
def cleanup_old_files(days=7):
    cutoff = time.time() - (days * 86400)
    for f in os.listdir(app.config['DOWNLOAD_FOLDER']):
        path = os.path.join(app.config['DOWNLOAD_FOLDER'], f)
        if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
            os.remove(path)
            logger.info(f"Archivo antiguo eliminado: {f}")

cleanup_old_files()

# ===================== INICIO =====================
if __name__ == '__main__':
    logger.info("YouTube Downloader PRO iniciado en http://localhost:5002")
    app.run(host='0.0.0.0', port=5002, debug=False, threaded=True)
