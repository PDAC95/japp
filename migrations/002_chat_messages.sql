-- Migration: 002_chat_messages.sql
-- Description: Create chat_messages table for storing conversation history
-- Date: 2025-10-10
-- User Story: US-038

-- ============================================================================
-- TABLE: chat_messages
-- ============================================================================
-- Stores all chat messages between users and JAPPI AI coach
-- Includes both user messages and AI responses with extracted food data

CREATE TABLE IF NOT EXISTS public.chat_messages (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign key to user
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Message content
    content TEXT NOT NULL,

    -- Sender type: 'user' or 'jappi'
    sender VARCHAR(10) NOT NULL CHECK (sender IN ('user', 'jappi')),

    -- Message type: 'text' or 'food'
    message_type VARCHAR(10) NOT NULL DEFAULT 'text' CHECK (message_type IN ('text', 'food')),

    -- Extracted food data (JSON) - only populated for food messages
    -- Structure: { foods: [...], total_calories: number, total_macros: {...} }
    food_data JSONB,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Soft delete flag (for future use)
    deleted_at TIMESTAMPTZ
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Index for fast user message retrieval
CREATE INDEX idx_chat_messages_user_id ON public.chat_messages(user_id);

-- Index for chronological ordering
CREATE INDEX idx_chat_messages_created_at ON public.chat_messages(created_at DESC);

-- Composite index for user + timestamp queries (most common)
CREATE INDEX idx_chat_messages_user_created ON public.chat_messages(user_id, created_at DESC);

-- Index for food message queries
CREATE INDEX idx_chat_messages_food_type ON public.chat_messages(user_id, message_type) WHERE message_type = 'food';

-- GIN index for JSONB food_data queries (for future analytics)
CREATE INDEX idx_chat_messages_food_data ON public.chat_messages USING GIN(food_data);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Enable RLS on chat_messages table
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only read their own messages
CREATE POLICY "Users can view their own chat messages"
    ON public.chat_messages
    FOR SELECT
    USING (auth.uid() = user_id);

-- Policy: Users can insert their own messages
CREATE POLICY "Users can insert their own chat messages"
    ON public.chat_messages
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can update their own messages (for editing)
CREATE POLICY "Users can update their own chat messages"
    ON public.chat_messages
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can soft delete their own messages
CREATE POLICY "Users can delete their own chat messages"
    ON public.chat_messages
    FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger: Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_chat_messages_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_chat_messages_updated_at
    BEFORE UPDATE ON public.chat_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_chat_messages_updated_at();

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function: Get recent messages for a user with pagination
CREATE OR REPLACE FUNCTION get_user_chat_messages(
    p_user_id UUID,
    p_limit INTEGER DEFAULT 50,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    sender VARCHAR(10),
    message_type VARCHAR(10),
    food_data JSONB,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        cm.id,
        cm.content,
        cm.sender,
        cm.message_type,
        cm.food_data,
        cm.created_at
    FROM public.chat_messages cm
    WHERE cm.user_id = p_user_id
        AND cm.deleted_at IS NULL
    ORDER BY cm.created_at DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Get message count for a user
CREATE OR REPLACE FUNCTION get_user_message_count(p_user_id UUID)
RETURNS INTEGER AS $$
BEGIN
    RETURN (
        SELECT COUNT(*)::INTEGER
        FROM public.chat_messages
        WHERE user_id = p_user_id
            AND deleted_at IS NULL
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Delete old messages (for cleanup - run periodically)
CREATE OR REPLACE FUNCTION cleanup_old_chat_messages(days_to_keep INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    WITH deleted AS (
        DELETE FROM public.chat_messages
        WHERE created_at < NOW() - (days_to_keep || ' days')::INTERVAL
            AND deleted_at IS NOT NULL  -- Only delete soft-deleted messages
        RETURNING id
    )
    SELECT COUNT(*)::INTEGER INTO deleted_count FROM deleted;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- GRANTS
-- ============================================================================

-- Grant usage on the table to authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON public.chat_messages TO authenticated;

-- Grant usage on functions
GRANT EXECUTE ON FUNCTION get_user_chat_messages(UUID, INTEGER, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_message_count(UUID) TO authenticated;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE public.chat_messages IS 'Stores chat conversation history between users and JAPPI AI coach';
COMMENT ON COLUMN public.chat_messages.user_id IS 'Foreign key to auth.users';
COMMENT ON COLUMN public.chat_messages.content IS 'Message text content';
COMMENT ON COLUMN public.chat_messages.sender IS 'Message sender: user or jappi';
COMMENT ON COLUMN public.chat_messages.message_type IS 'Message type: text or food';
COMMENT ON COLUMN public.chat_messages.food_data IS 'Extracted food data (JSON) for food messages';
COMMENT ON COLUMN public.chat_messages.deleted_at IS 'Soft delete timestamp';

-- ============================================================================
-- SAMPLE DATA (for testing)
-- ============================================================================
-- Uncomment to insert sample data for testing

/*
-- Insert sample messages (replace with your test user ID)
INSERT INTO public.chat_messages (user_id, content, sender, message_type) VALUES
    ('YOUR_USER_ID_HERE', 'I had a cheeseburger with fries', 'user', 'text'),
    ('YOUR_USER_ID_HERE', 'Great! I logged 3 food items for you: Cheeseburger (650 cal), French fries (400 cal), Coke (156 cal). Total: 1,206 calories.', 'jappi', 'food');
*/

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- Run these to verify the migration was successful

-- Check table exists
-- SELECT EXISTS (
--     SELECT FROM information_schema.tables
--     WHERE table_schema = 'public'
--     AND table_name = 'chat_messages'
-- );

-- Check RLS is enabled
-- SELECT relname, relrowsecurity
-- FROM pg_class
-- WHERE relname = 'chat_messages';

-- Check policies exist
-- SELECT * FROM pg_policies WHERE tablename = 'chat_messages';

-- Check indexes exist
-- SELECT indexname FROM pg_indexes WHERE tablename = 'chat_messages';

-- ============================================================================
-- ROLLBACK (if needed)
-- ============================================================================
-- Uncomment to rollback this migration

/*
DROP FUNCTION IF EXISTS cleanup_old_chat_messages(INTEGER);
DROP FUNCTION IF EXISTS get_user_message_count(UUID);
DROP FUNCTION IF EXISTS get_user_chat_messages(UUID, INTEGER, INTEGER);
DROP TRIGGER IF EXISTS trigger_update_chat_messages_updated_at ON public.chat_messages;
DROP FUNCTION IF EXISTS update_chat_messages_updated_at();
DROP TABLE IF EXISTS public.chat_messages CASCADE;
*/
