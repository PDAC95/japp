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

### Send Message to AI Coach

```http
POST /api/v1/chat
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "I had 2 eggs and toast for breakfast",
  "personality": "motivational",
  "context": {
    "current_streak": 5,
    "goal": "weight_loss"
  }
}
```

**Personalities:**
- `motivational`: Enthusiastic and encouraging
- `professional`: Direct and informative
- `friendly`: Casual and supportive

**Response (200):**
```json
{
  "id": "uuid",
  "message": "Great breakfast choice! Let me break that down:",
  "extracted_food": {
    "food_name": "2 eggs and toast",
    "protein_g": 16,
    "carbs_g": 30,
    "fat_g": 12,
    "calories": 280,
    "confidence": 0.95
  },
  "suggestions": [
    "Add some avocado for healthy fats",
    "Consider whole grain toast for more fiber"
  ],
  "created_at": "2025-01-15T08:30:00Z"
}
```

### Get Chat History

```http
GET /api/v1/chat/history?limit=20
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "messages": [
    {
      "id": "uuid",
      "role": "user",
      "content": "I had 2 eggs and toast",
      "created_at": "2025-01-15T08:30:00Z"
    },
    {
      "id": "uuid",
      "role": "assistant",
      "content": "Great breakfast choice!",
      "extracted_food": {...},
      "created_at": "2025-01-15T08:30:05Z"
    }
  ],
  "total": 2
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
