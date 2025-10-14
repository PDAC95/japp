# Food Search API Documentation

## Overview

Complete REST API for food search, management, and favorites tracking.

**Base URL:** `http://localhost:9000/api/v1/foods`

## Endpoints

### 1. Search Foods

**Endpoint:** `GET /foods/search`

Search for foods with intelligent prioritization across system foods, user custom foods, and favorites.

#### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `q` | string | Yes | - | Search query (1-100 chars) |
| `page` | integer | No | 1 | Page number (≥1) |
| `page_size` | integer | No | 20 | Items per page (1-100) |
| `category` | string | No | - | Filter by category |
| `brand_id` | string | No | - | Filter by brand UUID |
| `only_user_foods` | boolean | No | false | Only return user's custom foods |
| `min_calories` | float | No | - | Minimum calories filter |
| `max_calories` | float | No | - | Maximum calories filter |
| `is_vegetarian` | boolean | No | - | Filter vegetarian foods |
| `is_vegan` | boolean | No | - | Filter vegan foods |
| `is_gluten_free` | boolean | No | - | Filter gluten-free foods |

#### Categories

- `protein` - Chicken, beef, fish, eggs, tofu
- `grain` - Rice, pasta, bread, tortillas
- `vegetable` - Broccoli, lettuce, tomato, avocado
- `fruit` - Banana, apple, orange, berries
- `dairy` - Milk, cheese, yogurt
- `snack` - Chips, cookies, candy, fries

#### Priority Order

1. **User's custom foods (exact match)** - Score: 0.8 base + match bonus
2. **User's favorite foods** - Score: +0.3 boost
3. **System foods (exact match)** - Score: 0.6 base + match bonus
4. **Partial matches** - Lower scores based on match quality
5. **Category matches** - Lowest priority

#### Match Bonuses

- **Exact match:** +0.4
- **Starts with query:** +0.3
- **Contains query:** +0.2
- **Word starts with query:** +0.1

#### Example Requests

```bash
# Basic search
curl "http://localhost:9000/api/v1/foods/search?q=pollo"

# Search with filters
curl "http://localhost:9000/api/v1/foods/search?q=taco&category=snack&max_calories=300"

# Search only user foods
curl "http://localhost:9000/api/v1/foods/search?q=smoothie&only_user_foods=true"

# Vegetarian foods
curl "http://localhost:9000/api/v1/foods/search?q=ensalada&is_vegetarian=true"

# Pagination
curl "http://localhost:9000/api/v1/foods/search?q=manzana&page=2&page_size=10"
```

#### Response

```json
{
  "success": true,
  "data": [
    {
      "id": "food-uuid",
      "source": "system",
      "name": "Pechuga de pollo",
      "name_en": "Chicken breast",
      "category": "protein",
      "brand_name": null,
      "calories": 165.0,
      "protein_g": 31.0,
      "carbs_g": 0.0,
      "fat_g": 3.6,
      "serving_size_g": 100.0,
      "serving_size_description": "100g",
      "is_favorite": true,
      "use_count": 45,
      "relevance_score": 1.0
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 15,
    "total_pages": 1,
    "has_more": false
  },
  "message": "Found 15 results for 'pollo'"
}
```

#### Status Codes

- `200 OK` - Search successful
- `400 Bad Request` - Invalid parameters
- `500 Internal Server Error` - Search failed

---

### 2. Get Food by ID

**Endpoint:** `GET /foods/{food_id}`

Get detailed information about a specific food.

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `food_id` | string (UUID) | Yes | Food or UserFood ID |

#### Example Request

```bash
curl "http://localhost:9000/api/v1/foods/food-uuid-here"
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": "food-uuid",
    "source": "system",
    "name": "Pechuga de pollo",
    "name_en": "Chicken breast",
    "category": "protein",
    "brand_name": null,
    "calories": 165.0,
    "protein_g": 31.0,
    "carbs_g": 0.0,
    "fat_g": 3.6,
    "fiber_g": 0.0,
    "sugar_g": 0.0,
    "sodium_mg": 74.0,
    "serving_size_g": 100.0,
    "serving_size_description": "100g"
  },
  "message": "Food retrieved successfully"
}
```

#### Status Codes

- `200 OK` - Food found
- `404 Not Found` - Food doesn't exist
- `500 Internal Server Error` - Retrieval failed

---

### 3. Create Custom Food

**Endpoint:** `POST /foods/user-foods`

Create a custom user food with nutrition information.

#### Request Body

```json
{
  "name": "Mi smoothie proteico",
  "description": "Smoothie casero con proteína",
  "category": "snack",
  "brand_id": null,
  "calories": 250,
  "protein_g": 25,
  "carbs_g": 30,
  "fat_g": 5,
  "fiber_g": 4,
  "sugar_g": 20,
  "saturated_fat_g": 1,
  "sodium_mg": 150,
  "serving_size_g": 300,
  "serving_size_description": "1 vaso grande",
  "is_public": false
}
```

#### Validation Rules

1. **Name:** 1-200 characters, must be unique per user
2. **Calories:** Must match macro calculation within 10% tolerance
   - Formula: `(protein * 4) + (carbs * 4) + (fat * 9) ≈ calories ± 10%`
3. **All nutrition values:** Must be ≥ 0

#### Example Request

```bash
curl -X POST "http://localhost:9000/api/v1/foods/user-foods" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mi smoothie proteico",
    "category": "snack",
    "calories": 250,
    "protein_g": 25,
    "carbs_g": 30,
    "fat_g": 5
  }'
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": "user-food-uuid",
    "user_id": "user-uuid",
    "name": "Mi smoothie proteico",
    "category": "snack",
    "calories": 250.0,
    "protein_g": 25.0,
    "carbs_g": 30.0,
    "fat_g": 5.0,
    "is_public": false,
    "created_at": "2024-10-14T16:30:00Z",
    "updated_at": "2024-10-14T16:30:00Z"
  },
  "message": "Custom food 'Mi smoothie proteico' created successfully"
}
```

#### Status Codes

- `201 Created` - Food created successfully
- `400 Bad Request` - Validation error (e.g., calorie mismatch)
- `409 Conflict` - Duplicate food name for user
- `500 Internal Server Error` - Creation failed

---

### 4. Delete Custom Food

**Endpoint:** `DELETE /foods/user-foods/{food_id}`

Delete a custom user food. Only the owner can delete.

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `food_id` | string (UUID) | Yes | UserFood ID to delete |

#### Example Request

```bash
curl -X DELETE "http://localhost:9000/api/v1/foods/user-foods/food-uuid"
```

#### Response

- `204 No Content` - Food deleted successfully

#### Status Codes

- `204 No Content` - Deleted successfully
- `404 Not Found` - Food not found or access denied
- `500 Internal Server Error` - Deletion failed

---

### 5. Add to Favorites

**Endpoint:** `POST /foods/favorites`

Add a food to user's favorites for quick access.

#### Request Body

```json
{
  "food_id": "system-food-uuid",
  "user_food_id": null
}
```

**Note:** Either `food_id` OR `user_food_id` must be provided, not both.

#### Example Requests

```bash
# Add system food to favorites
curl -X POST "http://localhost:9000/api/v1/foods/favorites" \
  -H "Content-Type: application/json" \
  -d '{"food_id": "food-uuid"}'

# Add custom food to favorites
curl -X POST "http://localhost:9000/api/v1/foods/favorites" \
  -H "Content-Type: application/json" \
  -d '{"user_food_id": "user-food-uuid"}'
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": "favorite-uuid",
    "user_id": "user-uuid",
    "food_id": "food-uuid",
    "user_food_id": null,
    "use_count": 0,
    "last_used_at": "2024-10-14T16:30:00Z",
    "created_at": "2024-10-14T16:30:00Z"
  },
  "message": "Food added to favorites"
}
```

#### Status Codes

- `201 Created` - Added to favorites
- `409 Conflict` - Already in favorites
- `500 Internal Server Error` - Addition failed

---

### 6. Remove from Favorites

**Endpoint:** `DELETE /foods/favorites/{favorite_id}`

Remove a food from user's favorites.

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `favorite_id` | string (UUID) | Yes | Favorite ID to remove |

#### Example Request

```bash
curl -X DELETE "http://localhost:9000/api/v1/foods/favorites/favorite-uuid"
```

#### Response

- `204 No Content` - Removed successfully

#### Status Codes

- `204 No Content` - Removed successfully
- `500 Internal Server Error` - Removal failed

---

### 7. Get Frequent Foods

**Endpoint:** `GET /foods/favorites/frequent`

Get user's most frequently used foods from favorites, sorted by usage count.

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 10 | Max results (1-50) |

#### Example Request

```bash
curl "http://localhost:9000/api/v1/foods/favorites/frequent?limit=10"
```

#### Response

```json
{
  "success": true,
  "data": [
    {
      "food_id": "food-uuid",
      "food_name": "Pechuga de pollo",
      "use_count": 45,
      "last_used_at": "2024-10-14T16:00:00Z"
    },
    {
      "food_id": "user-food-uuid",
      "food_name": "Mi smoothie proteico",
      "use_count": 32,
      "last_used_at": "2024-10-14T15:30:00Z"
    }
  ],
  "message": "Retrieved 2 frequent foods"
}
```

#### Status Codes

- `200 OK` - Retrieved successfully
- `500 Internal Server Error` - Retrieval failed

---

## Authentication

**Current Status:** Placeholder implementation

All endpoints currently use a placeholder `user_id`. In production, authentication will be handled via:

1. **JWT Token:** Sent in `Authorization: Bearer <token>` header
2. **Supabase Auth:** Token validation via Supabase client
3. **User Extraction:** User ID extracted from validated JWT

**Example with Auth:**

```bash
curl "http://localhost:9000/api/v1/foods/search?q=pollo" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## Error Responses

All errors follow consistent format:

```json
{
  "detail": {
    "message": "Human-readable error message",
    "code": "ERROR_CODE",
    "field": "field_name"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `DUPLICATE_NAME` | 409 | Food name already exists |
| `NOT_FOUND` | 404 | Resource not found |
| `CALORIE_MISMATCH` | 400 | Calorie calculation doesn't match macros |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Testing

### Prerequisites

1. **Database Migration:** Execute `004_food_database_schema.sql` in Supabase
2. **Backend Server:** Running on `http://localhost:9000`
3. **Sample Data:** 20 foods seeded from migration

### Test Scenarios

#### 1. Basic Search

```bash
# Spanish search
curl "http://localhost:9000/api/v1/foods/search?q=pollo"

# English search
curl "http://localhost:9000/api/v1/foods/search?q=chicken"

# Partial match
curl "http://localhost:9000/api/v1/foods/search?q=pech"
```

#### 2. Filtered Search

```bash
# By category
curl "http://localhost:9000/api/v1/foods/search?q=&category=fruit"

# By calories
curl "http://localhost:9000/api/v1/foods/search?q=&max_calories=200"

# Vegetarian only
curl "http://localhost:9000/api/v1/foods/search?q=&is_vegetarian=true"
```

#### 3. Create Custom Food

```bash
# Valid food
curl -X POST "http://localhost:9000/api/v1/foods/user-foods" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mi ensalada",
    "category": "vegetable",
    "calories": 150,
    "protein_g": 10,
    "carbs_g": 20,
    "fat_g": 5
  }'

# Invalid (calorie mismatch)
curl -X POST "http://localhost:9000/api/v1/foods/user-foods" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Invalid food",
    "category": "snack",
    "calories": 999,
    "protein_g": 10,
    "carbs_g": 10,
    "fat_g": 5
  }'
# Expected: 400 Bad Request - Calorie calculation mismatch
```

#### 4. Favorites

```bash
# Add to favorites
curl -X POST "http://localhost:9000/api/v1/foods/favorites" \
  -H "Content-Type: application/json" \
  -d '{"food_id": "food-uuid-from-search"}'

# Get frequent foods
curl "http://localhost:9000/api/v1/foods/favorites/frequent?limit=5"
```

---

## Performance

### Expected Response Times

| Endpoint | Expected Time | Notes |
|----------|---------------|-------|
| Search (no filters) | < 100ms | With pagination |
| Search (with filters) | < 150ms | Complex filters |
| Get by ID | < 50ms | Single lookup |
| Create custom food | < 200ms | With validation |
| Add to favorites | < 100ms | Simple insert |

### Optimization Tips

1. **Use pagination:** Always specify `page_size` to limit results
2. **Filter wisely:** Combine filters to narrow results
3. **Cache frequent queries:** Store common searches client-side
4. **Batch operations:** Create multiple custom foods in batch (future feature)

---

## Integration with Chat

### Food Extraction Flow

1. **User input:** "Comí 2 tacos de carnitas"
2. **Claude extraction:** Identifies food + quantity
3. **Food search:** Search for "taco de carnitas"
4. **Selection:** Present top 3 matches to user
5. **Confirmation:** User selects correct food
6. **Meal logging:** Create `meal_entry` with selected food

---

## Next Steps

### Future Enhancements

1. **Barcode scanning:** `GET /foods/barcode/{barcode}`
2. **Bulk operations:** `POST /foods/user-foods/batch`
3. **Recipe builder:** `POST /foods/recipes`
4. **Nutrition goals:** `GET /foods/recommendations`
5. **Export data:** `GET /foods/export`

---

**API Version:** 1.0
**Last Updated:** 2024-10-14
**Story:** US-043
**Status:** ✅ Complete
