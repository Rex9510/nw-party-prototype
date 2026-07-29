import sys, importlib, os
print('CWD:', os.getcwd())
print('=== sys.path ===')
for p in sys.path:
    print(p)
print()
print('=== find app.schemas.activity ===')
try:
    spec = importlib.util.find_spec('app.schemas.activity')
    print('FOUND spec.origin:', spec.origin)
except Exception as e:
    print('find ERROR:', e)
print()
# Try direct import
try:
    from app.schemas.activity import ActivityBase
    print('IMPORT OK')
    f = ActivityBase.model_fields.get('audience_category')
    print('audience_category field:', f)
    if f:
        print('  annotation:', f.annotation)
except Exception as e:
    print('IMPORT ERROR:', e)
print()
print('=== app modules loaded ===')
for k, v in sorted(sys.modules.items()):
    if k.startswith('app'):
        print(k, getattr(v, '__file__', 'NO_FILE'))
