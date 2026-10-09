from pydantic import BaseModel, Field

class RoomCreate(BaseModel):
    room_name: str = Field(min_length=1, max_length=80)
    building: str = "Main Block"
    rows: int = Field(ge=1, le=30)
    columns: int = Field(ge=1, le=30)
    capacity: int = Field(ge=1, le=900)
    notes: str = ""

class StudentIn(BaseModel):
    roll_number: str
    name: str
    branch: str

