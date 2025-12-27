/**
 * Theme Toggle System
 * Manages light/dark theme switching across all pages
 * Defaults to light mode
 */

(function() {
    'use strict';

    const THEME_STORAGE_KEY = 'fluentory-theme';
    const THEME_LIGHT = 'light';
    const THEME_DARK = 'dark';

    /**
     * Get current theme from localStorage or default to light
     */
    function getTheme() {
        const stored = localStorage.getItem(THEME_STORAGE_KEY);
        // Default to light mode if no preference is stored
        return stored || THEME_LIGHT;
    }

    /**
     * Save theme preference to localStorage
     */
    function saveTheme(theme) {
        localStorage.setItem(THEME_STORAGE_KEY, theme);
    }

    /**
     * Apply theme to document
     */
    function applyTheme(theme) {
        const html = document.documentElement;
        const body = document.body;
        
        if (theme === THEME_DARK) {
            html.setAttribute('data-theme', 'dark');
            html.classList.add('dark-theme');
            html.classList.remove('light-theme');
        } else {
            html.setAttribute('data-theme', 'light');
            html.classList.add('light-theme');
            html.classList.remove('dark-theme');
        }
        
        // Update body classes for compatibility
        body.classList.remove('theme-light', 'theme-dark');
        body.classList.add(`theme-${theme}`);
        
        // Update toggle button icons
        updateToggleIcons(theme);
    }

    /**
     * Update toggle button icons based on current theme
     */
    function updateToggleIcons(theme) {
        const lightIcon = document.querySelector('.theme-icon-light');
        const darkIcon = document.querySelector('.theme-icon-dark');
        
        if (lightIcon && darkIcon) {
            if (theme === THEME_DARK) {
                // Show sun icon (to switch to light)
                lightIcon.classList.remove('hidden');
                darkIcon.classList.add('hidden');
            } else {
                // Show moon icon (to switch to dark)
                lightIcon.classList.add('hidden');
                darkIcon.classList.remove('hidden');
            }
        }
    }

    /**
     * Toggle between light and dark themes
     */
    function toggleTheme() {
        const currentTheme = getTheme();
        const newTheme = currentTheme === THEME_LIGHT ? THEME_DARK : THEME_LIGHT;
        saveTheme(newTheme);
        applyTheme(newTheme);
    }

    /**
     * Initialize theme on page load
     */
    function initTheme() {
        const theme = getTheme();
        applyTheme(theme);
    }

    /**
     * Set up event listeners
     */
    function setupEventListeners() {
        // Theme toggle button
        const toggleBtn = document.getElementById('theme-toggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', toggleTheme);
        }

        // Listen for theme changes from other tabs/windows
        window.addEventListener('storage', function(e) {
            if (e.key === THEME_STORAGE_KEY) {
                const newTheme = e.newValue || THEME_LIGHT;
                applyTheme(newTheme);
            }
        });
    }

    /**
     * Initialize when DOM is ready
     */
    function init() {
        // Apply theme immediately to prevent flash
        initTheme();
        
        // Set up event listeners when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', setupEventListeners);
        } else {
            setupEventListeners();
        }
    }

    // Start initialization
    init();

    // Export for external use if needed
    window.FluentoryTheme = {
        toggle: toggleTheme,
        setTheme: function(theme) {
            if (theme === THEME_LIGHT || theme === THEME_DARK) {
                saveTheme(theme);
                applyTheme(theme);
            }
        },
        getTheme: getTheme
    };
})();

