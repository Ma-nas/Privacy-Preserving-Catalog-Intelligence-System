-- Database initialization script for local development and docker-compose

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create roles
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_role') THEN
        CREATE ROLE app_role;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'auditor_role') THEN
        CREATE ROLE auditor_role;
    END IF;
END
$$;

-- Create application users with passwords
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
        CREATE USER app_user WITH PASSWORD 'app_password';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'auditor_user') THEN
        CREATE USER auditor_user WITH PASSWORD 'auditor_password';
    END IF;
END
$$;

-- Assign role memberships
GRANT app_role TO app_user;
GRANT auditor_role TO auditor_user;
