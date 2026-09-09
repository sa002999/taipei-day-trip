from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import re
from database import (
    create_order,
    create_payment,
    get_attraction,
    get_attractions,
    get_categories,
    get_mrts,
    get_order_by_number,
    get_booking_by_member,
    upsert_booking,
    delete_booking_by_member,
    update_order_status,
)
from pathlib import Path
from models.users import LoginRequest, RegisterRequest
from models.bookings import BookingRequest
from models.orders import OrderRequest
from services.auth_service import (
    AuthConfigurationError,
    InvalidCredentialsError,
    get_current_member,
    login_member,
    register_member,
)
from services.tappay_service import (
    TapPayConfigurationError,
    TapPayRequestError,
    pay_by_prime,
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


@app.get("/api/booking")
async def api_get_booking(authorization: str | None = Header(default=None)):
    member = get_current_member(authorization)
    if member is None:
        return JSONResponse(
            {"error": True, "message": "未登入系統，拒絕存取"},
            status_code=403,
        )

    booking = get_booking_by_member(member["id"])
    return JSONResponse({"data": booking})


@app.post("/api/booking")
async def api_create_booking(
    request: BookingRequest,
    authorization: str | None = Header(default=None),
):
    member = get_current_member(authorization)
    if member is None:
        return JSONResponse(
            {"error": True, "message": "未登入系統，拒絕存取"},
            status_code=403,
        )

    try:
        if request.attractionId <= 0 or not request.date or request.price <= 0:
            raise ValueError("invalid booking input")
        if request.time not in {"morning", "afternoon", "night"}:
            raise ValueError("invalid booking time")

        attraction = get_attraction(request.attractionId)
        if attraction is None:
            raise ValueError("attraction not found")

        upsert_booking(
            member["id"],
            request.attractionId,
            request.date,
            request.time,
            request.price,
        )
        return JSONResponse({"ok": True})
    except ValueError:
        return JSONResponse(
            {"error": True, "message": "建立失敗，輸入不正確或其他原因"},
            status_code=400,
        )
    except Exception:
        return JSONResponse(
            {"error": True, "message": "伺服器內部錯誤"},
            status_code=500,
        )


@app.delete("/api/booking")
async def api_delete_booking(authorization: str | None = Header(default=None)):
    member = get_current_member(authorization)
    if member is None:
        return JSONResponse(
            {"error": True, "message": "未登入系統，拒絕存取"},
            status_code=403,
        )

    try:
        delete_booking_by_member(member["id"])
        return JSONResponse({"ok": True})
    except Exception:
        return JSONResponse(
            {"error": True, "message": "伺服器內部錯誤"},
            status_code=500,
        )


@app.post("/api/orders")
async def api_create_order(
    request: OrderRequest,
    authorization: str | None = Header(default=None),
):
    member = get_current_member(authorization)
    if member is None:
        return JSONResponse(
            {"error": True, "message": "未登入系統，拒絕存取"},
            status_code=403,
        )

    contact_name = request.contactName.strip()
    contact_email = request.contactEmail.strip().lower()
    contact_phone = request.contactPhone.strip()
    if (
        not request.prime.strip()
        or not contact_name
        or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", contact_email)
        or not re.fullmatch(r"09\d{8}", contact_phone)
    ):
        return JSONResponse(
            {"error": True, "message": "聯絡資料格式不正確"},
            status_code=400,
        )

    try:
        booking = get_booking_by_member(member["id"])
        if booking is None:
            return JSONResponse(
                {"error": True, "message": "目前沒有待付款的行程"},
                status_code=400,
            )

        order = create_order(
            member["id"], booking, contact_name, contact_email, contact_phone
        )
        cardholder = {
            "phone_number": f"+886{contact_phone[1:]}",
            "name": contact_name,
            "email": contact_email,
        }

        try:
            tappay_result = pay_by_prime(
                request.prime.strip(),
                order["order_number"],
                booking["price"],
                cardholder,
            )
        except TapPayConfigurationError as error:
            tappay_result = {"status": -1, "msg": str(error)}
        except TapPayRequestError as error:
            tappay_result = {"status": -1, "msg": str(error)}

        create_payment(order["id"], booking["price"], tappay_result)
        if tappay_result.get("status") == 0:
            update_order_status(order["id"], "PAID")
            delete_booking_by_member(member["id"])
            return JSONResponse(
                {
                    "ok": True,
                    "orderNumber": order["order_number"],
                    "paymentStatus": "PAID",
                    "message": "付款成功",
                }
            )

        return JSONResponse(
            {
                "ok": False,
                "orderNumber": order["order_number"],
                "paymentStatus": "UNPAID",
                "message": tappay_result.get("msg", "付款失敗"),
            }
        )
    except ValueError:
        return JSONResponse(
            {"error": True, "message": "建立訂單失敗，輸入不正確"},
            status_code=400,
        )
    except Exception:
        return JSONResponse(
            {"error": True, "message": "建立訂單失敗，請稍後再試"},
            status_code=500,
        )


@app.get("/api/orders/{order_number}")
async def api_get_order(
    order_number: str,
    authorization: str | None = Header(default=None),
):
    member = get_current_member(authorization)
    if member is None:
        return JSONResponse(
            {"error": True, "message": "未登入系統，拒絕存取"},
            status_code=403,
        )

    order = get_order_by_number(order_number, member["id"])
    if order is None:
        return JSONResponse(
            {"error": True, "message": "找不到訂單"},
            status_code=404,
        )

    return JSONResponse({"data": order})
