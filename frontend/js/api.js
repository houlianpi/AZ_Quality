/**
 * API Module - Quality Push Dashboard
 * Handles all API requests to the backend
 */

const API_BASE = '/api';

/**
 * Generic fetch wrapper with error handling
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
