#!/usr/bin/env python3
"""
YTPlay - Universal Video Embed Player with Dynamic Menu & Admin Edit
play.pratamadigital.com
Flask app on port 2205
With automatic HEVC to H.264 conversion & Local Video Thumbnail Extraction
"""

from flask import Flask, render_template, request, jsonify, redirect, send_from_directory, url_for
from flask_httpauth import HTTPBasicAuth
import sqlite3
import string
import random
import re
import json
import os
import subprocess
import threading
from urllib.parse import urlparse, parse_qs, quote
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # Max upload 1GB
auth = HTTPBasicAuth()

DB_PATH = '/home/ytplay/ytplay.db'
CONFIG_PATH = '/home/ytplay/config.json'
VIDEO_DIR = '/home/ytplay/video'
DEFAULT_THUMB = 'https://via.placeholder.com/320x180/1e293b/475569?text=No+Thumb'
ALLOWED_EXTENSIONS = {'mp4', 'webm', 'ogg', 'ogv', 'mp3', 'wav', 'oga', 'aac', 'm4a', 'm4v', 'mkv', 'mov', 'flv', 'avi', 'wmv'}

# ─── Config & Auth ─────────────────────────────────────────
def load_config():
    """Load or create config file dengan default credentials"""
    if not os.path.exists(CONFIG_PATH):
        default_cfg = {
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "767676176"
        }
        try:
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            with open(CONFIG_PATH, 'w') as f:
                json.dump(default_cfg, f, indent=4)
            print(f"[CONFIG] Created new config at {CONFIG_PATH}")
        except IOError as e:
            print(f"[ERROR] Failed to create config: {e}")
            return default_cfg
        return default_cfg

    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[ERROR] Failed to load config: {e}")
        return {
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "767676176"
        }

config = load_config()

@auth.verify_password
def verify_password(username, password):
    """Verify admin credentials"""
    # Reload config untuk setiap verifikasi (untuk handle password change)
    global config
    config = load_config()
    
    if username == config.get('ADMIN_USERNAME') and password == config.get('ADMIN_PASSWORD'):
        return username
    return None

# ─── Database ───────────────────────────────────────────────
def get_db():
    """Get database connection with WAL mode for better concurrency"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    """Initialize database and tables"""
    conn = get_db()

    # Create main plays table
    conn.execute('''CREATE TABLE IF NOT EXISTS plays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        original_url TEXT NOT NULL,
        unique_code TEXT NOT NULL UNIQUE,
        embed_url TEXT,
        site_type TEXT DEFAULT 'unknown',
        title TEXT DEFAULT 'Unknown Title',
        thumbnail_url TEXT DEFAULT '',
        play_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_played TIMESTAMP,
        is_local INTEGER DEFAULT 0,
        conversion_status TEXT DEFAULT 'pending',
        original_filename TEXT DEFAULT ''
    )''')

    # Create navigation links table
    conn.execute('''CREATE TABLE IF NOT EXISTS nav_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        url TEXT NOT NULL,
        order_index INTEGER DEFAULT 0
    )''')

    # Check and add missing columns
    cursor = conn.execute("PRAGMA table_info(plays)")
    columns = [col[1] for col in cursor.fetchall()]

    column_definitions = {
        'title': "TEXT DEFAULT 'Unknown Title'",
        'thumbnail_url': "TEXT DEFAULT ''",
        'play_count': "INTEGER DEFAULT 0",
        'last_played': "TIMESTAMP",
        'is_local': "INTEGER DEFAULT 0",
        'conversion_status': "TEXT DEFAULT 'pending'",
        'original_filename': "TEXT DEFAULT ''"
    }

    for col_name, col_def in column_definitions.items():
        if col_name not in columns:
            try:
                conn.execute(f"ALTER TABLE plays ADD COLUMN {col_name} {col_def}")
                print(f"[DB] Added column: {col_name}")
            except sqlite3.OperationalError as e:
                print(f"[DB] Column {col_name} already exists or error: {e}")

    # Initialize default navigation links
    if conn.execute('SELECT COUNT(*) FROM nav_links').fetchone()[0] == 0:
        try:
            conn.executemany('INSERT INTO nav_links (title, url, order_index) VALUES (?, ?, ?)', [
                ('Berita Wonosobo', 'https://wonosobonews.web.id', 1),
                ('Pratama Digital', 'https://pratamadigital.com', 2),
                ('Panti Asuhan Yani Fazzahra', 'https://yanifazzahra.or.id', 3)
            ])
            print("[DB] Initialized default nav links")
        except sqlite3.IntegrityError:
            print("[DB] Nav links already initialized")

    conn.commit()
    conn.close()

    # Ensure video upload directory exists
    try:
        os.makedirs(VIDEO_DIR, exist_ok=True)
    except OSError as e:
        print(f"[ERROR] Failed to create video directory: {e}")

def generate_code(length=8):
    """Generate unique code for video playback"""
    chars = string.ascii_lowercase + string.digits
    max_attempts = 10

    for attempt in range(max_attempts):
        code = ''.join(random.choices(chars, k=length))
        try:
            conn = get_db()
            exists = conn.execute('SELECT 1 FROM plays WHERE unique_code=?', (code,)).fetchone()
            conn.close()
            if not exists:
                return code
        except sqlite3.Error as e:
            print(f"[ERROR] Database error in generate_code: {e}")
            continue

    # Fallback: append timestamp if all attempts failed
    return code + str(int(datetime.now().timestamp()) % 10000)

def get_nav_links():
    """Get all navigation links ordered by index"""
    try:
        conn = get_db()
        links = conn.execute('SELECT * FROM nav_links ORDER BY order_index ASC, id ASC').fetchall()
        conn.close()
        return links
    except sqlite3.Error as e:
        print(f"[ERROR] Failed to get nav links: {e}")
        return []

# ─── FFmpeg Video Codec Detection & Conversion ──────────────
def detect_video_codec(file_path):
    """
    Detect video codec using ffprobe
    Returns: 'hevc', 'h264', or 'unknown'
    """
    if not os.path.exists(file_path):
        print(f"[CODEC] File not found: {file_path}")
        return 'unknown'

    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
             '-show_entries', 'stream=codec_name', '-of', 'csv=p=0', file_path],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            print(f"[CODEC] ffprobe error: {result.stderr}")
            return 'unknown'

        codec = result.stdout.strip().lower()
        if 'hevc' in codec or 'h265' in codec:
            return 'hevc'
        elif 'h264' in codec or 'avc' in codec:
            return 'h264'

        return codec if codec else 'unknown'

    except subprocess.TimeoutExpired:
        print(f"[CODEC] Timeout detecting codec for: {file_path}")
        return 'unknown'
    except FileNotFoundError:
        print("[CODEC] ffprobe not found - install ffmpeg")
        return 'unknown'
    except Exception as e:
        print(f"[CODEC] Error detecting codec: {e}")
        return 'unknown'

def convert_hevc_to_h264(input_path, output_path, video_id):
    """
    Convert HEVC video to H.264 using ffmpeg
    Updates database conversion_status when done
    """
    if not os.path.exists(input_path):
        print(f"[CONVERSION] Input file not found: {input_path}")
        conn = get_db()
        conn.execute('UPDATE plays SET conversion_status=? WHERE id=?', ('failed', video_id))
        conn.commit()
        conn.close()
        return

    try:
        print(f"[CONVERSION] Starting conversion: {input_path} -> {output_path}")

        # FFmpeg command: convert HEVC to H.264
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-c:v', 'libx264',        # Video codec H.264
            '-preset', 'medium',       # Speed/quality balance (fast, medium, slow)
            '-crf', '23',              # Quality (0-51, lower=better, 23=default)
            '-c:a', 'aac',             # Audio codec AAC
            '-b:a', '128k',            # Audio bitrate
            '-y',                      # Overwrite output file
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)

        if result.returncode == 0:
            print(f"[CONVERSION] Success: {output_path}")

            # Remove original file
            try:
                if os.path.exists(input_path):
                    os.remove(input_path)
                    print(f"[CONVERSION] Removed original: {input_path}")
            except OSError as e:
                print(f"[CONVERSION] Error removing original: {e}")

            # Update database
            try:
                conn = get_db()
                rel_path = os.path.relpath(output_path, VIDEO_DIR)
                new_url = f'/video/{rel_path}'
                conn.execute('UPDATE plays SET conversion_status=?, embed_url=?, original_url=? WHERE id=?',
                            ('completed', new_url, new_url, video_id))
                conn.commit()
                conn.close()
                print(f"[CONVERSION] Database updated for video_id={video_id}")
            except sqlite3.Error as e:
                print(f"[CONVERSION] Database error: {e}")
        else:
            print(f"[CONVERSION] Failed: {result.stderr}")
            conn = get_db()
            conn.execute('UPDATE plays SET conversion_status=? WHERE id=?', ('failed', video_id))
            conn.commit()
            conn.close()

    except subprocess.TimeoutExpired:
        print(f"[CONVERSION] Timeout converting {input_path}")
        conn = get_db()
        conn.execute('UPDATE plays SET conversion_status=? WHERE id=?', ('timeout', video_id))
        conn.commit()
        conn.close()
    except FileNotFoundError:
        print("[CONVERSION] ffmpeg not found - install ffmpeg")
        conn = get_db()
        conn.execute('UPDATE plays SET conversion_status=? WHERE id=?', ('error', video_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[CONVERSION] Exception: {e}")
        conn = get_db()
        conn.execute('UPDATE plays SET conversion_status=? WHERE id=?', ('error', video_id))
        conn.commit()
        conn.close()

def process_video_conversion(input_path, output_path, video_id):
    """
    Run conversion in background thread
    """
    thread = threading.Thread(
        target=convert_hevc_to_h264,
        args=(input_path, output_path, video_id),
        daemon=True
    )
    thread.start()
    print(f"[CONVERSION] Background thread started for video_id={video_id}")

# ─── FFmpeg Thumbnail Extraction ────────────────────────────
def extract_thumbnail(video_path, output_thumb_path, timestamp='00:00:01'):
    """
    Extract thumbnail from video at specific timestamp
    Returns: path to thumbnail if successful, None otherwise
    
    Ekstrak frame dari video pada timestamp tertentu untuk dijadikan thumbnail
    Ukuran default: 320x180 px
    """
    if not os.path.exists(video_path):
        print(f"[THUMB] Video file not found: {video_path}")
        return None

    try:
        print(f"[THUMB] Extracting thumbnail from {video_path}")

        # FFmpeg command to extract thumbnail
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-ss', timestamp,           # Seek to timestamp
            '-vframes', '1',            # Extract 1 frame
            '-vf', 'scale=320:180',     # Resize to 320x180
            '-y',                       # Overwrite output
            output_thumb_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and os.path.exists(output_thumb_path):
            print(f"[THUMB] Success: {output_thumb_path}")
            return output_thumb_path
        else:
            print(f"[THUMB] Failed: {result.stderr}")
            return None

    except subprocess.TimeoutExpired:
        print(f"[THUMB] Timeout extracting thumbnail from {video_path}")
        return None
    except FileNotFoundError:
        print("[THUMB] ffmpeg not found - install ffmpeg")
        return None
    except Exception as e:
        print(f"[THUMB] Error extracting thumbnail: {e}")
        return None

def process_thumbnail_extraction(video_path, thumb_path, video_id):
    """
    Run thumbnail extraction in background thread
    """
    thread = threading.Thread(
        target=lambda: extract_and_update_thumbnail(video_path, thumb_path, video_id),
        daemon=True
    )
    thread.start()
    print(f"[THUMB] Background thread started for video_id={video_id}")

def extract_and_update_thumbnail(video_path, thumb_path, video_id):
    """
    Extract thumbnail and update database
    """
    result = extract_thumbnail(video_path, thumb_path)
    
    if result:
        try:
            thumb_relative = os.path.relpath(result, VIDEO_DIR)
            thumb_url = f'/video/{thumb_relative}'
            
            conn = get_db()
            conn.execute('UPDATE plays SET thumbnail_url=? WHERE id=?', (thumb_url, video_id))
            conn.commit()
            conn.close()
            print(f"[THUMB] Database updated with thumbnail for video_id={video_id}")
        except sqlite3.Error as e:
            print(f"[THUMB] Database error: {e}")
    else:
        print(f"[THUMB] Failed to extract thumbnail for video_id={video_id}")

# ─── yt-dlp Fetcher ─────────────────────────────────────────
def fetch_video_info(url, site_type):
    """Fetch video title and thumbnail from various sources"""
    title = 'Unknown Title'
    thumbnail = DEFAULT_THUMB

    # Try to extract YouTube thumbnail
    if 'youtube' in site_type:
        try:
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            path = parsed.path
            domain = parsed.netloc.lower()
            vid = None

            if 'youtu.be' in domain:
                vid = path.strip('/').split('/')[0].split('?')[0]
            elif '/embed/' in path:
                vid = path.split('/embed/')[-1].split('?')[0]
            elif '/shorts/' in path:
                vid = path.split('/shorts/')[-1].split('?')[0]
            elif '/live/' in path:
                vid = path.split('/live/')[-1].split('?')[0]
            elif '/watch' in path:
                vid = qs.get('v', [None])[0]

            if vid:
                thumbnail = f'https://img.youtube.com/vi/{vid}/hqdefault.jpg'
        except (ValueError, IndexError, KeyError):
            pass

    # Try to fetch info with yt-dlp
    try:
        import yt_dlp
        ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
        if site_type == 'youtube_playlist':
            ydl_opts['extract_flat'] = 'in_playlist'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                title = info.get('title') or 'Unknown Title'

                if site_type == 'youtube_playlist':
                    playlist_count = info.get('playlist_count', '?')
                    title = f"{title} (Playlist: {playlist_count} videos)"

                if info.get('thumbnails') and len(info['thumbnails']) > 0:
                    thumb_from_ytdlp = info['thumbnails'][-1].get('url', '')
                    if thumb_from_ytdlp:
                        thumbnail = thumb_from_ytdlp
                elif info.get('thumbnail'):
                    thumbnail = info.get('thumbnail', DEFAULT_THUMB)
    except ImportError:
        print("[INFO] yt-dlp not installed, using basic title extraction")
    except Exception as e:
        print(f"[INFO] Failed to fetch info with yt-dlp: {e}")

    return {'title': title, 'thumbnail': thumbnail}

# ─── URL Parser ─────────────────────────────────────────────
def parse_video_url(url):
    """Parse video URL and determine site type and embed URL"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path
        qs = parse_qs(parsed.query)

        # Remove www, m, gaming prefixes
        for prefix in ('www.', 'm.', 'gaming.'):
            if domain.startswith(prefix):
                domain = domain[len(prefix):]
    except (ValueError, AttributeError):
        return url, 'unknown'

    # YouTube
    if 'youtube.com' in domain or 'youtu.be' in domain:
        list_id = qs.get('list', [None])[0]
        if list_id:
            return f'https://www.youtube.com/embed/videoseries?list={list_id}&autoplay=1', 'youtube_playlist'

        vid = None
        if 'youtu.be' in domain:
            vid = path.strip('/').split('/')[0].split('?')[0]
        elif '/embed/' in path:
            vid = path.split('/embed/')[-1].split('?')[0]
        elif '/shorts/' in path:
            vid = path.split('/shorts/')[-1].split('?')[0]
        elif '/live/' in path:
            vid = path.split('/live/')[-1].split('?')[0]
        elif '/watch' in path:
            vid = qs.get('v', [None])[0]

        if vid:
            return f'https://www.youtube.com/embed/{vid}?autoplay=1&rel=0&modestbranding=1', 'youtube'

    # Vimeo
    elif 'vimeo.com' in domain and 'player.vimeo.com' not in domain:
        parts = [p for p in path.strip('/').split('/') if p.isdigit()]
        if parts:
            return f'https://player.vimeo.com/video/{parts[-1]}?autoplay=1', 'vimeo'

    # Dailymotion
    elif 'dailymotion.com' in domain:
        m = re.search(r'/video/([a-zA-Z0-9]+)', path)
        if m:
            return f'https://www.dailymotion.com/embed/video/{m.group(1)}?autoplay=1', 'dailymotion'

    # Twitch
    elif 'twitch.tv' in domain:
        parts = [p for p in path.strip('/').split('/') if p]
        if len(parts) >= 2 and parts[0] == 'videos':
            return f'https://player.twitch.tv/?video={parts[1]}&parent=play.pratamadigital.com', 'twitch'
        elif parts and parts[0] not in ('', 'directory', 'downloads'):
            return f'https://player.twitch.tv/?channel={parts[0]}&parent=play.pratamadigital.com', 'twitch'

    # TikTok
    elif 'tiktok.com' in domain:
        m = re.search(r'/video/(\d+)', path)
        if m:
            return f'https://www.tiktok.com/embed/v2/{m.group(1)}', 'tiktok'

    # Facebook
    elif 'facebook.com' in domain or 'fb.watch' in domain:
        return f'https://www.facebook.com/plugins/video.php?href={quote(url, safe="")}&autoplay=true', 'facebook'

    # OK.ru
    elif 'ok.ru' in domain:
        m = re.search(r'/video/(\d+)', path)
        if m:
            return f'https://ok.ru/videoembed/{m.group(1)}', 'okru'

    # Bilibili
    elif 'bilibili.com' in domain:
        m = re.search(r'/(BV[a-zA-Z0-9]+)', path)
        if m:
            return f'https://player.bilibili.com/player.html?bvid={m.group(1)}&autoplay=1', 'bilibili'

    # Streamable
    elif 'streamable.com' in domain:
        vid = path.strip('/').split('/')[-1]
        if vid:
            return f'https://streamable.com/e/{vid}?autoplay=1', 'streamable'

    # Google Drive
    elif 'drive.google.com' in domain:
        m = re.search(r'/d/([a-zA-Z0-9_-]+)', path)
        if m:
            return f'https://drive.google.com/file/d/{m.group(1)}/preview', 'gdrive'

    # Check file extensions for direct video/audio
    ext = path.lower().rsplit('.', 1)[-1] if '.' in path.rsplit('/', 1)[-1] else ''
    if ext in {'mp4', 'webm', 'ogg', 'ogv', 'mov', 'm4v'}:
        return url, 'video'
    elif ext in {'mp3', 'wav', 'oga', 'aac', 'flac', 'm4a'}:
        return url, 'audio'

    return url, 'unknown'

def is_url(text):
    """Check if text is a URL"""
    return text.startswith(('http://', 'https://', 'www.'))

# ─── Routes ─────────────────────────────────────────────────
@app.route('/')
def index():
    """Gallery page"""
    return render_template('gallery.html', nav_links=get_nav_links())

@app.route('/p/<code>')
def play_page(code):
    """Play page for a specific video code"""
    try:
        conn = get_db()
        row = conn.execute('SELECT * FROM plays WHERE unique_code=?', (code,)).fetchone()

        if not row:
            conn.close()
            return redirect('/')

        now_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_count = row['play_count'] + 1
        conn.execute('UPDATE plays SET play_count=?, last_played=? WHERE id=?', (new_count, now_time, row['id']))
        conn.commit()

        row = conn.execute('SELECT * FROM plays WHERE unique_code=?', (code,)).fetchone()
        conn.close()

        return render_template('player.html', play_data=dict(row), nav_links=get_nav_links())

    except sqlite3.Error as e:
        print(f"[ERROR] Database error in play_page: {e}")
        return redirect('/')

@app.route('/video/<path:filename>')
def serve_video(filename):
    """Serve video files from upload directory"""
    try:
        return send_from_directory(VIDEO_DIR, filename)
    except Exception as e:
        print(f"[ERROR] Failed to serve video {filename}: {e}")
        return "File not found", 404

@app.route('/api/play', methods=['POST'])
def api_play():
    """API endpoint to create/get play entry"""
    url = request.form.get('url', '').strip()

    if not url:
        return jsonify({'error': 'URL wajib diisi'}), 400

    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    embed_url, site_type = parse_video_url(url)
    now_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        conn = get_db()
        existing = conn.execute('SELECT * FROM plays WHERE original_url=? AND is_local=0', (url,)).fetchone()

        if existing:
            code = existing['unique_code']
            title = existing['title']
            thumbnail = existing['thumbnail_url'] or DEFAULT_THUMB
            new_count = existing['play_count'] + 1
            conn.execute('UPDATE plays SET play_count=?, last_played=? WHERE id=?', (new_count, now_time, existing['id']))
            conn.commit()
        else:
            info = fetch_video_info(url, site_type)
            title, thumbnail = info['title'], info['thumbnail']
            code = generate_code()
            conn.execute('INSERT INTO plays (original_url, unique_code, embed_url, site_type, title, thumbnail_url, play_count, last_played, is_local, conversion_status) VALUES (?,?,?,?,?,?,?,?,0,"completed")',
                         (url, code, embed_url, site_type, title, thumbnail, 1, now_time))
            conn.commit()

        conn.close()

        return jsonify({
            'unique_code': code,
            'embed_url': embed_url,
            'site_type': site_type,
            'original_url': url,
            'title': title,
            'thumbnail_url': thumbnail,
            'share_url': f'/p/{code}'
        })

    except sqlite3.Error as e:
        print(f"[ERROR] Database error in api_play: {e}")
        return jsonify({'error': 'Database error'}), 500
    except Exception as e:
        print(f"[ERROR] Error in api_play: {e}")
        return jsonify({'error': 'Server error'}), 500

@app.route('/api/play-by-code/<code>')
def api_play_by_code(code):
    """Get play data by code and update play count"""
    try:
        conn = get_db()
        row = conn.execute('SELECT * FROM plays WHERE unique_code=?', (code,)).fetchone()

        if not row:
            conn.close()
            return jsonify({'error': 'Not found'}), 404

        now_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_count = row['play_count'] + 1
        conn.execute('UPDATE plays SET play_count=?, last_played=? WHERE id=?', (new_count, now_time, row['id']))
        conn.commit()
        conn.close()

        d = dict(row)
        d['play_count'] = new_count
        d['last_played'] = now_time
        d['share_url'] = f'/p/{code}'
        if not d['thumbnail_url']:
            d['thumbnail_url'] = DEFAULT_THUMB

        return jsonify(d)

    except sqlite3.Error as e:
        print(f"[ERROR] Database error in api_play_by_code: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/history')
def api_history():
    """Get play history with pagination and search"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    per_page = request.args.get('per_page', 10, type=int)
    offset = (page - 1) * per_page

    try:
        conn = get_db()

        if search:
            like_search = f"%{search}%"
            total = conn.execute('SELECT COUNT(*) FROM plays WHERE title LIKE ? OR original_url LIKE ?', (like_search, like_search)).fetchone()[0]
            rows = conn.execute('SELECT * FROM plays WHERE title LIKE ? OR original_url LIKE ? ORDER BY last_played DESC, id DESC LIMIT ? OFFSET ?', (like_search, like_search, per_page, offset)).fetchall()
        else:
            total = conn.execute('SELECT COUNT(*) FROM plays').fetchone()[0]
            rows = conn.execute('SELECT * FROM plays ORDER BY last_played DESC, id DESC LIMIT ? OFFSET ?', (per_page, offset)).fetchall()

        conn.close()

        total_pages = max(1, (total + per_page - 1) // per_page)
        return jsonify({
            'plays': [dict(r) for r in rows],
            'page': page,
            'total_pages': total_pages,
            'total': total
        })

    except sqlite3.Error as e:
        print(f"[ERROR] Database error in api_history: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/related/<code>')
def api_related(code):
    """Get related videos based on title keywords"""
    limit = request.args.get('limit', 10, type=int)

    try:
        conn = get_db()
        row = conn.execute('SELECT title, id FROM plays WHERE unique_code=?', (code,)).fetchone()

        if not row or not row['title'] or row['title'] == 'Unknown Title':
            conn.close()
            return jsonify({'related': []})

        title = row['title']

        # Extract keywords (simple approach: words longer than 3 chars)
        stopwords = {'that', 'this', 'with', 'from', 'have', 'will', 'your', 'they', 'been', 'said', 'each', 'which', 'their', 'there', 'about', 'video', 'official'}
        keywords = [w.lower() for w in re.findall(r'\b\w{4,}\b', title) if w.lower() not in stopwords]

        if not keywords:
            conn.close()
            return jsonify({'related': []})

        conditions = []
        params = []
        for kw in keywords[:5]:  # Limit to 5 keywords for performance
            conditions.append("title LIKE ?")
            params.append(f"%{kw}%")

        query = f"SELECT * FROM plays WHERE ({' OR '.join(conditions)}) AND id != ? ORDER BY play_count DESC, last_played DESC LIMIT ?"
        params.extend([row['id'], limit])

        rows = conn.execute(query, params).fetchall()
        conn.close()

        return jsonify({'related': [dict(r) for r in rows]})

    except sqlite3.Error as e:
        print(f"[ERROR] Database error in api_related: {e}")
        return jsonify({'error': 'Database error'}), 500

# ─── Admin Routes (Protected) ──────────────────────────────
@app.route('/admin')
@auth.login_required
def admin():
    """Admin panel"""
    return render_template('admin.html', nav_links=get_nav_links())

@app.route('/api/admin/history')
@auth.login_required
def admin_history():
    """Admin: Get all plays history"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    per_page = 20
    offset = (page - 1) * per_page

    try:
        conn = get_db()

        if search:
            like_search = f"%{search}%"
            total = conn.execute('SELECT COUNT(*) FROM plays WHERE title LIKE ? OR original_url LIKE ?', (like_search, like_search)).fetchone()[0]
            rows = conn.execute('SELECT * FROM plays WHERE title LIKE ? OR original_url LIKE ? ORDER BY id DESC LIMIT ? OFFSET ?', (like_search, like_search, per_page, offset)).fetchall()
        else:
            total = conn.execute('SELECT COUNT(*) FROM plays').fetchone()[0]
            rows = conn.execute('SELECT * FROM plays ORDER BY id DESC LIMIT ? OFFSET ?', (per_page, offset)).fetchall()

        conn.close()

        total_pages = max(1, (total + per_page - 1) // per_page)
        return jsonify({
            'plays': [dict(r) for r in rows],
            'page': page,
            'total_pages': total_pages,
            'total': total
        })

    except sqlite3.Error as e:
        print(f"[ERROR] Database error in admin_history: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/admin/stats')
@auth.login_required
def admin_stats():
    """Admin: Get statistics"""
    try:
        conn = get_db()
        total = conn.execute('SELECT COUNT(*) FROM plays').fetchone()[0]
        local = conn.execute('SELECT COUNT(*) FROM plays WHERE is_local=1').fetchone()[0]
        embed = total - local
        total_plays = conn.execute('SELECT SUM(play_count) FROM plays').fetchone()[0] or 0
        conn.close()

        return jsonify({
            'total': total,
            'local': local,
            'embed': embed,
            'total_plays': total_plays
        })

    except sqlite3.Error as e:
        print(f"[ERROR] Database error in admin_stats: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/admin/popular-videos')
@auth.login_required
def admin_popular_videos():
    """Admin: Get popular videos by time period (daily, weekly, monthly)"""
    try:
        conn = get_db()
        limit = 10

        # Daily (last 24 hours)
        daily = conn.execute(
            '''SELECT id, unique_code, title, thumbnail_url, play_count, site_type,
                      last_played FROM plays
               WHERE last_played >= datetime('now', '-1 day')
               ORDER BY play_count DESC
               LIMIT ?''',
            (limit,)
        ).fetchall()

        # Weekly (last 7 days)
        weekly = conn.execute(
            '''SELECT id, unique_code, title, thumbnail_url, play_count, site_type,
                      last_played FROM plays
               WHERE last_played >= datetime('now', '-7 days')
               ORDER BY play_count DESC
               LIMIT ?''',
            (limit,)
        ).fetchall()

        # Monthly (last 30 days)
        monthly = conn.execute(
            '''SELECT id, unique_code, title, thumbnail_url, play_count, site_type,
                      last_played FROM plays
               WHERE last_played >= datetime('now', '-30 days')
               ORDER BY play_count DESC
               LIMIT ?''',
            (limit,)
        ).fetchall()

        conn.close()

        return jsonify({
            'daily': [dict(r) for r in daily],
            'weekly': [dict(r) for r in weekly],
            'monthly': [dict(r) for r in monthly]
        })

    except sqlite3.Error as e:
        print(f"[ERROR] Database error in admin_popular_videos: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/admin/delete', methods=['POST'])
@auth.login_required
def admin_delete():
    """Admin: Delete videos"""
    ids = request.form.getlist('ids[]')

    if not ids:
        return jsonify({'error': 'No IDs provided'}), 400

    try:
        conn = get_db()
        placeholders = ','.join(['?'] * len(ids))

        # Delete associated local files
        rows = conn.execute(f'SELECT original_url, embed_url FROM plays WHERE id IN ({placeholders}) AND is_local=1', ids).fetchall()

        for r in rows:
            for url_field in [r['original_url'], r['embed_url']]:
                if url_field and url_field.startswith('/video/'):
                    filepath = os.path.join(VIDEO_DIR, url_field.replace('/video/', ''))
                    if os.path.exists(filepath):
                        try:
                            os.remove(filepath)
                            print(f"[ADMIN] Deleted file: {filepath}")
                        except OSError as e:
                            print(f"[ADMIN] Error deleting file {filepath}: {e}")

        conn.execute(f'DELETE FROM plays WHERE id IN ({placeholders})', ids)
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'deleted': len(ids)})

    except sqlite3.Error as e:
        print(f"[ERROR] Database error in admin_delete: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/admin/reset', methods=['POST'])
@auth.login_required
def admin_reset():
    """Admin: Reset all data"""
    try:
        conn = get_db()

        # Delete local files
        local_rows = conn.execute('SELECT embed_url FROM plays WHERE is_local=1').fetchall()
        for r in local_rows:
            if r['embed_url'] and r['embed_url'].startswith('/video/'):
                filepath = os.path.join(VIDEO_DIR, r['embed_url'].replace('/video/', ''))
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except OSError as e:
                        print(f"[ADMIN] Error deleting file {filepath}: {e}")

        conn.execute('DELETE FROM plays')
        conn.commit()
        conn.close()

        print("[ADMIN] Database reset")
        return jsonify({'success': True})

    except sqlite3.Error as e:
        print(f"[ERROR] Database error in admin_reset: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/admin/edit_title/<int:video_id>', methods=['POST'])
@auth.login_required
def admin_edit_title(video_id):
    """Admin: Edit video title"""
    new_title = request.form.get('title', '').strip()

    if not new_title:
        return jsonify({'error': 'Title cannot be empty'}), 400

    try:
        conn = get_db()
        conn.execute('UPDATE plays SET title=? WHERE id=?', (new_title, video_id))
        conn.commit()
        conn.close()

        return jsonify({'success': True})

    except sqlite3.Error as e:
        print(f"[ERROR] Database error in admin_edit_title: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/admin/upload', methods=['POST'])
@auth.login_required
def admin_upload():
    """Admin: Upload video file with automatic thumbnail extraction"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    title = request.form.get('title', '').strip()
    if not title:
        title = os.path.splitext(file.filename)[0].replace('_', ' ').replace('-', ' ').title()

    filename = file.filename
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({'error': f'File type .{ext} not allowed. Supported: {", ".join(sorted(ALLOWED_EXTENSIONS))}'}), 400

    try:
        # Create date-based folder
        now = datetime.now()
        date_folder = now.strftime('%Y/%m/%d')
        full_dir = os.path.join(VIDEO_DIR, date_folder)
        os.makedirs(full_dir, exist_ok=True)

        # Generate unique filename to avoid conflicts
        safe_base = re.sub(r'[^\w\-.]', '_', os.path.splitext(filename)[0])
        unique_suffix = generate_code(4)
        final_filename = f"{safe_base}_{unique_suffix}.{ext}"
        final_path = os.path.join(full_dir, final_filename)

        # Save file
        file.save(final_path)
        print(f"[UPLOAD] File saved: {final_path}")

        # Determine site type and check for HEVC codec
        if ext in {'mp3', 'wav', 'oga', 'aac', 'flac', 'm4a'}:
            site_type = 'audio'
            conversion_status = 'completed'
            output_path = final_path
            detected_codec = None
            thumbnail_url = DEFAULT_THUMB
        else:
            site_type = 'local_video'

            # Detect codec
            detected_codec = detect_video_codec(final_path)
            print(f"[UPLOAD] Detected codec: {detected_codec} for {final_filename}")

            if detected_codec == 'hevc':
                conversion_status = 'processing'
                # Create H.264 version with .mp4 extension
                h264_filename = f"{safe_base}_{unique_suffix}_h264.mp4"
                output_path = os.path.join(full_dir, h264_filename)
            else:
                conversion_status = 'completed'
                output_path = final_path

            # Extract thumbnail for local video
            thumb_filename = f"{safe_base}_{unique_suffix}_thumb.jpg"
            thumb_path = os.path.join(full_dir, thumb_filename)
            thumbnail_url = DEFAULT_THUMB  # Default jika extraction gagal
            
            # Thumbnail akan di-extract di background

        db_path = f"/video/{date_folder}/{os.path.basename(output_path)}"
        embed_url = db_path
        original_url = db_path
        code = generate_code()
        now_time = now.strftime('%Y-%m-%d %H:%M:%S')

        conn = get_db()
        cursor = conn.execute('INSERT INTO plays (original_url, unique_code, embed_url, site_type, title, thumbnail_url, play_count, last_played, is_local, conversion_status, original_filename) VALUES (?,?,?,?,?,?,?,?,1,?,?)',
                 (original_url, code, embed_url, site_type, title, thumbnail_url, 0, now_time, conversion_status, filename))
        video_id = cursor.lastrowid
        conn.commit()
        conn.close()

        print(f"[UPLOAD] Video saved with code: {code}, conversion_status: {conversion_status}")

        # If HEVC detected, start conversion in background
        if detected_codec == 'hevc':
            print(f"[UPLOAD] Starting HEVC->H.264 conversion for video_id={video_id}")
            process_video_conversion(final_path, output_path, video_id)

        # Extract thumbnail for video files (non-audio)
        if site_type == 'local_video':
            print(f"[UPLOAD] Starting thumbnail extraction for video_id={video_id}")
            process_thumbnail_extraction(final_path, thumb_path, video_id)

        return jsonify({
            'success': True,
            'title': title,
            'code': code,
            'share_url': f'/p/{code}',
            'conversion_status': conversion_status
        })

    except OSError as e:
        print(f"[ERROR] File system error in admin_upload: {e}")
        return jsonify({'error': 'Failed to save file'}), 500
    except sqlite3.Error as e:
        print(f"[ERROR] Database error in admin_upload: {e}")
        return jsonify({'error': 'Database error'}), 500
    except Exception as e:
        print(f"[ERROR] Unexpected error in admin_upload: {e}")
        return jsonify({'error': 'Server error'}), 500

# ─── Admin Menu Management API ─────────────────────────────
@app.route('/api/admin/links', methods=['GET'])
@auth.login_required
def admin_get_links():
    """Admin: Get all navigation links"""
    try:
        conn = get_db()
        links = conn.execute('SELECT * FROM nav_links ORDER BY order_index ASC, id ASC').fetchall()
        conn.close()
        return jsonify({'links': [dict(l) for l in links]})

    except sqlite3.Error as e:
        print(f"[ERROR] Database error in admin_get_links: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/admin/links/add', methods=['POST'])
@auth.login_required
def admin_add_link():
    """Admin: Add navigation link"""
    title = request.form.get('title', '').strip()
    url = request.form.get('url', '').strip()
    order = request.form.get('order', 0, type=int)

    if not title or not url:
        return jsonify({'error': 'Title and URL required'}), 400

    try:
        conn = get_db()
        conn.execute('INSERT INTO nav_links (title, url, order_index) VALUES (?,?,?)', (title, url, order))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

    except sqlite3.Error as e:
        print(f"[ERROR] Database error in admin_add_link: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/admin/links/edit/<int:link_id>', methods=['POST'])
@auth.login_required
def admin_edit_link(link_id):
    """Admin: Edit navigation link"""
    title = request.form.get('title', '').strip()
    url = request.form.get('url', '').strip()
    order = request.form.get('order', 0, type=int)

    if not title or not url:
        return jsonify({'error': 'Title and URL required'}), 400

    try:
        conn = get_db()
        conn.execute('UPDATE nav_links SET title=?, url=?, order_index=? WHERE id=?', (title, url, order, link_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

    except sqlite3.Error as e:
        print(f"[ERROR] Database error in admin_edit_link: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/admin/links/delete/<int:link_id>', methods=['POST'])
@auth.login_required
def admin_delete_link(link_id):
    """Admin: Delete navigation link"""
    try:
        conn = get_db()
        conn.execute('DELETE FROM nav_links WHERE id=?', (link_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

    except sqlite3.Error as e:
        print(f"[ERROR] Database error in admin_delete_link: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/admin/change-password', methods=['POST'])
@auth.login_required
def admin_change_password():
    """Admin: Change admin password"""
    current_password = request.form.get('current_password', '').strip()
    new_password = request.form.get('new_password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()

    # Validate inputs
    if not current_password or not new_password or not confirm_password:
        return jsonify({'error': 'Semua field harus diisi'}), 400

    if new_password != confirm_password:
        return jsonify({'error': 'Password baru tidak cocok'}), 400

    if len(new_password) < 6:
        return jsonify({'error': 'Password baru minimal 6 karakter'}), 400

    # Reload config to get current password
    global config
    config = load_config()
    
    # Verify current password
    if current_password != config.get('ADMIN_PASSWORD'):
        return jsonify({'error': 'Password saat ini salah'}), 401

    if new_password == current_password:
        return jsonify({'error': 'Password baru harus berbeda dengan password lama'}), 400

    try:
        # Update config file
        config['ADMIN_PASSWORD'] = new_password

        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=4)

        print(f"[ADMIN] Password changed by user: {auth.current_user()}")
        return jsonify({'success': True, 'message': 'Password berhasil diubah'})

    except IOError as e:
        print(f"[ERROR] Failed to update config: {e}")
        return jsonify({'error': 'Gagal menyimpan password baru'}), 500
    except Exception as e:
        print(f"[ERROR] Unexpected error in change_password: {e}")
        return jsonify({'error': 'Server error'}), 500

@app.route('/logout')
def logout():
    """Logout route"""
    return redirect('/', 401)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=2205, debug=False)
