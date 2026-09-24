import json, urllib.request
resp = urllib.request.urlopen('https://gentokendev-default-rtdb.firebaseio.com/licenses.json', timeout=10)
data = json.loads(resp.read().decode())
for key, val in data.items():
    print(f"  {key} -> {val['user']} | vence: {val['expiry_date']} | activa: {val['active']}")
