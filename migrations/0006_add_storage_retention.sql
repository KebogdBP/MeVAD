ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS result_expires_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS storage_deleted_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS cleanup_lease_owner VARCHAR(128),
    ADD COLUMN IF NOT EXISTS cleanup_lease_expires_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX IF NOT EXISTS ix_jobs_result_expires_at
    ON jobs (result_expires_at);
CREATE INDEX IF NOT EXISTS ix_jobs_cleanup_lease_expires_at
    ON jobs (cleanup_lease_expires_at);
