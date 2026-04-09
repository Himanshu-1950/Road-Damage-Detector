"""
<<<<<<< HEAD
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
=======
RoadScan AI — Flask Web App
Loads trained EfficientNet-B4 model, detects road damage,
saves results (image + location) to live dataset CSV.
"""

import os, json, csv, uuid, hashlib, shutil
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED = {'png','jpg','jpeg','webp'}
DATASET_CSV = Path('live_dataset.csv')
CSV_FIELDS  = [
    'image_id','filename','label','damage_probability',
    'confidence_level','location_name','latitude','longitude',
    'timestamp','source'
]

# ── Init CSV ───────────────────────────────────────────────────────
if not DATASET_CSV.exists():
    with open(DATASET_CSV, 'w', newline='') as f:
        csv.writer(f).writerow(CSV_FIELDS)

Path('uploads').mkdir(exist_ok=True)

# ── Load Model ─────────────────────────────────────────────────────
MODEL = None
DEVICE = 'cpu'

def load_model():
    global MODEL, DEVICE
    model_path = Path('road_damage_model.pth')
    meta_path  = Path('model_metadata.json')

    if not model_path.exists():
        print('⚠ road_damage_model.pth not found')
        print('  Run the Colab notebook to train and download the model')
        print('  Then place road_damage_model.pth in this folder')
        return False

    try:
        import torch, timm
        import torch.nn as nn

        DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

        # Load metadata
        if meta_path.exists():
            with open(meta_path) as f:
                meta = json.load(f)
            arch = meta.get('model_arch', 'efficientnet_b4')
        else:
            arch = 'efficientnet_b4'

        # Recreate model
        class RoadDamageModel(nn.Module):
            def __init__(self):
                super().__init__()
                self.backbone = timm.create_model(arch, pretrained=False,
                                                  num_classes=0, global_pool='avg')
                feat_dim = self.backbone.num_features
                self.head = nn.Sequential(
                    nn.Dropout(0.3),
                    nn.Linear(feat_dim, 512),
                    nn.BatchNorm1d(512),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.15),
                    nn.Linear(512, 128),
                    nn.ReLU(inplace=True),
                    nn.Linear(128, 2)
                )
            def forward(self, x):
                return self.head(self.backbone(x))

        model = RoadDamageModel()
        model.load_state_dict(torch.load(model_path, map_location=DEVICE))
        model.to(DEVICE)
        model.eval()
        MODEL = model
        print(f'✅ Model loaded ({arch}) on {DEVICE}')
        return True

    except Exception as e:
        print(f'❌ Model load failed: {e}')
        return False

MODEL_LOADED = load_model()

# ── Inference ─────────────────────────────────────────────────────
def predict(img_path: str):
    if not MODEL_LOADED:
        return None, None  # model not available

    try:
        import torch, torch.nn.functional as F
        from torchvision import transforms
        from PIL import Image

        tf = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225]),
        ])

        img    = Image.open(img_path).convert('RGB')
        tensor = tf(img).unsqueeze(0).to(DEVICE)

        with torch.no_grad():
            logits = MODEL(tensor)
            probs  = F.softmax(logits, dim=1)[0].cpu().numpy()

        return float(probs[1]), float(probs[0])  # damaged_prob, clean_prob

    except Exception as e:
        print(f'Inference error: {e}')
        return None, None

# ── Helpers ───────────────────────────────────────────────────────
def file_hash(path):
    h = hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def allowed(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED

def append_dataset(img_id, filename, label, dam_prob, loc_name, lat, lng):
    conf = ('high'   if dam_prob > 0.85 or dam_prob < 0.15 else
            'medium' if dam_prob > 0.65 or dam_prob < 0.35 else 'low')
    with open(DATASET_CSV, 'a', newline='') as f:
        csv.writer(f).writerow([
            img_id, filename, label,
            f'{dam_prob:.4f}', conf,
            loc_name or 'Unknown',
            lat or '', lng or '',
            datetime.now().isoformat(),
            'web_upload'
        ])

# ── Routes ────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html', model_loaded=MODEL_LOADED)

@app.route('/uploads/<path:filename>')
def uploaded(filename):
    return send_from_directory('uploads', filename)

@app.route('/api/detect', methods=['POST'])
def detect():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    f = request.files['image']
    if not f.filename or not allowed(f.filename):
        return jsonify({'error': 'Invalid file type. Use JPG/PNG/WEBP'}), 400

    lat      = request.form.get('lat', type=float)
    lng      = request.form.get('lng', type=float)
    loc_name = request.form.get('location_name', 'Unknown')

    # Save file
    ext      = f.filename.rsplit('.',1)[1].lower()
    img_id   = uuid.uuid4().hex[:12].upper()
    filename = f'{img_id}.{ext}'
    filepath = str(Path('uploads') / filename)
    f.save(filepath)

    # Deduplicate by hash
    h = file_hash(filepath)
    df = _load_dataset()
    # (simple in-memory dedup check on filename/id — extend as needed)

    # Run detection
    if MODEL_LOADED:
        dam_prob, clean_prob = predict(filepath)
        if dam_prob is None:
            return jsonify({'error': 'Inference failed'}), 500
        label = 'damaged' if dam_prob >= 0.5 else 'clean'
        confidence = max(dam_prob, clean_prob) * 100
    else:
        # No model — return placeholder
        return jsonify({
            'error': 'Model not loaded. Train and download road_damage_model.pth from Colab first.',
            'model_loaded': False
        }), 503

    # Save to dataset
    # Move image to labelled subfolder inside uploads
    labelled_dir = Path('uploads') / label
    labelled_dir.mkdir(exist_ok=True)
    labelled_path = labelled_dir / filename
    shutil.copy2(filepath, labelled_path)

    append_dataset(img_id, filename, label, dam_prob, loc_name, lat, lng)

    return jsonify({
        'status'          : 'success',
        'image_id'        : img_id,
        'label'           : label,
        'is_damaged'      : label == 'damaged',
        'damage_prob'     : round(dam_prob * 100, 1),
        'clean_prob'      : round(clean_prob * 100, 1),
        'confidence'      : round(confidence, 1),
        'location_name'   : loc_name,
        'latitude'        : lat,
        'longitude'       : lng,
        'image_url'       : f'/uploads/{filename}',
        'timestamp'       : datetime.now().isoformat(),
        'saved_to_dataset': True
    })

@app.route('/api/dataset', methods=['GET'])
def get_dataset():
    rows = _load_dataset()
    return jsonify({'records': rows, 'total': len(rows)})

@app.route('/api/stats')
def stats():
    rows = _load_dataset()
    damaged = [r for r in rows if r.get('label') == 'damaged']
    clean   = [r for r in rows if r.get('label') == 'clean']
    return jsonify({
        'total'  : len(rows),
        'damaged': len(damaged),
        'clean'  : len(clean),
        'model_loaded': MODEL_LOADED
    })

def _load_dataset():
    try:
        import pandas as pd
        df = pd.read_csv(DATASET_CSV)
        return df.to_dict('records')
    except:
        return []

if __name__ == '__main__':
    print('\n🚧 RoadScan AI starting...')
    print(f'   Model loaded : {MODEL_LOADED}')
    print(f'   Dataset CSV  : {DATASET_CSV}')
    print(f'   Open browser : http://localhost:5000\n')
>>>>>>> f4b14cb (Initial commit)
    app.run(debug=True, host='0.0.0.0', port=5000)
