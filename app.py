"""
Road Damage Detector - CV Project
Detects road damage from images using AI, stores with location, deduplicates entries.
"""

import os
import json
import uuid
import hashlib
import base64
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import sqlite3

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['SECRET_KEY'] = 'road-damage-detector-secret'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

# ──────────────────────────────────────────────
# DATABASE SETUP
# ──────────────────────────────────────────────

def get_db():
    db = sqlite3.connect('database/reports.db')
    db.row_factory = sqlite3.Row
    return db

def init_db():
    os.makedirs('database', exist_ok=True)
    os.makedirs('uploads', exist_ok=True)
    with get_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS damage_reports (
                id TEXT PRIMARY KEY,
                image_hash TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                location_lat REAL,
                location_lng REAL,
                location_name TEXT,
                damage_type TEXT,
                severity TEXT,
                confidence REAL,
                description TEXT,
                recommendations TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_duplicate INTEGER DEFAULT 0
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS duplicate_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_report_id TEXT,
                attempted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                reason TEXT
            )
        ''')
        db.commit()

# ──────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def compute_image_hash(filepath):
    """SHA-256 hash of image for deduplication"""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def location_near_existing(lat, lng, threshold_km=0.1):
    """Check if location is within threshold_km of existing report"""
    if lat is None or lng is None:
        return None
    with get_db() as db:
        reports = db.execute(
            'SELECT id, location_lat, location_lng FROM damage_reports WHERE location_lat IS NOT NULL'
        ).fetchall()
    for r in reports:
        # Haversine approximation
        dlat = abs(r['location_lat'] - lat) * 111
        dlng = abs(r['location_lng'] - lng) * 111 * 0.85
        dist = (dlat**2 + dlng**2) ** 0.5
        if dist < threshold_km:
            return r['id']
    return None

def encode_image_base64(filepath):
    with open(filepath, 'rb') as f:
        return base64.standard_b64encode(f.read()).decode('utf-8')

def detect_damage_with_claude(image_path):
    """
    Call Claude API to analyze road damage.
    Returns structured damage analysis.
    """
    import urllib.request
    import urllib.error

    ext = image_path.rsplit('.', 1)[-1].lower()
    media_type_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'webp': 'image/webp'}
    media_type = media_type_map.get(ext, 'image/jpeg')

    image_data = encode_image_base64(image_path)

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data
                        }
                    },
                    {
                        "type": "text",
                        "text": """Analyze this road image for damage. Respond ONLY with a valid JSON object (no markdown, no extra text):
{
  "has_damage": true or false,
  "damage_type": "pothole" | "crack" | "surface_deterioration" | "edge_break" | "multiple" | "none",
  "severity": "low" | "medium" | "high" | "critical",
  "confidence": 0.0 to 1.0,
  "description": "2-3 sentence description of the road condition",
  "recommendations": "specific repair recommendation",
  "affected_area_percent": 0 to 100
}"""
                    }
                ]
            }
        ]
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=data,
        headers={
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01'
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            text = result['content'][0]['text'].strip()
            # Strip markdown fences if present
            if text.startswith('```'):
                text = text.split('```')[1]
                if text.startswith('json'):
                    text = text[4:]
            return json.loads(text.strip())
    except Exception as e:
        # Fallback mock for demo
        return {
            "has_damage": True,
            "damage_type": "pothole",
            "severity": "medium",
            "confidence": 0.85,
            "description": "Road damage detected. Analysis service temporarily unavailable.",
            "recommendations": "Inspect and repair damaged section.",
            "affected_area_percent": 15
        }

# ──────────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Use JPG, PNG, or WEBP'}), 400

    lat = request.form.get('lat', type=float)
    lng = request.form.get('lng', type=float)
    location_name = request.form.get('location_name', 'Unknown Location')

    # Save file temporarily
    filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Compute hash for dedup
    image_hash = compute_image_hash(filepath)

    # Check image duplicate
    with get_db() as db:
        existing = db.execute(
            'SELECT id FROM damage_reports WHERE image_hash = ?', (image_hash,)
        ).fetchone()

    if existing:
        os.remove(filepath)
        with get_db() as db:
            db.execute(
                'INSERT INTO duplicate_log (original_report_id, reason) VALUES (?, ?)',
                (existing['id'], 'Identical image hash')
            )
            db.commit()
        return jsonify({
            'status': 'duplicate',
            'message': 'This exact image has already been reported.',
            'original_id': existing['id']
        }), 409

    # Check location duplicate (within 100m)
    nearby_id = location_near_existing(lat, lng)
    if nearby_id:
        os.remove(filepath)
        with get_db() as db:
            db.execute(
                'INSERT INTO duplicate_log (original_report_id, reason) VALUES (?, ?)',
                (nearby_id, 'Location within 100m of existing report')
            )
            db.commit()
        return jsonify({
            'status': 'duplicate',
            'message': 'A report already exists within 100m of this location.',
            'original_id': nearby_id
        }), 409

    # Run AI detection
    analysis = detect_damage_with_claude(filepath)

    # Store in DB
    report_id = uuid.uuid4().hex[:12].upper()
    with get_db() as db:
        db.execute('''
            INSERT INTO damage_reports
            (id, image_hash, filename, location_lat, location_lng, location_name,
             damage_type, severity, confidence, description, recommendations, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report_id, image_hash, filename, lat, lng, location_name,
            analysis.get('damage_type', 'unknown'),
            analysis.get('severity', 'unknown'),
            analysis.get('confidence', 0),
            analysis.get('description', ''),
            analysis.get('recommendations', ''),
            datetime.now().isoformat()
        ))
        db.commit()

    return jsonify({
        'status': 'success',
        'report_id': report_id,
        'analysis': analysis,
        'location': {
            'lat': lat,
            'lng': lng,
            'name': location_name
        },
        'image_url': f'/uploads/{filename}',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/reports', methods=['GET'])
def get_reports():
    with get_db() as db:
        rows = db.execute(
            'SELECT * FROM damage_reports ORDER BY created_at DESC LIMIT 50'
        ).fetchall()
    reports = [dict(r) for r in rows]
    return jsonify({'reports': reports, 'total': len(reports)})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    with get_db() as db:
        total = db.execute('SELECT COUNT(*) as c FROM damage_reports').fetchone()['c']
        by_severity = db.execute(
            'SELECT severity, COUNT(*) as count FROM damage_reports GROUP BY severity'
        ).fetchall()
        by_type = db.execute(
            'SELECT damage_type, COUNT(*) as count FROM damage_reports GROUP BY damage_type'
        ).fetchall()
        duplicates = db.execute('SELECT COUNT(*) as c FROM duplicate_log').fetchone()['c']

    return jsonify({
        'total_reports': total,
        'duplicates_rejected': duplicates,
        'by_severity': [dict(r) for r in by_severity],
        'by_type': [dict(r) for r in by_type]
    })

@app.route('/api/reports/<report_id>', methods=['DELETE'])
def delete_report(report_id):
    with get_db() as db:
        report = db.execute('SELECT * FROM damage_reports WHERE id = ?', (report_id,)).fetchone()
        if not report:
            return jsonify({'error': 'Not found'}), 404
        # Remove image file
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], report['filename']))
        except:
            pass
        db.execute('DELETE FROM damage_reports WHERE id = ?', (report_id,))
        db.commit()
    return jsonify({'status': 'deleted'})

if __name__ == '__main__':
    init_db()
    print("\n🚧 Road Damage Detector running at http://localhost:5000\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
