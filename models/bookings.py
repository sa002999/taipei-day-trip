from pydantic import BaseModel


class BookingRequest(BaseModel):
    attractionId: int
    date: str
    time: str
    price: int
