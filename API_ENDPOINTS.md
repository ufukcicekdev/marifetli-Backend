# Marifetli.com.tr API Endpoints Documentation

This document describes all the API endpoints for the Marifetli.com.tr forum application.

## Base URL
`http://localhost:8001/api/` (development)
`https://api.marifetli.com.tr/` (production)

## Authentication

All authenticated endpoints require a valid JWT token in the Authorization header:
```
Authorization: Bearer <access_token>
```

## API Endpoints

### Authentication

#### Register User
- **POST** `/auth/register/`
- Headers: `Content-Type: application/json`
- Body:
```json
{
  "email": "user@example.com",
  "username": "username",
  "password": "secure_password"
}
```
- Response: `201 Created`
```json
{
  "refresh": "refresh_token",
  "access": "access_token",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "username",
    "first_name": "",
    "last_name": "",
    "bio": "",
    "profile_picture": null,
    "gender": "",
    "followers_count": 0,
    "following_count": 0,
    "date_of_birth": null,
    "is_verified": false,
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  }
}
```

#### Login User
- **POST** `/auth/login/`
- Headers: `Content-Type: application/json`
- Body:
```json
{
  "email": "user@example.com",
  "password": "secure_password"
}
```
- Response: `200 OK`
```json
{
  "refresh": "refresh_token",
  "access": "access_token",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "username",
    ...
  }
}
```

#### Logout
- **POST** `/auth/logout/`
- Headers: `Authorization: Bearer <access_token>`
- Body:
```json
{
  "refresh_token": "refresh_token_to_blacklist"
}
```
- Response: `205 Reset Content`

#### Get Current User
- **GET** `/auth/me/`
- Headers: `Authorization: Bearer <access_token>`
- Response: `200 OK`
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "username",
  ...
}
```

#### Update User Profile
- **PATCH** `/auth/profile/`
- Headers: `Authorization: Bearer <access_token>`, `Content-Type: application/json`
- Body: Partial user profile data
- Response: `200 OK`

#### Change Password
- **PUT** `/auth/change-password/`
- Headers: `Authorization: Bearer <access_token>`, `Content-Type: application/json`
- Body:
```json
{
  "old_password": "current_password",
  "new_password": "new_secure_password"
}
```
- Response: `200 OK`

### Users

#### Get User Profile
- **GET** `/users/{id}/`
- Headers: `Authorization: Bearer <access_token>`
- Response: `200 OK`

#### Follow User
- **POST** `/auth/{user_id}/follow/`
- Headers: `Authorization: Bearer <access_token>`
- Response: `201 Created`

#### Unfollow User
- **DELETE** `/auth/{user_id}/unfollow/`
- Headers: `Authorization: Bearer <access_token>`
- Response: `204 No Content`

#### Get Following List
- **GET** `/auth/following/`
- Headers: `Authorization: Bearer <access_token>`
- Response: `200 OK` - List of followed users

#### Get Followers List
- **GET** `/auth/followers/`
- Headers: `Authorization: Bearer <access_token>`
- Response: `200 OK` - List of followers

### Questions

#### List Questions
- **GET** `/questions/`
- Query Parameters:
  - `author` - Filter by author ID
  - `status` - Filter by status (open, closed, archived)
  - `tags` - Filter by tag IDs (comma separated)
  - `search` - Search in title/description
  - `ordering` - Sort by (created_at, updated_at, like_count, answer_count)
  - `page` - Page number
- Response: `200 OK` - Paginated list of questions

#### Create Question
- **POST** `/questions/`
- Headers: `Authorization: Bearer <access_token>`, `Content-Type: application/json`
- Body:
```json
{
  "title": "Question title",
  "description": "Detailed question description",
  "tags": [1, 2, 3]
}
```
- Response: `201 Created`

#### Get Question Detail
- **GET** `/questions/{slug}/`
- Headers: `Authorization: Bearer <access_token>` (optional for public viewing)
- Response: `200 OK`

#### Update Question
- **PUT/PATCH** `/questions/{slug}/`
- Headers: `Authorization: Bearer <access_token>`, `Content-Type: application/json`
- Body: Partial or full question data
- Response: `200 OK`

#### Delete Question
- **DELETE** `/questions/{slug}/`
- Headers: `Authorization: Bearer <access_token>`
- Response: `204 No Content`

#### Like Question
- **POST** `/questions/{question_id}/like/`
- Headers: `Authorization: Bearer <access_token>`
- Response: `201 Created`

#### Unlike Question
- **DELETE** `/questions/{question_id}/unlike/`
- Headers: `Authorization: Bearer <access_token>`
- Response: `204 No Content`

#### Get Question Answers
- **GET** `/questions/{question_id}/answers/`
- Headers: `Authorization: Bearer <access_token>` (optional for public viewing)
- Response: `200 OK` - List of answers

#### Report Question
- **POST** `/questions/{question_id}/report/`
- Headers: `Authorization: Bearer <access_token>`, `Content-Type: application/json`
- Body:
```json
{
  "reason": "spam|offensive|duplicate|other",
  "description": "Additional details about the report"
}
```
- Response: `201 Created`

#### Get My Questions
- **GET** `/questions/my-questions/`
- Headers: `Authorization: Bearer <access_token>`
- Response: `200 OK` - List of questions created by the user

#### Get Tags
- **GET** `/questions/tags/`
- Headers: Not required
- Response: `200 OK` - List of all tags

### Answers

#### List Answers for Question
- **GET** `/answers/{question_id}/answers/`
- Headers: `Authorization: Bearer <access_token>` (optional for public viewing)
- Response: `200 OK` - List of answers

#### Create Answer
- **POST** `/answers/{question_id}/answers/`
- Headers: `Authorization: Bearer <access_token>`, `Content-Type: application/json`
- Body:
```json
{
  "content": "Detailed answer content"
}
```
- Response: `201 Created`

#### Update Answer
- **PUT/PATCH** `/answers/{question_id}/answers/{answer_id}/`
- Headers: `Authorization: Bearer <access_token>`, `Content-Type: application/json`
- Body: Partial or full answer data
- Response: `200 OK`

#### Delete Answer
- **DELETE** `/answers/{question_id}/answers/{answer_id}/`
- Headers: `Authorization: Bearer <access_token>`
- Response: `204 No Content`

#### Like Answer
- **POST** `/answers/{answer_id}/like/`
- Headers: `Authorization: Bearer <access_token>`
- Response: `201 Created`

#### Unlike Answer
- **DELETE** `/answers/{answer_id}/unlike/`
- Headers: `Authorization: Bearer <access_token>`
- Response: `204 No Content`

#### Mark as Best Answer
- **POST** `/answers/{answer_id}/mark-best/`
- Headers: `Authorization: Bearer <access_token>`
- Response: `200 OK`

#### Report Answer
- **POST** `/answers/{answer_id}/report/`
- Headers: `Authorization: Bearer <access_token>`, `Content-Type: application/json`
- Body:
```json
{
  "reason": "spam|offensive|incorrect|other",
  "description": "Additional details about the report"
}
```
- Response: `201 Created`

### Notifications

#### List Notifications
- **GET** `/notifications/`
- Headers: `Authorization: Bearer <access_token>`
- Response: `200 OK` - List of user's notifications

#### Get Notification Detail
- **GET** `/notifications/{id}/`
- Headers: `Authorization: Bearer <access_token>`
- Response: `200 OK`

#### Mark Notification as Read
- **PATCH** `/notifications/{id}/`
- Headers: `Authorization: Bearer <access_token>`
- Response: `200 OK`

#### Mark All Notifications as Read
- **POST** `/notifications/mark-all-read/`
- Headers: `Authorization: Bearer <access_token>`
- Response: `200 OK`

#### Get Notification Settings
- **GET** `/notifications/settings/`
- Headers: `Authorization: Bearer <access_token>`
- Response: `200 OK`

#### Update Notification Settings
- **PUT** `/notifications/settings/`
- Headers: `Authorization: Bearer <access_token>`, `Content-Type: application/json`
- Response: `200 OK`

## Error Responses

All error responses follow the format:
```json
{
  "error": "Error message",
  "detail": "Additional details"
}
```

Common HTTP status codes:
- `200 OK` - Successful GET, PUT, PATCH
- `201 Created` - Successful POST
- `204 No Content` - Successful DELETE
- `400 Bad Request` - Validation error
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error