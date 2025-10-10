# Migration 002: Chat Messages Table

## Overview

This migration creates the `chat_messages` table for storing conversation history between users and JAPPI AI coach.

**User Story:** US-038
**Date:** 2025-10-10

## What This Migration Does

1. **Creates `chat_messages` table** with:
   - User messages and JAPPI responses
   - Food extraction data (JSONB)
   - Timestamps and soft delete support

2. **Creates indexes** for:
   - Fast user message queries
   - Chronological ordering
   - Food message filtering
   - JSONB data queries

3. **Configures RLS** (Row Level Security):
   - Users can only see their own messages
   - Users can insert their own messages
   - Users can update/delete their own messages

4. **Creates helper functions**:
   - `get_user_chat_messages()` - Paginated message retrieval
   - `get_user_message_count()` - Count messages for a user
   - `cleanup_old_chat_messages()` - Periodic cleanup of old messages

## How to Execute This Migration

### Step 1: Open Supabase SQL Editor

1. Go to your Supabase project dashboard: https://supabase.com/dashboard
2. Navigate to **SQL Editor** in the left sidebar
3. Click **+ New Query**

### Step 2: Copy Migration SQL

Copy the entire contents of `002_chat_messages.sql` file.

### Step 3: Execute Migration

1. Paste the SQL into the editor
2. Click **Run** or press `Ctrl+Enter` (Windows) / `Cmd+Enter` (Mac)
3. Wait for confirmation message: "Success. No rows returned"

### Step 4: Verify Migration

Run these verification queries in the SQL Editor:

```sql
-- Check table exists
SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name = 'chat_messages'
);
-- Expected result: true

-- Check RLS is enabled
SELECT relname, relrowsecurity
FROM pg_class
WHERE relname = 'chat_messages';
-- Expected result: chat_messages | true

-- Check policies exist
SELECT policyname FROM pg_policies WHERE tablename = 'chat_messages';
-- Expected result: 4 policies

-- Check indexes exist
SELECT indexname FROM pg_indexes WHERE tablename = 'chat_messages';
-- Expected result: 6 indexes

-- Check functions exist
SELECT routine_name
FROM information_schema.routines
WHERE routine_name LIKE '%chat_messages%'
    AND routine_schema = 'public';
-- Expected result: 3 functions
```

## Schema Details

### Table Structure

```sql
chat_messages (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    content TEXT NOT NULL,
    sender VARCHAR(10) NOT NULL, -- 'user' or 'jappi'
    message_type VARCHAR(10) NOT NULL DEFAULT 'text', -- 'text' or 'food'
    food_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
)
```

### Food Data Structure (JSONB)

```json
{
  "foods": [
    {
      "name": "Cheeseburger",
      "quantity": 1,
      "unit": "piece",
      "calories": 650,
      "protein_g": 30,
      "carbs_g": 50,
      "fat_g": 35
    }
  ],
  "total_calories": 650,
  "total_macros": {
    "protein": 30,
    "carbs": 50,
    "fat": 35
  }
}
```

## Testing the Migration

### Insert Test Message

```sql
-- Get your user ID first
SELECT id FROM auth.users WHERE email = 'dev@jappi.ca';
-- Copy the UUID

-- Insert test user message
INSERT INTO public.chat_messages (user_id, content, sender, message_type)
VALUES (
    'YOUR_USER_ID_HERE',
    'I had a cheeseburger with fries',
    'user',
    'text'
);

-- Insert test JAPPI response with food data
INSERT INTO public.chat_messages (user_id, content, sender, message_type, food_data)
VALUES (
    'YOUR_USER_ID_HERE',
    'Great! I logged 2 food items for you.',
    'jappi',
    'food',
    '{"foods": [{"name": "Cheeseburger", "quantity": 1, "unit": "piece", "calories": 650, "protein_g": 30, "carbs_g": 50, "fat_g": 35}, {"name": "French fries", "quantity": 150, "unit": "g", "calories": 400, "protein_g": 5, "carbs_g": 50, "fat_g": 20}], "total_calories": 1050, "total_macros": {"protein": 35, "carbs": 100, "fat": 55}}'::jsonb
);
```

### Query Messages

```sql
-- Get recent messages using helper function
SELECT * FROM get_user_chat_messages('YOUR_USER_ID_HERE', 10, 0);

-- Get message count
SELECT get_user_message_count('YOUR_USER_ID_HERE');

-- Query food messages only
SELECT id, content, created_at, food_data->'total_calories' as calories
FROM chat_messages
WHERE user_id = 'YOUR_USER_ID_HERE'
    AND message_type = 'food'
ORDER BY created_at DESC
LIMIT 10;
```

## Troubleshooting

### Error: "permission denied for table chat_messages"

**Cause:** RLS is enabled but you're not authenticated

**Solution:** Make sure you're logged in with a valid user when testing from the application

### Error: "relation chat_messages does not exist"

**Cause:** Migration wasn't executed successfully

**Solution:** Re-run the migration SQL in Supabase SQL Editor

### Error: "insert or update on table violates foreign key constraint"

**Cause:** Invalid user_id (user doesn't exist in auth.users)

**Solution:** Use a valid user ID from `SELECT id FROM auth.users`

## Rollback Instructions

If you need to rollback this migration, run:

```sql
-- WARNING: This will delete all chat messages!

DROP FUNCTION IF EXISTS cleanup_old_chat_messages(INTEGER);
DROP FUNCTION IF EXISTS get_user_message_count(UUID);
DROP FUNCTION IF EXISTS get_user_chat_messages(UUID, INTEGER, INTEGER);
DROP TRIGGER IF EXISTS trigger_update_chat_messages_updated_at ON public.chat_messages;
DROP FUNCTION IF EXISTS update_chat_messages_updated_at();
DROP TABLE IF EXISTS public.chat_messages CASCADE;
```

## Next Steps

After executing this migration:

1. ✅ Update frontend TypeScript types (already done in `apps/web/src/types/chat.ts`)
2. ✅ Update `useChat` hook to save messages to database
3. ✅ Load message history on chat mount
4. ✅ Test message persistence end-to-end

## References

- **Migration File:** `apps/backend/migrations/002_chat_messages.sql`
- **TypeScript Types:** `apps/web/src/types/chat.ts`
- **Hook Implementation:** `apps/web/src/hooks/useChat.ts`
- **User Story:** US-038 in `docs/Tasks.md`
