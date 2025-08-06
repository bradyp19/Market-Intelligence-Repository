-- PostgreSQL Schema for Competitive Intelligence Agent
-- Production-ready schema with proper constraints, indexes, and audit trails

-- Enable UUID extension for better primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table for authentication and approval tracking
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('product_manager', 'analyst', 'admin')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Competitors reference table
CREATE TABLE competitors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    domain VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Raw content queue - everything scraped goes here first
CREATE TABLE raw_fetch_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    competitor_id INTEGER NOT NULL REFERENCES competitors(id),
    url VARCHAR(1000) UNIQUE NOT NULL,
    title VARCHAR(500),
    content TEXT,
    raw_html TEXT,
    published_date TIMESTAMP WITH TIME ZONE,
    confidence_score DECIMAL(5,2) CHECK (confidence_score >= 0 AND confidence_score <= 100),
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'archived')),
    processed_at TIMESTAMP WITH TIME ZONE,
    processed_by UUID REFERENCES users(id),
    rejection_reason TEXT,
    meta_info JSONB DEFAULT '{}'::jsonb
);

-- Approved competitive intelligence updates
CREATE TABLE competitor_updates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    competitor_id INTEGER NOT NULL REFERENCES competitors(id),
    raw_fetch_id UUID NOT NULL REFERENCES raw_fetch_queue(id),
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    url VARCHAR(1000) NOT NULL,
    published_date TIMESTAMP WITH TIME ZONE NOT NULL,
    relevance_category VARCHAR(50) CHECK (relevance_category IN ('product_launch', 'partnership', 'strategy', 'acquisition', 'funding', 'other')),
    strategic_priority VARCHAR(10) DEFAULT 'medium' CHECK (strategic_priority IN ('high', 'medium', 'low')),
    confidence_score DECIMAL(5,2) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 100),
    approved_by UUID NOT NULL REFERENCES users(id),
    approved_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    pm_notes TEXT,
    ai_summary TEXT,
    tags TEXT[] DEFAULT '{}',
    is_archived BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Audit trail for all changes to competitive updates
CREATE TABLE competitor_updates_audit (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    competitor_update_id UUID NOT NULL REFERENCES competitor_updates(id),
    action VARCHAR(20) NOT NULL CHECK (action IN ('created', 'updated', 'archived', 'deleted')),
    changed_fields JSONB,
    old_values JSONB,
    new_values JSONB,
    changed_by UUID NOT NULL REFERENCES users(id),
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Deduplication tracking to prevent duplicate URLs
CREATE TABLE url_fingerprints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url_hash VARCHAR(64) UNIQUE NOT NULL, -- SHA-256 hash of normalized URL
    original_url VARCHAR(1000) NOT NULL,
    competitor_id INTEGER NOT NULL REFERENCES competitors(id),
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes
CREATE INDEX idx_raw_fetch_queue_competitor_status ON raw_fetch_queue(competitor_id, status);
CREATE INDEX idx_raw_fetch_queue_fetched_at ON raw_fetch_queue(fetched_at DESC);
CREATE INDEX idx_raw_fetch_queue_confidence ON raw_fetch_queue(confidence_score DESC);
CREATE INDEX idx_competitor_updates_competitor_date ON competitor_updates(competitor_id, published_date DESC);
CREATE INDEX idx_competitor_updates_priority ON competitor_updates(strategic_priority, approved_at DESC);
CREATE INDEX idx_competitor_updates_category ON competitor_updates(relevance_category);
CREATE INDEX idx_competitor_updates_approved_at ON competitor_updates(approved_at DESC);
CREATE INDEX idx_url_fingerprints_hash ON url_fingerprints(url_hash);
CREATE INDEX idx_audit_competitor_update ON competitor_updates_audit(competitor_update_id, changed_at DESC);

-- Full-text search indexes
CREATE INDEX idx_raw_fetch_queue_search ON raw_fetch_queue USING gin(to_tsvector('english', title || ' ' || COALESCE(content, '')));
CREATE INDEX idx_competitor_updates_search ON competitor_updates USING gin(to_tsvector('english', title || ' ' || COALESCE(summary, '') || ' ' || COALESCE(pm_notes, '')));

-- Insert default competitors
INSERT INTO competitors (name, domain) VALUES 
    ('Snowflake', 'snowflake.com'),
    ('Databricks', 'databricks.com'),
    ('Tableau', 'tableau.com'),
    ('Microsoft Power BI', 'powerbi.microsoft.com'),
    ('Domo', 'domo.com'),
    ('ThoughtSpot', 'thoughtspot.com'),
    ('Looker', 'looker.com');

-- Create a default admin user (update with real details)
INSERT INTO users (email, name, role) VALUES 
    ('admin@company.com', 'System Admin', 'admin'),
    ('pm@company.com', 'Product Manager', 'product_manager'),
    ('analyst@company.com', 'Market Analyst', 'analyst');

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update timestamps
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_competitor_updates_updated_at BEFORE UPDATE ON competitor_updates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to create audit trail
CREATE OR REPLACE FUNCTION create_audit_trail()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO competitor_updates_audit (
        competitor_update_id,
        action,
        old_values,
        new_values,
        changed_by
    ) VALUES (
        COALESCE(NEW.id, OLD.id),
        CASE 
            WHEN TG_OP = 'INSERT' THEN 'created'
            WHEN TG_OP = 'UPDATE' THEN 'updated'
            WHEN TG_OP = 'DELETE' THEN 'deleted'
        END,
        CASE WHEN TG_OP = 'DELETE' THEN row_to_json(OLD) ELSE NULL END,
        CASE WHEN TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN row_to_json(NEW) ELSE NULL END,
        COALESCE(NEW.approved_by, OLD.approved_by)
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ language 'plpgsql';

-- Audit trigger
CREATE TRIGGER competitor_updates_audit_trigger
    AFTER INSERT OR UPDATE OR DELETE ON competitor_updates
    FOR EACH ROW EXECUTE FUNCTION create_audit_trail();
