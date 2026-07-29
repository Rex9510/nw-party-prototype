"""Generate a JWT token directly using backend code."""
import sys, os
sys.path.insert(0, r'E:\new party\nw-party-prototype\V1-MVP版本\backend')
import asyncio
from app.core.security import create_access_token

token = create_access_token(1, extra={"role": "system_admin"})
print(token)
