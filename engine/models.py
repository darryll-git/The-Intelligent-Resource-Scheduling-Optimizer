from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime

class ShiftDefinition(BaseModel):
    id: str
    name: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    required_headcount: int = 2
    required_skills: List[str] = Field(default_factory=list)
    prohibited_following_shifts: List[str] = Field(default_factory=list)

class UnavailabilityBlock(BaseModel):
    date: str # YYYY-MM-DD format
    type: str # e.g., "full_day" or "specific_shifts"
    shift_ids: List[str] = Field(default_factory=list)

class StaffPreference(BaseModel):
    shift_type: str
    weight: int = 1
    
    class Config:
        extra = "allow" # allow extra fields for legacy compatibility

class StaffMember(BaseModel):
    staff_id: str
    is_active: bool = True
    max_shifts_per_month: int = 20
    max_shifts_per_week: int = 5
    skills: List[str] = Field(default_factory=list)
    preferences: List[Any] = Field(default_factory=list) # allow unstructured dicts for now to handle legacy DB maps
    historical_shift_counts: Any = Field(default_factory=dict)
    unavailability_blocks: List[UnavailabilityBlock] = Field(default_factory=list)
    
    class Config:
        extra = "allow" # To handle other legacy fields returned from DB

class ScheduleRequestPayload(BaseModel):
    month: Optional[int] = None
    year: Optional[int] = None
    days_in_month: Optional[int] = None
    staff_data: Optional[List[StaffMember]] = None
    shifts: Optional[List[ShiftDefinition]] = None
    webhook_url: Optional[str] = None

def get_default_shifts() -> List[ShiftDefinition]:
    return [
        ShiftDefinition(id="morning", name="Morning", required_headcount=2),
        ShiftDefinition(id="afternoon", name="Afternoon", required_headcount=2),
        ShiftDefinition(id="evening", name="Evening", required_headcount=2),
        ShiftDefinition(
            id="night", 
            name="Night", 
            required_headcount=2,
            prohibited_following_shifts=["morning"]
        ),
    ]
