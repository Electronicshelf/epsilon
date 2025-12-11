"""
SentriLens Mini API - Text-Only Compliance Checker
Simple REST API for text compliance analysis

Requirements:
    pip install flask

Run:
    python app.py

API Endpoints:
    GET  /                  - Welcome message
    GET  /health           - Health check
    POST /analyze          - Analyze text
    GET  /rules            - List available rules
"""

from flask import Flask, request, jsonify
from datetime import datetime
import json

app = Flask(__name__)


# ============================================================================
# COMPLIANCE RULES
# ============================================================================

RULES_DATABASE = {
    "biopharma": {
        "prohibited": ["cure", "guaranteed", "no side effects", "100% safe", "miracle"],
        "warning": ["instant", "overnight", "breakthrough", "secret formula"],
        "severity": "HIGH"
    },
    "finance": {
        "prohibited": ["guaranteed returns", "risk-free", "get rich quick", "no risk"],
        "warning": ["limited time", "act now", "exclusive offer"],
        "severity": "HIGH"
    },
    "ads": {
        "prohibited": ["100% safe", "guaranteed", "miracle"],
        "warning": ["instant", "overnight", "limited time"],
        "severity": "MEDIUM"
    }
}


# ============================================================================
# ANALYSIS ENGINE
# ============================================================================

def analyze_text(content, domain="general"):
    """Analyze text content for compliance violations"""
    
    violations = []
    content_lower = content.lower()
    
    # Get domain rules
    rules = RULES_DATABASE.get(domain, RULES_DATABASE.get("ads"))
    
    # Check prohibited terms
    for term in rules["prohibited"]:
        if term.lower() in content_lower:
            violations.append({
                "term": term,
                "severity": "HIGH",
                "type": "PROHIBITED",
                "message": f"Prohibited claim detected: '{term}'"
            })
    
    # Check warning terms
    for term in rules["warning"]:
        if term.lower() in content_lower:
            violations.append({
                "term": term,
                "severity": "MEDIUM",
                "type": "WARNING",
                "message": f"Warning keyword detected: '{term}'"
            })
    
    # Calculate risk score
    risk_score = min(0.1 + (len(violations) * 0.2), 1.0)
    
    # Determine risk level
    if risk_score < 0.3:
        risk_level = "LOW"
    elif risk_score < 0.6:
        risk_level = "MEDIUM"
    elif risk_score < 0.85:
        risk_level = "HIGH"
    else:
        risk_level = "CRITICAL"
    
    # Generate suggestions
    suggestions = []
    if violations:
        if any(v["type"] == "PROHIBITED" for v in violations):
            suggestions.append("Remove or rephrase prohibited claims")
        if any("cure" in v["term"] for v in violations):
            suggestions.append("Replace 'cure' with 'manage' or 'support'")
        if any("guaranteed" in v["term"] for v in violations):
            suggestions.append("Remove absolute guarantees")
    
    return {
        "risk_score": round(risk_score, 2),
        "risk_level": risk_level,
        "violations": violations,
        "violation_count": len(violations),
        "suggestions": suggestions,
        "domain": domain,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/', methods=['GET'])
def home():
    """Welcome endpoint"""
    return jsonify({
        "app": "SentriLens Mini API",
        "version": "0.1.0",
        "description": "Text compliance analysis API",
        "endpoints": {
            "health": "/health",
            "analyze": "/analyze (POST)",
            "rules": "/rules"
        },
        "example": {
            "url": "/analyze",
            "method": "POST",
            "body": {
                "content": "Your text here",
                "domain": "biopharma"
            }
        }
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Analyze text content for compliance violations
    
    Request Body:
        {
            "content": "Text to analyze",
            "domain": "biopharma" (optional, default: general)
        }
    
    Response:
        {
            "risk_score": 0.5,
            "risk_level": "MEDIUM",
            "violations": [...],
            "suggestions": [...]
        }
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "Invalid request",
                "message": "Request body must be JSON"
            }), 400
        
        # Validate content
        content = data.get('content', '').strip()
        if not content:
            return jsonify({
                "error": "Validation error",
                "message": "Content cannot be empty"
            }), 400
        
        # Get domain
        domain = data.get('domain', 'general').lower()
        
        # Analyze
        result = analyze_text(content, domain)
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route('/rules', methods=['GET'])
def get_rules():
    """Get available compliance rules"""
    
    rules_summary = {}
    for domain, rules in RULES_DATABASE.items():
        rules_summary[domain] = {
            "prohibited_count": len(rules["prohibited"]),
            "warning_count": len(rules["warning"]),
            "severity": rules["severity"]
        }
    
    return jsonify({
        "domains": list(RULES_DATABASE.keys()),
        "rules_summary": rules_summary,
        "total_rules": sum(
            len(r["prohibited"]) + len(r["warning"]) 
            for r in RULES_DATABASE.values()
        )
    })


@app.route('/rules/<domain>', methods=['GET'])
def get_domain_rules(domain):
    """Get rules for specific domain"""
    
    domain = domain.lower()
    if domain not in RULES_DATABASE:
        return jsonify({
            "error": "Not found",
            "message": f"Domain '{domain}' not found",
            "available_domains": list(RULES_DATABASE.keys())
        }), 404
    
    return jsonify({
        "domain": domain,
        "rules": RULES_DATABASE[domain]
    })


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Not found",
        "message": "Endpoint not found"
    }), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        "error": "Internal server error",
        "message": str(e)
    }), 500


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 SentriLens Mini API")
    print("=" * 60)
    print("Server starting on http://localhost:5000")
    print()
    print("Endpoints:")
    print("  GET  /            - API info")
    print("  GET  /health      - Health check")
    print("  POST /analyze     - Analyze text")
    print("  GET  /rules       - List rules")
    print()
    print("Example:")
    print("  curl -X POST http://localhost:5000/analyze \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '{\"content\": \"Guaranteed cure!\", \"domain\": \"biopharma\"}'")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
