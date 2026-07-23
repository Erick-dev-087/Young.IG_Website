import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Boolean, Date, DateTime, Text,
    ForeignKey, Enum, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.db.db import Base
from src.enums import (
    UserRole, UserStatus,
    CustomerType,
    FuelType, Transmission, VehicleType,
    OdoMeasure, InspectionStatus, OverallCondition,
    FieldInputType, ImageCategory,
)


class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20))
    password_hash = Column(Text, nullable=False)
    role = Column(Enum(UserRole, native_enum=False, length=20), nullable=False)
    status = Column(Enum(UserStatus, native_enum=False, length=20), nullable=False, default=UserStatus.PENDING)
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    approved_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, default=func.now())
    deleted_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    
    # self-referential relationship for approver
    approver = relationship('User', remote_side=[id], back_populates='approved_users')
    approved_users = relationship('User', back_populates='approver')


class Customer(Base):
    __tablename__ = 'customers'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(20), index=True)
    kra_pin = Column(String(50))
    customer_type = Column(Enum(CustomerType, native_enum=False, length=30))             # CustomerType enum values
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    inspections = relationship('Inspection', back_populates='customer')


class Vehicle(Base):
    __tablename__ = 'vehicles'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    registration_number = Column(String(30), unique=True, nullable=False, index=True)
    make = Column(String(100))
    model = Column(String(100))
    engine_number = Column(String(100))
    chassis_number = Column(String(100))
    manufacture_year = Column(Integer)
    fuel_type = Column(Enum(FuelType, native_enum=False, length=30))
    transmission = Column(Enum(Transmission, native_enum=False, length=30))
    vehicle_type = Column(Enum(VehicleType, native_enum=False, length=30))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    inspections = relationship('Inspection', back_populates='vehicle')


class Inspection(Base):
    __tablename__ = 'inspections'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inspection_number = Column(String(50), unique=True, nullable=False)
    inspection_date = Column(Date, nullable=False)
    inspector_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id'), index=True)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey('vehicles.id'), nullable=False, index=True)
    mileage = Column(Integer)
    odo_measure = Column(Enum(OdoMeasure, native_enum=False, length=10))
    mileage_authentic = Column(Boolean)
    seller_name = Column(String(255))
    status = Column(Enum(InspectionStatus, native_enum=False, length=20), default=InspectionStatus.DRAFT)
    final_notes = Column(Text)
    overall_condition = Column(Enum(OverallCondition, native_enum=False, length=50))
    pdf_url = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    inspector = relationship('User')
    customer = relationship('Customer', back_populates='inspections')
    vehicle = relationship('Vehicle', back_populates='inspections')
    results = relationship('InspectionResult', back_populates='inspection', cascade="all, delete")
    images = relationship('InspectionImage', back_populates='inspection', cascade="all, delete")


class InspectionCategory(Base):
    __tablename__ = 'inspection_categories'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    display_order = Column(Integer)

    fields = relationship('InspectionField', back_populates='category', cascade="all, delete")


class InspectionField(Base):
    __tablename__ = 'inspection_fields'
    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey('inspection_categories.id', ondelete='CASCADE'), nullable=False)
    field_name = Column(String(255), nullable=False)
    field_key = Column(String(100), unique=True, nullable=False)
    input_type = Column(Enum(FieldInputType, native_enum=False, length=30), nullable=False)
    options = Column(JSONB)
    is_required = Column(Boolean, default=True)
    display_order = Column(Integer)

    category = relationship('InspectionCategory', back_populates='fields')


class InspectionResult(Base):
    __tablename__ = 'inspection_results'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inspection_id = Column(UUID(as_uuid=True), ForeignKey('inspections.id', ondelete='CASCADE'), nullable=False, index=True)
    inspection_field_id = Column(Integer, ForeignKey('inspection_fields.id'), nullable=False, index=True)
    filed_value = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())

    inspection = relationship('Inspection', back_populates='results')
    field = relationship('InspectionField')


class InspectionImage(Base):
    __tablename__ = 'inspection_images'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inspection_id = Column(UUID(as_uuid=True), ForeignKey('inspections.id', ondelete='CASCADE'), nullable=False)
    image_url = Column(Text, nullable=False)
    image_category = Column(Enum(ImageCategory, native_enum=False, length=50))                 # ImageCategory enum values
    uploaded_at = Column(DateTime, default=func.now())

    inspection = relationship('Inspection', back_populates='images')
