#!/usr/bin/env python3
"""
Quick test script to verify your Gemini API key works.
Run this locally before deploying to Render.

Usage:
    python test_gemini_key.py YOUR_API_KEY_HERE
"""

import sys
import requests

def test_gemini_key(api_key):
    """Test if a Gemini API key works."""
    
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print("❌ ERROR: Please provide your API key as argument")
        print("Usage: python test_gemini_key.py AIza...")
        return False
    
    print(f"🔍 Testing Gemini API key...")
    print(f"   Key length: {len(api_key)} characters")
    print(f"   Key starts with: {api_key[:10]}...")
    print()
    
    url = (
        "https://generativelanguage.googleapis.com/v1beta"
        f"/models/gemini-1.5-flash:generateContent?key={api_key}"
    )
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": "Say 'Hello, API test successful!'"}
                ]
            }
        ]
    }
    
    try:
        print("📡 Sending test request to Gemini API...")
        resp = requests.post(url, json=payload, timeout=10)
        
        print(f"📊 Response Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            result = data["candidates"][0]["content"]["parts"][0]["text"]
            print(f"✅ SUCCESS! Gemini responded:")
            print(f"   {result}")
            return True
        
        elif resp.status_code == 429:
            print("❌ ERROR: 429 Too Many Requests")
            print("   This means one of:")
            print("   1. You've hit the free tier rate limit")
            print("   2. Need to enable billing on your Google Cloud project")
            print("   3. API key quota exhausted")
            print()
            print("   Response body:")
            print(f"   {resp.text[:300]}")
            return False
        
        elif resp.status_code == 400:
            print("❌ ERROR: 400 Bad Request")
            print("   API key might be invalid or malformed")
            print()
            print("   Response body:")
            print(f"   {resp.text[:300]}")
            return False
        
        else:
            print(f"❌ ERROR: Unexpected status {resp.status_code}")
            print(f"   Response: {resp.text[:300]}")
            return False
    
    except requests.Timeout:
        print("❌ ERROR: Request timed out")
        return False
    
    except requests.RequestException as e:
        print(f"❌ ERROR: Request failed: {e}")
        return False
    
    except Exception as e:
        print(f"❌ ERROR: Unexpected error: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ ERROR: API key required")
        print()
        print("Usage:")
        print("    python test_gemini_key.py YOUR_API_KEY_HERE")
        print()
        print("Get your key from:")
        print("    https://aistudio.google.com/app/apikey")
        sys.exit(1)
    
    api_key = sys.argv[1]
    success = test_gemini_key(api_key)
    
    sys.exit(0 if success else 1)
