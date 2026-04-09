<<<<<<< HEAD
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
=======
# 🚧 RoadScan AI — Complete Road Damage Detection System
### CV Project | EfficientNet-B4 | Train → Test → Deploy → Auto-Dataset

---

## 🗂️ Project Structure
```
roadscan/
├── app.py                      ← Flask web app (loads trained model)
├── requirements.txt
├── road_damage_model.pth       ← PUT HERE after training in Colab
├── model_metadata.json         ← PUT HERE after training in Colab
├── live_dataset.csv            ← Auto-created, grows with every upload
├── templates/
│   └── index.html              ← Full web UI
└── uploads/
    ├── damaged/                ← Auto-saved damaged road images
    └── clean/                  ← Auto-saved clean road images
```

---

## 🚀 STEP 1 — Train in Google Colab

1. Open **RoadScan_AI_Complete.ipynb** in Google Colab
2. Set runtime: **Runtime → Change runtime type → T4 GPU**
3. Run all cells in order:
   - CELL 1: Install packages
   - CELL 2: Download RDD2022 real dataset (India + Japan, ~47k images)
   - CELL 3: (Skip if CELL 2 worked) — generates synthetic data
   - CELL 4: Prepare DataLoaders
   - CELL 5: Build EfficientNet-B4 model
   - CELL 6: 3-stage training (warmup → fine-tune → full fine-tune)
   - CELL 7: Full evaluation report
   - CELL 8: Test with your own image + auto-save
   - CELL 10: Download model files

4. Download these files from Colab:
   - `road_damage_model.pth`    ← trained model weights
   - `model_metadata.json`      ← model config
   - `road_damage_live_dataset.csv` ← initial dataset

---

## 🌐 STEP 2 — Run the Flask Web App

```bash
# 1. Place downloaded files in the roadscan/ folder:
#    road_damage_model.pth
#    model_metadata.json

# 2. Install dependencies
pip install flask werkzeug pandas torch torchvision timm Pillow

# 3. Run the app
cd roadscan
python app.py

# 4. Open browser
# → http://localhost:5000
>>>>>>> f4b14cb (Initial commit)
```

---

<<<<<<< HEAD
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
=======
## ✨ How It Works

### Detection Flow:
```
User uploads photo + GPS location
         ↓
EfficientNet-B4 model runs inference
         ↓
P(damaged) ≥ 0.5 → DAMAGED  |  P(damaged) < 0.5 → CLEAN
         ↓
Image saved to uploads/damaged/ or uploads/clean/
         ↓
Row appended to live_dataset.csv
         ↓
Map pin added on Leaflet.js dark map
```

### Model Architecture:
```
Input (224×224×3)
    ↓
EfficientNet-B4 backbone (pretrained ImageNet)
    ↓
Global Average Pooling (1792-dim features)
    ↓
Dropout(0.3) → Linear(512) → BN → ReLU
    ↓
Dropout(0.15) → Linear(128) → ReLU
    ↓
Linear(2) → Softmax
    ↓
[P(clean), P(damaged)]
```

### Training Strategy (3 stages):
| Stage | Epochs | LR      | What's trained           |
|-------|--------|---------|--------------------------|
| 1     | 5      | 1e-3    | Head only (warmup)       |
| 2     | 15     | 3e-4    | Head + last 2 BB blocks  |
| 3     | 5      | 5e-5    | Full network (fine-tune) |

### Dataset:
- **Real data**: RDD2022 — 47,000 images (Japan, India, Norway, USA)
- **Labels**: Damaged (D00/D10/D20/D40) vs Clean
- **Split**: 70% train / 15% val / 15% test
- **Augmentation**: flip, rotation, color jitter, perspective, erasing

### Expected Accuracy:
| Dataset      | Expected Accuracy |
|--------------|------------------|
| Synthetic    | ~88-92%          |
| RDD2022 real | ~93-97%          |

---

## 📊 API Endpoints

| Endpoint         | Method | Description              |
|------------------|--------|--------------------------|
| `/`              | GET    | Web UI                   |
| `/api/detect`    | POST   | Upload image, get result |
| `/api/dataset`   | GET    | All saved records        |
| `/api/stats`     | GET    | Summary statistics       |

### POST /api/detect fields:
- `image` — file (JPG/PNG/WEBP)
- `location_name` — string
- `lat` — float
- `lng` — float

### Response:
```json
{
  "status": "success",
  "image_id": "ABC123",
  "label": "damaged",
  "is_damaged": true,
  "damage_prob": 87.3,
  "clean_prob": 12.7,
  "confidence": 87.3,
  "location_name": "MG Road, Nagpur",
  "latitude": 21.1458,
  "longitude": 79.0882,
  "saved_to_dataset": true
}
```

---

## 🛠 Tech Stack
| Component   | Technology                       |
|-------------|----------------------------------|
| AI Model    | EfficientNet-B4 (timm library)   |
| Training    | PyTorch + 3-stage fine-tuning    |
| Dataset     | RDD2022 (real) / Synthetic       |
| Backend     | Python + Flask                   |
| Database    | CSV (live_dataset.csv)           |
| Frontend    | Vanilla JS + CSS                 |
| Maps        | Leaflet.js + CartoDB Dark        |
| Colab Demo  | Gradio (public URL)              |
>>>>>>> f4b14cb (Initial commit)
