import urllib.request, json

print("=" * 55)
print("  Testing Patient Intake Triage Assistant API")
print("=" * 55)

# Test 1: GET /
try:
    req = urllib.request.urlopen('http://localhost:8000/')
    print(f"\n[1] GET /            -> {req.status} OK - Page loaded")
except Exception as e:
    print(f"\n[1] GET /            -> FAILED: {e}")

# Test 2: POST /api/start
session_id = None
try:
    req = urllib.request.Request(
        'http://localhost:8000/api/start',
        data=b'{}',
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    session_id = data.get('session_id', '')
    greeting = data.get('message', '')
    print(f"[2] POST /api/start  -> {resp.status} OK")
    print(f"    Session ID : {session_id[:16]}...")
    print(f"    Greeting   : {greeting[:70]}...")
except Exception as e:
    print(f"[2] POST /api/start  -> FAILED: {e}")

# Test 3: POST /api/chat
if session_id:
    try:
        payload = json.dumps({
            'session_id': session_id,
            'message': 'I have a high fever and my neck feels very stiff'
        }).encode()
        req = urllib.request.Request(
            'http://localhost:8000/api/chat',
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        has_note = data.get('note') is not None
        msg = data.get('message', '')
        print(f"[3] POST /api/chat   -> {resp.status} OK")
        print(f"    Response   : {msg[:70]}...")
        print(f"    Note ready : {has_note}")
        if has_note:
            print(f"    Urgency Lvl: {data['note']['urgency_level']}")
            print(f"    Rule cited : {'FV-01' in data['note']['raw']}")
    except Exception as e:
        print(f"[3] POST /api/chat   -> FAILED: {e}")

print("\n" + "=" * 55)
print("  All tests complete!")
print("  Open: http://localhost:8000")
print("=" * 55)
