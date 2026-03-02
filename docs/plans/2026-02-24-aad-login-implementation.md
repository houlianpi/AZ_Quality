# AAD Login Implementation Plan

> **Status**: ✅ COMPLETED (2026-02-25)

**Goal:** Add Microsoft AAD authentication to Quality Platform with frontend MSAL.js login and backend JWT verification.

**Architecture:** Frontend uses MSAL.js for AAD login popup, stores token in sessionStorage, attaches to all API requests. Backend verifies JWT signature against AAD public keys, extracts user info, protects all `/api/*` routes.

**Tech Stack:** MSAL.js 2.x (browser), PyJWT (JWT verification), FastAPI dependencies

---

## Implementation Summary

All tasks completed successfully. AAD authentication is fully functional.

### Completed Features

| Feature | Status | Notes |
|---------|--------|-------|
| Backend JWT verification | ✅ | PyJWT with AAD JWKS |
| AAD config settings | ✅ | AAD_CLIENT_ID, AAD_TENANT_ID |
| Protected API routes | ✅ | All /api/* except /api/auth/config |
| Frontend MSAL.js module | ✅ | Login popup, token management |
| API token attachment | ✅ | Bearer token in all requests |
| User profile display | ✅ | Name, email, initials avatar |
| Login/logout flow | ✅ | Auto-login, logout button |

### Files Created/Modified

```
app/core/auth.py              # JWT verification (NEW)
app/core/config.py            # AAD settings added
app/api/routes/bugs.py        # Auth dependency added
app/main.py                   # /api/auth/config endpoint
frontend/js/auth.js           # MSAL.js module (NEW)
frontend/js/api.js            # Token attachment
frontend/js/app.js            # Auth flow integration
frontend/index.html           # MSAL.js script, user profile
frontend/team.html            # MSAL.js script, user profile
frontend/css/style.css        # User profile styles
.env.example                  # AAD config variables
pyproject.toml                # PyJWT dependency
```

### Known Limitations

- User avatar fetching requires Access Token for Graph API (currently uses initials fallback)

---

## Original Task Plan (Reference)

## Task 1: Add Backend Dependencies

**Files:**
- Modify: `pyproject.toml:14-23`

**Step 1: Add python-jose dependency**

```bash
uv add "python-jose[cryptography]>=3.3.0"
```

**Step 2: Verify installation**

Run: `uv run python -c "from jose import jwt; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat: add python-jose for JWT verification"
```

---

## Task 2: Add AAD Config to Settings

**Files:**
- Modify: `app/core/config.py:5-27`
- Modify: `.env.example`

**Step 1: Update Settings class**

Edit `app/core/config.py`:

```python
# app/core/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "quality_platform"

    # AAD Authentication
    AAD_CLIENT_ID: str = ""
    AAD_TENANT_ID: str = ""

    @property
    def database_url(self) -> str:
        """Return MySQL connection URL for SQLAlchemy."""
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    @property
    def aad_issuer(self) -> str:
        """Return AAD token issuer URL."""
        return f"https://login.microsoftonline.com/{self.AAD_TENANT_ID}/v2.0"

    @property
    def aad_jwks_url(self) -> str:
        """Return AAD JWKS (public keys) URL."""
        return f"https://login.microsoftonline.com/{self.AAD_TENANT_ID}/discovery/v2.0/keys"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
```

**Step 2: Update .env.example**

Append to `.env.example`:

```bash
# AAD Authentication
AAD_CLIENT_ID=your-client-id-here
AAD_TENANT_ID=your-tenant-id-here
```

**Step 3: Verify config loads**

Run: `uv run python -c "from app.core.config import settings; print(settings.AAD_CLIENT_ID)"`
Expected: Empty string (no error)

**Step 4: Commit**

```bash
git add app/core/config.py .env.example
git commit -m "feat: add AAD config settings"
```

---

## Task 3: Create Auth Module with JWT Verification

**Files:**
- Create: `app/core/auth.py`
- Create: `tests/core/test_auth.py`

**Step 1: Write the failing test**

```python
# tests/core/test_auth.py
import pytest

from app.core.auth import verify_token, AuthError


def test_verify_token_rejects_invalid_token():
    """Test that invalid tokens are rejected."""
    with pytest.raises(AuthError):
        # This is a malformed token
        verify_token("invalid.token.here")


def test_verify_token_rejects_expired_token():
    """Test that expired tokens are rejected."""
    # This is a valid format but expired JWT (exp in past)
    expired_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxfQ.invalid"
    with pytest.raises(AuthError):
        verify_token(expired_token)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/test_auth.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.core.auth'"

**Step 3: Write the auth module**

```python
# app/core/auth.py
"""AAD JWT Authentication module."""
from functools import lru_cache
from typing import Any

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError

from app.core.config import settings


class AuthError(Exception):
    """Authentication error."""
    pass


@lru_cache(maxsize=1)
def get_jwks() -> dict[str, Any]:
    """
    Fetch AAD public keys (JWKS).
    Cached to avoid repeated network calls.
    """
    if not settings.AAD_TENANT_ID:
        raise AuthError("AAD_TENANT_ID not configured")

    response = httpx.get(settings.aad_jwks_url, timeout=10.0)
    response.raise_for_status()
    return response.json()


def get_signing_key(token: str) -> dict[str, Any]:
    """Get the signing key for a token from JWKS."""
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise AuthError(f"Invalid token header: {e}")

    jwks = get_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == unverified_header.get("kid"):
            return key

    raise AuthError("Unable to find signing key")


def verify_token(token: str) -> dict[str, Any]:
    """
    Verify AAD JWT token and return user claims.

    Args:
        token: JWT token string

    Returns:
        Dictionary with user claims (name, email, oid, etc.)

    Raises:
        AuthError: If token is invalid, expired, or verification fails
    """
    if not settings.AAD_CLIENT_ID or not settings.AAD_TENANT_ID:
        raise AuthError("AAD not configured")

    try:
        signing_key = get_signing_key(token)

        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=settings.AAD_CLIENT_ID,
            issuer=settings.aad_issuer,
            options={
                "verify_exp": True,
                "verify_aud": True,
                "verify_iss": True,
            },
        )

        return {
            "oid": payload.get("oid"),  # Object ID (unique user ID)
            "name": payload.get("name", ""),
            "email": payload.get("preferred_username", payload.get("email", "")),
            "roles": payload.get("roles", []),
        }

    except JWTError as e:
        raise AuthError(f"Token verification failed: {e}")


# FastAPI security scheme
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    """
    FastAPI dependency to get current authenticated user.

    Usage:
        @router.get("/protected")
        def protected_route(user: dict = Depends(get_current_user)):
            return {"user": user["name"]}
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = verify_token(credentials.credentials)
        return user
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/core/test_auth.py -v`
Expected: PASS (tests should pass as invalid tokens raise AuthError)

**Step 5: Commit**

```bash
git add app/core/auth.py tests/core/test_auth.py
git commit -m "feat: add AAD JWT verification module"
```

---

## Task 4: Protect API Routes

**Files:**
- Modify: `app/api/routes/bugs.py:1-71`

**Step 1: Update bugs.py with auth dependency**

Replace the entire file:

```python
# app/api/routes/bugs.py
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import get_current_user
from app.services.bug_service import BugService

router = APIRouter()
bug_service = BugService()


@router.get("/summary")
def get_summary(user: dict[str, Any] = Depends(get_current_user)):
    """Get global summary across all teams."""
    return bug_service.get_global_summary()


@router.get("/teams")
def get_teams(user: dict[str, Any] = Depends(get_current_user)):
    """Get list of teams with summary stats."""
    teams = bug_service.get_teams_overview()
    return {"teams": teams}


@router.get("/teams/{team_name}/summary")
def get_team_summary(
    team_name: str,
    user: dict[str, Any] = Depends(get_current_user),
):
    """Get summary for a specific team."""
    try:
        return bug_service.get_team_summary(team_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/teams/{team_name}/bugs")
def get_team_bugs(
    team_name: str,
    user: dict[str, Any] = Depends(get_current_user),
    bug_type: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    sort_by: str = Query("due_date"),
    sort_order: str = Query("asc"),
):
    """Get bug list for a team with optional filters."""
    try:
        return bug_service.get_team_bugs(
            team_name,
            bug_type=bug_type,
            status=status,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/teams/{team_name}/trend")
def get_team_trend(
    team_name: str,
    user: dict[str, Any] = Depends(get_current_user),
    days: int = Query(30),
):
    """Get trend data for a team."""
    try:
        return bug_service.get_team_trend(team_name, days=days)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/teams/{team_name}/query-links")
def get_team_query_links(
    team_name: str,
    user: dict[str, Any] = Depends(get_current_user),
):
    """Get ADO query links for a team."""
    try:
        return bug_service.get_team_query_links(team_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/me")
def get_current_user_info(user: dict[str, Any] = Depends(get_current_user)):
    """Get current authenticated user info."""
    return user
```

**Step 2: Verify API routes require auth**

Run: `uv run uvicorn app.main:app --port 8000 &`
Run: `curl -s http://localhost:8000/api/summary | head -c 100`
Expected: `{"detail":"Missing authentication token"}`

**Step 3: Stop test server**

Run: `pkill -f uvicorn`

**Step 4: Commit**

```bash
git add app/api/routes/bugs.py
git commit -m "feat: protect all API routes with auth dependency"
```

---

## Task 5: Add Auth Config Endpoint

**Files:**
- Modify: `app/main.py`

**Step 1: Add config endpoint for frontend**

Edit `app/main.py`:

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import bugs
from app.core.config import settings

app = FastAPI(
    title="Quality Platform API",
    description="Bug status dashboard API",
    version="1.0.0",
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(bugs.router, prefix="/api", tags=["bugs"])


@app.get("/api/auth/config")
def get_auth_config():
    """
    Return AAD config for frontend MSAL.js.
    This endpoint is public (no auth required).
    """
    return {
        "clientId": settings.AAD_CLIENT_ID,
        "authority": f"https://login.microsoftonline.com/{settings.AAD_TENANT_ID}",
        "redirectUri": "/",  # Frontend will override with window.location.origin
    }


# Static files (frontend) - must be last
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
```

**Step 2: Verify config endpoint works**

Run: `uv run uvicorn app.main:app --port 8000 &`
Run: `curl -s http://localhost:8000/api/auth/config`
Expected: `{"clientId":"","authority":"https://login.microsoftonline.com/","redirectUri":"/"}`

**Step 3: Stop test server**

Run: `pkill -f uvicorn`

**Step 4: Commit**

```bash
git add app/main.py
git commit -m "feat: add public auth config endpoint for frontend"
```

---

## Task 6: Create Frontend Auth Module

**Files:**
- Create: `frontend/js/auth.js`

**Step 1: Create auth.js**

```javascript
/**
 * Auth Module - Quality Push Dashboard
 * Handles Microsoft AAD authentication via MSAL.js
 */

// MSAL configuration - loaded from backend
let msalConfig = null;
let msalInstance = null;
let currentAccount = null;

// Login request scopes
const loginRequest = {
    scopes: ["User.Read", "openid", "profile", "email"]
};

// Token request for API calls
const tokenRequest = {
    scopes: ["User.Read"]
};

/**
 * Initialize MSAL with config from backend
 */
async function initAuth() {
    try {
        // Fetch config from backend
        const response = await fetch('/api/auth/config');
        const config = await response.json();

        if (!config.clientId) {
            console.warn('[Auth] AAD not configured on backend');
            return false;
        }

        msalConfig = {
            auth: {
                clientId: config.clientId,
                authority: config.authority,
                redirectUri: window.location.origin,
                postLogoutRedirectUri: window.location.origin,
                navigateToLoginRequestUrl: true
            },
            cache: {
                cacheLocation: "sessionStorage",
                storeAuthStateInCookie: false
            },
            system: {
                loggerOptions: {
                    loggerCallback: (level, message, containsPii) => {
                        if (!containsPii) {
                            console.log(`[MSAL] ${message}`);
                        }
                    },
                    logLevel: msal.LogLevel.Warning
                }
            }
        };

        msalInstance = new msal.PublicClientApplication(msalConfig);

        // Handle redirect response (if coming back from login)
        await msalInstance.initialize();
        const response2 = await msalInstance.handleRedirectPromise();
        if (response2) {
            currentAccount = response2.account;
            console.log('[Auth] Login redirect completed');
        }

        // Check for existing session
        const accounts = msalInstance.getAllAccounts();
        if (accounts.length > 0) {
            currentAccount = accounts[0];
            console.log('[Auth] Found existing session:', currentAccount.username);
        }

        return true;
    } catch (error) {
        console.error('[Auth] Init failed:', error);
        return false;
    }
}

/**
 * Check if user is logged in
 */
function isLoggedIn() {
    return currentAccount !== null;
}

/**
 * Get current user info
 */
function getCurrentUser() {
    if (!currentAccount) return null;
    return {
        name: currentAccount.name || currentAccount.username,
        email: currentAccount.username,
        oid: currentAccount.localAccountId
    };
}

/**
 * Trigger login popup
 */
async function login() {
    if (!msalInstance) {
        console.error('[Auth] MSAL not initialized');
        return null;
    }

    try {
        const response = await msalInstance.loginPopup(loginRequest);
        currentAccount = response.account;
        console.log('[Auth] Login successful:', currentAccount.username);
        return currentAccount;
    } catch (error) {
        console.error('[Auth] Login failed:', error);
        // If popup blocked, try redirect
        if (error.errorCode === 'popup_window_error') {
            console.log('[Auth] Popup blocked, using redirect');
            await msalInstance.loginRedirect(loginRequest);
        }
        throw error;
    }
}

/**
 * Logout user
 */
async function logout() {
    if (!msalInstance) return;

    try {
        await msalInstance.logoutPopup({
            account: currentAccount,
            postLogoutRedirectUri: window.location.origin
        });
        currentAccount = null;
    } catch (error) {
        console.error('[Auth] Logout failed:', error);
        // Fallback to redirect logout
        await msalInstance.logoutRedirect({
            account: currentAccount
        });
    }
}

/**
 * Get access token for API calls (silently or via popup)
 */
async function getAccessToken() {
    if (!msalInstance || !currentAccount) {
        throw new Error('Not logged in');
    }

    const request = {
        ...tokenRequest,
        account: currentAccount
    };

    try {
        // Try silent token acquisition first
        const response = await msalInstance.acquireTokenSilent(request);
        return response.idToken;  // Use ID token for our API
    } catch (error) {
        console.warn('[Auth] Silent token failed, trying popup:', error);
        // If silent fails, try popup
        const response = await msalInstance.acquireTokenPopup(request);
        return response.idToken;
    }
}

/**
 * Fetch user avatar from Microsoft Graph
 */
async function getUserAvatar() {
    try {
        const token = await getAccessToken();
        const response = await fetch('https://graph.microsoft.com/v1.0/me/photo/$value', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const blob = await response.blob();
            return URL.createObjectURL(blob);
        }
    } catch (error) {
        console.warn('[Auth] Failed to fetch avatar:', error);
    }
    return null;
}

// Export for use in other modules
window.Auth = {
    init: initAuth,
    isLoggedIn,
    getCurrentUser,
    login,
    logout,
    getAccessToken,
    getUserAvatar
};
```

**Step 2: Verify file created**

Run: `ls -la frontend/js/auth.js`
Expected: File exists

**Step 3: Commit**

```bash
git add frontend/js/auth.js
git commit -m "feat: add frontend auth module with MSAL.js"
```

---

## Task 7: Update API Module to Use Auth

**Files:**
- Modify: `frontend/js/api.js`

**Step 1: Update api.js to attach auth token**

Replace the entire file:

```javascript
/**
 * API Module - Quality Push Dashboard
 * Handles all API requests to the backend with authentication
 */

const API_BASE = '/api';

/**
 * Generic fetch wrapper with error handling and auth
 */
async function fetchAPI(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;

    try {
        // Get auth token if logged in
        let authHeader = {};
        if (window.Auth && window.Auth.isLoggedIn()) {
            try {
                const token = await window.Auth.getAccessToken();
                authHeader = { 'Authorization': `Bearer ${token}` };
            } catch (e) {
                console.warn('[API] Failed to get token:', e);
                // Redirect to login
                window.Auth.login();
                throw new Error('Authentication required');
            }
        }

        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...authHeader,
                ...options.headers
            },
            ...options
        });

        // Handle 401 - trigger re-login
        if (response.status === 401) {
            console.warn('[API] 401 Unauthorized, triggering login');
            if (window.Auth) {
                await window.Auth.login();
            }
            throw new Error('Authentication required');
        }

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`API Error [${endpoint}]:`, error);
        throw error;
    }
}

/**
 * Get global summary across all teams
 */
async function getSummary() {
    return fetchAPI('/summary');
}

/**
 * Get list of all teams with summary stats
 */
async function getTeams() {
    const data = await fetchAPI('/teams');
    return data.teams || [];
}

/**
 * Get summary for a specific team
 */
async function getTeamSummary(teamName) {
    return fetchAPI(`/teams/${encodeURIComponent(teamName)}/summary`);
}

/**
 * Get bug list for a team with optional filters
 */
async function getTeamBugs(teamName, filters = {}) {
    const params = new URLSearchParams();

    if (filters.bug_type) params.append('bug_type', filters.bug_type);
    if (filters.status) params.append('status', filters.status);
    if (filters.search) params.append('search', filters.search);
    if (filters.sort_by) params.append('sort_by', filters.sort_by);
    if (filters.sort_order) params.append('sort_order', filters.sort_order);

    const queryString = params.toString();
    const endpoint = `/teams/${encodeURIComponent(teamName)}/bugs${queryString ? '?' + queryString : ''}`;

    return fetchAPI(endpoint);
}

/**
 * Get trend data for a team
 */
async function getTeamTrend(teamName, days = 30) {
    return fetchAPI(`/teams/${encodeURIComponent(teamName)}/trend?days=${days}`);
}

/**
 * Get global trend data (aggregate all teams)
 */
async function getGlobalTrend(days = 30) {
    const teams = await getTeams();
    const trends = await Promise.all(
        teams.map(t => getTeamTrend(t.team_name, days).catch(() => null))
    );

    // Aggregate trends for all 5 bug types
    const dateMap = new Map();
    const bugTypes = ['blocking', 'a11y', 'security', 'needtriage', 'p0p1'];

    for (const trend of trends) {
        if (!trend || !trend.dates) continue;

        trend.dates.forEach((date, i) => {
            if (!dateMap.has(date)) {
                const entry = {};
                bugTypes.forEach(t => entry[t] = 0);
                dateMap.set(date, entry);
            }
            const entry = dateMap.get(date);
            bugTypes.forEach(t => {
                entry[t] += trend[t]?.[i] || 0;
            });
        });
    }

    const dates = Array.from(dateMap.keys()).sort();
    const result = { dates };
    bugTypes.forEach(t => {
        result[t] = dates.map(d => dateMap.get(d)[t]);
    });
    return result;
}

/**
 * Get ADO query links for a team
 */
async function getTeamQueryLinks(teamName) {
    return fetchAPI(`/teams/${encodeURIComponent(teamName)}/query-links`);
}

/**
 * Get current user info from backend
 */
async function getCurrentUser() {
    return fetchAPI('/me');
}

// Export for use in other modules
window.API = {
    getSummary,
    getTeams,
    getTeamSummary,
    getTeamBugs,
    getTeamTrend,
    getGlobalTrend,
    getTeamQueryLinks,
    getCurrentUser
};
```

**Step 2: Commit**

```bash
git add frontend/js/api.js
git commit -m "feat: add auth token to all API requests"
```

---

## Task 8: Update HTML Pages with MSAL.js and User Profile

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/team.html`

**Step 1: Update index.html**

Add MSAL.js script and user profile section. Edit `frontend/index.html`:

In `<head>`, add MSAL.js CDN after Chart.js:

```html
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <script src="https://alcdn.msauth.net/browser/2.38.0/js/msal-browser.min.js"></script>
```

Replace the sidebar-header section (lines 13-16):

```html
        <div class="sidebar-header">
            <div class="sidebar-logo">QP</div>
            <div class="sidebar-title">Quality Push</div>
        </div>
        <!-- User Profile (shown when logged in) -->
        <div id="user-profile" class="user-profile" style="display: none;">
            <img id="user-avatar" class="user-avatar" src="" alt="Avatar">
            <div class="user-info">
                <div id="user-name" class="user-name">--</div>
                <div id="user-email" class="user-email">--</div>
            </div>
            <button id="logout-btn" class="logout-btn" title="Logout">⏻</button>
        </div>
```

Update script section (before closing `</body>`):

```html
    <!-- Scripts -->
    <script src="js/auth.js"></script>
    <script src="js/api.js"></script>
    <script src="js/charts.js"></script>
    <script src="js/table.js"></script>
    <script src="js/app.js"></script>
```

**Step 2: Update team.html similarly**

Add MSAL.js in `<head>`:

```html
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <script src="https://alcdn.msauth.net/browser/2.38.0/js/msal-browser.min.js"></script>
```

Add user profile section after sidebar-header.

Update script order to include auth.js first.

**Step 3: Commit**

```bash
git add frontend/index.html frontend/team.html
git commit -m "feat: add MSAL.js and user profile to HTML pages"
```

---

## Task 9: Add User Profile CSS Styles

**Files:**
- Modify: `frontend/css/style.css`

**Step 1: Add user profile styles**

Append to `frontend/css/style.css`:

```css
/* User Profile Styles */
.user-profile {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    padding: var(--space-md);
    border-top: 1px solid var(--border-primary);
    margin-top: auto;
}

.user-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: var(--bg-tertiary);
    object-fit: cover;
    flex-shrink: 0;
}

.user-avatar-placeholder {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: var(--accent-blue);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 600;
    color: var(--bg-primary);
    flex-shrink: 0;
}

.user-info {
    flex: 1;
    min-width: 0;
    overflow: hidden;
}

.user-name {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.user-email {
    font-size: 0.7rem;
    color: var(--text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.logout-btn {
    background: transparent;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    padding: var(--space-xs);
    font-size: 1rem;
    border-radius: var(--radius-sm);
    transition: all 0.2s ease;
    flex-shrink: 0;
}

.logout-btn:hover {
    background: var(--bg-tertiary);
    color: var(--accent-red);
}

/* Login overlay */
.login-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: var(--bg-primary);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
}

.login-box {
    text-align: center;
    padding: var(--space-xl);
}

.login-title {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: var(--space-md);
}

.login-desc {
    color: var(--text-secondary);
    margin-bottom: var(--space-lg);
}

.login-btn {
    background: var(--accent-blue);
    color: var(--bg-primary);
    border: none;
    padding: var(--space-md) var(--space-xl);
    font-family: var(--font-mono);
    font-size: 0.9rem;
    font-weight: 600;
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all 0.2s ease;
}

.login-btn:hover {
    background: var(--accent-green);
    transform: translateY(-2px);
}

.login-btn:disabled {
    background: var(--text-dim);
    cursor: not-allowed;
    transform: none;
}
```

**Step 2: Commit**

```bash
git add frontend/css/style.css
git commit -m "feat: add user profile and login styles"
```

---

## Task 10: Update App.js with Auth Flow

**Files:**
- Modify: `frontend/js/app.js`

**Step 1: Update app.js to handle auth**

At the beginning of `app.js`, add auth initialization. Wrap the DOMContentLoaded handler:

```javascript
/**
 * App Module - Quality Push Dashboard
 * Main entry point and page initialization
 */

// Determine current page
function getCurrentPage() {
    const path = window.location.pathname;
    if (path.includes('team.html') || path.includes('team')) {
        return 'team';
    }
    return 'index';
}

// Get team name from URL
function getTeamFromURL() {
    const params = new URLSearchParams(window.location.search);
    return params.get('team');
}

// Format numbers with commas
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// Get current timestamp
function getTimestamp() {
    const now = new Date();
    return now.toISOString().replace('T', ' ').substring(0, 19);
}

// Show loading state
function showLoading(elementId) {
    const el = document.getElementById(elementId);
    if (el) {
        el.innerHTML = '<div class="loading">Loading data</div>';
    }
}

// Show error state
function showError(elementId, message) {
    const el = document.getElementById(elementId);
    if (el) {
        el.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <div class="empty-state-title">Error</div>
                <div class="empty-state-desc">${message}</div>
            </div>
        `;
    }
}

/**
 * Display user profile in sidebar
 */
async function displayUserProfile() {
    const userProfile = document.getElementById('user-profile');
    const userName = document.getElementById('user-name');
    const userEmail = document.getElementById('user-email');
    const userAvatar = document.getElementById('user-avatar');
    const logoutBtn = document.getElementById('logout-btn');

    if (!userProfile || !Auth.isLoggedIn()) return;

    const user = Auth.getCurrentUser();
    if (!user) return;

    userName.textContent = user.name || 'User';
    userEmail.textContent = user.email || '';
    userProfile.style.display = 'flex';

    // Try to load avatar
    const avatarUrl = await Auth.getUserAvatar();
    if (avatarUrl) {
        userAvatar.src = avatarUrl;
        userAvatar.style.display = 'block';
    } else {
        // Show initials instead
        const initials = (user.name || 'U').split(' ').map(n => n[0]).join('').substring(0, 2);
        userAvatar.outerHTML = `<div class="user-avatar-placeholder">${initials}</div>`;
    }

    // Logout handler
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            await Auth.logout();
            window.location.reload();
        });
    }
}

/**
 * Initialize authentication and show login if needed
 */
async function initWithAuth(pageInitFn) {
    console.log('[Dashboard] Initializing authentication...');

    // Initialize auth
    const authReady = await Auth.init();

    if (!authReady) {
        // AAD not configured, proceed without auth (dev mode)
        console.warn('[Dashboard] AAD not configured, running without auth');
        pageInitFn();
        return;
    }

    // Check if logged in
    if (!Auth.isLoggedIn()) {
        console.log('[Dashboard] Not logged in, triggering login...');
        try {
            await Auth.login();
        } catch (error) {
            console.error('[Dashboard] Login failed:', error);
            showLoginError();
            return;
        }
    }

    // Display user profile
    await displayUserProfile();

    // Initialize page
    pageInitFn();
}

function showLoginError() {
    document.body.innerHTML = `
        <div class="login-overlay">
            <div class="login-box">
                <div class="login-title">Authentication Required</div>
                <div class="login-desc">Please sign in with your Microsoft account to continue.</div>
                <button class="login-btn" onclick="window.Auth.login().then(() => window.location.reload())">
                    Sign in with Microsoft
                </button>
            </div>
        </div>
    `;
}

/**
 * Initialize Index Page (Home)
 */
async function initIndexPage() {
    console.log('[Dashboard] Initializing index page...');

    // Update timestamp
    const timestampEl = document.getElementById('report-timestamp');
    if (timestampEl) {
        timestampEl.textContent = getTimestamp();
    }

    try {
        // Fetch summary and teams data in parallel
        const [summary, teams] = await Promise.all([
            API.getSummary(),
            API.getTeams()
        ]);

        console.log('[Dashboard] Data loaded:', { summary, teams });

        // Update summary cards
        updateSummaryCard('stat-total', summary.total_bugs);
        updateSummaryCard('stat-blocking', summary.blocking_bugs);
        updateSummaryCard('stat-overdue', summary.overdue_bugs);
        updateSummaryCard('stat-needtriage', summary.need_triage_bugs);

        // Update snapshot date
        const snapshotEl = document.getElementById('snapshot-date');
        if (snapshotEl && summary.snapshot_date) {
            snapshotEl.textContent = summary.snapshot_date;
        }

        // Render team table
        renderTeamTable(teams);

        // Load and render trend chart
        try {
            const trend = await API.getGlobalTrend(30);
            if (trend.dates && trend.dates.length > 0) {
                Charts.createTrendChart('trend-chart', trend);
            } else {
                document.getElementById('trend-chart-container').innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">📊</div>
                        <div class="empty-state-title">No trend data yet</div>
                        <div class="empty-state-desc">Trend data will appear after multiple daily syncs</div>
                    </div>
                `;
            }
        } catch (e) {
            console.warn('[Dashboard] Trend data not available:', e);
        }

    } catch (error) {
        console.error('[Dashboard] Failed to load data:', error);
        showError('team-table-body', error.message);
    }
}

function updateSummaryCard(elementId, value) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = formatNumber(value || 0);
    }
}

function renderTeamTable(teams) {
    const tbody = document.getElementById('team-table-body');
    if (!tbody) return;

    if (!teams || teams.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <div class="empty-state-title">No teams found</div>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = teams.map(team => `
        <tr onclick="window.location.href='team.html?team=${encodeURIComponent(team.team_name)}'">
            <td><span class="team-name">${team.display_name}</span></td>
            <td>${formatNumber(team.total)}</td>
            <td><span class="badge blocking">${team.blocking}</span></td>
            <td><span class="badge p0p1">${team.p0p1}</span></td>
            <td><span class="badge overdue">${team.overdue}</span></td>
        </tr>
    `).join('');
}

/**
 * Initialize Team Detail Page
 */
async function initTeamPage() {
    const teamName = getTeamFromURL();

    if (!teamName) {
        window.location.href = '/';
        return;
    }

    console.log(`[Dashboard] Initializing team page for: ${teamName}`);

    // Update page title and header
    const teamTitle = document.getElementById('team-title');
    const pageTitle = document.getElementById('page-title');
    const cmdTeam = document.getElementById('cmd-team');
    const displayName = teamName.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

    if (teamTitle) teamTitle.textContent = displayName;
    if (pageTitle) pageTitle.textContent = `${displayName} - Bug Status`;
    if (cmdTeam) cmdTeam.textContent = teamName;

    // Update timestamp
    const timestampEl = document.getElementById('report-timestamp');
    if (timestampEl) {
        timestampEl.textContent = getTimestamp();
    }

    try {
        // Fetch team data
        const [summary, bugsData] = await Promise.all([
            API.getTeamSummary(teamName),
            API.getTeamBugs(teamName)
        ]);

        console.log('[Dashboard] Team data loaded:', { summary, bugsData });

        // Update summary cards with bug type counts
        const byType = summary.by_type || {};
        updateSummaryCard('stat-blocking', byType.Blocking || 0);
        updateSummaryCard('stat-a11y', byType.A11y || 0);
        updateSummaryCard('stat-security', byType.Security || 0);
        updateSummaryCard('stat-needtriage', byType.NeedTriage || 0);
        updateSummaryCard('stat-p0p1', byType.P0P1 || 0);

        // Update snapshot date
        const snapshotEl = document.getElementById('snapshot-date');
        if (snapshotEl && summary.snapshot_date) {
            snapshotEl.textContent = summary.snapshot_date;
        }

        // Render top assignees list
        renderTopAssignees(summary.top_assignees);

        // Render pie charts
        if (summary.top_assignees && summary.top_assignees.length > 0) {
            Charts.createPieChart('assignee-pie-chart', summary.top_assignees);
        }
        if (summary.top_area_paths && summary.top_area_paths.length > 0) {
            Charts.createPieChart('areapath-pie-chart', summary.top_area_paths);
        }

        // Load and render trend chart (moved to terminal body)
        try {
            const trend = await API.getTeamTrend(teamName, 30);
            if (trend.dates && trend.dates.length > 0) {
                Charts.createTrendChart('trend-chart', trend);
            } else {
                document.getElementById('trend-chart-container').innerHTML = `
                    <div class="empty-state" style="padding: 40px 20px;">
                        <div class="empty-state-icon">📊</div>
                        <div class="empty-state-title">No trend data yet</div>
                        <div class="empty-state-desc">Trend data appears after multiple daily syncs</div>
                    </div>
                `;
            }
        } catch (e) {
            console.warn('[Dashboard] Trend data not available:', e);
        }

        // Get query links
        let queryLinks = {};
        try {
            queryLinks = await API.getTeamQueryLinks(teamName);
        } catch (e) {
            console.warn('[Dashboard] Query links not available:', e);
        }

        // Group bugs by type
        const bugsByType = {
            blocking: [],
            a11y: [],
            security: [],
            needtriage: [],
            p0p1: []
        };

        for (const bug of bugsData.bugs) {
            const typeKey = bug.bug_type.toLowerCase().replace(/\s+/g, '');
            if (bugsByType[typeKey]) {
                bugsByType[typeKey].push(bug);
            }
        }

        // Initialize 5 separate tables with query links
        const blockingTable = new BugTable('blocking-table-container', {
            tableKey: 'blocking',
            queryLink: queryLinks.blocking
        });
        blockingTable.setData(bugsByType.blocking);

        const a11yTable = new BugTable('a11y-table-container', {
            tableKey: 'a11y',
            queryLink: queryLinks.a11y
        });
        a11yTable.setData(bugsByType.a11y);

        const securityTable = new BugTable('security-table-container', {
            tableKey: 'security',
            queryLink: queryLinks.security
        });
        securityTable.setData(bugsByType.security);

        const needTriageTable = new BugTable('needtriage-table-container', {
            tableKey: 'needtriage',
            queryLink: queryLinks.needtriage
        });
        needTriageTable.setData(bugsByType.needtriage);

        const p0p1Table = new BugTable('p0p1-table-container', {
            tableKey: 'p0p1',
            queryLink: queryLinks.p0p1
        });
        p0p1Table.setData(bugsByType.p0p1);

    } catch (error) {
        console.error('[Dashboard] Failed to load team data:', error);
        showError('blocking-table-body', error.message);
    }
}

function renderTopAssignees(assignees) {
    const container = document.getElementById('top-assignees');
    if (!container) return;

    if (!assignees || assignees.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="padding: 20px;">
                <div class="empty-state-title">No assignees</div>
            </div>
        `;
        return;
    }

    container.innerHTML = assignees.slice(0, 10).map((assignee, index) => `
        <div class="assignee-item">
            <div class="assignee-rank">${index + 1}</div>
            <div class="assignee-name">${assignee.name}</div>
            <div class="assignee-count">${assignee.count}</div>
        </div>
    `).join('');
}

/**
 * Load sidebar teams
 */
async function loadSidebarTeams() {
    const container = document.getElementById('sidebar-teams');
    if (!container) return;

    try {
        const teams = await API.getTeams();
        const currentTeam = getTeamFromURL();

        container.innerHTML = teams.map(team => `
            <a href="team.html?team=${encodeURIComponent(team.team_name)}"
               class="sidebar-team ${team.team_name === currentTeam ? 'active' : ''}">
                <span class="sidebar-team-icon"></span>
                <span class="sidebar-text">${team.display_name}</span>
                <span class="sidebar-team-count">${team.total}</span>
            </a>
        `).join('');
    } catch (e) {
        console.warn('[Dashboard] Failed to load sidebar teams:', e);
    }
}

/**
 * Main initialization
 */
document.addEventListener('DOMContentLoaded', () => {
    const page = getCurrentPage();
    console.log(`[Dashboard] Page detected: ${page}`);

    // Initialize with auth
    initWithAuth(async () => {
        // Load sidebar teams on all pages
        loadSidebarTeams();

        if (page === 'team') {
            initTeamPage();
        } else {
            initIndexPage();
        }
    });
});
```

**Step 2: Commit**

```bash
git add frontend/js/app.js
git commit -m "feat: integrate auth flow into app initialization"
```

---

## Task 11: Final Integration Test

**Step 1: Set up test environment variables**

Create or update `.env` with test AAD credentials (after registering AAD app):

```bash
# Copy example and add your AAD credentials
cp .env.example .env
# Edit .env and add AAD_CLIENT_ID and AAD_TENANT_ID
```

**Step 2: Start the server**

Run: `uv run uvicorn app.main:app --reload --port 8000`

**Step 3: Test unauthenticated API access**

Run: `curl -s http://localhost:8000/api/summary`
Expected: `{"detail":"Missing authentication token"}`

**Step 4: Test auth config endpoint**

Run: `curl -s http://localhost:8000/api/auth/config`
Expected: JSON with clientId and authority

**Step 5: Test frontend login flow**

Open: http://localhost:8000
Expected: MSAL login popup appears (if AAD configured) or dashboard loads (if not configured)

**Step 6: Final commit**

```bash
git add -A
git commit -m "feat: complete AAD authentication implementation"
```

---

## Summary

| Task | Description | Status |
|------|-------------|--------|
| 1 | Add Backend Dependencies | ⬜ |
| 2 | Add AAD Config to Settings | ⬜ |
| 3 | Create Auth Module with JWT Verification | ⬜ |
| 4 | Protect API Routes | ⬜ |
| 5 | Add Auth Config Endpoint | ⬜ |
| 6 | Create Frontend Auth Module | ⬜ |
| 7 | Update API Module to Use Auth | ⬜ |
| 8 | Update HTML Pages with MSAL.js | ⬜ |
| 9 | Add User Profile CSS Styles | ⬜ |
| 10 | Update App.js with Auth Flow | ⬜ |
| 11 | Final Integration Test | ⬜ |

**Estimated Total Time:** ~90 minutes
