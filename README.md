

# 📺 YTPlay - Universal Video Embed Player

**Version:** 1.0.0 | **Author:** Pratama Digital | **Website:**  [play.pratamadigital.com](https://play.pratamadigital.com/)

----------

## 📖 Table of Contents

-   Overview
    
-   Features
    
-   Security Features
    
-   Installation
    
-   First Time Setup
    
-   Configuration
    
-   Usage
    
-   Admin Panel
    
-   API Endpoints
    
-   Supported Platforms
    
-   File Upload Support
    
-   Database Structure
    
-   Troubleshooting
    
-   Security Best Practices
    
-   Upgrade Guide
    
-   Contributing
    
-   License
    

----------

## 🎯 Overview

YTPlay is a universal video embed player with dynamic menu and admin edit capabilities. It allows users to:

-   Embed videos from **50+ platforms** (YouTube, Vimeo, Facebook, TikTok, etc.)
    
-   **Upload local videos** with automatic conversion
    
-   **Extract thumbnails** automatically from uploaded videos
    
-   **Manage content** through an intuitive admin panel
    
-   **Track video analytics** (play counts, last played, etc.)
    
-   **Organize videos** with custom navigation links
    

### 🚀 Key Highlights

-   **Zero configuration** for most platforms
    
-   **Automatic HEVC to H.264 conversion** for browser compatibility
    
-   **YouTube thumbnail extraction**
    
-   **Responsive design** for all devices
    
-   **Lightweight** SQLite database
    
-   **Secure** password management with bcrypt
    

----------

## ✨ Features

### Core Features

-   🎬 **Universal Video Embedding** from 50+ platforms
    
-   📤 **Local Video Upload** with automatic processing
    
-   🔄 **Automatic Codec Conversion** (HEVC → H.264)
    
-   🖼️ **Automatic Thumbnail Extraction** from uploaded videos
    
-   📊 **Play Statistics** and analytics
    
-   🔍 **Search & Filter** functionality
    
-   📱 **Responsive** mobile-first design
    
-   🎨 **Custom Navigation Links** (editable via admin)
    
-   📈 **Popular Videos** section (daily/weekly/monthly)
    
-   🔗 **Shareable Links** with unique codes
    

### Admin Features

-   🔐 **Secure Admin Panel** with password protection
    
-   📝 **Edit Video Titles** on-the-fly
    
-   🗑️ **Delete Videos** (single or bulk)
    
-   📊 **View Statistics** (total videos, plays, etc.)
    
-   🔗 **Manage Navigation Links** (add/edit/delete)
    
-   🔑 **Change Admin Password** securely
    
-   📹 **Upload Videos** with automatic processing
    
-   📥 **Export Data** functionality
    

----------

## 🔒 Security Features

YTPlay implements **multiple layers of security** to protect your data:

### Authentication & Authorization

-   ✅ **bcrypt password hashing** (not plain text)
    
-   ✅ **Force password change** on first login
    
-   ✅ **Password strength validation** (min 8 chars with mix of uppercase, lowercase, numbers, symbols)
    
-   ✅ **Session management** with secure secret key
    
-   ✅ **HTTP Basic Auth** for admin endpoints
    
-   ✅ **Auto-logout** after inactivity
    

### Input Validation

-   ✅ **Path traversal prevention** (no `../` attacks)
    
-   ✅ **SQL injection protection** (parameterized queries)
    
-   ✅ **XSS protection** (input sanitization)
    
-   ✅ **Filename sanitization** with `secure_filename()`
    
-   ✅ **URL validation** for navigation links
    
-   ✅ **Code format validation** (regex pattern)
    

### File Upload Security

-   ✅ **File type validation** (only allowed extensions)
    
-   ✅ **File size limits** (max 1GB configurable)
    
-   ✅ **Secure file storage** (outside web root)
    
-   ✅ **Safe file deletion** (with path validation)
    
-   ✅ **Unique filename generation** (prevents overwriting)
    

### System Security

-   ✅ **No hardcoded credentials** in source code
    
-   ✅ **Environment variable support** for production
    
-   ✅ **Random password generation** on first run
    
-   ✅ **Config file permissions** (600 - owner only)
    
-   ✅ **WAL mode** for database concurrency
    

----------

## 📦 Installation

### Prerequisites

bash

# System Requirements
- Python 3.6+
- FFmpeg (for video conversion & thumbnail extraction)
- SQLite3
- 1GB+ disk space (for videos)
# Required Python Packages
pip install flask flask-httpauth bcrypt werkzeug yt-dlp

### Quick Install

#### 1. Clone the Repository

bash

git clone https://github.com/yourusername/ytplay.git
cd ytplay

#### 2. Install Dependencies

bash

pip install -r requirements.txt

#### 3. Install FFmpeg

bash

# Ubuntu/Debian
sudo apt-get install ffmpeg
# CentOS/RHEL
sudo yum install ffmpeg
# macOS
brew install ffmpeg
# Windows
# Download from https://ffmpeg.org/download.html

#### 4. Create Required Directories

bash

mkdir -p /home/ytplay/video
chmod 755 /home/ytplay/video

#### 5. Run the Application

bash

python3 ytplay.py

#### 6. Access the Application

text

http://localhost:2205

----------

## 🔐 First Time Setup

When you run YTPlay for the first time, it will:

### 1. Generate Random Password

bash

============================================================
🔐 YTPlay - FIRST TIME SETUP
============================================================
⚠️  SECURITY NOTICE:
 Default credentials are generated for initial setup.
 YOU MUST CHANGE THE ADMIN PASSWORD IMMEDIATELY!
============================================================
✅ INITIAL SETUP COMPLETE!
📝 ADMIN USERNAME: admin
🔑 TEMPORARY PASSWORD: Xyz123!@#abcDEF
⚠️  IMPORTANT:
 1. Login to admin panel immediately
 2. Change the password on first login
 3. Save your new password securely
📍 Admin Panel: http://YOUR_SERVER:2205/admin
============================================================

### 2. Temporary Password File

A file is created at `/home/ytplay/first_run_password.txt` containing the temporary password. **DELETE THIS FILE AFTER CHANGING THE PASSWORD!**

### 3. Force Password Change

Upon first login to the admin panel, you will be forced to change the password. This ensures:

-   Default password is not left unchanged
    
-   Password meets security requirements
    
-   Password is stored securely (bcrypt hash)
    

### 4. Configuration File

The config file is created at `/home/ytplay/config.json`:

json

{
 "ADMIN_USERNAME": "admin",
 "ADMIN_PASSWORD_HASH": "$2b$12$...",
 "CREATED_AT": "2026-06-30T10:30:00",
 "PASSWORD_CHANGED": false,
 "FIRST_RUN": true
}

----------

## ⚙️ Configuration

### Environment Variables (Recommended for Production)

bash

# Set admin credentials via environment variables
export ADMIN_USERNAME="your_admin_username"
export ADMIN_PASSWORD="your_secure_password"
# Set secret key for sessions
export SECRET_KEY="your_random_secret_key_here"
# Run the application
python3 ytplay.py

### Configuration File

The config file is stored at `/home/ytplay/config.json`:

json

{
 "ADMIN_USERNAME": "admin",
 "ADMIN_PASSWORD_HASH": "$2b$12$...",  // bcrypt hash
 "CREATED_AT": "2026-06-30T10:30:00",
 "PASSWORD_CHANGED": true,
 "PASSWORD_CHANGED_AT": "2026-06-30T11:00:00",
 "FIRST_RUN": false
}

### Changing Configuration

1.  **Via Admin Panel**: Change password through the admin interface
    
2.  **Via Environment Variables**: Override config file in production
    
3.  **Manual Edit**: Edit `/home/ytplay/config.json` (requires server restart)
    

### Port Configuration

The application runs on port **2205** by default. To change:

python

# In ytplay.py
app.run(host='0.0.0.0', port=8080, debug=False)  # Change port number

----------

## 🎮 Usage

### Adding a Video (Public)

1.  Visit the homepage (`http://localhost:2205`)
    
2.  Enter a video URL (from any supported platform)
    
3.  Click "Play" or press Enter
    
4.  The video will be added and you'll be redirected to the player
    

### Playing a Video

-   **Direct URL**: `http://localhost:2205/p/{unique_code}`
    
-   **From Gallery**: Click on any video thumbnail
    
-   **Share Link**: Copy the share URL from the player page
    

### Supported URL Formats

bash

# YouTube Videos
https://youtube.com/watch?v=VIDEO_ID
https://youtu.be/VIDEO_ID
https://youtube.com/embed/VIDEO_ID
https://youtube.com/shorts/VIDEO_ID
https://youtube.com/live/VIDEO_ID
# YouTube Playlists
https://youtube.com/playlist?list=PLAYLIST_ID
# Vimeo
https://vimeo.com/VIDEO_ID
# Facebook
https://facebook.com/.../videos/...
https://fb.watch/...
# TikTok
https://tiktok.com/@username/video/VIDEO_ID
# And many more...

----------

## 🔧 Admin Panel

### Access Admin Panel

text

http://localhost:2205/admin

### Admin Features

#### 📊 Dashboard

-   Total videos count
    
-   Local vs Embedded videos
    
-   Total play count
    
-   Popular videos (daily/weekly/monthly)
    

#### 📹 Video Management

-   View all videos with search/filter
    
-   Edit video titles
    
-   Delete individual videos
    
-   Bulk delete videos
    
-   Upload new videos
    

#### 🔗 Navigation Links

-   Add custom navigation links
    
-   Edit existing links
    
-   Delete links
    
-   Reorder links (via order index)
    

#### 🔑 Password Management

-   Change admin password
    
-   Password strength validation
    
-   Force password change on first login
    

#### 📤 Video Upload

-   Upload MP4, WebM, AVI, MKV, and more
    
-   Automatic HEVC to H.264 conversion
    
-   Automatic thumbnail extraction
    
-   Support for audio files (MP3, WAV, etc.)
    

----------

## 🌐 API Endpoints

### Public APIs

#### Add a Video

http

POST /api/play
Content-Type: application/x-www-form-urlencoded
url=https://youtube.com/watch?v=VIDEO_ID

**Response:**

json

{
 "unique_code": "abc123def",
 "embed_url": "https://www.youtube.com/embed/VIDEO_ID?autoplay=1",
 "site_type": "youtube",
 "original_url": "https://youtube.com/watch?v=VIDEO_ID",
 "title": "Video Title",
 "thumbnail_url": "https://img.youtube.com/vi/VIDEO_ID/hqdefault.jpg",
 "share_url": "/p/abc123def"
}

#### Get Video by Code

http

GET /api/play-by-code/{code}

**Response:**

json

{
 "id": 1,
 "unique_code": "abc123def",
 "title": "Video Title",
 "thumbnail_url": "https://...",
 "embed_url": "https://...",
 "play_count": 42,
 "created_at": "2026-06-30 10:30:00",
 "last_played": "2026-06-30 11:00:00"
}

#### Get History

http

GET /api/history?page=1&per_page=10&search=keyword

**Response:**

json

{
 "plays": [...],
 "page": 1,
 "total_pages": 5,
 "total": 42
}

#### Get Related Videos

http

GET /api/related/{code}?limit=10

### Admin APIs (Requires Authentication)

#### Get Stats

http

GET /api/admin/stats

#### Get All Videos

http

GET /api/admin/history?page=1&search=keyword

#### Delete Videos

http

POST /api/admin/delete
ids[]=1&ids[]=2&ids[]=3

#### Edit Title

http

POST /api/admin/edit_title/{video_id}
title=New Title

#### Upload Video

http

POST /api/admin/upload
Content-Type: multipart/form-data
file: video.mp4
title: My Video Title

#### Change Password

http

POST /api/admin/change-password
current_password=oldpass
new_password=newpass
confirm_password=newpass

#### Manage Navigation Links

http

GET    /api/admin/links
POST   /api/admin/links/add      (title, url, order)
POST   /api/admin/links/edit/{id} (title, url, order)
POST   /api/admin/links/delete/{id}

----------

## 📱 Supported Platforms

Platform

Type

Embed Support

YouTube

Video/Playlist

✅ Full

YouTube Shorts

Video

✅ Full

YouTube Live

Live Stream

✅ Full

Vimeo

Video

✅ Full

Dailymotion

Video

✅ Full

Twitch

Live/Video

✅ Full

Facebook

Video

✅ Full

TikTok

Video

✅ Full

[OK.ru](https://ok.ru/)

Video

✅ Full

Bilibili

Video

✅ Full

Streamable

Video

✅ Full

Google Drive

Video

✅ Full

Direct Video

MP4/WebM/MOV

✅ Full

Direct Audio

MP3/WAV/AAC

✅ Full

----------

## 📁 File Upload Support

### Supported Video Formats

Format

Extension

Codec Support

Conversion

MP4

`.mp4`

H.264, HEVC

✅ Auto

WebM

`.webm`

VP8, VP9

❌

AVI

`.avi`

Various

❌

MKV

`.mkv`

Various

❌

MOV

`.mov`

H.264, HEVC

✅ Auto

FLV

`.flv`

Various

❌

WMV

`.wmv`

Various

❌

M4V

`.m4v`

H.264, HEVC

✅ Auto

### Supported Audio Formats

-   MP3 (`.mp3`)
    
-   WAV (`.wav`)
    
-   OGG (`.oga`)
    
-   AAC (`.aac`)
    
-   FLAC (`.flac`)
    
-   M4A (`.m4a`)
    

### File Size Limits

-   **Default**: 1GB (configurable via `MAX_CONTENT_LENGTH`)
    
-   **Recommended**: 500MB for stable performance
    

### Automatic Processing

1.  **HEVC Detection**: Auto-detects HEVC/H.265 codec
    
2.  **Conversion**: Converts to H.264 for browser compatibility
    
3.  **Thumbnail Extraction**: Extracts thumbnail at 00:00:01
    
4.  **Database Update**: Updates status when complete
    

----------

## 🗄️ Database Structure

### Table: `plays`

Column

Type

Description

`id`

INTEGER

Primary key

`original_url`

TEXT

Original video URL

`unique_code`

TEXT

Unique shareable code

`embed_url`

TEXT

Embed URL for player

`site_type`

TEXT

Platform type (youtube, vimeo, etc.)

`title`

TEXT

Video title

`thumbnail_url`

TEXT

Thumbnail image URL

`play_count`

INTEGER

Number of plays

`created_at`

TIMESTAMP

Creation timestamp

`last_played`

TIMESTAMP

Last play timestamp

`is_local`

INTEGER

Local file flag (0/1)

`conversion_status`

TEXT

Conversion status

`original_filename`

TEXT

Original filename

### Table: `nav_links`

Column

Type

Description

`id`

INTEGER

Primary key

`title`

TEXT

Link title

`url`

TEXT

Link URL

`order_index`

INTEGER

Display order

### Conversion Status Values

-   `pending`: Waiting for processing
    
-   `processing`: Currently converting
    
-   `completed`: Conversion successful
    
-   `failed`: Conversion failed
    
-   `timeout`: Conversion timed out
    
-   `error`: Error occurred
    

----------

## 🔧 Troubleshooting

### Common Issues

#### 1. "No module named 'bcrypt'"

bash

pip install bcrypt

#### 2. FFmpeg not found

bash

# Check if FFmpeg is installed
ffmpeg -version
# Install FFmpeg
sudo apt-get install ffmpeg  # Ubuntu/Debian
brew install ffmpeg          # macOS

#### 3. Permission denied on /home/ytplay/

bash

# Create directory with proper permissions
sudo mkdir -p /home/ytplay
sudo chown $USER:$USER /home/ytplay
chmod 755 /home/ytplay

#### 4. Port 2205 already in use

bash

# Change port in ytplay.py
app.run(host='0.0.0.0', port=8080, debug=False)
# Or kill existing process
sudo lsof -i :2205
sudo kill -9 PID

#### 5. Database locked error

bash

# WAL mode is enabled by default, but if issues:
# Stop the application and delete -wal and -shm files
rm /home/ytplay/ytplay.db-wal
rm /home/ytplay/ytplay.db-shm

#### 6. Videos not playing in browser

-   Check if video codec is supported (HEVC needs conversion)
    
-   Verify the embed URL is correct
    
-   Check browser console for errors
    
-   Ensure Content-Type headers are correct
    

#### 7. HEVC conversion taking too long

-   Conversion time depends on video length and server CPU
    
-   Consider using `-preset fast` for quicker conversion
    
-   For large files, consider limiting upload size
    

### Logs

Logs are printed to the console. For production, consider redirecting to a file:

bash

python3 ytplay.py > /var/log/ytplay.log 2>&1

----------

## 🛡️ Security Best Practices

### For Server Administrators

#### 1. **Use HTTPS in Production**

bash

# Install nginx as reverse proxy
sudo apt-get install nginx
# Configure SSL with Let's Encrypt
sudo certbot --nginx -d yourdomain.com

#### 2. **Set Strong Passwords**

-   Use password manager to generate passwords
    
-   Minimum 12 characters with mix of character types
    
-   Change passwords every 90 days
    
-   Never reuse passwords
    

#### 3. **Regular Updates**

bash

# Update Python packages
pip install --upgrade flask flask-httpauth bcrypt yt-dlp
# Update system packages
sudo apt-get update
sudo apt-get upgrade

#### 4. **Backup Database**

bash

# Daily backup
cp /home/ytplay/ytplay.db /backup/ytplay_$(date +%Y%m%d).db
# Use cron for automation
0 2 * * * cp /home/ytplay/ytplay.db /backup/ytplay_$(date +%Y%m%d).db

#### 5. **Monitor Access Logs**

bash

# Check admin access
tail -f /var/log/ytplay.log | grep "ADMIN"
# Monitor failed login attempts
grep "AUTH" /var/log/ytplay.log

#### 6. **Firewall Configuration**

bash

# Allow only necessary ports
sudo ufw allow 2205
sudo ufw enable

#### 7. **Environment Variables for Production**

bash

# Set credentials via environment variables
export ADMIN_USERNAME="secure_username"
export ADMIN_PASSWORD="super_secure_password"
export SECRET_KEY="your_random_secret_key"

#### 8. **Delete Temporary Files**

bash

# After first setup
rm /home/ytplay/first_run_password.txt

### For Developers

#### 1. **Never Commit Config Files**

Add to `.gitignore`:

gitignore

config.json
*.db
*.db-journal
*.db-wal
*.db-shm
/video/
__pycache__/
*.pyc
.env

#### 2. **Use Secrets Management**

-   Use environment variables
    
-   Use secrets manager (Vault, AWS Secrets Manager)
    
-   Never hardcode credentials
    

#### 3. **Regular Security Audits**

-   Review dependencies for vulnerabilities
    
-   Check for exposed endpoints
    
-   Update security headers
    

----------

## 🔄 Upgrade Guide

### Upgrading from Older Version

#### 1. **Backup Everything**

bash

# Backup database
cp /home/ytplay/ytplay.db /backup/ytplay_backup.db
# Backup config
cp /home/ytplay/config.json /backup/config_backup.json
# Backup videos
cp -r /home/ytplay/video /backup/video_backup

#### 2. **Update Code**

bash

# Pull latest version
git pull origin main
# Or replace ytplay.py with new version

#### 3. **Update Dependencies**

bash

pip install --upgrade -r requirements.txt

#### 4. **Run Database Migration**

The application automatically migrates the database on startup. Check logs for:

text

[DB] Added column: title
[DB] Added column: thumbnail_url

#### 5. **Restart Application**

bash

# Using systemd
sudo systemctl restart ytplay
# Or manually
pkill -f ytplay.py
python3 ytplay.py

----------

## 🤝 Contributing

### Development Setup

bash

# Clone repository
git clone https://github.com/yourusername/ytplay.git
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
# Install dev dependencies
pip install -r requirements-dev.txt

### Coding Standards

-   Follow PEP 8
    
-   Add comments for complex logic
    
-   Write docstrings for functions
    
-   Test your changes
    

### Pull Request Process

1.  Fork the repository
    
2.  Create a feature branch
    
3.  Make your changes
    
4.  Test thoroughly
    
5.  Submit a pull request
    

----------

## 📄 License

Copyright © 2026 Pratama Digital

This project is licensed under the MIT License - see the [LICENSE](https://license/) file for details.

### Credits

-   Flask - Web framework
    
-   SQLite - Database
    
-   FFmpeg - Video processing
    
-   yt-dlp - Video metadata extraction
    
-   bcrypt - Password hashing
    

----------

## 📞 Support

### Documentation

-   [GitHub Wiki](https://github.com/yourusername/ytplay/wiki)
    
-   [API Reference](https://play.pratamadigital.com/api-docs)
    

### Community

-   [GitHub Issues](https://github.com/yourusername/ytplay/issues)
    
-   [Discord Server](https://discord.gg/yourinvite)
    

### Commercial Support

For enterprise support and custom development:

-   Email: support@pratamadigital.com
    
-   Website: [pratamadigital.com](https://pratamadigital.com/)
    

----------

## 📊 Version History

### v1.0.0 (Current)

-   ✅ Initial release
    
-   ✅ Universal video embedding
    
-   ✅ Local video upload
    
-   ✅ HEVC to H.264 conversion
    
-   ✅ Thumbnail extraction
    
-   ✅ Admin panel
    
-   ✅ Security improvements
    
-   ✅ bcrypt password hashing
    

### Planned Features

-   User roles and permissions
    
-   Video categories/tags
    
-   API rate limiting
    
-   Redis caching
    
-   S3/Cloud storage support
    
-   Video analytics dashboard
    
-   Email notifications
    
-   Two-factor authentication
    

----------

## 🚀 Quick Reference

### Common Commands

bash

# Start application
python3 ytplay.py
# Start in background
nohup python3 ytplay.py &
# Check if running
ps aux | grep ytplay.py
# Stop application
pkill -f ytplay.py
# View logs
tail -f /var/log/ytplay.log
# Backup database
cp /home/ytplay/ytplay.db /backup/ytplay_$(date +%Y%m%d).db
# Reset database (caution!)
rm /home/ytplay/ytplay.db

### Default Paths

bash

Application: /home/ytplay/ytplay.py
Database: /home/ytplay/ytplay.db
Config: /home/ytplay/config.json
Videos: /home/ytplay/video/
Logs: Console output (redirect to file)

### Ports

bash

Web Interface: 2205
Admin Interface: 2205

----------

## ⚠️ Important Security Notes

### 🔴 **CRITICAL: First Run Security**

1.  **IMMEDIATELY change the default password** on first login
    
2.  Delete the `first_run_password.txt` file after changing password
    
3.  Use a **strong password** (min 8 chars with mix of uppercase, lowercase, numbers, symbols)
    
4.  Never share your admin credentials
    
5.  Use **HTTPS** in production
    

### 🟡 **Recommended: Production Security**

1.  Use environment variables for credentials
    
2.  Configure firewall to restrict access
    
3.  Enable HTTPS with SSL certificate
    
4.  Regular security updates
    
5.  Monitor access logs
    
6.  Implement IP whitelisting for admin access
    
7.  Use a reverse proxy (nginx)
    
8.  Regular database backups
    

### 🟢 **Best Practices**

1.  Keep software updated
    
2.  Use strong passwords
    
3.  Enable two-factor authentication (if available)
    
4.  Regular security audits
    
5.  Backup data regularly
    
6.  Monitor for suspicious activity
    

----------

**Made with ❤️ by Pratama Digital**

_"Universal Video Embed Player for Everyone"_
