from pydantic import BaseModel


class BookingRequest(BaseModel):
    attractionId: int
    date: str
    time: str
    price: int


class OrderRequest(BaseModel):
    prime: str
    contactName: str
    contactEmail: str
    contactPhone: str
