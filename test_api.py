#!/usr/bin/env python3
"""
Test script for SentriLens Mini API
Run this to test all endpoints
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_health():
    """Test health endpoint"""
    print_section("TEST 1: Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ PASSED")
            return True
        else:
            print("❌ FAILED")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_info():
    """Test API info endpoint"""
    print_section("TEST 2: API Info")
    
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"App: {data.get('app')}")
        print(f"Version: {data.get('version')}")
        print(f"Endpoints: {list(data.get('endpoints', {}).keys())}")
        
        if response.status_code == 200:
            print("✅ PASSED")
            return True
        else:
            print("❌ FAILED")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_analyze_low_risk():
    """Test analysis with low risk content"""
    print_section("TEST 3: Analyze Text (LOW Risk)")
    
    try:
        payload = {
            "content": "Our product may help support your wellness goals.",
            "domain": "biopharma"
        }
        
        print(f"Request: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            f"{BASE_URL}/analyze",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\nStatus Code: {response.status_code}")
        result = response.json()
        print(f"Risk Level: {result.get('risk_level')}")
        print(f"Risk Score: {result.get('risk_score')}")
        print(f"Violations: {result.get('violation_count')}")
        
        if response.status_code == 200 and result.get('risk_level') == 'LOW':
            print("✅ PASSED")
            return True
        else:
            print("❌ FAILED")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_analyze_high_risk():
    """Test analysis with high risk content"""
    print_section("TEST 4: Analyze Text (HIGH Risk)")
    
    try:
        payload = {
            "content": "Guaranteed to cure diabetes with no side effects!",
            "domain": "biopharma"
        }
        
        print(f"Request: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            f"{BASE_URL}/analyze",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\nStatus Code: {response.status_code}")
        result = response.json()
        print(f"Risk Level: {result.get('risk_level')}")
        print(f"Risk Score: {result.get('risk_score')}")
        print(f"Violations: {result.get('violation_count')}")
        print(f"\nViolations Found:")
        for v in result.get('violations', []):
            print(f"  - {v.get('term')}: {v.get('message')}")
        
        if response.status_code == 200 and result.get('violation_count') > 0:
            print("✅ PASSED")
            return True
        else:
            print("❌ FAILED")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_rules():
    """Test rules endpoint"""
    print_section("TEST 5: Get Rules")
    
    try:
        response = requests.get(f"{BASE_URL}/rules")
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"Domains: {data.get('domains')}")
        print(f"Total Rules: {data.get('total_rules')}")
        
        if response.status_code == 200:
            print("✅ PASSED")
            return True
        else:
            print("❌ FAILED")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_domain_rules():
    """Test domain-specific rules"""
    print_section("TEST 6: Get Domain Rules")
    
    try:
        response = requests.get(f"{BASE_URL}/rules/biopharma")
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"Domain: {data.get('domain')}")
        rules = data.get('rules', {})
        print(f"Prohibited Terms: {len(rules.get('prohibited', []))}")
        print(f"Warning Terms: {len(rules.get('warning', []))}")
        
        if response.status_code == 200:
            print("✅ PASSED")
            return True
        else:
            print("❌ FAILED")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_error_handling():
    """Test error handling"""
    print_section("TEST 7: Error Handling (Empty Content)")
    
    try:
        payload = {
            "content": "",
            "domain": "biopharma"
        }
        
        response = requests.post(
            f"{BASE_URL}/analyze",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        print(f"Error: {result.get('error')}")
        print(f"Message: {result.get('message')}")
        
        if response.status_code == 400:
            print("✅ PASSED (Correctly rejected empty content)")
            return True
        else:
            print("❌ FAILED")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  🧪 SentriLens Mini API - Test Suite")
    print("="*60)
    print(f"  Testing: {BASE_URL}")
    print("  Make sure the API is running: python app.py")
    print("="*60)
    
    # Wait a moment for server
    time.sleep(1)
    
    # Run tests
    results = []
    results.append(("Health Check", test_health()))
    results.append(("API Info", test_info()))
    results.append(("Low Risk Analysis", test_analyze_low_risk()))
    results.append(("High Risk Analysis", test_analyze_high_risk()))
    results.append(("List Rules", test_rules()))
    results.append(("Domain Rules", test_domain_rules()))
    results.append(("Error Handling", test_error_handling()))
    
    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\n\n👋 Tests interrupted")
        exit(1)
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to API")
        print("Make sure the API is running: python app.py")
        exit(1)
