#!/usr/bin/env python3
"""
YTPlay - Universal Video Embed Player with Dynamic Menu & Admin Edit
play.pratamadigital.com
Flask app on port 2205
"""

from flask import Flask, render_template, request, jsonify, redirect
from flask_httpauth import HTTPBasicAuth
import sqlite3
import string
import random
import re
import json
import os
from urllib.parse import urlparse, parse_qs, quote
from datetime import datetime

app = Flask(__name__)
auth = HTTPBasicAuth()

DB_PATH = '/home/ytplay/ytplay.db'
CONFIG_PATH = '/home/ytplay/config.json'
DEFAULT_THUMB = 'https://via.placeholder.com/320x180/1e293b/475569?text=No+Thumb'

# ─── Config & Auth ─────────────────────────────────────────
def load_config():
    if not os.path.exists(CONFIG_PATH):
        default_cfg = {"ADMIN_USERNAME": "admin", "ADMIN_PASSWORD": "767676176"}
        with open(CONFIG_PATH, 'w') as f: json.dump(default_cfg, f, indent=4)
        return default_cfg
    with open(CONFIG_PATH, 'r') as f: return json.load(f)

config = load_config()

@auth.verify_password
def verify_password(username, password):
    if username == config.get('ADMIN_USERNAME') and password == config.get('ADMIN_PASSWORD'): return username
    return None

# ─── Database ───────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    # Tabel Video
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
        last_played TIMESTAMP
    )''')
    
    # Tabel Menu Navigasi
    conn.execute('''CREATE TABLE IF NOT EXISTS nav_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        url TEXT NOT NULL,
        order_index INTEGER DEFAULT 0
    )''')
    
    # Auto-migrate plays
    cursor = conn.execute("PRAGMA table_info(plays)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'title' not in columns: conn.execute("ALTER TABLE plays ADD COLUMN title TEXT DEFAULT 'Unknown Title'")
    if 'thumbnail_url' not in columns: conn.execute("ALTER TABLE plays ADD COLUMN thumbnail_url TEXT DEFAULT ''")
    if 'play_count' not in columns: conn.execute("ALTER TABLE plays ADD COLUMN play_count INTEGER DEFAULT 0")
    if 'last_played' not in columns: conn.execute("ALTER TABLE plays ADD COLUMN last_played TIMESTAMP")
    
    # Isi menu default jika kosong
    if conn.execute('SELECT COUNT(*) FROM nav_links').fetchone()[0] == 0:
        conn.executemany('INSERT INTO nav_links (title, url, order_index) VALUES (?, ?, ?)', [
            ('Berita Wonosobo', 'https://wonosobonews.web.id', 1),
            ('Pratama Digital', 'https://pratamadigital.com', 2),
            ('Panti Asuhan Yani Fazzahra', 'https://yanifazzahra.or.id', 3)
        ])
        
    conn.commit()
    conn.close()

def generate_code(length=8):
    chars = string.ascii_lowercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=length))
        conn = get_db()
        exists = conn.execute('SELECT 1 FROM plays WHERE unique_code=?', (code,)).fetchone()
        conn.close()
        if not exists: return code

def get_nav_links():
    conn = get_db()
    links = conn.execute('SELECT * FROM nav_links ORDER BY order_index ASC, id ASC').fetchall()
    conn.close()
    return links

# ─── yt-dlp Fetcher ─────────────────────────────────────────
def fetch_video_info(url, site_type):
    title = 'Unknown Title'
    thumbnail = DEFAULT_THUMB # Set default sejak awal
    
    # Optimasi YouTube
    if 'youtube' in site_type:
        try:
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            path = parsed.path
            domain = parsed.netloc.lower()
            vid = None
            if 'youtu.be' in domain: vid = path.strip('/').split('/')[0].split('?')[0]
            elif '/embed/' in path: vid = path.split('/embed/')[-1].split('?')[0]
            elif '/shorts/' in path: vid = path.split('/shorts/')[-1].split('?')[0]
            elif '/live/' in path: vid = path.split('/live/')[-1].split('?')[0]
            elif '/watch' in path: vid = qs.get('v', [None])[0]
            if vid: thumbnail = f'https://img.youtube.com/vi/{vid}/hqdefault.jpg'
        except Exception: pass

    try:
        import yt_dlp
        ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
        if site_type == 'youtube_playlist': ydl_opts['extract_flat'] = 'in_playlist'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                title = info.get('title') or 'Unknown Title'
                if site_type == 'youtube_playlist':
                    playlist_count = info.get('playlist_count', '?')
                    title = f"{title} (Playlist: {playlist_count} videos)"
                
                if info.get('thumbnails') and len(info['thumbnails']) > 0:
                    thumb_from_ytdlp = info['thumbnails'][-1].get('url', '')
                    if thumb_from_ytdlp: thumbnail = thumb_from_ytdlp
                elif info.get('thumbnail'):
                    thumbnail = info.get('thumbnail', DEFAULT_THUMB)
    except Exception: pass
        
    return {'title': title, 'thumbnail': thumbnail}

# ─── URL Parser ─────────────────────────────────────────────
def parse_video_url(url):
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path
        qs = parse_qs(parsed.query)
        for prefix in ('www.', 'm.', 'gaming.'):
            if domain.startswith(prefix): domain = domain[len(prefix):]
    except Exception: return url, 'unknown'

    if 'youtube.com' in domain or 'youtu.be' in domain:
        list_id = qs.get('list', [None])[0]
        if list_id: return f'https://www.youtube.com/embed/videoseries?list={list_id}&autoplay=1', 'youtube_playlist'
        vid = None
        if 'youtu.be' in domain: vid = path.strip('/').split('/')[0].split('?')[0]
        elif '/embed/' in path: vid = path.split('/embed/')[-1].split('?')[0]
        elif '/shorts/' in path: vid = path.split('/shorts/')[-1].split('?')[0]
        elif '/live/' in path: vid = path.split('/live/')[-1].split('?')[0]
        elif '/watch' in path: vid = qs.get('v', [None])[0]
        if vid: return f'https://www.youtube.com/embed/{vid}?autoplay=1&rel=0&modestbranding=1', 'youtube'

    elif 'vimeo.com' in domain and 'player.vimeo.com' not in domain:
        parts = [p for p in path.strip('/').split('/') if p.isdigit()]
        if parts: return f'https://player.vimeo.com/video/{parts[-1]}?autoplay=1', 'vimeo'
    elif 'dailymotion.com' in domain:
        m = re.search(r'/video/([a-zA-Z0-9]+)', path)
        if m: return f'https://www.dailymotion.com/embed/video/{m.group(1)}?autoplay=1', 'dailymotion'
    elif 'twitch.tv' in domain:
        parts = [p for p in path.strip('/').split('/') if p]
        if len(parts) >= 2 and parts[0] == 'videos': return f'https://player.twitch.tv/?video={parts[1]}&parent=play.pratamadigital.com', 'twitch'
        elif parts and parts[0] not in ('', 'directory', 'downloads'): return f'https://player.twitch.tv/?channel={parts[0]}&parent=play.pratamadigital.com', 'twitch'
    elif 'tiktok.com' in domain:
        m = re.search(r'/video/(\d+)', path)
        if m: return f'https://www.tiktok.com/embed/v2/{m.group(1)}', 'tiktok'
    elif 'facebook.com' in domain or 'fb.watch' in domain:
        return f'https://www.facebook.com/plugins/video.php?href={quote(url, safe="")}&autoplay=true', 'facebook'
    elif 'ok.ru' in domain:
        m = re.search(r'/video/(\d+)', path)
        if m: return f'https://ok.ru/videoembed/{m.group(1)}', 'okru'
    elif 'bilibili.com' in domain:
        m = re.search(r'/(BV[a-zA-Z0-9]+)', path)
        if m: return f'https://player.bilibili.com/player.html?bvid={m.group(1)}&autoplay=1', 'bilibili'
    elif 'streamable.com' in domain:
        vid = path.strip('/').split('/')[-1]
        if vid: return f'https://streamable.com/e/{vid}?autoplay=1', 'streamable'
    elif 'drive.google.com' in domain:
        m = re.search(r'/d/([a-zA-Z0-9_-]+)', path)
        if m: return f'https://drive.google.com/file/d/{m.group(1)}/preview', 'gdrive'

    ext = path.lower().rsplit('.', 1)[-1] if '.' in path.rsplit('/', 1)[-1] else ''
    if ext in {'mp4', 'webm', 'ogg', 'ogv', 'mov', 'm4v'}: return url, 'video'
    elif ext in {'mp3', 'wav', 'oga', 'aac', 'flac', 'm4a'}: return url, 'audio'

    return url, 'unknown'

# ─── Routes ─────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('gallery.html', nav_links=get_nav_links())

@app.route('/p/<code>')
def play_page(code):
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

@app.route('/api/play', methods=['POST'])
def api_play():
    url = request.form.get('url', '').strip()
    if not url: return jsonify({'error': 'URL wajib diisi'}), 400
    if not url.startswith(('http://', 'https://')): url = 'https://' + url

    embed_url, site_type = parse_video_url(url)
    now_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db()
    existing = conn.execute('SELECT * FROM plays WHERE original_url=?', (url,)).fetchone()

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
        conn.execute('INSERT INTO plays (original_url, unique_code, embed_url, site_type, title, thumbnail_url, play_count, last_played) VALUES (?,?,?,?,?,?,?,?)',
                     (url, code, embed_url, site_type, title, thumbnail, 1, now_time))
        conn.commit()
    conn.close()

    return jsonify({'unique_code': code, 'embed_url': embed_url, 'site_type': site_type, 'original_url': url, 'title': title, 'thumbnail_url': thumbnail, 'share_url': f'/p/{code}'})

@app.route('/api/play-by-code/<code>')
def api_play_by_code(code):
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
    d['play_count'] = new_count; d['last_played'] = now_time; d['share_url'] = f'/p/{code}'
    if not d['thumbnail_url']: d['thumbnail_url'] = DEFAULT_THUMB
    return jsonify(d)

@app.route('/api/history')
def api_history():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    per_page = request.args.get('per_page', 10, type=int)
    offset = (page - 1) * per_page

    conn = get_db()
    if search:
        like_search = f"%{search}%"
        total = conn.execute('SELECT COUNT(*) FROM plays WHERE title LIKE ? OR original_url LIKE ?', (like_search, like_search)).fetchone()[0]
        rows = conn.execute('SELECT * FROM plays WHERE title LIKE ? OR original_url LIKE ? ORDER BY last_played DESC, id DESC LIMIT ? OFFSET ?', (like_search, like_search, per_page, offset)).fetchall()
    else:
        total = conn.execute('SELECT COUNT(*) FROM plays').fetchone()[0]
        rows = conn.execute('SELECT * FROM plays ORDER BY last_played DESC, id DESC LIMIT ? OFFSET ?', (per_page, offset)).fetchall()
    conn.close()
    return jsonify({'plays': [dict(r) for r in rows], 'page': page, 'total_pages': max(1, (total + per_page - 1) // per_page), 'total': total})

# ─── Admin Routes (Protected) ──────────────────────────────
@app.route('/admin')
@auth.login_required
def admin(): return render_template('admin.html', nav_links=get_nav_links())

@app.route('/api/admin/history')
@auth.login_required
def admin_history():
    page = request.args.get('page', 1, type=int); search = request.args.get('search', '').strip()
    per_page = 20; offset = (page - 1) * per_page
    conn = get_db()
    if search:
        like_search = f"%{search}%"
        total = conn.execute('SELECT COUNT(*) FROM plays WHERE title LIKE ? OR original_url LIKE ?', (like_search, like_search)).fetchone()[0]
        rows = conn.execute('SELECT * FROM plays WHERE title LIKE ? OR original_url LIKE ? ORDER BY id DESC LIMIT ? OFFSET ?', (like_search, like_search, per_page, offset)).fetchall()
    else:
        total = conn.execute('SELECT COUNT(*) FROM plays').fetchone()[0]
        rows = conn.execute('SELECT * FROM plays ORDER BY id DESC LIMIT ? OFFSET ?', (per_page, offset)).fetchall()
    conn.close()
    return jsonify({'plays': [dict(r) for r in rows], 'page': page, 'total_pages': max(1, (total + per_page - 1) // per_page), 'total': total})

@app.route('/api/admin/delete', methods=['POST'])
@auth.login_required
def admin_delete():
    ids = request.form.getlist('ids[]')
    if ids:
        conn = get_db(); placeholders = ','.join(['?'] * len(ids))
        conn.execute(f'DELETE FROM plays WHERE id IN ({placeholders})', ids); conn.commit(); conn.close()
        return jsonify({'success': True, 'deleted': len(ids)})
    return jsonify({'error': 'No IDs provided'}), 400

@app.route('/api/admin/reset', methods=['POST'])
@auth.login_required
def admin_reset():
    conn = get_db(); conn.execute('DELETE FROM plays'); conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/edit_title/<int:video_id>', methods=['POST'])
@auth.login_required
def admin_edit_title(video_id):
    new_title = request.form.get('title', '').strip()
    if not new_title: return jsonify({'error': 'Title cannot be empty'}), 400
    conn = get_db()
    conn.execute('UPDATE plays SET title=? WHERE id=?', (new_title, video_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ─── Admin Menu Management API ─────────────────────────────
@app.route('/api/admin/links', methods=['GET'])
@auth.login_required
def admin_get_links():
    conn = get_db()
    links = conn.execute('SELECT * FROM nav_links ORDER BY order_index ASC, id ASC').fetchall()
    conn.close()
    return jsonify({'links': [dict(l) for l in links]})

@app.route('/api/admin/links/add', methods=['POST'])
@auth.login_required
def admin_add_link():
    title = request.form.get('title', '').strip()
    url = request.form.get('url', '').strip()
    order = request.form.get('order', 0, type=int)
    if not title or not url: return jsonify({'error': 'Title and URL required'}), 400
    conn = get_db()
    conn.execute('INSERT INTO nav_links (title, url, order_index) VALUES (?,?,?)', (title, url, order))
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/links/edit/<int:link_id>', methods=['POST'])
@auth.login_required
def admin_edit_link(link_id):
    title = request.form.get('title', '').strip()
    url = request.form.get('url', '').strip()
    order = request.form.get('order', 0, type=int)
    if not title or not url: return jsonify({'error': 'Title and URL required'}), 400
    conn = get_db()
    conn.execute('UPDATE nav_links SET title=?, url=?, order_index=? WHERE id=?', (title, url, order, link_id))
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/links/delete/<int:link_id>', methods=['POST'])
@auth.login_required
def admin_delete_link(link_id):
    conn = get_db()
    conn.execute('DELETE FROM nav_links WHERE id=?', (link_id,))
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/logout')
def logout():
    return redirect('/', 401)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=2205, debug=False)
