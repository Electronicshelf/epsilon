# SentriLens Mini API - Example Commands

# ==============================================================================
# BASIC COMMANDS
# ==============================================================================

# 1. Check if API is running
curl http://localhost:5000/health

# 2. Get API information
curl http://localhost:5000/

# 3. Get all rules
curl http://localhost:5000/rules

# 4. Get rules for specific domain
curl http://localhost:5000/rules/biopharma

# ==============================================================================
# ANALYZE TEXT - Examples
# ==============================================================================

# Example 1: Safe Content (LOW risk)
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Our product may help support your wellness goals when used as directed.",
    "domain": "biopharma"
  }'

# Example 2: Risky Content (HIGH risk)
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Guaranteed to cure diabetes with no side effects!",
    "domain": "biopharma"
  }'

# Example 3: Finance Content
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Get rich quick with guaranteed returns and zero risk!",
    "domain": "finance"
  }'

# Example 4: General Ads
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Limited time offer! Instant results overnight!",
    "domain": "ads"
  }'

# ==============================================================================
# DIFFERENT DOMAINS
# ==============================================================================

# Biopharma
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"content": "Miracle cure for all diseases!", "domain": "biopharma"}'

# Finance
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"content": "Risk-free investment with guaranteed profits!", "domain": "finance"}'

# Ads
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"content": "100% safe and instant results!", "domain": "ads"}'

# ==============================================================================
# ERROR TESTING
# ==============================================================================

# Empty content (should return 400 error)
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"content": "", "domain": "biopharma"}'

# Invalid endpoint (should return 404)
curl http://localhost:5000/invalid

# ==============================================================================
# PRETTY PRINTING WITH JQ
# ==============================================================================

# Install jq: brew install jq (Mac) or apt-get install jq (Linux)

# Pretty print health check
curl -s http://localhost:5000/health | jq .

# Pretty print analysis result
curl -s -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"content": "Guaranteed cure!", "domain": "biopharma"}' | jq .

# Get just the risk level
curl -s -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"content": "Guaranteed cure!", "domain": "biopharma"}' | jq -r '.risk_level'

# Count violations
curl -s -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"content": "Guaranteed cure!", "domain": "biopharma"}' | jq '.violation_count'

# ==============================================================================
# SAVE TO FILE
# ==============================================================================

# Save result to file
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"content": "Your text here", "domain": "biopharma"}' \
  -o result.json

# Save and view
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"content": "Your text here", "domain": "biopharma"}' | tee result.json

# ==============================================================================
# BATCH TESTING
# ==============================================================================

# Test multiple texts (bash script)
for text in "Cure all diseases" "Safe and effective" "Guaranteed results"; do
  echo "Testing: $text"
  curl -s -X POST http://localhost:5000/analyze \
    -H "Content-Type: application/json" \
    -d "{\"content\": \"$text\", \"domain\": \"biopharma\"}" | jq -r '.risk_level'
  echo "---"
done

# ==============================================================================
# TIMING
# ==============================================================================

# Measure response time
time curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"content": "Test content", "domain": "biopharma"}'

# Show only time
curl -w "\nTime: %{time_total}s\n" -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"content": "Test", "domain": "biopharma"}' -o /dev/null -s

# ==============================================================================
# WINDOWS POWERSHELL
# ==============================================================================

# Health check
Invoke-RestMethod -Uri http://localhost:5000/health

# Analyze text
$body = @{
    content = "Guaranteed cure!"
    domain = "biopharma"
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:5000/analyze -Method Post -Body $body -ContentType "application/json"
