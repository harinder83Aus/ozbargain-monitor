-- OzBargain Deal Monitor Database Schema

-- Search terms table - stores user-defined search criteria
CREATE TABLE search_terms (
    id SERIAL PRIMARY KEY,
    term VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Deals table - stores scraped deal information
CREATE TABLE deals (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    url TEXT NOT NULL UNIQUE,
    description TEXT,
    price DECIMAL(10, 2),
    original_price DECIMAL(10, 2),
    discount_percentage INTEGER,
    store VARCHAR(255),
    category VARCHAR(100),
    votes INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    deal_date TIMESTAMP,
    expiry_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Search matches table - links deals to search terms
CREATE TABLE search_matches (
    id SERIAL PRIMARY KEY,
    deal_id INTEGER REFERENCES deals(id) ON DELETE CASCADE,
    search_term_id INTEGER REFERENCES search_terms(id) ON DELETE CASCADE,
    match_score DECIMAL(3, 2), -- confidence score for the match
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(deal_id, search_term_id)
);

-- Scraping log table - tracks scraping activities
CREATE TABLE scraping_logs (
    id SERIAL PRIMARY KEY,
    scrape_type VARCHAR(50) NOT NULL, -- 'rss', 'category', etc.
    source_url TEXT NOT NULL,
    deals_found INTEGER DEFAULT 0,
    new_deals INTEGER DEFAULT 0,
    updated_deals INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'success', -- 'success', 'error', 'partial'
    error_message TEXT,
    scrape_duration INTEGER, -- in seconds
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_deals_title ON deals(title);
CREATE INDEX idx_deals_store ON deals(store);
CREATE INDEX idx_deals_category ON deals(category);
CREATE INDEX idx_deals_created_at ON deals(created_at);
CREATE INDEX idx_deals_is_active ON deals(is_active);
CREATE INDEX idx_search_terms_term ON search_terms(term);
CREATE INDEX idx_search_terms_is_active ON search_terms(is_active);
CREATE INDEX idx_search_matches_deal_id ON search_matches(deal_id);
CREATE INDEX idx_search_matches_search_term_id ON search_matches(search_term_id);
CREATE INDEX idx_scraping_logs_created_at ON scraping_logs(created_at);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_search_terms_updated_at
    BEFORE UPDATE ON search_terms
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_deals_updated_at
    BEFORE UPDATE ON deals
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Matching jobs table for automated matching
CREATE TABLE matching_jobs (
    id SERIAL PRIMARY KEY,
    search_term_id INTEGER REFERENCES search_terms(id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL DEFAULT 'new_search_term',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    scheduled_at TIMESTAMP NOT NULL,
    executed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for matching jobs
CREATE INDEX idx_matching_jobs_status_scheduled ON matching_jobs(status, scheduled_at);
CREATE INDEX idx_matching_jobs_search_term ON matching_jobs(search_term_id);

-- Function to create matching job
CREATE OR REPLACE FUNCTION create_matching_job()
RETURNS TRIGGER AS $$
BEGIN
    -- Create a matching job for 5 minutes from now
    INSERT INTO matching_jobs (search_term_id, job_type, scheduled_at)
    VALUES (NEW.id, 'new_search_term', NOW() + INTERVAL '5 minutes');
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to create matching job when new search term is added
CREATE TRIGGER trigger_new_search_term_matching
    AFTER INSERT ON search_terms
    FOR EACH ROW
    EXECUTE FUNCTION create_matching_job();

-- Function to create matching job for reactivated search terms
CREATE OR REPLACE FUNCTION create_matching_job_on_reactivation()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if search term was reactivated
    IF OLD.is_active = false AND NEW.is_active = true THEN
        INSERT INTO matching_jobs (search_term_id, job_type, scheduled_at)
        VALUES (NEW.id, 'reactivated_search_term', NOW() + INTERVAL '5 minutes');
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for reactivated search terms
CREATE TRIGGER trigger_reactivated_search_term_matching
    AFTER UPDATE ON search_terms
    FOR EACH ROW
    EXECUTE FUNCTION create_matching_job_on_reactivation();