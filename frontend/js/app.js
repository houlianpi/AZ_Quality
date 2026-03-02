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
            // After successful login, reload the page to ensure clean state
            console.log('[Dashboard] Login successful, reloading page...');
            window.location.reload();
            return;
        } catch (error) {
            console.error('[Dashboard] Login failed:', error);
            showLoginError();
            return;
        }
    }

    console.log('[Dashboard] User is logged in:', Auth.getCurrentUser());

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
