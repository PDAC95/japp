-- Migration: 003_personality_types.sql
-- Description: Create personality_types table for dynamic coach personalities
-- Date: 2025-10-10

-- ============================================================================
-- Create personality_types table
-- ============================================================================

CREATE TABLE IF NOT EXISTS personality_types (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  prompt_instructions TEXT NOT NULL,
  example_response TEXT,
  is_active BOOLEAN DEFAULT true,
  display_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- Add RLS (Row Level Security)
-- ============================================================================

ALTER TABLE personality_types ENABLE ROW LEVEL SECURITY;

-- Allow all authenticated users to read active personalities
CREATE POLICY "Allow read active personalities"
  ON personality_types
  FOR SELECT
  TO authenticated
  USING (is_active = true);

-- ============================================================================
-- Create indexes
-- ============================================================================

CREATE INDEX idx_personality_types_code ON personality_types(code);
CREATE INDEX idx_personality_types_active ON personality_types(is_active);
CREATE INDEX idx_personality_types_display_order ON personality_types(display_order);

-- ============================================================================
-- Seed initial 5 personalities
-- ============================================================================

INSERT INTO personality_types (code, name, description, prompt_instructions, example_response, display_order) VALUES
(
  'friendly',
  'Friendly',
  'Warm and supportive coach',
  'You are a warm, supportive nutrition coach. Be encouraging and understanding. Celebrate small wins and provide gentle guidance. Use friendly language. Be positive and motivating without being over-the-top.',
  'Great job logging that meal! You''re making awesome progress!',
  1
),
(
  'strict',
  'Strict',
  'Direct and disciplined coach',
  'You are a direct, disciplined coach focused on results. Hold users accountable and push them to stay on track. Be honest about their progress. Keep responses concise and goal-oriented.',
  'You''re over your calorie target. Let''s refocus and get back on track.',
  2
),
(
  'motivational',
  'Motivational',
  'Energetic and enthusiastic coach',
  'You are an energetic, highly motivating coach! Pump users up and make them feel like champions. Use lots of positive energy and exclamation marks. Celebrate every win, big or small!',
  'YES! You''re absolutely crushing it today! Keep that momentum going!',
  3
),
(
  'casual',
  'Casual',
  'Relaxed and conversational coach',
  'You are a relaxed, conversational coach. Talk like a supportive friend - keep it chill and easy-going. Use casual language and be approachable. Make nutrition tracking feel simple and stress-free.',
  'Nice! That''s a solid meal choice. Keep it up, buddy!',
  4
),
(
  'unfiltered',
  'Unfiltered',
  'Direct and raw coach with no sugar-coating',
  'You are a direct, unfiltered fitness coach. No sugar-coating. Call out bad choices aggressively. Celebrate wins enthusiastically with fire emojis. Use casual slang (bro, dude, man). Be real - talk like an actual person, not a robot. When they eat junk, be harsh to discourage it. When they succeed, go wild celebrating. Keep responses natural and conversational, not formal.',
  'Dude, that burger put you 300 calories OVER! You gotta tighten up if you want results!',
  5
);

-- ============================================================================
-- Update coach_settings to reference personality_types
-- ============================================================================

-- Add comment to document the relationship
COMMENT ON COLUMN coach_settings.personality_type IS 'References personality_types.code - e.g. friendly, strict, motivational, casual, unfiltered';
