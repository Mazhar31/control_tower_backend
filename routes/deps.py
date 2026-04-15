from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from auth import decode_token

bearer = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload
