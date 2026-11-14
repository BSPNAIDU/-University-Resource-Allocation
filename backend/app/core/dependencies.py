from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.core.security import decode_access_token
from backend.app.models.university import University


bearer_scheme = HTTPBearer()


def get_current_university(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> University:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        university_id = payload.get("sub")

        if university_id is None:
            raise credentials_exception

        university_id = int(university_id)

    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    university = db.query(University).filter(
        University.id == university_id,
        University.is_active == True
    ).first()

    if university is None:
        raise credentials_exception

    return university
