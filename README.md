# How to Run SentriLens Mini API

**Super simple guide - No experience needed!**

---

## 🎯 Goal

Get the API running so you can test it in your browser or with commands.

---

## ✅ Step 1: Check Python

Open terminal and type:

```bash
python --version
```

**Should show:** Python 3.8 or higher

If not working, try:
```bash
python3 --version
```

**If Python is not installed:** Download from [python.org](https://python.org)

---

## ✅ Step 2: Go to Project Folder

```bash
cd ~/PycharmProjects/sentrilens-mini-api
```

**Check you're in the right place:**
```bash
ls
```

**Should see these files:**
- app.py
- README.md
- requirements.txt
- test_api.py

---

## ✅ Step 3: Install Flask (One Time Only)

```bash
pip install flask
pip install flask-cors
```

**If that doesn't work, try:**
```bash
pip3 install flask
pip3 install flask-cors
```

**Wait for it to finish** (takes ~30 seconds)

---

## ✅ Step 4: Start the API

```bash
python app.py
```

**You should see this:**
```
============================================================
🚀 SentriLens Mini API
============================================================
Server starting on http://localhost:5000

Endpoints:
  GET  /            - API info
  GET  /health      - Health check
  POST /analyze     - Analyze text
  GET  /rules       - List rules
============================================================
 * Running on http://0.0.0.0:5000
```

**✨ SUCCESS! The API is now running!**

⚠️ **IMPORTANT:** Keep this terminal window open! Don't close it!

---

## ✅ Step 5: Test It

### Option A: Using Browser (Easiest)

1. **Open a web browser**
2. **Go to:** http://localhost:5000/health
3. **You should see:**
   ```json
   {
     "status": "ok",
     "timestamp": "2025-12-11T..."
   }
   ```

**🎉 It's working!**

### Option B: Using Terminal (Open NEW Terminal)

**Open a NEW terminal** (keep the first one running)

```bash
curl http://localhost:5000/health
```

**Should show:**
```json
{"status":"ok","timestamp":"..."}
```

---

## 🌐 Using the Web Interface

### Create the HTML Page

1. **In the same folder** (`sentrilens-mini-api`), create a file called `index.html`
2. **Copy the HTML code** from the previous message into it
3. **Double-click** `index.html` to open in browser
4. **Use the form** to test compliance checking!

---

## 🧪 Test with Commands

**Open a NEW terminal** (keep API running in the first one)

```bash
# Go to the project folder
cd ~/PycharmProjects/sentrilens-mini-api

# Test 1: Check health
curl http://localhost:5000/health

# Test 2: Analyze text
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"content": "Guaranteed cure!", "domain": "biopharma"}'
```

---

## 🛑 How to Stop the API

In the terminal where the API is running:

**Press:** `Ctrl + C`

**You'll see:** `Keyboard interrupt received`

**To start again:** `python app.py`

---

## 📋 Quick Reference

| Action | Command |
|--------|---------|
| **Start API** | `python app.py` |
| **Stop API** | Press `Ctrl + C` |
| **Test in browser** | http://localhost:5000/health |
| **Run tests** | `python test_api.py` |

---

## ❓ Common Problems

### Problem 1: "pip: command not found"

**Try:**
```bash
pip3 install flask
```

### Problem 2: "Port 5000 already in use"

**Solution:**
```bash
# Kill the process using port 5000
lsof -ti:5000 | xargs kill -9

# Then start again
python app.py
```

### Problem 3: "Connection refused"

**The API is not running!**

**Solution:**
1. Check terminal where you ran `python app.py`
2. Make sure it says "Running on http://0.0.0.0:5000"
3. If not, start it: `python app.py`

### Problem 4: "Cannot find app.py"

**You're in the wrong folder!**

**Solution:**
```bash
cd ~/PycharmProjects/sentrilens-mini-api
ls  # Should show app.py
python app.py
```

### Problem 5: "ModuleNotFoundError: No module named 'flask'"

**Flask is not installed!**

**Solution:**
```bash
pip install flask
```

---

## 🎯 Complete Workflow

### Terminal 1 (API Server)
```bash
cd ~/PycharmProjects/sentrilens-mini-api
python app.py
# Keep this running!
```

### Terminal 2 (Testing)
```bash
cd ~/PycharmProjects/sentrilens-mini-api
curl http://localhost:5000/health
```

### Browser
```
Open: http://localhost:5000/
Or: Open index.html file
```

---

## 📱 What Each Endpoint Does

| URL | What it does |
|-----|--------------|
| http://localhost:5000/ | Shows API info |
| http://localhost:5000/health | Health check (is it working?) |
| http://localhost:5000/rules | Shows all compliance rules |
| http://localhost:5000/analyze | Checks text (POST only) |

---

## ✨ You're Done!

**What you can do now:**
- ✅ Test compliance checking
- ✅ Try different domains (biopharma, finance, ads)
- ✅ Build your own apps using this API
- ✅ Show it to others

**Need help?** 
- Run `python test_api.py` to verify everything works
- Check README.md for detailed docs

---

**Made with ❤️ for easy learning**
