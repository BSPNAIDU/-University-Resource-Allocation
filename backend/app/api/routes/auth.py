from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.university import University
from backend.app.schemas.university import (
    UniversityRegister,
    UniversityLogin,
    TokenResponse,
    UniversityResponse,
)
from backend.app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)

router = APIRouter(
    prefix="/auth",
    tags=["University Authentication"]
)


@router.post(
    "/register",
    response_model=UniversityResponse,
    status_code=status.HTTP_201_CREATED
)
def register_university(
    university_data: UniversityRegister,
    db: Session = Depends(get_db)
):
    university_code = university_data.university_code.strip().upper()
    university_name = university_data.university_name.strip()

    existing_university = db.query(University).filter(
        (University.university_code == university_code) |
        (University.university_name.ilike(university_name))
    ).first()

    if existing_university:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="University name or code is already registered."
        )

    university = University(
        university_name=university_name,
        university_code=university_code,
        address=university_data.address,
        city=university_data.city,
        state=university_data.state,
        password_hash=hash_password(university_data.password),
    )

    db.add(university)
    db.commit()
    db.refresh(university)

    return university


@router.post("/login", response_model=TokenResponse)
def login_university(
    login_data: UniversityLogin,
    db: Session = Depends(get_db)
):
    university_code = login_data.university_code.strip().upper()

    university = db.query(University).filter(
        University.university_code == university_code
    ).first()

    if university is None or university.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid university code or password."
        )

    if verify_password(login_data.password, university.password_hash) is False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid university code or password."
        )

    access_token = create_access_token(university.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "university": university,
    }
