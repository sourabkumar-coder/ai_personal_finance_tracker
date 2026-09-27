import urllib.request
import json
data = json.dumps({
    "name": "Jordan",
    "email": "jordan3@college.edu",
    "password": "password123",
    "monthly_allowance": 1000,
    "currency": "INR",
    "college_year": "Freshman"
}).encode("utf-8")
req = urllib.request.Request("http://localhost:8000/api/auth/register", data=data, headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req) as response:
        print(response.status)
        print(response.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print(e.code)
    print(e.read().decode("utf-8"))
