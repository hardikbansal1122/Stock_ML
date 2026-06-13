-- Run this in your Supabase SQL Editor to create the access_requests table

CREATE TABLE IF NOT EXISTS access_requests (
    id          bigserial PRIMARY KEY,
    uid         text NOT NULL,
    email       text NOT NULL,
    display_name text DEFAULT '',
    reason      text DEFAULT '',
    status      text NOT NULL DEFAULT 'pending',  -- 'pending' | 'approved' | 'rejected'
    created_at  timestamptz DEFAULT now(),
    reviewed_at timestamptz,
    reviewed_by text DEFAULT ''
);

-- Optional index for faster lookups by uid and status
CREATE INDEX IF NOT EXISTS access_requests_uid_idx ON access_requests(uid);
CREATE INDEX IF NOT EXISTS access_requests_status_idx ON access_requests(status);
