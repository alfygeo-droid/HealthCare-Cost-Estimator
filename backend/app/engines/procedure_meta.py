"""Procedure metadata used for breakdowns and consistency checks — not medical advice."""

from __future__ import annotations

FEATURED_CODES = [
    "OR089",  # TKR
    "OR087",  # THR
    "CV013",  # CABG
    "CP001",  # PTCA
    "OP099",  # Cataract SICS
    "AG045",  # Appendicectomy
    "AG037",  # Cholecystectomy
    "AG022",  # Umbilical hernia
]

DEFAULT_LOS = {
    "OR089": 5,
    "OR087": 6,
    "CV013": 8,
    "CP001": 3,
    "OP099": 1,
    "AG045": 3,
    "AG037": 4,
    "AG022": 3,
}

EXPECTED_CATEGORIES = {
    "OR089": ["Surgery", "Room", "Diagnostics", "Medicines", "Consumables", "Implant"],
    "OR087": ["Surgery", "Room", "Diagnostics", "Medicines", "Consumables", "Implant"],
    "CV013": ["Surgery", "Room", "ICU", "Diagnostics", "Medicines", "Consumables"],
    "CP001": ["Surgery", "Room", "Diagnostics", "Medicines", "Consumables", "Implant"],
    "OP099": ["Surgery", "Room", "Diagnostics", "Medicines", "Consumables", "Implant"],
    "AG045": ["Surgery", "Room", "Diagnostics", "Medicines", "Consumables"],
    "AG037": ["Surgery", "Room", "Diagnostics", "Medicines", "Consumables"],
    "AG022": ["Surgery", "Room", "Diagnostics", "Medicines", "Consumables"],
    "_default": ["Surgery", "Room", "Diagnostics", "Medicines", "Consumables"],
}

# Share of package used to illustrate drivers (CGHS package is typically inclusive).
DRIVER_SHARES = {
    "Surgery": 0.48,
    "Room": 0.18,
    "Diagnostics": 0.10,
    "Medicines": 0.09,
    "Consumables": 0.08,
    "Implant": 0.07,
}

ROOM_KEYS = {
    "general": "room_general",
    "sharing": "room_sharing",
    "private": "room_private",
    "icu": "room_icu",
}

SPECIALITY_TO_DEPT = {
    "Orthopaedics Procedure": "Orthopedics",
    "Cardiovascular And Cardiac Surgery Procedure": "Cardiology",
    "Cardiology Procedure": "Cardiology",
    "Cardiology Investigation": "Cardiology",
    "Ophthalmology Procedure": "General Surgery",
    "Abdomen/GI Surgery Procedure": "General Surgery",
}

DIAGNOSIS_FOR_DEPT = {
    "Orthopedics": "Fracture",
    "Cardiology": "Heart Disease",
    "General Surgery": "Infection",
    "Neurology": "Stroke",
    "Oncology": "Cancer",
}
