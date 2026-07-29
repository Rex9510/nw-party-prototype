import sys, importlib
print('=== sys.path ===')
for p in sys.path:
    print(p)
print()
try:
    spec = importlib.util.find_spec('app.schemas.activity')
    print('=== spec ===')
    print('origin:', spec.origin)
    print('name:', spec.name)
    print('loader:', spec.loader)
except Exception as e:
    print('ERROR:', e)
print()
print('=== app related modules ===')
for k, v in sorted(sys.modules.items()):
    if 'app' in k:
        print(k, getattr(v, '__file__', 'NO_FILE'))
