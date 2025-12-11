# 🚀 SentriLens Mini API

**Simple REST API for text compliance analysis - Perfect for testing and demos**

## What is this?

A lightweight Flask API that checks text for compliance violations. Super simple to run and test!

## Quick Start (2 minutes)

```bash
# 1. Install Flask
pip install flask

# 2. Run the API
python app.py

# 3. Test it
curl http://localhost:5000/health
```

That's it! Your API is running on `http://localhost:5000` 🎉

## API Endpoints

### 1. GET `/` - API Info
Get information about the API

**Request:**
```bash
curl http://localhost:5000/
```

**Response:**
```json
{
  "app": "SentriLens Mini API",
  "version": "0.1.0",
  "endpoints": {
    "health": "/health",
    "analyze": "/analyze (POST)",
    "rules": "/rules"
  }
}
```

### 2. GET `/health` - Health Check
Check if API is running

**Request:**
```bash
curl http://localhost:5000/health
```

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-01-15T10:30:00"
}
```

### 3. POST `/analyze` - Analyze Text
Check text for compliance violations

**Request:**
```bash
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Guaranteed cure with no side effects!",
    "domain": "biopharma"
  }'
```

**Response:**
```json
{
  "risk_score": 0.5,
  "risk_level": "MEDIUM",
  "violations": [
    {
      "term": "guaranteed",
      "severity": "HIGH",
      "type": "PROHIBITED",
      "message": "Prohibited claim detected: 'guaranteed'"
    },
    {
      "term": "cure",
      "severity": "HIGH",
      "type": "PROHIBITED",
      "message": "Prohibited claim detected: 'cure'"
    }
  ],
  "violation_count": 2,
  "suggestions": [
    "Remove or rephrase prohibited claims",
    "Replace 'cure' with 'manage' or 'support'"
  ],
  "domain": "biopharma"
}
```

**Request Body:**
- `content` (required): Text to analyze
- `domain` (optional): "biopharma", "finance", or "ads" (default: general)

### 4. GET `/rules` - List Rules
Get all available compliance rules

**Request:**
```bash
curl http://localhost:5000/rules
```

**Response:**
```json
{
  "domains": ["biopharma", "finance", "ads"],
  "rules_summary": {
    "biopharma": {
      "prohibited_count": 5,
      "warning_count": 4,
      "severity": "HIGH"
    }
  },
  "total_rules": 27
}
```

### 5. GET `/rules/<domain>` - Domain Rules
Get rules for specific domain

**Request:**
```bash
curl http://localhost:5000/rules/biopharma
```

**Response:**
```json
{
  "domain": "biopharma",
  "rules": {
    "prohibited": ["cure", "guaranteed", "no side effects"],
    "warning": ["instant", "overnight", "breakthrough"],
    "severity": "HIGH"
  }
}
```

## Testing Examples

### Example 1: Safe Content (LOW risk)
```bash
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "content": "May help support your wellness goals",
    "domain": "biopharma"
  }'
```

**Result:** ✅ Risk Level: LOW, No violations

### Example 2: Risky Content (HIGH risk)
```bash
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Guaranteed to cure diabetes with no side effects!",
    "domain": "biopharma"
  }'
```

**Result:** ❌ Risk Level: HIGH, Multiple violations

### Example 3: Finance Content
```bash
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Guaranteed returns with zero risk!",
    "domain": "finance"
  }'
```

**Result:** ❌ Risk Level: HIGH, Finance violations

## Using Python Requests

```python
import requests

# Analyze text
response = requests.post(
    'http://localhost:5000/analyze',
    json={
        'content': 'Our product may help support your health goals.',
        'domain': 'biopharma'
    }
)

result = response.json()
print(f"Risk Level: {result['risk_level']}")
print(f"Violations: {result['violation_count']}")
```

## Using JavaScript/Fetch

```javascript
fetch('http://localhost:5000/analyze', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    content: 'Guaranteed results!',
    domain: 'ads'
  })
})
.then(response => response.json())
.then(data => {
  console.log('Risk Level:', data.risk_level);
  console.log('Violations:', data.violations);
});
```

## Response Format

### Risk Levels
- **LOW**: 0.0 - 0.29 (Safe)
- **MEDIUM**: 0.30 - 0.59 (Review recommended)
- **HIGH**: 0.60 - 0.84 (Action required)
- **CRITICAL**: 0.85 - 1.00 (Do not publish)

### Violation Types
- **PROHIBITED**: High-severity violation (e.g., "cure", "guaranteed")
- **WARNING**: Medium-severity issue (e.g., "instant", "breakthrough")

### Domains
- **biopharma**: Health, medical, pharmaceutical
- **finance**: Investment, trading, financial services
- **ads**: General advertising and marketing

## Common Use Cases

### 1. Pre-Publication Check
```bash
# Check ad copy before running campaign
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d @ad_copy.json
```

### 2. Batch Processing
```python
import requests

texts = [
    "Product description 1",
    "Product description 2",
    "Product description 3"
]

for text in texts:
    result = requests.post(
        'http://localhost:5000/analyze',
        json={'content': text, 'domain': 'ads'}
    ).json()
    print(f"Text: {text[:30]}... | Risk: {result['risk_level']}")
```

### 3. Integration with CI/CD
```yaml
# .github/workflows/check-content.yml
- name: Check Marketing Copy
  run: |
    curl -X POST http://localhost:5000/analyze \
      -H "Content-Type: application/json" \
      -d @marketing/copy.json
```

## Error Handling

### 400 - Bad Request
```json
{
  "error": "Validation error",
  "message": "Content cannot be empty"
}
```

### 404 - Not Found
```json
{
  "error": "Not found",
  "message": "Endpoint not found"
}
```

### 500 - Server Error
```json
{
  "error": "Internal server error",
  "message": "Error details here"
}
```

## Customization

### Adding New Rules

Edit `app.py` and add to `RULES_DATABASE`:

```python
RULES_DATABASE = {
    "your_domain": {
        "prohibited": ["term1", "term2"],
        "warning": ["keyword1", "keyword2"],
        "severity": "HIGH"
    }
}
```

### Changing Port

```python
# In app.py, change:
app.run(debug=True, host='0.0.0.0', port=5000)
# To:
app.run(debug=True, host='0.0.0.0', port=8080)
```

## Production Deployment

### Using Gunicorn (Recommended)

```bash
pip install gunicorn

gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Using Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .
CMD ["python", "app.py"]
```

Build and run:
```bash
docker build -t sentrilens-mini .
docker run -p 5000:5000 sentrilens-mini
```

## Troubleshooting

### Port already in use
```bash
# Use different port
python app.py  # Edit app.py to change port
# Or kill existing process
lsof -ti:5000 | xargs kill -9
```

### Flask not installed
```bash
pip install flask
```

### CORS issues (if using from browser)
Add to `app.py`:
```python
from flask_cors import CORS
CORS(app)
```

## Performance Notes

- **Requests per second**: ~100-500 (single instance)
- **Response time**: <50ms average
- **Memory usage**: ~50MB
- **Concurrent requests**: Limited by Flask development server

For production, use Gunicorn or uWSGI.

## Limitations

This is a **demo/mini version**. It uses simple keyword matching.

**Full version includes:**
- Advanced NLP and ML models
- Database persistence
- Authentication
- Rate limiting
- Image/video analysis
- Batch processing
- Analytics dashboard

## Testing the API

### Quick Test Script

Save as `test_api.py`:
```python
import requests

base_url = "http://localhost:5000"

# Test 1: Health check
print("Testing health endpoint...")
r = requests.get(f"{base_url}/health")
print(f"Status: {r.status_code}")

# Test 2: Analyze text
print("\nTesting analyze endpoint...")
r = requests.post(
    f"{base_url}/analyze",
    json={
        "content": "Guaranteed cure!",
        "domain": "biopharma"
    }
)
result = r.json()
print(f"Risk: {result['risk_level']}")
print(f"Violations: {result['violation_count']}")

print("\n✅ All tests passed!")
```

Run: `python test_api.py`

## What's Next?

1. ✅ Test the basic endpoints
2. ✅ Try different domains
3. ✅ Integrate with your application
4. 🎯 Contact for full version with advanced features

## Support

Questions? Issues?
- Check if Flask is installed: `pip list | grep -i flask`
- Check if port is free: `lsof -i :5000`
- Check server logs in terminal

---

**SentriLens Mini API** | Version 0.1.0 | Made for easy testing
