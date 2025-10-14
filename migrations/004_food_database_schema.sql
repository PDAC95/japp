-- =====================================================
-- MIGRATION 004: Food Database Schema
-- =====================================================
-- Description: Complete food database structure for JAPPI
-- Includes: foods, user_foods, food_favorites, food_brands
-- Created: 2024-10-14
-- Story: US-042
-- =====================================================

-- =====================================================
-- 1. FOOD BRANDS TABLE
-- =====================================================
-- Store commercial food brands
CREATE TABLE IF NOT EXISTS public.food_brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    country TEXT, -- Country of origin
    website TEXT,
    verified BOOLEAN DEFAULT false, -- Admin verified brand
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for brand search
CREATE INDEX idx_food_brands_name ON public.food_brands USING gin(to_tsvector('spanish', name));

-- =====================================================
-- 2. FOODS TABLE (System Foods)
-- =====================================================
-- Base food database with nutrition info
CREATE TABLE IF NOT EXISTS public.foods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Basic Information
    name TEXT NOT NULL,
    name_en TEXT, -- English name for translations
    description TEXT,
    category TEXT NOT NULL, -- 'fruit', 'vegetable', 'protein', 'grain', 'dairy', 'snack', etc.
    brand_id UUID REFERENCES public.food_brands(id) ON DELETE SET NULL,
    barcode TEXT UNIQUE, -- For barcode scanning

    -- Nutrition per 100g (base unit)
    calories DECIMAL(8, 2) NOT NULL CHECK (calories >= 0),
    protein_g DECIMAL(8, 2) NOT NULL DEFAULT 0 CHECK (protein_g >= 0),
    carbs_g DECIMAL(8, 2) NOT NULL DEFAULT 0 CHECK (carbs_g >= 0),
    fat_g DECIMAL(8, 2) NOT NULL DEFAULT 0 CHECK (fat_g >= 0),

    -- Additional Macros
    fiber_g DECIMAL(8, 2) DEFAULT 0 CHECK (fiber_g >= 0),
    sugar_g DECIMAL(8, 2) DEFAULT 0 CHECK (sugar_g >= 0),
    saturated_fat_g DECIMAL(8, 2) DEFAULT 0 CHECK (saturated_fat_g >= 0),
    trans_fat_g DECIMAL(8, 2) DEFAULT 0 CHECK (trans_fat_g >= 0),

    -- Micronutrients (optional)
    sodium_mg DECIMAL(8, 2) DEFAULT 0 CHECK (sodium_mg >= 0),
    potassium_mg DECIMAL(8, 2) DEFAULT 0 CHECK (potassium_mg >= 0),
    cholesterol_mg DECIMAL(8, 2) DEFAULT 0 CHECK (cholesterol_mg >= 0),
    vitamin_a_mcg DECIMAL(8, 2) DEFAULT 0 CHECK (vitamin_a_mcg >= 0),
    vitamin_c_mg DECIMAL(8, 2) DEFAULT 0 CHECK (vitamin_c_mg >= 0),
    calcium_mg DECIMAL(8, 2) DEFAULT 0 CHECK (calcium_mg >= 0),
    iron_mg DECIMAL(8, 2) DEFAULT 0 CHECK (iron_mg >= 0),

    -- Serving Information
    serving_size_g DECIMAL(8, 2) DEFAULT 100, -- Default serving size
    serving_size_description TEXT, -- "1 cup", "1 piece", "1 tablespoon"

    -- Additional Info
    allergens TEXT[], -- Array of allergens: ['gluten', 'dairy', 'nuts', etc.]
    is_vegetarian BOOLEAN DEFAULT false,
    is_vegan BOOLEAN DEFAULT false,
    is_gluten_free BOOLEAN DEFAULT false,

    -- Verification
    verified BOOLEAN DEFAULT false, -- Admin verified
    source TEXT, -- Data source: 'usda', 'manual', 'user', 'api'

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast search
CREATE INDEX idx_foods_name ON public.foods USING gin(to_tsvector('spanish', name));
CREATE INDEX idx_foods_name_en ON public.foods USING gin(to_tsvector('english', name_en));
CREATE INDEX idx_foods_category ON public.foods(category);
CREATE INDEX idx_foods_barcode ON public.foods(barcode) WHERE barcode IS NOT NULL;
CREATE INDEX idx_foods_brand ON public.foods(brand_id) WHERE brand_id IS NOT NULL;

-- =====================================================
-- 3. USER FOODS TABLE (Custom User Foods)
-- =====================================================
-- User-created custom foods
CREATE TABLE IF NOT EXISTS public.user_foods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Basic Information
    name TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,
    brand_id UUID REFERENCES public.food_brands(id) ON DELETE SET NULL,

    -- Nutrition per 100g
    calories DECIMAL(8, 2) NOT NULL CHECK (calories >= 0),
    protein_g DECIMAL(8, 2) NOT NULL DEFAULT 0 CHECK (protein_g >= 0),
    carbs_g DECIMAL(8, 2) NOT NULL DEFAULT 0 CHECK (carbs_g >= 0),
    fat_g DECIMAL(8, 2) NOT NULL DEFAULT 0 CHECK (fat_g >= 0),

    -- Additional Macros
    fiber_g DECIMAL(8, 2) DEFAULT 0 CHECK (fiber_g >= 0),
    sugar_g DECIMAL(8, 2) DEFAULT 0 CHECK (sugar_g >= 0),
    saturated_fat_g DECIMAL(8, 2) DEFAULT 0 CHECK (saturated_fat_g >= 0),

    -- Micronutrients
    sodium_mg DECIMAL(8, 2) DEFAULT 0 CHECK (sodium_mg >= 0),

    -- Serving Information
    serving_size_g DECIMAL(8, 2) DEFAULT 100,
    serving_size_description TEXT,

    -- Privacy
    is_public BOOLEAN DEFAULT false, -- Share with other users

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraint: Unique name per user
    UNIQUE(user_id, name)
);

-- Indexes for user foods
CREATE INDEX idx_user_foods_user ON public.user_foods(user_id);
CREATE INDEX idx_user_foods_name ON public.user_foods USING gin(to_tsvector('spanish', name));
CREATE INDEX idx_user_foods_category ON public.user_foods(category);
CREATE INDEX idx_user_foods_public ON public.user_foods(is_public) WHERE is_public = true;

-- =====================================================
-- 4. FOOD FAVORITES TABLE
-- =====================================================
-- User's favorite foods for quick access
CREATE TABLE IF NOT EXISTS public.food_favorites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    food_id UUID REFERENCES public.foods(id) ON DELETE CASCADE,
    user_food_id UUID REFERENCES public.user_foods(id) ON DELETE CASCADE,

    -- Usage tracking
    use_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ DEFAULT NOW(),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraint: Either food_id OR user_food_id must be set, not both
    CONSTRAINT check_food_reference CHECK (
        (food_id IS NOT NULL AND user_food_id IS NULL) OR
        (food_id IS NULL AND user_food_id IS NOT NULL)
    ),

    -- Constraint: Unique favorite per user per food
    UNIQUE(user_id, food_id),
    UNIQUE(user_id, user_food_id)
);

-- Indexes for favorites
CREATE INDEX idx_food_favorites_user ON public.food_favorites(user_id);
CREATE INDEX idx_food_favorites_food ON public.food_favorites(food_id) WHERE food_id IS NOT NULL;
CREATE INDEX idx_food_favorites_user_food ON public.food_favorites(user_food_id) WHERE user_food_id IS NOT NULL;
CREATE INDEX idx_food_favorites_last_used ON public.food_favorites(user_id, last_used_at DESC);

-- =====================================================
-- 5. MEAL ENTRIES UPDATE (Add Foreign Keys)
-- =====================================================
-- Add foreign keys to existing meal_entries table
ALTER TABLE public.meal_entries
ADD COLUMN IF NOT EXISTS food_id UUID REFERENCES public.foods(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS user_food_id UUID REFERENCES public.user_foods(id) ON DELETE SET NULL;

-- Index for meal entries food references
CREATE INDEX IF NOT EXISTS idx_meal_entries_food ON public.meal_entries(food_id) WHERE food_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_meal_entries_user_food ON public.meal_entries(user_food_id) WHERE user_food_id IS NOT NULL;

-- =====================================================
-- 6. VALIDATION FUNCTIONS
-- =====================================================

-- Function: Validate calorie calculation from macros
CREATE OR REPLACE FUNCTION validate_food_calories()
RETURNS TRIGGER AS $$
DECLARE
    calculated_calories DECIMAL(8, 2);
    tolerance DECIMAL(8, 2);
BEGIN
    -- Calculate calories from macros (Protein: 4cal/g, Carbs: 4cal/g, Fat: 9cal/g)
    calculated_calories := (NEW.protein_g * 4) + (NEW.carbs_g * 4) + (NEW.fat_g * 9);

    -- Allow 10% tolerance for rounding and fiber adjustments
    tolerance := calculated_calories * 0.10;

    -- Check if calories are within tolerance
    IF ABS(NEW.calories - calculated_calories) > tolerance THEN
        RAISE EXCEPTION
            'Calorie calculation mismatch: Provided % cal, Calculated % cal (tolerance: ±%)',
            NEW.calories, calculated_calories, tolerance;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply validation trigger to foods table
DROP TRIGGER IF EXISTS trigger_validate_food_calories ON public.foods;
CREATE TRIGGER trigger_validate_food_calories
    BEFORE INSERT OR UPDATE ON public.foods
    FOR EACH ROW
    EXECUTE FUNCTION validate_food_calories();

-- Apply validation trigger to user_foods table
DROP TRIGGER IF EXISTS trigger_validate_user_food_calories ON public.user_foods;
CREATE TRIGGER trigger_validate_user_food_calories
    BEFORE INSERT OR UPDATE ON public.user_foods
    FOR EACH ROW
    EXECUTE FUNCTION validate_food_calories();

-- =====================================================
-- 7. AUTO-UPDATE TIMESTAMPS
-- =====================================================

-- Function: Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to food_brands
DROP TRIGGER IF EXISTS trigger_update_food_brands_updated_at ON public.food_brands;
CREATE TRIGGER trigger_update_food_brands_updated_at
    BEFORE UPDATE ON public.food_brands
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply to foods
DROP TRIGGER IF EXISTS trigger_update_foods_updated_at ON public.foods;
CREATE TRIGGER trigger_update_foods_updated_at
    BEFORE UPDATE ON public.foods
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply to user_foods
DROP TRIGGER IF EXISTS trigger_update_user_foods_updated_at ON public.user_foods;
CREATE TRIGGER trigger_update_user_foods_updated_at
    BEFORE UPDATE ON public.user_foods
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- 8. ROW LEVEL SECURITY (RLS)
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE public.food_brands ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.foods ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_foods ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.food_favorites ENABLE ROW LEVEL SECURITY;

-- RLS Policies for food_brands
-- Everyone can read brands
CREATE POLICY "Public food brands are viewable by everyone"
    ON public.food_brands FOR SELECT
    USING (true);

-- Only authenticated users can suggest brands (admin approves)
CREATE POLICY "Authenticated users can suggest brands"
    ON public.food_brands FOR INSERT
    TO authenticated
    WITH CHECK (true);

-- RLS Policies for foods
-- Everyone can read verified foods
CREATE POLICY "Public foods are viewable by everyone"
    ON public.foods FOR SELECT
    USING (verified = true);

-- Authenticated users can suggest foods (admin verifies)
CREATE POLICY "Authenticated users can suggest foods"
    ON public.foods FOR INSERT
    TO authenticated
    WITH CHECK (true);

-- RLS Policies for user_foods
-- Users can only see their own custom foods or public ones
CREATE POLICY "Users can view their own foods"
    ON public.user_foods FOR SELECT
    USING (
        auth.uid() = user_id OR is_public = true
    );

-- Users can insert their own foods
CREATE POLICY "Users can create their own foods"
    ON public.user_foods FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own foods
CREATE POLICY "Users can update their own foods"
    ON public.user_foods FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Users can delete their own foods
CREATE POLICY "Users can delete their own foods"
    ON public.user_foods FOR DELETE
    TO authenticated
    USING (auth.uid() = user_id);

-- RLS Policies for food_favorites
-- Users can only see their own favorites
CREATE POLICY "Users can view their own favorites"
    ON public.food_favorites FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

-- Users can insert their own favorites
CREATE POLICY "Users can create their own favorites"
    ON public.food_favorites FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own favorites
CREATE POLICY "Users can update their own favorites"
    ON public.food_favorites FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Users can delete their own favorites
CREATE POLICY "Users can delete their own favorites"
    ON public.food_favorites FOR DELETE
    TO authenticated
    USING (auth.uid() = user_id);

-- =====================================================
-- 9. HELPER FUNCTIONS
-- =====================================================

-- Function: Search foods by name (Spanish text search)
CREATE OR REPLACE FUNCTION search_foods(search_query TEXT, limit_count INT DEFAULT 20)
RETURNS TABLE (
    id UUID,
    name TEXT,
    category TEXT,
    calories DECIMAL,
    protein_g DECIMAL,
    carbs_g DECIMAL,
    fat_g DECIMAL,
    verified BOOLEAN,
    relevance REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        f.id,
        f.name,
        f.category,
        f.calories,
        f.protein_g,
        f.carbs_g,
        f.fat_g,
        f.verified,
        ts_rank(to_tsvector('spanish', f.name), plainto_tsquery('spanish', search_query)) as relevance
    FROM public.foods f
    WHERE
        f.verified = true AND
        to_tsvector('spanish', f.name) @@ plainto_tsquery('spanish', search_query)
    ORDER BY relevance DESC, f.name
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Function: Get user's most used foods (from favorites)
CREATE OR REPLACE FUNCTION get_user_frequent_foods(user_uuid UUID, limit_count INT DEFAULT 10)
RETURNS TABLE (
    food_id UUID,
    food_name TEXT,
    use_count INTEGER,
    last_used_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(f.id, uf.id) as food_id,
        COALESCE(f.name, uf.name) as food_name,
        fav.use_count,
        fav.last_used_at
    FROM public.food_favorites fav
    LEFT JOIN public.foods f ON fav.food_id = f.id
    LEFT JOIN public.user_foods uf ON fav.user_food_id = uf.id
    WHERE fav.user_id = user_uuid
    ORDER BY fav.use_count DESC, fav.last_used_at DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 10. SEED DATA (Common Mexican/American Foods)
-- =====================================================

-- Insert common food brands
INSERT INTO public.food_brands (name, country, verified) VALUES
    ('Generic', 'Global', true),
    ('Bimbo', 'Mexico', true),
    ('Coca-Cola', 'USA', true),
    ('Herdez', 'Mexico', true),
    ('La Costeña', 'Mexico', true)
ON CONFLICT (name) DO NOTHING;

-- Insert common foods (sample dataset)
INSERT INTO public.foods (name, name_en, category, calories, protein_g, carbs_g, fat_g, fiber_g, sugar_g, verified, source) VALUES
    -- Proteins
    ('Pechuga de pollo', 'Chicken breast', 'protein', 165, 31, 0, 3.6, 0, 0, true, 'usda'),
    ('Huevo', 'Egg', 'protein', 155, 13, 1.1, 11, 0, 1.1, true, 'usda'),
    ('Atún', 'Tuna', 'protein', 130, 29, 0, 1.3, 0, 0, true, 'usda'),
    ('Carne molida de res', 'Ground beef', 'protein', 250, 26, 0, 17, 0, 0, true, 'usda'),

    -- Grains
    ('Arroz blanco cocido', 'White rice cooked', 'grain', 130, 2.7, 28, 0.3, 0.4, 0, true, 'usda'),
    ('Pan blanco', 'White bread', 'grain', 265, 9, 49, 3.2, 2.7, 5, true, 'usda'),
    ('Tortilla de maíz', 'Corn tortilla', 'grain', 218, 5.7, 45, 2.8, 6.3, 1.1, true, 'usda'),
    ('Pasta cocida', 'Cooked pasta', 'grain', 131, 5, 25, 1.1, 1.8, 0.6, true, 'usda'),

    -- Vegetables
    ('Brócoli', 'Broccoli', 'vegetable', 43, 2.8, 7, 0.4, 2.6, 1.7, true, 'usda'),
    ('Lechuga', 'Lettuce', 'vegetable', 19, 1.4, 2.9, 0.2, 1.3, 0.8, true, 'usda'),
    ('Tomate', 'Tomato', 'vegetable', 21, 0.9, 3.9, 0.2, 1.2, 2.6, true, 'usda'),
    ('Aguacate', 'Avocado', 'vegetable', 160, 2, 8.5, 15, 6.7, 0.7, true, 'usda'),

    -- Fruits
    ('Plátano', 'Banana', 'fruit', 99, 1.1, 23, 0.3, 2.6, 12, true, 'usda'),
    ('Manzana', 'Apple', 'fruit', 59, 0.3, 14, 0.2, 2.4, 10, true, 'usda'),
    ('Naranja', 'Orange', 'fruit', 52, 0.9, 12, 0.1, 2.4, 9, true, 'usda'),

    -- Dairy
    ('Leche entera', 'Whole milk', 'dairy', 61, 3.2, 4.8, 3.3, 0, 5.1, true, 'usda'),
    ('Queso fresco', 'Fresh cheese', 'dairy', 264, 18, 3.1, 21, 0, 0.5, true, 'usda'),
    ('Yogurt natural', 'Plain yogurt', 'dairy', 61, 3.5, 4.7, 3.3, 0, 4.7, true, 'usda'),

    -- Snacks
    ('Papas fritas', 'French fries', 'snack', 312, 3.4, 41, 15, 3.8, 0.2, true, 'usda'),
    ('Hamburguesa', 'Hamburger', 'snack', 295, 17, 24, 14, 1.5, 3.5, true, 'usda')
ON CONFLICT DO NOTHING;

-- =====================================================
-- 11. COMMENTS AND DOCUMENTATION
-- =====================================================

COMMENT ON TABLE public.food_brands IS 'Commercial food brands for product identification';
COMMENT ON TABLE public.foods IS 'System-wide food database with verified nutrition data';
COMMENT ON TABLE public.user_foods IS 'User-created custom foods with personal recipes';
COMMENT ON TABLE public.food_favorites IS 'User favorite foods for quick access and tracking usage';

COMMENT ON COLUMN public.foods.calories IS 'Calories per 100g - must match macro calculation within 10% tolerance';
COMMENT ON COLUMN public.foods.verified IS 'Admin verified food entry - only verified foods shown to users';
COMMENT ON COLUMN public.user_foods.is_public IS 'Allow other users to see and use this custom food';
COMMENT ON COLUMN public.food_favorites.use_count IS 'Number of times user has logged this food';

-- =====================================================
-- MIGRATION COMPLETE
-- =====================================================
-- Execute this file in Supabase SQL Editor
-- All tables, indexes, triggers, and RLS policies created
-- Sample data seeded
-- Ready for Sprint 2 food tracking features
-- =====================================================
