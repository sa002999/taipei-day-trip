from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from database import get_attraction, get_attractions, get_categories, get_mrts

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

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