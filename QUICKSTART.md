# 🚀 Quick Start Guide - SentriLens Mini API

Get up and running in 60 seconds!

## Step 1: Install Flask (10 seconds)

```bash
pip install flask
```

## Step 2: Run the API (5 seconds)

```bash
python app.py
```

You should see:
```
🚀 SentriLens Mini API
Server starting on http://localhost:5000
```

## Step 3: Test it! (45 seconds)

### Option A: Using curl (Command Line)

```bash
# Test 1: Health check
curl http://localhost:5000/health

# Test 2: Analyze text
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"content": "Guaranteed cure!", "domain": "biopharma"}'
```

### Option B: Using Browser

1. Open: http://localhost:5000/
2. You'll see API information

### Option C: Using Python

```python
import requests

result = requests.post(
    'http://localhost:5000/analyze',
    json={'content': 'Guaranteed cure!', 'domain': 'biopharma'}
).json()

print(f"Risk: {result['risk_level']}")
```

## Done! 🎉

Your API is working. Now try:

1. **Run tests**: `python test_api.py`
2. **See examples**: Open `examples.sh`
3. **Read docs**: Open `README.md`

## Common Issues

**Port 5000 in use?**
```bash
# Kill process
lsof -ti:5000 | xargs kill -9
```

**Flask not installed?**
```bash
pip install flask
```

**Can't connect?**
- Make sure `python app.py` is running
- Check http://localhost:5000/health in browser

## What's Next?

- Try different domains: `biopharma`, `finance`, `ads`
- Test your own text
- Integrate with your app
- Read README.md for full API docs

---

**Need help?** Check README.md or run `python test_api.py`
