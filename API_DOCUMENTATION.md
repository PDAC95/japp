# JAPPI Health Coach - API Documentation

## Base URL

```
Development: http://localhost:8000
Production: https://api.jappi.app
```

## API Version

Current Version: `v1`

Base Path: `/api/v1`

---

## Table of Contents

1. [Authentication](#authentication)
2. [Profile](#profile)
3. [Meals](#meals)
4. [Chat](#chat)
5. [Fasting](#fasting)
6. [Analytics](#analytics)
7. [Error Codes](#error-codes)
8. [Rate Limiting](#rate-limiting)

---

## Authentication

All authenticated endpoints require a valid Supabase JWT token in the `Authorization` header:

```
Authorization: Bearer <supabase_jwt_token>
```

### Supabase Auth Endpoints

Authentication is handled by Supabase Auth. Frontend uses `@supabase/supabase-js` client.

**Supabase Auth URL:** `https://your-project.supabase.co/auth/v1`

#### Sign Up
```http
POST /auth/v1/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "data": {
    "full_name": "John Doe"
  }
}
```

**Response (201):**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "user_metadata": {
      "full_name": "John Doe"
    },
    "created_at": "2025-01-01T00:00:00Z"
  },
  "session": {
    "access_token": "jwt_token",
    "refresh_token": "refresh_token",
    "expires_in": 3600
  }
}
```

#### Sign In
```http
POST /auth/v1/token?grant_type=password
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response (200):**
```json
{
  "access_token": "jwt_token",
  "refresh_token": "refresh_token",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "email": "user@example.com"
  }
}
```

#### Sign Out
```http
POST /auth/v1/logout
Authorization: Bearer <token>
```

**Response (204):**
```
No Content
```

#### Password Reset Request
```http
POST /auth/v1/recover
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Response (200):**
```json
{
  "message": "Password reset email sent"
}
```

#### Password Reset Confirm
```http
POST /auth/v1/verify
Content-Type: application/json

{
  "type": "recovery",
  "token": "recovery_token",
  "password": "NewPassword123!"
}
```

**Response (200):**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com"
  }
}
```

---

## Profile

### Get User Profile

```http
GET /api/v1/profile
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "full_name": "John Doe",
  "age": 30,
  "gender": "male",
  "height_cm": 180,
  "weight_kg": 80,
  "goal_weight_kg": 75,
  "activity_level": "moderately_active",
  "goal_type": "weight_loss",
  "bmr": 1800,
  "tdee": 2500,
  "recommended_protein_g": 150,
  "recommended_carbs_g": 250,
  "recommended_fat_g": 70,
  "recommended_calories": 2200,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

### Create/Update Profile

```http
POST /api/v1/profile
Authorization: Bearer <token>
Content-Type: application/json

{
  "full_name": "John Doe",
  "age": 30,
  "gender": "male",
  "height_cm": 180,
  "weight_kg": 80,
  "goal_weight_kg": 75,
  "activity_level": "moderately_active",
  "goal_type": "weight_loss"
}
```

**Activity Levels:**
- `sedentary` (1.2x multiplier)
- `lightly_active` (1.375x)
- `moderately_active` (1.55x)
- `very_active` (1.725x)
- `extra_active` (1.9x)

**Goal Types:**
- `weight_loss`
- `muscle_gain`
- `maintain`
- `health`

**Response (200):**
```json
{
  "id": "uuid",
  "bmr": 1800,
  "tdee": 2500,
  "recommended_protein_g": 150,
  "recommended_carbs_g": 250,
  "recommended_fat_g": 70,
  "recommended_calories": 2200,
  "message": "Profile updated successfully"
}
```

**Validation Rules:**
- `age`: 13-120
- `height_cm`: 100-250
- `weight_kg`: 30-300
- `goal_weight_kg`: 30-300
- `gender`: male, female, other
- All numbers must be positive

---

## Meals

### Log Meal Entry

```http
POST /api/v1/meals
Authorization: Bearer <token>
Content-Type: application/json

{
  "food_name": "Grilled Chicken Breast",
  "protein_g": 30,
  "carbs_g": 0,
  "fat_g": 3.5,
  "calories": 165,
  "meal_time": "2025-01-15T12:30:00Z",
  "meal_type": "lunch",
  "notes": "Post-workout meal"
}
```

**Meal Types:**
- `breakfast`
- `lunch`
- `dinner`
- `snack`

**Response (201):**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "food_name": "Grilled Chicken Breast",
  "protein_g": 30,
  "carbs_g": 0,
  "fat_g": 3.5,
  "calories": 165,
  "meal_time": "2025-01-15T12:30:00Z",
  "meal_type": "lunch",
  "notes": "Post-workout meal",
  "created_at": "2025-01-15T12:35:00Z"
}
```

**Validation:**
```sql
-- Database constraint ensures calorie accuracy
CHECK (
  ABS(calories - (protein_g * 4 + carbs_g * 4 + fat_g * 9)) <= (calories * 0.05)
)
```

**Error (400) - Invalid Macros:**
```json
{
  "error": "INVALID_MACROS",
  "message": "Calories don't match macros (protein×4 + carbs×4 + fat×9)",
  "details": {
    "provided_calories": 200,
    "calculated_calories": 165,
    "difference": 35,
    "tolerance": 10
  }
}
```

### Get Meal History

```http
GET /api/v1/meals?start_date=2025-01-01&end_date=2025-01-15&meal_type=lunch
Authorization: Bearer <token>
```

**Query Parameters:**
- `start_date` (optional): ISO 8601 date
- `end_date` (optional): ISO 8601 date
- `meal_type` (optional): breakfast, lunch, dinner, snack
- `limit` (optional): default 50, max 100
- `offset` (optional): default 0

**Response (200):**
```json
{
  "meals": [
    {
      "id": "uuid",
      "food_name": "Grilled Chicken Breast",
      "protein_g": 30,
      "carbs_g": 0,
      "fat_g": 3.5,
      "calories": 165,
      "meal_time": "2025-01-15T12:30:00Z",
      "meal_type": "lunch",
      "created_at": "2025-01-15T12:35:00Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

### Update Meal Entry

```http
PUT /api/v1/meals/{meal_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "protein_g": 35,
  "carbs_g": 0,
  "fat_g": 4,
  "calories": 180
}
```

**Response (200):**
```json
{
  "id": "uuid",
  "message": "Meal updated successfully"
}
```

### Delete Meal Entry

```http
DELETE /api/v1/meals/{meal_id}
Authorization: Bearer <token>
```

**Response (204):**
```
No Content
```

---

## Chat

### Extract Food from Text (Claude AI)

```http
POST /api/v1/chat/extract
Content-Type: application/json

{
  "text": "I had 3 eggs and toast with butter for breakfast"
}
```

**Description:**
Extracts food items and nutrition data from natural language text using Claude AI. Optimized for North American foods (USA/Canada market) with support for international cuisine.

**Examples:**
- "3 eggs and toast" → extracts eggs and toast separately
- "grilled chicken breast with rice" → extracts both items with nutrition
- "turkey sandwich on whole wheat" → understands typical portions
- "protein shake and banana" → extracts beverages and fruits

**Request Body:**
```typescript
{
  text: string;  // 1-1000 characters, cannot be empty
}
```

**Response (200) - Success:**
```json
{
  "success": true,
  "data": {
    "foods": [
      {
        "name": "Scrambled eggs",
        "quantity": 3,
        "unit": "piece",
        "calories": 210.0,
        "protein_g": 18.0,
        "carbs_g": 3.0,
        "fat_g": 15.0
      },
      {
        "name": "Toast with butter",
        "quantity": 2,
        "unit": "piece",
        "calories": 200.0,
        "protein_g": 4.0,
        "carbs_g": 30.0,
        "fat_g": 8.0
      }
    ],
    "total_calories": 410.0,
    "total_macros": {
      "protein": 22.0,
      "carbs": 33.0,
      "fat": 23.0
    },
    "message": "Food logged successfully!",
    "error": null
  },
  "message": "Extracted 2 food item(s)",
  "error": null
}
```

**Response (422) - Validation Error:**
```json
{
  "success": false,
  "data": null,
  "message": null,
  "error": {
    "message": "Food description cannot be empty",
    "code": "VALIDATION_ERROR",
    "statusCode": 422
  }
}
```

**Response (504) - API Timeout:**
```json
{
  "success": false,
  "data": null,
  "message": null,
  "error": {
    "message": "AI service timeout - please try again",
    "code": "CLAUDE_TIMEOUT",
    "statusCode": 504
  }
}
```

**Response (500) - Extraction Failed:**
```json
{
  "success": false,
  "data": null,
  "message": null,
  "error": {
    "message": "Could not understand food description",
    "code": "EXTRACTION_FAILED",
    "statusCode": 422
  }
}
```

**Validation Rules:**
- All nutrition values must be >= 0 (no negative values)
- Quantity must be > 0
- Calories calculated as: (protein_g * 4) + (carbs_g * 4) + (fat_g * 9)
- ±5% tolerance for calorie rounding
- Maximum 30 seconds timeout
- Automatic retry with exponential backoff (3 attempts)

---

### Send Chat Message

```http
POST /api/v1/chat/message
Content-Type: application/json

{
  "content": "I had 2 tacos for lunch",
  "extract_food": true
}
```

**Description:**
Send a message to the AI health coach. Optionally extracts food data if the message contains food descriptions.

**Request Body:**
```typescript
{
  content: string;        // 1-2000 characters
  extract_food: boolean;  // default: true
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "response": "Food logged successfully!",
    "extracted_data": {
      "foods": [
        {
          "name": "Tacos",
          "quantity": 2,
          "unit": "piece",
          "calories": 260.0,
          "protein_g": 14.0,
          "carbs_g": 21.0,
          "fat_g": 12.0
        }
      ],
      "total_calories": 260.0,
      "total_macros": {
        "protein": 14.0,
        "carbs": 21.0,
        "fat": 12.0
      },
      "message": "Food logged successfully!",
      "error": null
    }
  },
  "message": "Message processed successfully",
  "error": null
}
```

---

### Chat Service Health Check

```http
GET /api/v1/chat/health
```

**Description:**
Verifies that Claude service is properly initialized and configured.

**Response (200) - Healthy:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 2000,
    "temperature": 0.3
  },
  "message": "Chat service is healthy",
  "error": null
}
```

**Response (503) - Unhealthy:**
```json
{
  "success": false,
  "data": null,
  "message": null,
  "error": {
    "message": "ANTHROPIC_API_KEY not configured in environment",
    "code": "SERVICE_UNHEALTHY",
    "statusCode": 503
  }
}
```

---

## Fasting

### Get Current Fasting Status

```http
GET /api/v1/fasting/current
Authorization: Bearer <token>
```

**Response (200) - Active Fast:**
```json
{
  "is_fasting": true,
  "start_time": "2025-01-15T20:00:00Z",
  "elapsed_hours": 12.5,
  "target_hours": 16,
  "remaining_hours": 3.5,
  "progress_percentage": 78
}
```

**Response (200) - No Active Fast:**
```json
{
  "is_fasting": false,
  "last_fast_ended": "2025-01-15T12:00:00Z"
}
```

### Start Fasting Window

```http
POST /api/v1/fasting/start
Authorization: Bearer <token>
Content-Type: application/json

{
  "target_hours": 16,
  "notes": "16:8 intermittent fasting"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "start_time": "2025-01-15T20:00:00Z",
  "target_hours": 16,
  "estimated_end": "2025-01-16T12:00:00Z",
  "message": "Fasting started successfully"
}
```

### End Fasting Window

```http
POST /api/v1/fasting/end
Authorization: Bearer <token>
Content-Type: application/json

{
  "notes": "Completed successfully"
}
```

**Response (200):**
```json
{
  "id": "uuid",
  "start_time": "2025-01-15T20:00:00Z",
  "end_time": "2025-01-16T12:00:00Z",
  "duration_hours": 16,
  "target_hours": 16,
  "completed": true,
  "message": "Fasting completed successfully"
}
```

### Get Fasting History

```http
GET /api/v1/fasting/history?limit=30
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "fasts": [
    {
      "id": "uuid",
      "start_time": "2025-01-15T20:00:00Z",
      "end_time": "2025-01-16T12:00:00Z",
      "duration_hours": 16,
      "target_hours": 16,
      "completed": true
    }
  ],
  "stats": {
    "total_fasts": 30,
    "average_duration_hours": 15.5,
    "longest_fast_hours": 18,
    "completion_rate": 0.93
  }
}
```

---

## Analytics

### Get Daily Summary

```http
GET /api/v1/analytics/daily?date=2025-01-15
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "date": "2025-01-15",
  "totals": {
    "protein_g": 150,
    "carbs_g": 200,
    "fat_g": 65,
    "calories": 1965
  },
  "goals": {
    "protein_g": 150,
    "carbs_g": 250,
    "fat_g": 70,
    "calories": 2200
  },
  "progress": {
    "protein_percentage": 100,
    "carbs_percentage": 80,
    "fat_percentage": 93,
    "calories_percentage": 89
  },
  "meals_count": 4,
  "water_intake_ml": 2000,
  "fasting_hours": 16
}
```

### Get Weekly Summary

```http
GET /api/v1/analytics/weekly?start_date=2025-01-08
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "week_start": "2025-01-08",
  "week_end": "2025-01-14",
  "daily_summaries": [
    {
      "date": "2025-01-08",
      "calories": 2100,
      "protein_g": 145,
      "carbs_g": 230,
      "fat_g": 68
    }
  ],
  "weekly_averages": {
    "calories": 2050,
    "protein_g": 148,
    "carbs_g": 235,
    "fat_g": 66
  },
  "streak_days": 7,
  "goals_met_days": 5
}
```

### Get Progress Stats

```http
GET /api/v1/analytics/progress?period=30
Authorization: Bearer <token>
```

**Query Parameters:**
- `period`: days to include (7, 30, 90)

**Response (200):**
```json
{
  "period_days": 30,
  "weight_change_kg": -2.5,
  "average_calories": 2100,
  "goal_adherence_percentage": 85,
  "streak": {
    "current": 15,
    "longest": 20
  },
  "fasting": {
    "total_fasts": 25,
    "average_duration_hours": 15.8,
    "completion_rate": 0.92
  }
}
```

---

## Error Codes

### Standard HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | OK | Successful GET request |
| 201 | Created | Meal logged successfully |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid input data |
| 401 | Unauthorized | Missing/invalid JWT token |
| 403 | Forbidden | Not allowed to access resource |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Validation failed |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

### Custom Error Codes

| Code | HTTP Status | Description | Solution |
|------|-------------|-------------|----------|
| `INVALID_MACROS` | 400 | Calories don't match macros | Recalculate macros: protein×4 + carbs×4 + fat×9 |
| `NEGATIVE_VALUES` | 400 | Negative nutrition values | All values must be ≥ 0 |
| `INVALID_MEAL_TIME` | 400 | Meal time in future | Use current or past time |
| `PROFILE_NOT_FOUND` | 404 | User has no profile | Create profile first |
| `MEAL_NOT_FOUND` | 404 | Meal entry doesn't exist | Check meal ID |
| `ACTIVE_FAST_EXISTS` | 409 | Already fasting | End current fast first |
| `NO_ACTIVE_FAST` | 409 | No fast to end | Start fast first |
| `INVALID_FAST_DURATION` | 400 | Duration < 0 or > 24h | Valid range: 0-24 hours |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests | Wait before retrying |
| `CLAUDE_API_ERROR` | 503 | Claude API unavailable | Retry later |

### Error Response Format

```json
{
  "error": "INVALID_MACROS",
  "message": "Calories don't match macros",
  "details": {
    "provided_calories": 200,
    "calculated_calories": 165,
    "difference": 35,
    "tolerance": 10
  },
  "timestamp": "2025-01-15T12:35:00Z",
  "path": "/api/v1/meals"
}
```

---

## Rate Limiting

### Limits

| Endpoint | Rate Limit | Window |
|----------|------------|--------|
| All endpoints | 100 requests | 1 minute |
| `/api/v1/chat` | 20 requests | 1 minute |
| `/api/v1/meals` POST | 50 requests | 1 minute |

### Rate Limit Headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642262400
```

### Rate Limit Exceeded Response

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 60

{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Too many requests",
  "retry_after_seconds": 60
}
```

---

## Pagination

Endpoints that return lists support pagination:

**Query Parameters:**
- `limit`: Items per page (default: 50, max: 100)
- `offset`: Skip items (default: 0)

**Response:**
```json
{
  "data": [...],
  "pagination": {
    "total": 150,
    "limit": 50,
    "offset": 0,
    "has_more": true
  }
}
```

---

## Timestamps

All timestamps are in **ISO 8601 format** with UTC timezone:

```
2025-01-15T12:30:00Z
```

---

## CORS

Allowed origins:
- `http://localhost:4000` (development)
- `https://jappi.app` (production)
- `https://*.jappi.app` (subdomains)

Allowed methods: `GET, POST, PUT, DELETE, OPTIONS`

Allowed headers: `Authorization, Content-Type`

---

## Versioning

API version is specified in the URL path: `/api/v1`

Breaking changes will increment the version number (`v2`, `v3`, etc.).

---

## OpenAPI/Swagger Specification

Interactive API documentation available at:

```
Development: http://localhost:8000/docs
Production: https://api.jappi.app/docs
```

Alternative ReDoc documentation:

```
Development: http://localhost:8000/redoc
Production: https://api.jappi.app/redoc
```

---

## Support

For API support:
- Email: api@jappi.ca
- Documentation: https://docs.jappi.app
- GitHub Issues: https://github.com/jappi/api/issues

---

**Last Updated:** 2025-10-09
**API Version:** v1
**Status:** Draft - Pending Implementation
