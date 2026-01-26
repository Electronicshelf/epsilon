# SentriLens Compliance API

API-first advertising compliance system for Meta image ads (v1).

## Architecture

This repository follows a clean, minimal architecture with clear separation of concerns:

```
api/          - Request/response handling (Flask routes)
pipeline/     - Orchestration: signals → violations → outcome
models/       - Wrappers for OCR / vision / embeddings / VLM
schemas/      - Internal data models (Asset, Signal, Violation, Evidence, Outcome)
webapp/       - Thin frontend client (no business logic)
```

## Data Flow

```
Image Upload → API → Pipeline → Models → Signals → Rule Checking → Violations → Outcome
```

1. **API** receives image upload
2. **Pipeline** orchestrates the analysis:
   - Extracts signals using **Models** (OCR, Vision, Embeddings, VLM)
   - Checks signals against compliance rules
   - Generates violations with evidence
   - Calculates risk score and status
3. **Outcome** returned to client

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the API

```bash
python app.py
```

The API will start on `http://localhost:5000`

## Configuration

- **`VLM_API_KEY`**: Optional. If set, GPT‑4o Vision is used to attach a short explainability note **only** when routing is `borderline_requires_context` and an OCR-triggered violation already exists. If unset or the API fails, a fallback message is attached.

### 3. Use the Web App

Open `webapp/index.html` in your browser and upload an image.

### 4. Test the API

```bash
python test_api.py
```

## API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `POST /analyze` - Analyze image for compliance
  - Form data: `image` (file), `domain` (optional: biopharma, finance, ads)
- `GET /rules` - List available compliance rules

## Example Usage

### Using the Test Script (Easiest)

```bash
# Test with a real image
python test_with_real_image.py path/to/your/image.jpg

# With specific domain
python test_with_real_image.py path/to/your/image.jpg --domain biopharma
```

### Using curl

```bash
# V1 API endpoint
curl -X POST http://localhost:5000/v1/ads/meta/image/check \
  -F "image=@your_image.jpg" \
  -F "domain=ads" | jq .

# Legacy endpoint
curl -X POST http://localhost:5000/analyze \
  -F "image=@your_image.jpg" \
  -F "domain=biopharma"
```

### Using Python

```python
import requests

with open('image.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:5000/v1/ads/meta/image/check',
        files={'image': f},
        data={'domain': 'ads'}
    )
    
result = response.json()
print(f"Risk Score: {result['risk_score']}")
print(f"Verdict: {result['verdict']}")
print(f"Violations: {len(result['violations'])}")
```

### Using the Web App

1. Open `webapp/index.html` in your browser
2. Upload an image
3. Select domain
4. Click "Analyze Compliance"

## Project Structure

```
epsilon/
├── api/              # API routes and request handling
│   ├── __init__.py
│   └── routes.py
├── pipeline/         # Compliance pipeline orchestration
│   ├── __init__.py
│   └── engine.py
├── models/           # Model wrappers (OCR, Vision, VLM)
│   ├── __init__.py
│   ├── ocr.py
│   ├── vision.py
│   └── vlm.py
├── schemas/          # Data models
│   ├── __init__.py
│   └── models.py
├── webapp/           # Frontend client
│   ├── index.html
│   └── README.md
├── app.py            # Application entry point
├── test_api.py       # API tests
└── requirements.txt
```

## Key Design Decisions

- **API-First**: Backend is a REST API, frontend is a consumer
- **Pipeline-Based**: Clear flow from signals to violations to outcome
- **Minimal**: No production infra, auth, or dashboards
- **OCR is primary**: Violations are triggered by OCR text matches (rules). Vision/embeddings/VLM are supporting evidence only.
- **Model integrations (current)**:
  - OCR: Tesseract (real)
  - Vision: Grounding DINO object detection (real; supporting evidence only)
  - Embeddings: SigLIP (real; optional similarity signals; supporting evidence only)
  - VLM: GPT‑4o Vision API (borderline-only explainability; never triggers violations)
- **Clear Separation**: Business logic in pipeline, not in API or webapp

## Data Models

- **Asset**: Input image with metadata
- **Signal**: Detected feature from models (text, objects, etc.)
- **Violation**: Compliance rule violation with severity
- **Evidence**: Supporting data for violations
- **Outcome**: Final compliance assessment

## Compliance Rules

Rules are defined in `pipeline/engine.py` and check for:
- Prohibited text claims (e.g., "cure", "guaranteed")
- Medical / health claims (`medical_health_claims`) (OCR-triggered; supporting evidence may include vision/embedding signals)
- Restricted objects/scenes
- Brand usage violations
- Contextual violations

## Development

The codebase is designed to be:
- **Readable**: Clear structure and minimal complexity
- **Extensible**: Easy to add new models or rules
- **Testable**: Clear separation allows unit testing

## Future Enhancements

- Expand policies and improve rule matching
- Load rules from database or config file
- Add image preview with violation overlays
- Support batch processing
- Add more sophisticated rule matching (NLP, regex)

## Notes

- Vision/embedding/VLM signals are used for **supporting evidence only** and must not create violations by themselves
- Rules are hardcoded but structured for easy extension
- Web app is a thin client with no business logic
- All compliance logic lives in the backend pipeline
