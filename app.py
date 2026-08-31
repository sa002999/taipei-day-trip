from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from database import (
    get_attraction,
    get_attractions,
    get_categories,
    get_mrts,
)
from pathlib import Path
from models.users import LoginRequest, RegisterRequest
from services.auth_service import (
    AuthConfigurationError,
    InvalidCredentialsError,
    get_current_member,
    login_member,
    register_member,
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Static Pages (Never Modify Code in this Block)
@app.get("/", include_in_schema=False)
async def index(request: Request):
    return FileResponse("./static/index.html", media_type="text/html")


@app.get("/attraction/{id}", include_in_schema=False)
async def attraction(request: Request, id: int):
    return FileResponse("./static/attraction.html", media_type="text/html")


@app.get("/booking", include_in_schema=False)
async def booking(request: Request):
    return FileResponse("./static/booking.html", media_type="text/html")


@app.get("/thankyou", include_in_schema=False)
async def thankyou(request: Request):
    return FileResponse("./static/thankyou.html", media_type="text/html")


@app.get("/api/attractions")
async def api_get_attractions(
    category: str | None = None,
    keyword: str | None = None,
    page: int = Query(..., ge=1),
):
    return JSONResponse(get_attractions(category=category, keyword=keyword, page=page))


@app.get("/api/attraction/{attraction_id}")
async def api_get_attraction(attraction_id: int):
    attraction = get_attraction(attraction_id)
    if attraction is None:
        raise HTTPException(status_code=404, detail="Attraction not found")
    return JSONResponse({"data": attraction})


@app.get("/api/categories")
async def api_get_categories():
    return JSONResponse(get_categories())


@app.get("/api/mrts")
async def api_get_mrts():
    return JSONResponse(get_mrts())


@app.post("/api/user")
async def api_register_member(request: RegisterRequest):
    try:
        register_member(request.name, request.email, request.password)
        return JSONResponse({"ok": True})
    except ValueError as error:
        return JSONResponse({"error": True, "message": str(error)}, status_code=400)
    except Exception:
        return JSONResponse(
            {"error": True, "message": "註冊失敗，請稍後再試"}, status_code=500
        )


@app.get("/api/user/auth")
async def api_get_current_member(authorization: str | None = Header(default=None)):
    return JSONResponse({"data": get_current_member(authorization)})


@app.put("/api/user/auth")
async def api_login_member(request: LoginRequest):
    try:
        return JSONResponse({"token": login_member(request.email, request.password)})
    except InvalidCredentialsError:
        return JSONResponse(
            {"error": True, "message": "帳號或密碼錯誤"}, status_code=400
        )
    except AuthConfigurationError:
        return JSONResponse(
            {"error": True, "message": "伺服器內部錯誤"}, status_code=500
        )
    except Exception:
        return JSONResponse(
            {"error": True, "message": "登入失敗，請稍後再試"}, status_code=500
        )
