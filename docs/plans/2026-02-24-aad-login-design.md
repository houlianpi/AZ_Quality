# AAD Login Design

**Date**: 2026-02-24
**Status**: ✅ Implemented

## Overview

Add Microsoft AAD (Azure Active Directory) authentication to Quality Platform. Users must log in before accessing the dashboard. All API endpoints require OAuth token verification.

### Requirements

- Mandatory login for all pages
- Display user profile (name, email, avatar) in UI
- Logout functionality
- All `/api/*` endpoints protected with JWT verification

### Tech Stack

- **Frontend**: MSAL.js (Microsoft Authentication Library)
- **Backend**: python-jose for JWT verification
- **Auth Flow**: Frontend authentication (SPA pattern)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser                                                         │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Frontend (HTML/JS)                                          ││
│  │  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐ ││
│  │  │  MSAL.js     │───▶│  ID Token    │───▶│ API Request   │ ││
│  │  │  Login       │    │  (memory)    │    │ Bearer Token  │ ││
│  │  └──────────────┘    └──────────────┘    └───────────────┘ ││
│  └─────────────────────────────────────────────────────────────┘│
└───────────────────────────┬─────────────────────────────────────┘
                            │ Authorization: Bearer <token>
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI Backend                                                 │
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │  JWT Middleware   │───▶│  API Routes      │                   │
│  │  Verify AAD Token │    │  /api/*          │                   │
│  └──────────────────┘    └──────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

### Authentication Flow

1. User visits page → Frontend checks login status via MSAL
2. Not logged in → MSAL.js triggers AAD login popup/redirect
3. Login success → Receive ID Token, store in memory (sessionStorage)
4. API request → Automatically attach `Authorization: Bearer <token>`
5. Backend → Verify token signature and claims, return data

## Frontend Design

### New Files

```
frontend/
├── js/
│   └── auth.js           # MSAL config and login logic
└── index.html / team.html # Modified: add user profile display
```

### User Interface

Display user info in sidebar header:

```
┌─────────────────────────────────────────────┐
│  [Avatar] Kun Wang                  [Logout]│
│           kunwang@microsoft.com             │
└─────────────────────────────────────────────┘
```

**When not logged in:** Auto-trigger MSAL login popup

### MSAL.js Configuration

```javascript
// frontend/js/auth.js
const msalConfig = {
    auth: {
        clientId: "YOUR_CLIENT_ID",
        authority: "https://login.microsoftonline.com/YOUR_TENANT_ID",
        redirectUri: window.location.origin
    },
    cache: {
        cacheLocation: "sessionStorage"  // Clear on browser close
    }
};

const msalInstance = new msal.PublicClientApplication(msalConfig);

// Login request scopes
const loginRequest = {
    scopes: ["User.Read"]  // For profile and avatar
};
```

### API Request Changes

Modify `api.js` to attach token to all requests:

```javascript
// Before
fetch('/api/summary')

// After
async function fetchWithAuth(url, options = {}) {
    const token = await getAccessToken();
    return fetch(url, {
        ...options,
        headers: {
            ...options.headers,
            'Authorization': `Bearer ${token}`
        }
    });
}
```

## Backend Design

### New Files

```
app/
├── core/
│   └── auth.py           # JWT verification logic
└── main.py               # Modified: add auth dependency
```

### Dependencies

```toml
# pyproject.toml additions
"python-jose[cryptography]>=3.3.0"   # JWT decode/verify
```

### JWT Verification

```python
# app/core/auth.py
from jose import jwt, JWTError
import httpx

JWKS_URL = "https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys"

async def get_jwks():
    """Fetch AAD public keys (cached)."""
    async with httpx.AsyncClient() as client:
        response = await client.get(JWKS_URL)
        return response.json()

async def verify_token(token: str) -> dict:
    """
    1. Fetch AAD public keys (JWKS)
    2. Verify token signature
    3. Verify claims: aud, iss, exp
    4. Return user info (name, email, oid)
    """
    # Implementation details in implementation plan
```

### API Protection

Use FastAPI dependency injection:

```python
# app/core/auth.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(credentials = Depends(security)) -> dict:
    token = credentials.credentials
    try:
        user = await verify_token(token)
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
```

```python
# app/api/routes/bugs.py
from app.core.auth import get_current_user

@router.get("/summary")
def get_summary(user: dict = Depends(get_current_user)):
    return bug_service.get_global_summary()
```

### Environment Variables

```bash
# .env additions
AAD_CLIENT_ID=your-client-id
AAD_TENANT_ID=your-tenant-id
```

## AAD App Registration Guide

### Step 1: Register Application

1. Go to https://portal.azure.com
2. Navigate to: Azure Active Directory → App registrations
3. Click "New registration"
4. Fill in:
   - **Name**: `Quality Platform`
   - **Supported account types**: `Accounts in this organizational directory only (Microsoft only - Single tenant)`
   - **Redirect URI**:
     - Platform: `Single-page application (SPA)`
     - URL: `http://localhost:8000`

### Step 2: Record Configuration

After registration, note down:
- **Application (client) ID** → `AAD_CLIENT_ID`
- **Directory (tenant) ID** → `AAD_TENANT_ID`

### Step 3: API Permissions

Default permissions should include:
- Microsoft Graph → `User.Read` (for profile info)

If not present, add it:
1. API permissions → Add a permission
2. Microsoft Graph → Delegated permissions
3. Select `User.Read` → Add permissions

### Step 4: Production Deployment

When deploying to production, add production URL:
1. Authentication → Platform configurations
2. Add URI: `https://your-production-domain.com`

## File Changes Summary

| Component | Files | Change Type |
|-----------|-------|-------------|
| Frontend | `js/auth.js` | New |
| Frontend | `js/api.js` | Modify |
| Frontend | `index.html`, `team.html` | Modify |
| Frontend | `css/style.css` | Modify |
| Backend | `app/core/auth.py` | New |
| Backend | `app/core/config.py` | Modify |
| Backend | `app/api/routes/bugs.py` | Modify |
| Backend | `app/main.py` | Modify |
| Config | `pyproject.toml` | Modify |
| Config | `.env.example` | Modify |

## Security Considerations

1. **Token Storage**: Use `sessionStorage` (cleared on browser close) instead of `localStorage`
2. **HTTPS**: Production must use HTTPS for secure token transmission
3. **Token Validation**: Always verify signature, audience, issuer, and expiration
4. **CORS**: Restrict origins in production (remove `allow_origins=["*"]`)

## Next Steps

1. Register AAD application in Azure Portal
2. Implement frontend auth module
3. Implement backend JWT verification
4. Update all API routes with auth dependency
5. Add user profile UI components
