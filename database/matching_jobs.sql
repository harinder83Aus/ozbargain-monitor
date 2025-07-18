-- Add matching jobs table and trigger for automated matching

-- Create table to track pending matching jobs
CREATE TABLE IF NOT EXISTS matching_jobs (
    id SERIAL PRIMARY KEY,
    search_term_id INTEGER REFERENCES search_terms(id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL DEFAULT 'new_search_term',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    scheduled_at TIMESTAMP NOT NULL,
    executed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_matching_jobs_status_scheduled ON matching_jobs(status, scheduled_at);
CREATE INDEX IF NOT EXISTS idx_matching_jobs_search_term ON matching_jobs(search_term_id);

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
DROP TRIGGER IF EXISTS trigger_new_search_term_matching ON search_terms;
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
DROP TRIGGER IF EXISTS trigger_reactivated_search_term_matching ON search_terms;
CREATE TRIGGER trigger_reactivated_search_term_matching
    AFTER UPDATE ON search_terms
    FOR EACH ROW
    EXECUTE FUNCTION create_matching_job_on_reactivation();