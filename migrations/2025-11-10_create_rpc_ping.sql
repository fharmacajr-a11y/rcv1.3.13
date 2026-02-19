-- Migration: Create RPC ping function for health check
-- Date: 2025-11-10
-- Description: Creates a simple ping function for health monitoring via PostgREST

-- Drop existing function if present
DROP FUNCTION IF EXISTS public.ping();

-- Create ping function
-- Returns a simple JSON object with status "ok"
-- This function is stable (same input = same output) and lightweight
CREATE OR REPLACE FUNCTION public.ping()
RETURNS json
LANGUAGE sql
STABLE
AS $$
  SELECT json_build_object('status', 'ok', 'timestamp', NOW());
$$;

-- Add comment for documentation
COMMENT ON FUNCTION public.ping() IS 'Health check endpoint for monitoring. Returns {"status": "ok", "timestamp": "..."}';

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION public.ping() TO authenticated;

-- Grant execute permission to anonymous users (for public health checks)
GRANT EXECUTE ON FUNCTION public.ping() TO anon;

-- Note: This function will be available at POST /rest/v1/rpc/ping
-- Example usage:
--   curl -X POST 'https://your-project.supabase.co/rest/v1/rpc/ping' \
--     -H "apikey: YOUR_ANON_KEY" \
--     -H "Content-Type: application/json"
--
-- Expected response:
--   {"status": "ok", "timestamp": "2025-11-10T12:34:56.789Z"}
