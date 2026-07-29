#!/usr/bin/env python3
"""Check OpenAPI schema for Activity schemas"""
import json, sys
d = json.load(sys.stdin)
sch = d.get('components',{}).get('schemas',{})
for k in sorted(sch.keys()):
    if 'Activity' in k:
        props = sch[k].get('properties',{})
        print(f'=== {k} ===')
        for pk, pv in props.items():
            t = pv.get('type','?')
            print(f'  {pk}: type={json.dumps(t) if isinstance(t,str) else t}, title={pv.get("title","")}')
        print()
