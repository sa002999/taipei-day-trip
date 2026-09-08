from pydantic import BaseModel


class OrderRequest(BaseModel):
    prime: str
    contactName: str
    contactEmail: str
    contactPhone: str
