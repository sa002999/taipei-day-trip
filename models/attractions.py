import json
from dataclasses import dataclass
from typing import Any


@dataclass
class Attraction:
    id: int
    name: str
    category: str | None
    description: str | None
    address: str | None
    transport: str | None
    mrt: list[str]
    latitude: float | None
    longitude: float | None
    images: list[str]

    @classmethod
    def from_row(cls, row: tuple[Any, ...]) -> "Attraction":
        return cls(
            id=row[0],
            name=row[1],
            category=row[2],
            description=row[3],
            address=row[4],
            transport=row[5],
            mrt=json.loads(row[6]) if row[6] else [],
            latitude=float(row[7]) if row[7] is not None else None,
            longitude=float(row[8]) if row[8] is not None else None,
            images=json.loads(row[9]) if row[9] else [],
        )

    def to_dict(self, img_host: str = "") -> dict[str, Any]:
        base = img_host.rstrip("/")
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "address": self.address,
            "transport": self.transport,
            "mrt": ", ".join(self.mrt) if self.mrt else "",
            "lat": self.latitude,
            "lng": self.longitude,
            "images": [f"{base}{path}" if base and path.startswith("/") else f"{base}/{path}" if base else path for path in self.images],
        }
