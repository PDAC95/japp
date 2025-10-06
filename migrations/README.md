# JAPPI Database Migrations

This directory contains SQL migration scripts for the JAPPI PostgreSQL database in Supabase.

## Migration Files

- `001_initial_schema.sql` - Initial database schema (profiles, coach_settings, meal_entries)

## How to Execute Migrations in Supabase

### Step 1: Access Supabase SQL Editor

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Select your JAPPI project
3. Navigate to **SQL Editor** (left sidebar)
4. Click **New Query**

### Step 2: Run Migration Script

1. Open `001_initial_schema.sql` in your code editor
2. Copy the **entire file contents**
3. Paste into the Supabase SQL Editor
4. Click **Run** or press `Ctrl+Enter` (Windows) / `Cmd+Enter` (Mac)

### Step 3: Verify Migration

After running, verify the tables were created:

```sql
-- Check all tables exist
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('profiles', 'coach_settings', 'meal_entries');

-- Verify RLS is enabled
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('profiles', 'coach_settings', 'meal_entries');

-- Check policies exist
SELECT tablename, policyname, permissive, roles, cmd
FROM pg_policies
WHERE schemaname = 'public';
```

### Step 4: Test with Sample Data (Optional)

```sql
-- This will automatically create a profile when you sign up via Supabase Auth
-- Test by registering a user at http://localhost:4000/signup

-- Or manually insert test data (replace USER_ID with actual UUID from auth.users)
INSERT INTO public.profiles (id, full_name, age, height_cm, current_weight_kg, gender, activity_level, goal_type)
VALUES (
    'YOUR_USER_UUID_HERE',
    'Test User',
    30,
    175,
    75.5,
    'male',
    'moderate',
    'weight_loss'
);
```

## What This Migration Creates

### Tables

1. **profiles** - User profile data (extends auth.users)

   - Personal info: name, age, height, weight
   - Health goals: goal type, activity level
   - Calculated fields: BMI, BMR, TDEE
   - Localization: country, timezone, language

2. **coach_settings** - AI coach preferences per user

   - Personality: friendly, strict, scientific, motivational, casual, zen
   - Intensity level: 1-5
   - Voice settings
   - Language preferences

3. **meal_entries** - Food logs with nutrition tracking
   - Food details: name, quantity, meal type
   - Macros: calories, protein, carbs, fat (with validation)
   - Metadata: logged via (chat/voice/photo), original input
   - Timestamps: date, time, created_at

### Security Features

- **Row Level Security (RLS)** enabled on all tables
- **Policies** ensure users can only access their own data
- **Automatic profile creation** when user signs up
- **Calorie validation** ensures macro math is correct (±5% tolerance)

### Performance Optimizations

- **Indexes** on common query patterns:
  - `profiles(created_at)`
  - `meal_entries(user_id, date)`
  - `meal_entries(user_id, created_at)`
  - `coach_settings(user_id)`

### Automatic Features

- **Auto-updating timestamps** on profiles and coach_settings
- **Calorie validation trigger** on meal_entries
- **Profile auto-creation** on user signup
- **Daily nutrition summary view** for dashboard queries

## Critical Validations (JAPPI-Specific)

The migration includes CRITICAL nutrition validations:

1. **No negative values** - All calories and macros must be >= 0
2. **Calorie math validation** - Calories must match macro calculation within 5%
   - Formula: `(protein × 4) + (carbs × 4) + (fat × 9) = calories ± 5%`
3. **Quantity validation** - Food quantity must be > 0
4. **Realistic ranges** - Age, height, weight within human ranges

## Troubleshooting

### Error: "permission denied for schema public"

```sql
-- Grant permissions to authenticated users
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
```

### Error: "extension uuid-ossp already exists"

This is fine - the migration uses `CREATE EXTENSION IF NOT EXISTS`

### Error: "relation already exists"

Run this to drop tables and start fresh (⚠️ WARNING: deletes all data):

```sql
DROP TABLE IF EXISTS public.meal_entries CASCADE;
DROP TABLE IF EXISTS public.coach_settings CASCADE;
DROP TABLE IF EXISTS public.profiles CASCADE;
-- Then re-run the migration
```

### Error: "calorie calculation mismatch"

The validation trigger is working. Fix your data:

```sql
-- Example: 100g chicken breast
-- protein: 31g, carbs: 0g, fat: 3.6g
-- calories: (31 × 4) + (0 × 4) + (3.6 × 9) = 124 + 0 + 32.4 = 156.4
-- Rounded to 165 is OK (within 5%), but 200 would fail
```

## Next Steps After Migration

1. ✅ Verify tables exist in Supabase dashboard
2. ✅ Test signup flow creates profile automatically
3. ✅ Test meal entry with calorie validation
4. 🔄 Update backend models to match schema
5. 🔄 Create TypeScript types for frontend
6. 🔄 Build CRUD endpoints in FastAPI

## Migration Status

- [x] Initial schema created
- [x] RLS policies enabled
- [x] Triggers configured
- [x] Validation constraints added
- [ ] Backend models updated
- [ ] Frontend types generated
- [ ] API endpoints implemented

---

**Last Updated:** 2024-10-03
**Schema Version:** 001
**Database:** Supabase PostgreSQL 15+
