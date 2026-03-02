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

    // Check if already logged in (from another tab or session)
    const accounts = msalInstance.getAllAccounts();
    if (accounts.length > 0) {
        currentAccount = accounts[0];
        console.log('[Auth] Already logged in:', currentAccount.username);
        return currentAccount;
    }

    try {
        const response = await msalInstance.loginPopup(loginRequest);
        currentAccount = response.account;
        console.log('[Auth] Login successful:', currentAccount.username);
        return currentAccount;
    } catch (error) {
        console.error('[Auth] Login failed:', error);
        // Handle user cancel
        if (error.errorCode === 'user_cancelled') {
            console.log('[Auth] User cancelled login');
            throw error;
        }
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
        const response = await msalInstance.acquireTokenSilent(request);
        return response.idToken;
    } catch (error) {
        console.warn('[Auth] Silent token failed, trying popup:', error);
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
