/**
 * Table Module - Quality Push Dashboard
 * Handles bug table with sorting, filtering, search, and pagination
 * Supports multiple tables per page
 */

class BugTable {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.tableKey = options.tableKey || containerId.replace('-table-container', '');
        this.queryLink = options.queryLink || null;
        this.options = {
            pageSize: 20,
            showTypeColumn: false,  // Hide type column since each table is for one type
            ...options
        };

        this.bugs = [];
        this.filteredBugs = [];
        this.currentPage = 1;
        this.sortColumn = 'due_date';
        this.sortOrder = 'asc';
        this.searchTerm = '';

        this.init();
    }

    init() {
        // Update table title with query link if available
        if (this.queryLink) {
            const titleEl = this.container.querySelector('.table-title');
            if (titleEl) {
                const originalText = titleEl.textContent.replace('$ ', '');
                titleEl.innerHTML = `<a href="${this.queryLink}" target="_blank" class="table-title-link">${originalText}</a>`;
            }
        }

        // Bind search input for this specific table
        const searchInput = this.container.querySelector(`input[data-table="${this.tableKey}"]`);
        if (searchInput) {
            let debounceTimer;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    this.searchTerm = e.target.value.toLowerCase();
                    this.applyFilters();
                }, 300);
            });
        }
    }

    setData(bugs) {
        this.bugs = bugs || [];
        this.applyFilters();
    }

    applyFilters() {
        this.filteredBugs = this.bugs.filter(bug => {
            // Search filter
            if (this.searchTerm) {
                const matchId = String(bug.bug_id).includes(this.searchTerm);
                const matchTitle = bug.title.toLowerCase().includes(this.searchTerm);
                const matchAssignee = (bug.assigned_to || '').toLowerCase().includes(this.searchTerm);
                if (!matchId && !matchTitle && !matchAssignee) return false;
            }
            return true;
        });

        this.sortBugs();
        this.currentPage = 1;
        this.render();
    }

    sortBugs() {
        this.filteredBugs.sort((a, b) => {
            let valA = a[this.sortColumn];
            let valB = b[this.sortColumn];

            // Handle null values
            if (valA === null || valA === undefined) valA = this.sortOrder === 'asc' ? Infinity : -Infinity;
            if (valB === null || valB === undefined) valB = this.sortOrder === 'asc' ? Infinity : -Infinity;

            // Compare
            let result = 0;
            if (typeof valA === 'string') {
                result = valA.localeCompare(valB);
            } else {
                result = valA < valB ? -1 : valA > valB ? 1 : 0;
            }

            return this.sortOrder === 'asc' ? result : -result;
        });
    }

    sort(column) {
        if (this.sortColumn === column) {
            this.sortOrder = this.sortOrder === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = column;
            this.sortOrder = 'asc';
        }

        this.sortBugs();
        this.render();
        this.updateSortIndicators();
    }

    updateSortIndicators() {
        const headers = this.container.querySelectorAll('th.sortable');
        headers.forEach(th => {
            th.classList.remove('sorted-asc', 'sorted-desc');
            if (th.dataset.sort === this.sortColumn) {
                th.classList.add(this.sortOrder === 'asc' ? 'sorted-asc' : 'sorted-desc');
            }
        });
    }

    goToPage(page) {
        const totalPages = Math.ceil(this.filteredBugs.length / this.options.pageSize);
        if (page < 1 || page > totalPages) return;
        this.currentPage = page;
        this.render();
    }

    render() {
        const tbody = this.container.querySelector('tbody');
        const paginationInfo = document.getElementById(`${this.tableKey}-pagination-info`);
        const paginationControls = document.getElementById(`${this.tableKey}-pagination-controls`);
        const tableCount = document.getElementById(`${this.tableKey}-table-count`);

        if (!tbody) return;

        // Calculate pagination
        const totalItems = this.filteredBugs.length;
        const totalPages = Math.ceil(totalItems / this.options.pageSize);
        const startIndex = (this.currentPage - 1) * this.options.pageSize;
        const endIndex = Math.min(startIndex + this.options.pageSize, totalItems);
        const pageItems = this.filteredBugs.slice(startIndex, endIndex);

        // Update count
        if (tableCount) {
            tableCount.textContent = `${totalItems} items`;
        }

        // Render rows
        if (pageItems.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="empty-state">
                        <div class="empty-state-icon">🎉</div>
                        <div class="empty-state-title">${this.bugs.length === 0 ? 'Congratulations!!!' : 'No bugs found'}</div>
                        <div class="empty-state-desc">${this.bugs.length === 0 ? 'Your team has already cleaned all bugs in this category.' : 'Try adjusting your search'}</div>
                    </td>
                </tr>
            `;
        } else {
            tbody.innerHTML = pageItems.map(bug => this.renderRow(bug)).join('');
        }

        // Update pagination info
        if (paginationInfo) {
            paginationInfo.textContent = totalItems > 0
                ? `Showing ${startIndex + 1} - ${endIndex} of ${totalItems}`
                : 'No results';
        }

        // Render pagination controls
        if (paginationControls) {
            paginationControls.innerHTML = this.renderPagination(totalPages);
            this.bindPaginationEvents();
        }

        // Bind sort events
        this.bindSortEvents();
    }

    renderRow(bug) {
        const priorityClass = bug.priority !== null ? `p${bug.priority}` : '';
        const dueDateClass = this.getDueDateClass(bug);
        const stateClass = bug.state.toLowerCase();
        const escapedTitle = this.escapeHtml(bug.title);
        const areaPath = this.formatAreaPath(bug.area_path);

        return `
            <tr>
                <td>
                    <a href="${bug.ado_url}" target="_blank" class="bug-id-link">${bug.bug_id}</a>
                </td>
                <td class="bug-title-cell">
                    <div class="bug-title-wrapper">
                        <span class="bug-title">${escapedTitle}</span>
                        <div class="bug-title-tooltip">${escapedTitle}</div>
                    </div>
                </td>
                <td>
                    ${bug.priority !== null
                        ? `<span class="priority-badge ${priorityClass}">P${bug.priority}</span>`
                        : '<span class="text-muted">-</span>'}
                </td>
                <td>
                    <span class="due-date ${dueDateClass}">${this.formatDate(bug.due_date)}</span>
                </td>
                <td>${bug.assigned_to || '<span class="text-muted">Unassigned</span>'}</td>
                <td>
                    <span class="state-badge ${stateClass}">${bug.state}</span>
                </td>
                <td class="area-path-cell">
                    <span class="area-path" title="${bug.area_path || ''}">${areaPath}</span>
                </td>
            </tr>
        `;
    }

    formatAreaPath(areaPath) {
        if (!areaPath) return '<span class="text-muted">-</span>';
        // Show only the last 2 segments for brevity
        const parts = areaPath.split('\\');
        if (parts.length <= 2) return areaPath;
        return parts.slice(-2).join('\\');
    }

    getDueDateClass(bug) {
        if (!bug.due_date || bug.state !== 'Active') return '';

        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const dueDate = new Date(bug.due_date);
        const diffDays = Math.floor((dueDate - today) / (1000 * 60 * 60 * 24));

        if (diffDays < 0) return 'overdue';
        if (diffDays <= 7) return 'warning';
        return 'ok';
    }

    formatDate(dateStr) {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
    }

    escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    renderPagination(totalPages) {
        if (totalPages <= 1) return '';

        let html = '';

        // Previous button
        html += `<button class="pagination-btn" data-page="${this.currentPage - 1}" ${this.currentPage === 1 ? 'disabled' : ''}>&lt;</button>`;

        // Page numbers
        const maxVisible = 5;
        let startPage = Math.max(1, this.currentPage - Math.floor(maxVisible / 2));
        let endPage = Math.min(totalPages, startPage + maxVisible - 1);

        if (endPage - startPage < maxVisible - 1) {
            startPage = Math.max(1, endPage - maxVisible + 1);
        }

        if (startPage > 1) {
            html += `<button class="pagination-btn" data-page="1">1</button>`;
            if (startPage > 2) html += `<span class="pagination-btn" style="border:none;">...</span>`;
        }

        for (let i = startPage; i <= endPage; i++) {
            html += `<button class="pagination-btn ${i === this.currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`;
        }

        if (endPage < totalPages) {
            if (endPage < totalPages - 1) html += `<span class="pagination-btn" style="border:none;">...</span>`;
            html += `<button class="pagination-btn" data-page="${totalPages}">${totalPages}</button>`;
        }

        // Next button
        html += `<button class="pagination-btn" data-page="${this.currentPage + 1}" ${this.currentPage === totalPages ? 'disabled' : ''}>&gt;</button>`;

        return html;
    }

    bindPaginationEvents() {
        const controls = document.getElementById(`${this.tableKey}-pagination-controls`);
        if (!controls) return;

        controls.querySelectorAll('.pagination-btn[data-page]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const page = parseInt(e.target.dataset.page);
                if (!isNaN(page)) {
                    this.goToPage(page);
                }
            });
        });
    }

    bindSortEvents() {
        this.container.querySelectorAll('th.sortable').forEach(th => {
            // Remove old listeners by cloning
            const newTh = th.cloneNode(true);
            th.parentNode.replaceChild(newTh, th);

            newTh.addEventListener('click', () => {
                this.sort(newTh.dataset.sort);
            });
        });
    }
}

// Export for use in other modules
window.BugTable = BugTable;
