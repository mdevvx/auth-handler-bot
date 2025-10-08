-- =====================================================
-- Discord Authentication Bot - Database Schema
-- Database: Supabase (PostgreSQL)
-- Version: 2.0
-- =====================================================

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- Table: server_config
-- Stores server-specific configuration (channels, settings)
-- =====================================================
CREATE TABLE IF NOT EXISTS server_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    guild_id BIGINT NOT NULL UNIQUE,
    login_channel_id BIGINT,
    logout_channel_id BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster guild lookups
CREATE INDEX IF NOT EXISTS idx_server_config_guild_id ON server_config(guild_id);

-- =====================================================
-- Table: allowed_roles
-- Stores roles that users can select during signup
-- =====================================================
CREATE TABLE IF NOT EXISTS allowed_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    guild_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    role_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique role per guild
    CONSTRAINT unique_role_per_guild UNIQUE (guild_id, role_id)
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_allowed_roles_guild_id ON allowed_roles(guild_id);
CREATE INDEX IF NOT EXISTS idx_allowed_roles_role_id ON allowed_roles(role_id);

-- =====================================================
-- Table: users
-- Stores user authentication data
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    guild_id BIGINT NOT NULL,
    discord_user_id BIGINT NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    designation VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    
    -- Ensure unique email per guild (same email can exist in different servers)
    CONSTRAINT unique_email_per_guild UNIQUE (guild_id, email),
    
    -- Ensure one user can only have one account per guild
    CONSTRAINT unique_user_per_guild UNIQUE (guild_id, discord_user_id)
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_users_guild_id ON users(guild_id);
CREATE INDEX IF NOT EXISTS idx_users_discord_user_id ON users(discord_user_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_guild_email ON users(guild_id, email);
CREATE INDEX IF NOT EXISTS idx_users_guild_discord_id ON users(guild_id, discord_user_id);

-- =====================================================
-- Table: login_history (Optional - for tracking)
-- Stores login attempts and history
-- =====================================================
CREATE TABLE IF NOT EXISTS login_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    guild_id BIGINT NOT NULL,
    discord_user_id BIGINT NOT NULL,
    email VARCHAR(255) NOT NULL,
    success BOOLEAN NOT NULL DEFAULT FALSE,
    ip_address VARCHAR(45),
    user_agent TEXT,
    attempted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for faster history queries
CREATE INDEX IF NOT EXISTS idx_login_history_user_id ON login_history(user_id);
CREATE INDEX IF NOT EXISTS idx_login_history_guild_id ON login_history(guild_id);
CREATE INDEX IF NOT EXISTS idx_login_history_discord_user_id ON login_history(discord_user_id);
CREATE INDEX IF NOT EXISTS idx_login_history_attempted_at ON login_history(attempted_at);
CREATE INDEX IF NOT EXISTS idx_login_history_success ON login_history(success);

-- =====================================================
-- Function: Update updated_at timestamp automatically
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- Triggers: Auto-update updated_at column
-- =====================================================

-- Trigger for server_config table
DROP TRIGGER IF EXISTS update_server_config_updated_at ON server_config;
CREATE TRIGGER update_server_config_updated_at
    BEFORE UPDATE ON server_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for users table
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- Function: Clean up orphaned data when guild is removed
-- Call this when bot leaves a server
-- =====================================================
CREATE OR REPLACE FUNCTION cleanup_guild_data(p_guild_id BIGINT)
RETURNS void AS $$
BEGIN
    -- Delete users
    DELETE FROM users WHERE guild_id = p_guild_id;
    
    -- Delete allowed roles
    DELETE FROM allowed_roles WHERE guild_id = p_guild_id;
    
    -- Delete server config
    DELETE FROM server_config WHERE guild_id = p_guild_id;
    
    -- Delete login history
    DELETE FROM login_history WHERE guild_id = p_guild_id;
    
    RAISE NOTICE 'Cleaned up all data for guild_id: %', p_guild_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- Function: Get guild statistics
-- =====================================================
CREATE OR REPLACE FUNCTION get_guild_stats(p_guild_id BIGINT)
RETURNS TABLE (
    total_users INTEGER,
    total_allowed_roles INTEGER,
    recent_signups INTEGER,
    recent_logins INTEGER,
    login_channel_configured BOOLEAN,
    logout_channel_configured BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        (SELECT COUNT(*)::INTEGER FROM users WHERE guild_id = p_guild_id),
        (SELECT COUNT(*)::INTEGER FROM allowed_roles WHERE guild_id = p_guild_id),
        (SELECT COUNT(*)::INTEGER FROM users WHERE guild_id = p_guild_id AND created_at > NOW() - INTERVAL '7 days'),
        (SELECT COUNT(*)::INTEGER FROM login_history WHERE guild_id = p_guild_id AND success = true AND attempted_at > NOW() - INTERVAL '7 days'),
        (SELECT login_channel_id IS NOT NULL FROM server_config WHERE guild_id = p_guild_id),
        (SELECT logout_channel_id IS NOT NULL FROM server_config WHERE guild_id = p_guild_id);
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- Views: Useful queries
-- =====================================================

-- View: Active users per guild
CREATE OR REPLACE VIEW v_guild_user_counts AS
SELECT 
    guild_id,
    COUNT(*) as user_count,
    COUNT(DISTINCT designation) as unique_roles,
    MAX(created_at) as last_signup
FROM users
GROUP BY guild_id;

-- View: Login activity summary
CREATE OR REPLACE VIEW v_login_activity AS
SELECT 
    guild_id,
    discord_user_id,
    email,
    COUNT(*) as total_attempts,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_logins,
    SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) as failed_attempts,
    MAX(attempted_at) as last_attempt
FROM login_history
GROUP BY guild_id, discord_user_id, email;

-- View: Guild configuration status
CREATE OR REPLACE VIEW v_guild_config_status AS
SELECT 
    sc.guild_id,
    sc.login_channel_id,
    sc.logout_channel_id,
    COUNT(ar.id) as allowed_roles_count,
    COUNT(u.id) as user_count,
    CASE 
        WHEN sc.login_channel_id IS NOT NULL AND sc.logout_channel_id IS NOT NULL AND COUNT(ar.id) > 0 
        THEN 'Fully Configured'
        WHEN sc.login_channel_id IS NOT NULL OR sc.logout_channel_id IS NOT NULL OR COUNT(ar.id) > 0 
        THEN 'Partially Configured'
        ELSE 'Not Configured'
    END as config_status
FROM server_config sc
LEFT JOIN allowed_roles ar ON sc.guild_id = ar.guild_id
LEFT JOIN users u ON sc.guild_id = u.guild_id
GROUP BY sc.guild_id, sc.login_channel_id, sc.logout_channel_id;

-- =====================================================
-- Row Level Security (RLS) - Optional but recommended
-- Uncomment these if you want additional security
-- =====================================================
-- ALTER TABLE server_config ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE allowed_roles ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE login_history ENABLE ROW LEVEL SECURITY;

-- Create policies for service role access
-- CREATE POLICY "Service role can do anything" ON server_config FOR ALL TO service_role USING (true);
-- CREATE POLICY "Service role can do anything" ON users FOR ALL TO service_role USING (true);
-- CREATE POLICY "Service role can do anything" ON allowed_roles FOR ALL TO service_role USING (true);
-- CREATE POLICY "Service role can do anything" ON login_history FOR ALL TO service_role USING (true);

-- =====================================================
-- Sample Queries for Testing and Management
-- =====================================================

-- View all server configurations
-- SELECT * FROM server_config;

-- View all users in a specific guild
-- SELECT * FROM users WHERE guild_id = 123456789 ORDER BY created_at DESC;

-- View all allowed roles for a guild
-- SELECT * FROM allowed_roles WHERE guild_id = 123456789 ORDER BY role_name;

-- View login history for a user
-- SELECT * FROM login_history WHERE discord_user_id = 123456789 ORDER BY attempted_at DESC;

-- Count users per guild
-- SELECT guild_id, COUNT(*) as user_count FROM users GROUP BY guild_id ORDER BY user_count DESC;

-- Find user by email in specific guild
-- SELECT * FROM users WHERE guild_id = 123456789 AND email = 'user@example.com';

-- Get guild statistics
-- SELECT * FROM get_guild_stats(123456789);

-- View guild configuration status
-- SELECT * FROM v_guild_config_status;

-- View recent login activity
-- SELECT * FROM v_login_activity WHERE attempted_at > NOW() - INTERVAL '7 days';

-- Clean up data for a guild (use when bot leaves server)
-- SELECT cleanup_guild_data(123456789);

-- Find users who haven't logged in recently
-- SELECT u.guild_id, u.discord_user_id, u.email, u.full_name, u.last_login
-- FROM users u
-- WHERE u.last_login IS NULL OR u.last_login < NOW() - INTERVAL '30 days'
-- ORDER BY u.last_login ASC;

-- Get roles that are configured but might not exist in Discord anymore
-- SELECT ar.guild_id, ar.role_id, ar.role_name, ar.created_at
-- FROM allowed_roles ar
-- LEFT JOIN users u ON ar.guild_id = u.guild_id AND ar.role_name = u.designation
-- GROUP BY ar.guild_id, ar.role_id, ar.role_name, ar.created_at
-- HAVING COUNT(u.id) = 0
-- ORDER BY ar.created_at DESC;

-- =====================================================
-- Maintenance Queries
-- =====================================================

-- Remove duplicate entries (if any)
-- WITH duplicates AS (
--     SELECT id, ROW_NUMBER() OVER (PARTITION BY guild_id, email ORDER BY created_at) as rn
--     FROM users
-- )
-- DELETE FROM users WHERE id IN (SELECT id FROM duplicates WHERE rn > 1);

-- Update role names if they changed in Discord
-- UPDATE users SET designation = 'NewRoleName' WHERE designation = 'OldRoleName' AND guild_id = 123456789;

-- Archive old login history (older than 90 days)
-- DELETE FROM login_history WHERE attempted_at < NOW() - INTERVAL '90 days';

-- =====================================================
-- Performance Optimization
-- =====================================================

-- Analyze tables for better query planning
ANALYZE server_config;
ANALYZE users;
ANALYZE allowed_roles;
ANALYZE login_history;

-- Vacuum tables to reclaim space
-- VACUUM ANALYZE server_config;
-- VACUUM ANALYZE users;
-- VACUUM ANALYZE allowed_roles;
-- VACUUM ANALYZE login_history;

-- =====================================================
-- Backup Recommendations
-- =====================================================
-- Regular backups are important! Supabase provides automatic backups,
-- but you can also create manual backups:
-- 
-- 1. Use Supabase Dashboard: Project Settings → Database → Database Backups
-- 2. Export specific tables:
--    pg_dump -h [host] -U [user] -d [database] -t users -t allowed_roles > backup.sql
-- 
-- =====================================================

-- =====================================================
-- Schema Version
-- =====================================================
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    description TEXT,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO schema_version (version, description) 
VALUES (1, 'Initial schema with server_config, users, login_history')
ON CONFLICT (version) DO NOTHING;

INSERT INTO schema_version (version, description) 
VALUES (2, 'Added allowed_roles table and helper functions')
ON CONFLICT (version) DO NOTHING;

-- View current schema version
-- SELECT * FROM schema_version ORDER BY version DESC LIMIT 1;