CREATE TABLE IF NOT EXISTS job_outbox (
    event_id VARCHAR(64) PRIMARY KEY,
    job_id VARCHAR(64) NOT NULL UNIQUE REFERENCES jobs(job_id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    lease_owner VARCHAR(128),
    lease_expires_at TIMESTAMP WITH TIME ZONE,
    last_error TEXT
);

CREATE INDEX IF NOT EXISTS ix_job_outbox_created_at
    ON job_outbox (created_at);
CREATE INDEX IF NOT EXISTS ix_job_outbox_lease_expires_at
    ON job_outbox (lease_expires_at);
