/**
 * QuickFilter - Reusable instant search/filter system for Django admin pages
 * 
 * Features:
 * - Instant filtering on input change (with debounce)
 * - URL query param sync
 * - Loading states
 * - Empty states
 * - Pagination preservation
 * - Combined filters (AND logic)
 */

class QuickFilter {
    constructor(options) {
        this.formId = options.formId;
        this.tableContainerId = options.tableContainerId;
        this.filterControls = options.filterControls || []; // Array of { selector: '#id', param: 'name', type: 'input' | 'select' }
        this.debounceTime = options.debounceTime || 300;
        this.loadingClass = options.loadingClass || 'opacity-50 pointer-events-none';
        this.form = document.getElementById(this.formId);
        this.tableContainer = document.getElementById(this.tableContainerId);
        this.debounceTimer = null;

        if (!this.form || !this.tableContainer) {
            console.error('QuickFilter: Form or table container not found.', {
                formId: this.formId,
                tableContainerId: this.tableContainerId,
                form: this.form,
                tableContainer: this.tableContainer
            });
            return;
        }

        this.init();
    }

    init() {
        this.filterControls.forEach(control => {
            const element = this.form.querySelector(control.selector);
            if (element) {
                if (control.type === 'input') {
                    element.addEventListener('input', () => this.debounce(() => this.applyFilters()));
                } else if (control.type === 'select') {
                    element.addEventListener('change', () => this.applyFilters());
                }
            } else {
                console.warn(`QuickFilter: Control element not found for selector: ${control.selector}`);
            }
        });

        // Intercept form submission to prevent full page reload
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.applyFilters();
        });

        // Handle browser back/forward buttons
        window.addEventListener('popstate', () => {
            this.loadFiltersFromUrl();
            this.fetchResults(false); // Don't push state again
        });

        // Initial load of filters from URL on page load
        this.loadFiltersFromUrl();
    }

    debounce(func) {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            func();
        }, this.debounceTime);
    }

    getQueryParams() {
        const params = new URLSearchParams();
        this.filterControls.forEach(control => {
            const element = this.form.querySelector(control.selector);
            if (element && element.value && element.value.trim() !== '') {
                params.set(control.param, element.value);
            }
        });
        // Always reset to page 1 on filter change
        // But preserve page if it's already in URL (for pagination links)
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has('page')) {
            params.set('page', urlParams.get('page'));
        } else {
            params.set('page', '1');
        }
        return params;
    }

    applyFilters() {
        const queryParams = this.getQueryParams();
        this.updateUrl(queryParams);
        this.fetchResults();
    }

    updateUrl(queryParams) {
        const newUrl = queryParams.toString() 
            ? `${window.location.pathname}?${queryParams.toString()}`
            : window.location.pathname;
        window.history.pushState({ path: newUrl }, '', newUrl);
    }

    loadFiltersFromUrl() {
        const params = new URLSearchParams(window.location.search);
        this.filterControls.forEach(control => {
            const element = this.form.querySelector(control.selector);
            if (element && params.has(control.param)) {
                element.value = params.get(control.param);
            } else if (element) {
                // If param is not in URL, reset the control to its default (e.g., "All")
                if (control.type === 'select') {
                    element.value = ''; // Assuming default "All" option has empty value
                } else if (control.type === 'input') {
                    element.value = '';
                }
            }
        });
    }

    fetchResults(pushState = true) {
        const queryParams = this.getQueryParams();
        // Add ajax=1 parameter for Django view detection
        queryParams.set('ajax', '1');
        const url = queryParams.toString()
            ? `${window.location.pathname}?${queryParams.toString()}`
            : `${window.location.pathname}?ajax=1`;

        if (pushState) {
            // Update URL without ajax parameter for cleaner URLs
            const urlParams = this.getQueryParams();
            this.updateUrl(urlParams);
        }

        this.tableContainer.classList.add(this.loadingClass); // Show loading state

        fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest', // Indicate AJAX request
                'HX-Request': 'true' // For HTMX-like partial rendering
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.text();
        })
        .then(html => {
            this.tableContainer.innerHTML = html;
            this.tableContainer.classList.remove(this.loadingClass); // Hide loading state
            // Re-attach event listeners for pagination if needed
            this.rebindPaginationEvents();
        })
        .catch(error => {
            console.error('Error fetching filtered results:', error);
            this.tableContainer.classList.remove(this.loadingClass); // Hide loading state
            this.tableContainer.innerHTML = '<p class="text-center text-red-500 dark:text-red-400 py-12">Error loading results. Please try again.</p>';
        });
    }

    rebindPaginationEvents() {
        const paginationLinks = this.tableContainer.querySelectorAll('a[href*="page="]');
        paginationLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const url = new URL(link.href);
                const page = url.searchParams.get('page');
                if (page) {
                    const currentParams = new URLSearchParams(this.getQueryParams());
                    currentParams.set('page', page);
                    this.updateUrl(currentParams);
                    this.fetchResults(false); // Don't push state again since we just updated it
                }
            });
        });
    }

    clearFilters() {
        this.filterControls.forEach(control => {
            const element = this.form.querySelector(control.selector);
            if (element) {
                if (control.type === 'select') {
                    element.value = '';
                } else if (control.type === 'input') {
                    element.value = '';
                }
            }
        });
        this.applyFilters();
    }
}
