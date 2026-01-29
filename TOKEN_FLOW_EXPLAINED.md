# Token Refresh System - Complete Flow Explanation

## Overview
This system uses **JWT tokens** with two types:
- **Access Token**: Short-lived (15 minutes) - Used to access protected endpoints
- **Refresh Token**: Long-lived (7 days) - Used to get new access tokens

---

## Step-by-Step Flow

### 1️⃣ **User Login**
```
POST /login
Body: {
  "username": "user@email.com",
  "password": "password123"
}

Response: {
  "access_token": "eyJhbGciOiJIUzI1NiIs...",  # Valid for 15 minutes
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...", # Valid for 7 days
  "token_type": "bearer"
}
```

**What happens:**
- User credentials are verified
- Both tokens are generated with user info embedded
- Refresh token is saved to database with JTI (unique ID)

---

### 2️⃣ **Access Protected Resource**
```
GET /uploadFile
Headers: {
  "Authorization": "Bearer <access_token>"
}
```

**What happens:**
- Server verifies access token signature
- Extracts user info from token
- Grants access to resource

---

### 3️⃣ **Access Token Expires (After 15 minutes)**
```
GET /uploadFile
Headers: {
  "Authorization": "Bearer <expired_access_token>"
}

Response Error: {
  "detail": "Could not validate credentials"
}
```

---

### 4️⃣ **Refresh Token to Get New Access Token**
```
POST /refresh
Body: {
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}

Response: {
  "access_token": "eyJhbGciOiJIUzI1NiIs...",  # New token, valid for 15 minutes
  "token_type": "bearer",
  "expires_in": 900  # 15 minutes in seconds
}
```

**What happens:**
1. Server decodes refresh token
2. Checks if token type is "refresh"
3. Queries database to verify JTI (token ID) exists
4. Checks if token is revoked (is_revoked = False)
5. Checks if token is not expired
6. If all valid, generates new access token
7. Returns new access token to client

---

### 5️⃣ **User Logout**
```
POST /logout
Headers: {
  "Authorization": "Bearer <access_token>"
}

Response: {
  "message": "log out successful"
}
```

**What happens:**
1. Access token is added to blacklist (can't use anymore)
2. All refresh tokens for user are marked as revoked
3. User must login again to get new tokens

---

## Key Functions Explained

### `verify_refresh_token(token: str, db: Session) -> dict`
**Purpose**: Validates refresh token before issuing new access token

**Checks performed**:
1. ✅ JWT signature is valid
2. ✅ Token type is "refresh"
3. ✅ JTI (token ID) exists in database
4. ✅ Token is not revoked (is_revoked = False)
5. ✅ Token is not expired (current time < expires_at)

**Raises error if**:
- Invalid signature
- Wrong token type
- Token not in database
- Token is revoked
- Token is expired

---

### `refresh_access_token(refresh_token: str, db: Session) -> dict`
**Purpose**: Generate new access token from valid refresh token

**Steps**:
1. Call `verify_refresh_token()` to validate
2. Extract user_id from token payload
3. Query user from database
4. Create fresh access token with user data
5. Return new access token

---

## Token Structure (JWT Payload)

### Access Token Payload:
```json
{
  "jti": "550e8400-e29b-41d4-a716-446655440000",  # Unique token ID
  "exp": 1704067200,                               # Expiration time (Unix timestamp)
  "user_id": 1,
  "email": "user@email.com",
  "name": "John Doe",
  "type": "access",
  "iat": 1704066300
}
```

### Refresh Token Payload:
```json
{
  "sub": "John Doe",
  "iat": 1704066300,                               # Issued at time
  "exp": 1704671100,                               # Expiration time (7 days later)
  "user_id": 1,
  "type": "refresh",
  "jti": "550e8400-e29b-41d4-a716-446655440001"   # Unique token ID
}
```

---

## Database Storage

### RefreshToken Table:
```
Fields:
- token_id: Primary key
- user_id: Foreign key to users
- token: Hashed token value (bcrypt)
- jti: Unique token ID (from JWT)
- created_at: When token was issued
- expires_at: When token expires
- is_revoked: Boolean (True if user logged out)
```

**Why store refresh tokens?**
- Can revoke all tokens for a user at once (logout)
- Can verify token hasn't been revoked
- Can check token expiration before generating new access token

### BlacklistedAccessTokens Table:
```
Fields:
- id: Primary key
- user_id: Foreign key to users
- jti: Token's unique ID
- blacklisted_at: When it was blacklisted
- expires_at: When the JTI expires (auto-delete after)
```

**Why blacklist access tokens?**
- After logout, old access tokens should be invalid
- Prevents using old token after logout

---

## Frontend Implementation Example (JavaScript)

```javascript
// 1. Login and store tokens
async function login(email, password) {
  const response = await fetch('/login', {
    method: 'POST',
    body: new FormData({ username: email, password })
  });
  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);
}

// 2. Make API request
async function apiCall(endpoint) {
  let token = localStorage.getItem('access_token');
  
  let response = await fetch(endpoint, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  // If 401 (unauthorized), try refreshing
  if (response.status === 401) {
    response = await refreshAccessToken();
    
    if (response.ok) {
      // Retry original request with new token
      token = localStorage.getItem('access_token');
      response = await fetch(endpoint, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
    }
  }
  
  return response;
}

// 3. Refresh access token using refresh token
async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('refresh_token');
  
  const response = await fetch('/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken })
  });
  
  if (response.ok) {
    const data = await response.json();
    localStorage.setItem('access_token', data.access_token);
  } else {
    // Refresh token invalid, force re-login
    logout();
  }
  
  return response;
}

// 4. Logout
async function logout() {
  const token = localStorage.getItem('access_token');
  
  await fetch('/logout', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  window.location.href = '/login';
}
```

---

## Security Features

✅ **Access tokens are short-lived** (15 min)
- Even if compromised, limited damage

✅ **Refresh tokens are long-lived but stored securely in DB**
- Can revoke all tokens by marking revoked = True
- Can't be reused after logout

✅ **JTI (JWT ID) tracking**
- Each token has unique ID
- Can revoke individual tokens
- Can verify in database

✅ **Tokens can be blacklisted after logout**
- Prevents using old access tokens
- User must re-login

---

## Timeline Example

```
User logs in at 10:00 AM
├─ Access Token valid until 10:15 AM
└─ Refresh Token valid until 10:00 AM + 7 days

At 10:10 AM - User makes request
├─ Access token still valid ✅
└─ Request succeeds

At 10:16 AM - User makes request
├─ Access token expired ❌
├─ Client calls /refresh endpoint
├─ Server validates refresh token ✅
├─ Server generates new access token (valid until 10:31 AM)
└─ Request retried with new token ✅

At 3:00 PM - User clicks logout
├─ Access token added to blacklist
├─ All refresh tokens marked revoked = True
└─ User must login again to proceed

At 3:05 PM - User tries to use old refresh token
├─ Server checks: is_revoked = True
├─ Response: "Please log in again" ❌
└─ User redirected to login page
```

---

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Could not validate credentials` | Access token expired | Call `/refresh` to get new token |
| `Invalid token type` | Using access token in refresh endpoint | Use refresh token for `/refresh` |
| `Refresh token not found` | Token JTI not in database | User must login again |
| `Refresh token has been revoked` | User logged out | User must login again |
| `Refresh token has expired` | 7 days have passed | User must login again |

---

## Testing with Postman

### Test 1: Login and Get Tokens
```
POST http://localhost:8000/login
Body (form-data):
  username: user@email.com
  password: password123

Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### Test 2: Use Access Token (Valid)
```
POST http://localhost:8000/uploadFile
Headers:
  Authorization: Bearer <access_token>
File: (any PDF)

Response:
{
  "message": "File uploaded successfully",
  ...
}
```

### Test 3: Refresh Token (After 15 min)
```
POST http://localhost:8000/refresh
Body (JSON):
{
  "refresh_token": "<your_refresh_token>"
}

Response:
{
  "access_token": "eyJ...", (NEW TOKEN)
  "token_type": "bearer",
  "expires_in": 900
}
```

### Test 4: Logout
```
POST http://localhost:8000/logout
Headers:
  Authorization: Bearer <access_token>

Response:
{
  "message": "log out successful"
}
```

### Test 5: Try Using Old Refresh Token
```
POST http://localhost:8000/refresh
Body (JSON):
{
  "refresh_token": "<old_refresh_token>"
}

Response (Error):
{
  "detail": "Refresh token has been revoked. Please log in again"
}
```

---

## Summary

| Aspect | Details |
|--------|---------|
| **Access Token Lifetime** | 15 minutes |
| **Refresh Token Lifetime** | 7 days |
| **Storage** | Refresh tokens stored in DB with JTI |
| **Revocation** | Logout marks all refresh tokens as revoked |
| **Security** | Short-lived access tokens + revocable refresh tokens |
| **Frontend Flow** | Check for 401 → Call /refresh → Retry request |

