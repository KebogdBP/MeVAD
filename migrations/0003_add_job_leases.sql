ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS lease_owner VARCHAR(128),
    ADD COLUMN IF NOT EXISTS lease_expires_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX IF NOT EXISTS ix_jobs_lease_expires_at ON jobs (lease_expires_at);
