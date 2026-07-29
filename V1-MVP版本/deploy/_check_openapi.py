"""Check the OpenAPI schema for audience_category type."""
import json, urllib.request

resp = urllib.request.urlopen("http://127.0.0.1:8000/openapi.json")
d = json.loads(resp.read())

s = d["components"]["schemas"]["ActivityCreate"]
print("audience_category schema:", json.dumps(s["properties"]["audience_category"], indent=2))

# Also check ActivityUpdate
s2 = d["components"]["schemas"]["ActivityUpdate"]
print("\nActivityUpdate audience_category:", json.dumps(s2["properties"]["audience_category"], indent=2))
