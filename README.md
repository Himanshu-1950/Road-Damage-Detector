# 🚧 RoadScan AI — Road Damage Detection System
### CV Project | AI-Powered Road Damage Detection with Location & Deduplication

---

## 📦 Setup & Run

### Step 1 — Install dependencies
```bash
pip install flask werkzeug
```

### Step 2 — Run the app
```bash
cd road-damage-detector
python app.py
```

### Step 3 — Open in browser
```
http://localhost:5000
```

---

## 🔑 API Key Setup (for real AI detection)

The app uses Claude AI to detect road damage. Add your API key:

**Option A — Environment variable (recommended):**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python app.py
```

**Option B — Edit app.py:**
In `detect_damage_with_claude()`, add to headers:
```python
'x-api-key': 'sk-ant-YOUR_KEY_HERE',
```

Without an API key, the app uses a fallback demo response.

---

## ✨ Features

| Feature | Description |
|--------|-------------|
| 📸 Image Upload | Upload road photos (JPG, PNG, WEBP) |
| 🤖 AI Detection | Claude AI identifies damage type and severity |
| 📍 GPS Location | Auto-capture GPS or enter manually |
| 🔁 Deduplication | Rejects duplicate images (hash) and nearby locations (<100m) |
| 🗺️ Live Map | Dark map showing all damage reports with color-coded severity |
| 📊 Stats Dashboard | Total reports, critical/high counts, duplicates rejected |
| 🗑️ Report Management | View, browse, and delete reports |

## 🔍 Damage Types Detected
- Pothole
- Crack
- Surface Deterioration
- Edge Break
- Multiple Damage Types

## 📐 Severity Levels
- 🟢 **Low** — Minor surface issues
- 🟡 **Medium** — Moderate damage, schedule repair
- 🟠 **High** — Significant damage, urgent repair
- 🔴 **Critical** — Severe damage, immediate action required

## 🛠 Tech Stack
- **Backend**: Python + Flask
- **AI**: Anthropic Claude API (Vision)
- **Database**: SQLite (no setup needed)
- **Frontend**: Vanilla JS + CSS
- **Maps**: Leaflet.js + CartoDB Dark tiles
- **Dedup**: SHA-256 image hashing + Haversine distance

---

## 📁 Project Structure
```
road-damage-detector/
├── app.py              ← Main Flask server
├── requirements.txt    ← Dependencies
├── templates/
│   └── index.html      ← Frontend UI
├── uploads/            ← Stored road images (auto-created)
└── database/
    └── reports.db      ← SQLite database (auto-created)
```
