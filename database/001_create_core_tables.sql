-- ==========================================================
-- Young Auto Inspection Management System
-- Database Schema
-- PostgreSQL
-- ==========================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==========================================================
-- USERS
-- ==========================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    full_name VARCHAR(255) NOT NULL,

    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),

    password_hash TEXT NOT NULL,

    role VARCHAR(20) NOT NULL
        CHECK (role IN ('ADMIN', 'INSPECTOR')),

    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','APPROVED','REJECTED','SUSPENDED')),

    approved_by UUID REFERENCES users(id),

    approved_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================================
-- CUSTOMERS
-- ==========================================================

CREATE TABLE customers (

    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    full_name VARCHAR(255) NOT NULL,

    email VARCHAR(255),

    phone VARCHAR(20),

    kra_pin VARCHAR(50),

    customer_type VARCHAR(30)
        CHECK (customer_type IN ('INDIVIDUAL','INSTITUTION','DEALER')),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================================
-- VEHICLES
-- ==========================================================

CREATE TABLE vehicles (

    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    registration_number VARCHAR(30) UNIQUE NOT NULL,

    make VARCHAR(100),

    model VARCHAR(100),

    engine_number VARCHAR(100),

    chassis_number VARCHAR(100),

    manufacture_year INTEGER,

    fuel_type VARCHAR(30)
    CHECK (fuel_type IN ('PETROL', 'DIESEL')),

    transmission VARCHAR(30)
    CHECK (transmission IN ('AUTOMATIC', 'MANUAL', 'CVT', 'EV', 'N/A')),

    vehicle_type VARCHAR(30)
    CHECK (vehicle_type IN ('INTERNAL_COMBUSTION', 'HYBRID', 'FULLY_ELECTRIC', 'FUEL_CELL', 'N/A')),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================================
-- INSPECTIONS
-- ==========================================================

CREATE TABLE inspections (

    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inspection_number VARCHAR(50) UNIQUE NOT NULL,

    inspection_date DATE NOT NULL,

    inspector_id UUID NOT NULL
        REFERENCES users(id),

    customer_id UUID
        REFERENCES customers(id),

    vehicle_id UUID NOT NULL
        REFERENCES vehicles(id),

    mileage INTEGER,

    odo_measure VARCHAR(10)
        CHECK (odo_measure IN ('KMS','MILES')),

    mileage_authentic BOOLEAN,

    seller_name VARCHAR(255),

    status VARCHAR(20)

    CHECK (

    status IN (

    'DRAFT',

    'IN_PROGRESS',

    'COMPLETED',

    'ARCHIVED'

    )), 
    final_notes TEXT,

    recommendation VARCHAR(50),

    pdf_url TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================================
-- INSPECTION CATEGORIES
-- ==========================================================

CREATE TABLE inspection_categories (

    id SERIAL PRIMARY KEY,

    name VARCHAR(100) UNIQUE NOT NULL,

    display_order INTEGER
);

-- ==========================================================
-- INSPECTION FIELDS
-- ==========================================================
CREATE TABLE inspection_fields (

    id SERIAL PRIMARY KEY,

    category_id INTEGER NOT NULL
        REFERENCES inspection_categories(id)
        ON DELETE CASCADE,

    field_name VARCHAR(255) NOT NULL,

    field_key VARCHAR(100) UNIQUE NOT NULL,

    input_type VARCHAR(30) NOT NULL
        CHECK (
            input_type IN (
                'CHECK',
                'SELECT',
                'TEXT',
                'TEXTAREA',
                'NUMBER',
                'BOOLEAN',
                'DATE'
            )
        ),

    options JSONB,

    is_required BOOLEAN DEFAULT TRUE,

    display_order INTEGER,

    UNIQUE(category_id, field_name)
);

-- ==========================================================
-- INSPECTION RESULTS
-- ==========================================================

CREATE TABLE inspection_results (

    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inspection_id UUID NOT NULL
        REFERENCES inspections(id)
        ON DELETE CASCADE,

    inspection_field_id INTEGER NOT NULL
        REFERENCES inspection_fields(id),

    filed_value TEXT,
    
    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(inspection_id, inspection_field_id)
);

-- ==========================================================
-- INSPECTION IMAGES
-- ==========================================================

CREATE TABLE inspection_images (

    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    inspection_id UUID NOT NULL
        REFERENCES inspections(id)
        ON DELETE CASCADE,

    image_url TEXT NOT NULL,

    image_category VARCHAR(50),

    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================================
-- INDEXES
-- ==========================================================

CREATE INDEX idx_inspection_inspector
ON inspections(inspector_id);

CREATE INDEX idx_inspection_customer
ON inspections(customer_id);

CREATE INDEX idx_inspection_vehicle
ON inspections(vehicle_id);

CREATE INDEX idx_results_inspection
ON inspection_results(inspection_id);

CREATE INDEX idx_results_item
ON inspection_results(inspection_field_id);

CREATE INDEX idx_vehicle_registration
ON vehicles(registration_number);

CREATE INDEX idx_customer_phone
ON customers(phone);

CREATE INDEX idx_user_email
ON users(email);