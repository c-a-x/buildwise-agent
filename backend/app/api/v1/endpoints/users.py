from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_current_user
from app.api.response import ok
from app.models import User
from app.schemas.auth import UserRead


router = APIRouter(prefix="/users", tags=["用户"])


@router.get("/me")
def current_user(http_request: Request, user: User = Depends(get_current_user)):
    return ok(UserRead.model_validate(user).model_dump(), http_request)
