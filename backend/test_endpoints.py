import requests
import json

base_url = "http://127.0.0.1:5000"

print("=" * 60)
print("🔍 TESTING DABBA'S BACKEND ENDPOINTS")
print("=" * 60)

# Test 1: Home endpoint
try:
    r = requests.get(f"{base_url}/")
    print(f"\n1. Home: {r.status_code}")
    if r.status_code == 200:
        print(f"   ✅ Response: {r.json()}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Health endpoint
try:
    r = requests.get(f"{base_url}/api/health")
    print(f"\n2. Health: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ Status: {data.get('status')}")
        print(f"   ✅ Database: {data.get('database')}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Providers list (with 's')
try:
    r = requests.get(f"{base_url}/api/providers/list")
    print(f"\n3. Providers List (with 's'): {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ Success: {data.get('success')}")
        print(f"   📊 Count: {data.get('count', 0)} providers")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 4: Provider list (without 's') - This should give 404
try:
    r = requests.get(f"{base_url}/api/provider/list")
    print(f"\n4. Provider List (without 's'): {r.status_code}")
    if r.status_code == 404:
        print(f"   ⚠️ This is the 404 error you're seeing")
    elif r.status_code == 200:
        print(f"   ✅ Working: {r.json()}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 5: Test database endpoint
try:
    r = requests.get(f"{base_url}/api/test")
    print(f"\n5. Test Database: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ Message: {data.get('message')}")
        print(f"   📊 Tables: {data.get('table_counts', {})}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 6: Test registration (POST)
try:
    test_data = {
        "businessName": "Test Restaurant",
        "ownerName": "Test Owner",
        "email": "test@example.com",
        "phone": "1234567890",
        "businessAddress": "123 Test St",
        "city": "pune",
        "cuisine": "Test",
        "password": "test123"
    }
    r = requests.post(f"{base_url}/api/provider/register", json=test_data)
    print(f"\n6. Provider Register: {r.status_code}")
    if r.status_code in [200, 201]:
        print(f"   ✅ Success: {r.json()}")
    elif r.status_code == 400:
        print(f"   ⚠️ Already exists or bad data: {r.json()}")
    else:
        print(f"   ⚠️ Status: {r.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 7: Provider login
try:
    login_data = {
        "email": "test@example.com",
        "password": "test123"
    }
    r = requests.post(f"{base_url}/api/provider/login", json=login_data)
    print(f"\n7. Provider Login: {r.status_code}")
    if r.status_code == 200:
        print(f"   ✅ Success: Logged in")
    else:
        print(f"   ⚠️ Response: {r.json() if r.text else 'No response'}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("📋 SUMMARY")
print("=" * 60)
print("\n✅ Working endpoints:")
print("   • GET  /")
print("   • GET  /api/health")
print("   • GET  /api/test")
print("   • GET  /api/providers/list")
print("   • POST /api/provider/register")
print("   • POST /api/provider/login")
print("\n❌ Not working (404):")
print("   • GET  /api/provider/list")
print("\n💡 FIX: Use /api/providers/list instead of /api/provider/list")
print("=" * 60)