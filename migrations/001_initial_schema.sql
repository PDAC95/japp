-- ============================================================================
-- JAPPI Initial Database Schema Migration
-- Version: 001
-- Description: Create core tables (profiles, coach_settings, meal_entries)
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- PROFILES TABLE
-- Extends auth.users with application-specific user data
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT,
    age INTEGER CHECK (age >= 13 AND age <= 120),
    height_cm INTEGER CHECK (height_cm >= 50 AND height_cm <= 300),
    current_weight_kg DECIMAL(5, 2) CHECK (current_weight_kg >= 20 AND current_weight_kg <= 500),
    goal_weight_kg DECIMAL(5, 2) CHECK (goal_weight_kg >= 20 AND goal_weight_kg <= 500),
    gender TEXT CHECK (gender IN ('male', 'female', 'other')),
    activity_level TEXT CHECK (activity_level IN ('sedentary', 'light', 'moderate', 'active', 'very_active')),
    goal_type TEXT CHECK (goal_type IN ('weight_loss', 'muscle_gain', 'maintain', 'health')),
    bmi DECIMAL(5, 2),
    bmr_calories INTEGER CHECK (bmr_calories >= 0),
    tdee INTEGER CHECK (tdee >= 0),
    country TEXT,
    timezone TEXT DEFAULT 'UTC',
    language TEXT DEFAULT 'en',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add index for faster user lookups
CREATE INDEX IF NOT EXISTS idx_profiles_created_at ON public.profiles(created_at DESC);

-- ============================================================================
-- COACH SETTINGS TABLE
-- Stores user preferences for AI coach personality and behavior
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.coach_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    personality_type TEXT CHECK (personality_type IN ('friendly', 'strict', 'scientific', 'motivational', 'casual', 'zen')) DEFAULT 'friendly',
    intensity_level INTEGER CHECK (intensity_level >= 1 AND intensity_level <= 5) DEFAULT 3,
    use_profanity BOOLEAN DEFAULT FALSE,
    use_voice BOOLEAN DEFAULT FALSE,
    voice_type TEXT,
    language TEXT DEFAULT 'en',
    timezone TEXT DEFAULT 'UTC',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Add index for user_id lookups
CREATE INDEX IF NOT EXISTS idx_coach_settings_user_id ON public.coach_settings(user_id);

-- ============================================================================
-- MEAL ENTRIES TABLE
-- Stores all user food logs with nutrition data
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.meal_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    food_name TEXT NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    time TIME NOT NULL DEFAULT CURRENT_TIME,
    meal_type TEXT CHECK (meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')),
    quantity_g DECIMAL(10, 2) CHECK (quantity_g > 0),
    calories INTEGER CHECK (calories >= 0) NOT NULL,
    protein_g DECIMAL(10, 2) CHECK (protein_g >= 0) NOT NULL DEFAULT 0,
    carbs_g DECIMAL(10, 2) CHECK (carbs_g >= 0) NOT NULL DEFAULT 0,
    fat_g DECIMAL(10, 2) CHECK (fat_g >= 0) NOT NULL DEFAULT 0,
    logged_via TEXT CHECK (logged_via IN ('chat', 'voice', 'photo', 'manual', 'barcode')) DEFAULT 'chat',
    original_input TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes for common queries
CREATE INDEX IF NOT EXISTS idx_meal_entries_user_id_date ON public.meal_entries(user_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_meal_entries_user_id_created_at ON public.meal_entries(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_meal_entries_meal_type ON public.meal_entries(meal_type);

-- ============================================================================
-- AUTOMATIC TIMESTAMP UPDATES
-- Trigger to update updated_at on profiles and coach_settings
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_coach_settings_updated_at
    BEFORE UPDATE ON public.coach_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- Ensure users can only access their own data
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.coach_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.meal_entries ENABLE ROW LEVEL SECURITY;

-- Profiles policies
CREATE POLICY "Users can view own profile"
    ON public.profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
    ON public.profiles FOR INSERT
    WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON public.profiles FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- Coach settings policies
CREATE POLICY "Users can view own coach settings"
    ON public.coach_settings FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own coach settings"
    ON public.coach_settings FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own coach settings"
    ON public.coach_settings FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Meal entries policies
CREATE POLICY "Users can view own meal entries"
    ON public.meal_entries FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own meal entries"
    ON public.meal_entries FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own meal entries"
    ON public.meal_entries FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own meal entries"
    ON public.meal_entries FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================================================
-- AUTOMATIC PROFILE CREATION ON USER SIGNUP
-- Trigger to create empty profile when user signs up
-- ============================================================================

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, created_at, updated_at)
    VALUES (NEW.id, NOW(), NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- ============================================================================
-- VALIDATION CONSTRAINTS
-- Additional constraints for nutrition data integrity (CRITICAL for JAPPI)
-- ============================================================================

-- Ensure calorie calculation is within tolerance (protein: 4cal/g, carbs: 4cal/g, fat: 9cal/g)
CREATE OR REPLACE FUNCTION validate_meal_calories()
RETURNS TRIGGER AS $$
DECLARE
    calculated_calories INTEGER;
    tolerance DECIMAL;
BEGIN
    -- Calculate expected calories from macros
    calculated_calories := (NEW.protein_g * 4) + (NEW.carbs_g * 4) + (NEW.fat_g * 9);

    -- Allow 5% tolerance
    tolerance := calculated_calories * 0.05;

    -- Check if provided calories are within tolerance
    IF ABS(NEW.calories - calculated_calories) > tolerance THEN
        RAISE EXCEPTION 'Calorie calculation mismatch: provided % calories, but macros calculate to % calories',
            NEW.calories, calculated_calories;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER validate_meal_entry_calories
    BEFORE INSERT OR UPDATE ON public.meal_entries
    FOR EACH ROW
    EXECUTE FUNCTION validate_meal_calories();

-- ============================================================================
-- HELPFUL VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Daily nutrition summary view
CREATE OR REPLACE VIEW public.daily_nutrition_summary AS
SELECT
    user_id,
    date,
    COUNT(*) as total_meals,
    SUM(calories) as total_calories,
    SUM(protein_g) as total_protein_g,
    SUM(carbs_g) as total_carbs_g,
    SUM(fat_g) as total_fat_g
FROM public.meal_entries
GROUP BY user_id, date
ORDER BY date DESC;

-- Grant access to view
GRANT SELECT ON public.daily_nutrition_summary TO authenticated;

-- RLS policy for view
ALTER VIEW public.daily_nutrition_summary SET (security_invoker = true);

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE public.profiles IS 'User profile information extending auth.users';
COMMENT ON TABLE public.coach_settings IS 'AI coach personality and behavior preferences per user';
COMMENT ON TABLE public.meal_entries IS 'Food logs with nutrition data';

COMMENT ON COLUMN public.profiles.bmi IS 'Body Mass Index, calculated as weight_kg / (height_m ^ 2)';
COMMENT ON COLUMN public.profiles.bmr_calories IS 'Basal Metabolic Rate - calories burned at rest';
COMMENT ON COLUMN public.profiles.tdee IS 'Total Daily Energy Expenditure - BMR * activity multiplier';

COMMENT ON COLUMN public.meal_entries.calories IS 'Total calories, must match macro calculation within 5% tolerance';
COMMENT ON COLUMN public.meal_entries.original_input IS 'Original user text input for food log (for Claude context)';

-- ============================================================================
-- MIGRATION COMPLETE
-- Execute this entire file in Supabase SQL Editor
-- ============================================================================
