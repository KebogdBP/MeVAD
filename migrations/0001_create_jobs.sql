CREATE TABLE IF NOT EXISTS jobs (
    job_id VARCHAR(64) PRIMARY KEY,
    operation VARCHAR(32) NOT NULL,
    source_url TEXT NOT NULL,
    parameters JSON NOT NULL,
    status VARCHAR(32) NOT NULL,
    progress_percent INTEGER NOT NULL CHECK (progress_percent BETWEEN 0 AND 100),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    version INTEGER NOT NULL CHECK (version > 0),
    result_reference TEXT,
    error_code VARCHAR(64),
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS ix_jobs_status ON jobs (status);
