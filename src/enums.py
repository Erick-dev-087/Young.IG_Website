"""
Central Enums for Young IG Auto Inspection System.
Used by both SQLAlchemy models and Pydantic schemas.
"""

import enum


# ─── User ────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    INSPECTOR = "INSPECTOR"


class UserStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


# ─── Customer ─────────────────────────────────────────────────────────────────

class CustomerType(str, enum.Enum):
    INDIVIDUAL = "INDIVIDUAL"
    INSTITUTION = "INSTITUTION"
    DEALER = "DEALER"


# ─── Vehicle ──────────────────────────────────────────────────────────────────

class FuelType(str, enum.Enum):
    PETROL = "PETROL"
    DIESEL = "DIESEL"
    ELECTRIC = "ELECTRIC"
    HYBRID = "HYBRID"


class Transmission(str, enum.Enum):
    AUTOMATIC = "AUTOMATIC"
    MANUAL = "MANUAL"
    CVT = "CVT"
    EV = "EV"
    NA = "N/A"


class VehicleType(str, enum.Enum):
    INTERNAL_COMBUSTION = "INTERNAL_COMBUSTION"
    HYBRID = "HYBRID"
    FULLY_ELECTRIC = "FULLY_ELECTRIC"
    FUEL_CELL = "FUEL_CELL"
    NA = "N/A"


# ─── Inspection ───────────────────────────────────────────────────────────────

class OdoMeasure(str, enum.Enum):
    KMS = "KMS"
    MILES = "MILES"


class InspectionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class OverallCondition(str, enum.Enum):
    NO_MAJOR_ISSUES = "NO_MAJOR_ISSUES"
    MINOR_ISSUES_FOUND = "MINOR_ISSUES_FOUND"
    MAJOR_ISSUES_FOUND = "MAJOR_ISSUES_FOUND"
    CRITICAL_SAFETY_ISSUES = "CRITICAL_SAFETY_ISSUES"


# ─── Inspection Field Input Types ─────────────────────────────────────────────

class FieldInputType(str, enum.Enum):
    CHECK = "CHECK"
    SELECT = "SELECT"
    TEXT = "TEXT"
    TEXTAREA = "TEXTAREA"
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"


# ─── Inspection Image Categories ─────────────────────────────────────────────

class ImageCategory(str, enum.Enum):
    EXTERIOR = "EXTERIOR"
    INTERIOR = "INTERIOR"
    ENGINE = "ENGINE"
    UNDERCARRIAGE = "UNDERCARRIAGE"
    TYRES = "TYRES"
    DOCUMENTS = "DOCUMENTS"
    OTHER = "OTHER"
