# Food Database Schema Documentation

## Overview

Complete database schema for JAPPI's food tracking system, supporting:
- System-wide verified food database
- User-created custom foods
- Favorite foods with usage tracking
- Commercial food brands
- Barcode scanning support
- Multi-language support (Spanish/English)

## Database Structure

### 1. `food_brands` Table

Commercial food brands for product identification.

```sql
CREATE TABLE public.food_brands (
    id UUID PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    country TEXT,
    website TEXT,
    verified BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)
```

**Key Features:**
- Unique brand names globally
- Admin verification system
- Country of origin tracking
- Full-text search index on name

**Usage Examples:**
```sql
-- Find brand
SELECT * FROM food_brands WHERE name ILIKE '%bimbo%';

-- List verified brands
SELECT * FROM food_brands WHERE verified = true;
```

---

### 2. `foods` Table

System-wide food database with verified nutrition data.

```sql
CREATE TABLE public.foods (
    id UUID PRIMARY KEY,

    -- Basic Info
    name TEXT NOT NULL,
    name_en TEXT,
    description TEXT,
    category TEXT NOT NULL,
    brand_id UUID REFERENCES food_brands(id),
    barcode TEXT UNIQUE,

    -- Macros per 100g
    calories DECIMAL(8,2) NOT NULL CHECK (calories >= 0),
    protein_g DECIMAL(8,2) NOT NULL CHECK (protein_g >= 0),
    carbs_g DECIMAL(8,2) NOT NULL CHECK (carbs_g >= 0),
    fat_g DECIMAL(8,2) NOT NULL CHECK (fat_g >= 0),

    -- Additional Macros
    fiber_g DECIMAL(8,2),
    sugar_g DECIMAL(8,2),
    saturated_fat_g DECIMAL(8,2),
    trans_fat_g DECIMAL(8,2),

    -- Micronutrients
    sodium_mg DECIMAL(8,2),
    potassium_mg DECIMAL(8,2),
    cholesterol_mg DECIMAL(8,2),
    vitamin_a_mcg DECIMAL(8,2),
    vitamin_c_mg DECIMAL(8,2),
    calcium_mg DECIMAL(8,2),
    iron_mg DECIMAL(8,2),

    -- Serving Info
    serving_size_g DECIMAL(8,2) DEFAULT 100,
    serving_size_description TEXT,

    -- Additional Info
    allergens TEXT[],
    is_vegetarian BOOLEAN,
    is_vegan BOOLEAN,
    is_gluten_free BOOLEAN,

    -- Verification
    verified BOOLEAN DEFAULT false,
    source TEXT,

    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)
```

**Categories:**
- `protein`: Chicken, beef, fish, eggs, tofu
- `grain`: Rice, pasta, bread, tortillas
- `vegetable`: Broccoli, lettuce, tomato
- `fruit`: Banana, apple, orange
- `dairy`: Milk, cheese, yogurt
- `snack`: Chips, cookies, candy

**Validation Rules:**
1. All nutrition values must be >= 0
2. Calories must match macro calculation within 10% tolerance
3. Formula: `calories ≈ (protein_g * 4) + (carbs_g * 4) + (fat_g * 9)`

**Indexes:**
- Full-text search on `name` (Spanish)
- Full-text search on `name_en` (English)
- Category index for filtering
- Barcode index for scanning
- Brand index for brand filtering

**Usage Examples:**
```sql
-- Search foods by name (Spanish)
SELECT * FROM search_foods('pollo', 10);

-- Find by barcode
SELECT * FROM foods WHERE barcode = '7501055300013';

-- Get all proteins
SELECT * FROM foods WHERE category = 'protein' AND verified = true;

-- Get vegetarian options
SELECT * FROM foods WHERE is_vegetarian = true AND verified = true;
```

---

### 3. `user_foods` Table

User-created custom foods with personal recipes.

```sql
CREATE TABLE public.user_foods (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id),

    -- Basic Info
    name TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,
    brand_id UUID REFERENCES food_brands(id),

    -- Macros per 100g
    calories DECIMAL(8,2) NOT NULL CHECK (calories >= 0),
    protein_g DECIMAL(8,2) NOT NULL CHECK (protein_g >= 0),
    carbs_g DECIMAL(8,2) NOT NULL CHECK (carbs_g >= 0),
    fat_g DECIMAL(8,2) NOT NULL CHECK (fat_g >= 0),

    -- Additional
    fiber_g DECIMAL(8,2),
    sugar_g DECIMAL(8,2),
    saturated_fat_g DECIMAL(8,2),
    sodium_mg DECIMAL(8,2),

    -- Serving Info
    serving_size_g DECIMAL(8,2) DEFAULT 100,
    serving_size_description TEXT,

    -- Privacy
    is_public BOOLEAN DEFAULT false,

    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,

    UNIQUE(user_id, name)
)
```

**Key Features:**
- Unique food name per user
- Optional public sharing
- Same validation as system foods
- Full-text search support

**RLS Policies:**
- Users can only see their own foods or public ones
- Users can CRUD their own foods
- Public foods visible to all authenticated users

**Usage Examples:**
```sql
-- Create custom food
INSERT INTO user_foods (user_id, name, category, calories, protein_g, carbs_g, fat_g)
VALUES (auth.uid(), 'Mi receta de pollo', 'protein', 180, 32, 2, 5);

-- Get user's custom foods
SELECT * FROM user_foods WHERE user_id = auth.uid();

-- Search public custom foods
SELECT * FROM user_foods WHERE is_public = true AND name ILIKE '%smoothie%';
```

---

### 4. `food_favorites` Table

User favorite foods for quick access and usage tracking.

```sql
CREATE TABLE public.food_favorites (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id),
    food_id UUID REFERENCES foods(id),
    user_food_id UUID REFERENCES user_foods(id),

    -- Usage Tracking
    use_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ DEFAULT NOW(),

    created_at TIMESTAMPTZ,

    -- Either food_id OR user_food_id, not both
    CHECK (
        (food_id IS NOT NULL AND user_food_id IS NULL) OR
        (food_id IS NULL AND user_food_id IS NOT NULL)
    ),

    UNIQUE(user_id, food_id),
    UNIQUE(user_id, user_food_id)
)
```

**Key Features:**
- Track usage frequency
- Quick access to frequently used foods
- Support both system and custom foods
- Auto-tracking with use_count

**Usage Examples:**
```sql
-- Add to favorites
INSERT INTO food_favorites (user_id, food_id)
VALUES (auth.uid(), 'food-uuid-here');

-- Get most used foods
SELECT * FROM get_user_frequent_foods(auth.uid(), 10);

-- Increment use count
UPDATE food_favorites
SET use_count = use_count + 1, last_used_at = NOW()
WHERE user_id = auth.uid() AND food_id = 'food-uuid-here';
```

---

## Helper Functions

### `search_foods(query TEXT, limit INT)`

Full-text search for foods by name (Spanish).

```sql
-- Search for chicken
SELECT * FROM search_foods('pollo', 20);

-- Returns:
-- id, name, category, calories, protein_g, carbs_g, fat_g, verified, relevance
```

**Features:**
- Spanish text search with ranking
- Returns only verified foods
- Sorted by relevance + name
- Configurable result limit

---

### `get_user_frequent_foods(user_id UUID, limit INT)`

Get user's most frequently used foods from favorites.

```sql
-- Get top 10 foods
SELECT * FROM get_user_frequent_foods(auth.uid(), 10);

-- Returns:
-- food_id, food_name, use_count, last_used_at
```

**Features:**
- Combines system and custom foods
- Sorted by use_count DESC
- Shows last usage timestamp

---

## Validation System

### Calorie Validation Trigger

Automatically validates that calories match macro calculation.

**Formula:**
```
calories ≈ (protein_g * 4) + (carbs_g * 4) + (fat_g * 9)
```

**Tolerance:** 10% (allows for rounding and fiber adjustments)

**Example:**
```sql
-- This will PASS (within 10% tolerance)
INSERT INTO foods (name, category, calories, protein_g, carbs_g, fat_g, verified)
VALUES ('Chicken', 'protein', 165, 31, 0, 3.6, true);
-- Calculated: (31*4) + (0*4) + (3.6*9) = 124 + 32.4 = 156.4
-- Provided: 165
-- Difference: 5.2% ✓

-- This will FAIL (over 10% tolerance)
INSERT INTO foods (name, category, calories, protein_g, carbs_g, fat_g, verified)
VALUES ('Invalid', 'protein', 500, 10, 10, 5, true);
-- Calculated: (10*4) + (10*4) + (5*9) = 40 + 40 + 45 = 125
-- Provided: 500
-- Difference: 300% ✗ EXCEPTION!
```

---

## Row Level Security (RLS)

### `foods` Table
- ✅ **SELECT**: Everyone can read verified foods
- ✅ **INSERT**: Authenticated users can suggest foods (admin verifies later)

### `user_foods` Table
- ✅ **SELECT**: Users see own foods OR public foods
- ✅ **INSERT**: Users can create own foods
- ✅ **UPDATE**: Users can update own foods
- ✅ **DELETE**: Users can delete own foods

### `food_favorites` Table
- ✅ **ALL**: Users can only access their own favorites

### `food_brands` Table
- ✅ **SELECT**: Everyone can read brands
- ✅ **INSERT**: Authenticated users can suggest brands

---

## Indexes

### Performance Indexes

```sql
-- Full-text search (Spanish)
CREATE INDEX idx_foods_name ON foods USING gin(to_tsvector('spanish', name));
CREATE INDEX idx_user_foods_name ON user_foods USING gin(to_tsvector('spanish', name));

-- Full-text search (English)
CREATE INDEX idx_foods_name_en ON foods USING gin(to_tsvector('english', name_en));

-- Category filtering
CREATE INDEX idx_foods_category ON foods(category);
CREATE INDEX idx_user_foods_category ON user_foods(category);

-- Barcode scanning
CREATE INDEX idx_foods_barcode ON foods(barcode) WHERE barcode IS NOT NULL;

-- User data
CREATE INDEX idx_user_foods_user ON user_foods(user_id);
CREATE INDEX idx_food_favorites_user ON food_favorites(user_id);

-- Favorites sorting
CREATE INDEX idx_food_favorites_last_used ON food_favorites(user_id, last_used_at DESC);
```

---

## Seeded Data

Migration includes 20 common foods:

**Proteins:**
- Pechuga de pollo (Chicken breast)
- Huevo (Egg)
- Atún (Tuna)
- Carne molida de res (Ground beef)

**Grains:**
- Arroz blanco cocido (White rice)
- Pan blanco (White bread)
- Tortilla de maíz (Corn tortilla)
- Pasta cocida (Cooked pasta)

**Vegetables:**
- Brócoli (Broccoli)
- Lechuga (Lettuce)
- Tomate (Tomato)
- Aguacate (Avocado)

**Fruits:**
- Plátano (Banana)
- Manzana (Apple)
- Naranja (Orange)

**Dairy:**
- Leche entera (Whole milk)
- Queso fresco (Fresh cheese)
- Yogurt natural (Plain yogurt)

**Snacks:**
- Papas fritas (French fries)
- Hamburguesa (Hamburger)

---

## Integration with `meal_entries`

Migration adds foreign key columns to existing `meal_entries` table:

```sql
ALTER TABLE meal_entries
ADD COLUMN food_id UUID REFERENCES foods(id),
ADD COLUMN user_food_id UUID REFERENCES user_foods(id);
```

**Usage:**
```sql
-- Log meal with system food
INSERT INTO meal_entries (
    user_id, food_id, quantity_g, date, meal_type,
    calories, protein_g, carbs_g, fat_g
)
SELECT
    auth.uid(),
    f.id,
    150, -- 150g serving
    CURRENT_DATE,
    'lunch',
    f.calories * 1.5, -- Scale by serving
    f.protein_g * 1.5,
    f.carbs_g * 1.5,
    f.fat_g * 1.5
FROM foods f
WHERE f.name = 'Pechuga de pollo';
```

---

## API Integration Points

### Backend Endpoints (to implement)

```python
# GET /api/v1/foods/search?q=pollo&limit=20
# Search system foods

# GET /api/v1/foods/{food_id}
# Get specific food details

# POST /api/v1/foods/barcode/{barcode}
# Lookup food by barcode

# GET /api/v1/user-foods
# Get user's custom foods

# POST /api/v1/user-foods
# Create custom food

# PUT /api/v1/user-foods/{id}
# Update custom food

# DELETE /api/v1/user-foods/{id}
# Delete custom food

# GET /api/v1/favorites
# Get user's favorite foods

# POST /api/v1/favorites
# Add to favorites

# DELETE /api/v1/favorites/{id}
# Remove from favorites

# POST /api/v1/favorites/{id}/use
# Increment use count
```

---

## Testing Queries

```sql
-- Test calorie validation (should PASS)
INSERT INTO foods (name, category, calories, protein_g, carbs_g, fat_g, verified)
VALUES ('Test Food', 'protein', 165, 31, 0, 3.6, true);

-- Test calorie validation (should FAIL)
INSERT INTO foods (name, category, calories, protein_g, carbs_g, fat_g, verified)
VALUES ('Invalid Food', 'protein', 999, 10, 10, 5, true);
-- Expected: EXCEPTION - Calorie calculation mismatch

-- Test search function
SELECT * FROM search_foods('pollo', 5);

-- Test user food creation
INSERT INTO user_foods (user_id, name, category, calories, protein_g, carbs_g, fat_g)
VALUES (auth.uid(), 'Mi smoothie', 'snack', 200, 15, 30, 2);

-- Test favorites
INSERT INTO food_favorites (user_id, food_id)
SELECT auth.uid(), id FROM foods WHERE name = 'Pechuga de pollo' LIMIT 1;

-- Test frequent foods function
SELECT * FROM get_user_frequent_foods(auth.uid(), 10);
```

---

## Migration Steps

1. **Execute in Supabase SQL Editor:**
   ```bash
   # Copy contents of 004_food_database_schema.sql
   # Paste in Supabase SQL Editor
   # Click "Run"
   ```

2. **Verify Tables Created:**
   ```sql
   SELECT table_name
   FROM information_schema.tables
   WHERE table_schema = 'public'
   AND table_name IN ('foods', 'user_foods', 'food_favorites', 'food_brands');
   ```

3. **Verify RLS Enabled:**
   ```sql
   SELECT tablename, rowsecurity
   FROM pg_tables
   WHERE schemaname = 'public'
   AND tablename IN ('foods', 'user_foods', 'food_favorites', 'food_brands');
   ```

4. **Test Search Function:**
   ```sql
   SELECT * FROM search_foods('pollo', 5);
   ```

5. **Verify Seed Data:**
   ```sql
   SELECT COUNT(*) FROM foods WHERE verified = true;
   -- Expected: 20 foods
   ```

---

## Performance Considerations

### Expected Query Performance

| Query Type | Expected Time | Index Used |
|------------|---------------|------------|
| Search by name | < 50ms | GIN full-text |
| Get by ID | < 10ms | Primary key |
| Category filter | < 20ms | B-tree category |
| Barcode lookup | < 15ms | B-tree barcode |
| User favorites | < 30ms | User + timestamp |

### Optimization Tips

1. **Use indexes:** All search queries use indexes automatically
2. **Limit results:** Always use LIMIT in searches
3. **Cache frequently used:** Cache common foods in application layer
4. **Batch operations:** Insert multiple favorites at once
5. **Prepared statements:** Use parameterized queries

---

## Future Enhancements

### Planned Features

1. **Food Photos:**
   - Add `image_url` column to foods/user_foods
   - Store in Supabase Storage

2. **Meal Templates:**
   - Create `meal_templates` table
   - Link multiple foods into common meals

3. **Recipe Builder:**
   - Create `recipes` table with ingredients
   - Auto-calculate nutrition from ingredients

4. **Nutrition Goals:**
   - Add per-meal macro targets
   - Track adherence over time

5. **Food Ratings:**
   - User ratings and reviews
   - Community feedback system

---

## Troubleshooting

### Common Issues

**Issue:** Calorie validation fails
```
ERROR: Calorie calculation mismatch
```
**Solution:** Check macro values match calorie formula within 10%

---

**Issue:** Food search returns no results
```sql
SELECT * FROM search_foods('chicken', 10);
-- Returns 0 rows
```
**Solution:** Use Spanish name: `search_foods('pollo', 10)`

---

**Issue:** Can't insert duplicate user food
```
ERROR: duplicate key value violates unique constraint
```
**Solution:** Each user can only have one food with same name

---

**Issue:** RLS blocks food access
```
ERROR: new row violates row-level security policy
```
**Solution:** Ensure user is authenticated with `auth.uid()`

---

## Support

For questions or issues:
- Check ERRORS.md for known issues
- Review CLAUDE.md for development guidelines
- Test queries in Supabase SQL Editor
- Verify RLS policies are enabled

---

**Migration Status:** ✅ Ready to Execute
**Tables:** 4 (foods, user_foods, food_favorites, food_brands)
**Functions:** 2 (search_foods, get_user_frequent_foods)
**Triggers:** 6 (validation + timestamps)
**Seed Data:** 20 common foods + 5 brands
**Story:** US-042
**Author:** JAPPI Development Team
**Date:** 2024-10-14
