/**
 * PLACEMENTIQ AI - Master Client-Side Utilities
 * Playbook & Bamco inspired intuitive micro-interactions, filters & toasts
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Initialize Lucide Icons if available
    if (window.lucide) {
        window.lucide.createIcons();
    }

    // 2. Global ChatGPT-Style Sidebar Toggle & Backdrop
    const toggleBtn = document.getElementById("sidebar-toggle");
    const collapseBtn = document.getElementById("sidebar-collapse-btn") || document.getElementById("sidebar-close-btn");
    const sidebar = document.querySelector(".app-sidebar");
    const backdrop = document.getElementById("sidebar-backdrop");

    function isMobileView() {
        return window.innerWidth <= 900;
    }

    function updateToggleTitle() {
        if (!collapseBtn) return;
        const isCollapsed = document.body.classList.contains("sidebar-collapsed");
        collapseBtn.setAttribute("title", isCollapsed ? "Expand Sidebar (Ctrl+B)" : "Collapse Sidebar (Ctrl+B)");
        collapseBtn.setAttribute("aria-label", isCollapsed ? "Expand sidebar" : "Collapse sidebar");
    }

    // Restore desktop collapsed preference
    if (!isMobileView()) {
        try {
            if (localStorage.getItem("glint_sidebar_collapsed") === "true" || localStorage.getItem("campuslink_sidebar_collapsed") === "true") {
                document.body.classList.add("sidebar-collapsed");
            }
        } catch (e) {
            console.warn(e);
        }
        updateToggleTitle();
    }

    function toggleAppSidebar(e) {
        if (e) e.stopPropagation();
        if (!sidebar) return;

        if (isMobileView()) {
            const isOpen = sidebar.classList.toggle("open");
            if (backdrop) {
                backdrop.classList.toggle("active", isOpen);
            }
        } else {
            const isCollapsed = document.body.classList.toggle("sidebar-collapsed");
            try {
                localStorage.setItem("glint_sidebar_collapsed", isCollapsed ? "true" : "false");
            } catch (err) {}
            updateToggleTitle();
        }
    }

    function closeAppSidebar() {
        if (!sidebar) return;
        if (isMobileView()) {
            sidebar.classList.remove("open");
            if (backdrop) backdrop.classList.remove("active");
        } else {
            document.body.classList.add("sidebar-collapsed");
            try {
                localStorage.setItem("glint_sidebar_collapsed", "true");
            } catch (err) {}
            updateToggleTitle();
        }
    }

    if (toggleBtn) {
        toggleBtn.addEventListener("click", toggleAppSidebar);
    }

    if (collapseBtn) {
        collapseBtn.addEventListener("click", toggleAppSidebar);
    }

    if (backdrop) {
        backdrop.addEventListener("click", () => {
            closeAppSidebar();
        });
    }

    // Shortcut: Ctrl+B or Cmd+B to toggle sidebar anytime
    document.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b") {
            e.preventDefault();
            toggleAppSidebar();
        } else if (e.key === "Escape") {
            closeAppSidebar();
        }
    });

    // 3. Auto-dismiss Flash Alerts after 5 seconds
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach((alert) => {
        setTimeout(() => {
            alert.style.transition = "opacity 0.5s ease, transform 0.5s ease";
            alert.style.opacity = "0";
            alert.style.transform = "translateY(-4px)";
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });

    // 4. Close role switcher menu when clicking outside
    document.addEventListener("click", (e) => {
        const menu = document.getElementById("role-dropdown-menu");
        const toggle = document.getElementById("role-switcher-toggle");
        if (menu && toggle && !toggle.contains(e.target) && !menu.contains(e.target)) {
            menu.classList.remove("show");
        }
    });
});

/**
 * Toggle Role Switcher Dropdown
 */
function toggleRoleDropdown(e) {
    if (e) e.stopPropagation();
    const menu = document.getElementById("role-dropdown-menu");
    if (menu) {
        menu.classList.toggle("show");
    }
}
window.toggleRoleDropdown = toggleRoleDropdown;

/**
 * Global Toast Notification Helper
 */
function showGlobalToast(message, iconName = "check-circle-2") {
    const toast = document.getElementById("global-toast");
    const textEl = document.getElementById("global-toast-text");
    if (toast && textEl) {
        textEl.innerText = message;
        toast.classList.add("show");
        if (window.lucide) {
            window.lucide.createIcons();
        }
        setTimeout(() => {
            toast.classList.remove("show");
        }, 4500);
    }
}
window.showGlobalToast = showGlobalToast;

/**
 * Quick fill helper for 1-Click demo logins
 */
function fillDemoAccount(email, password) {
    const emailField = document.getElementById("email");
    const passField = document.getElementById("password");
    if (emailField && passField) {
        emailField.value = email;
        passField.value = password;
        emailField.focus();
        showGlobalToast(`Filled demo credentials for ${email}`);
    }
}
window.fillDemoAccount = fillDemoAccount;
