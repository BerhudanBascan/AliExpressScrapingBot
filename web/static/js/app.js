/**
 * AliExpress Dropshipping Pro - Frontend JavaScript
 * Tema yönetimi, toast sistemi, genel yardımcılar
 */

document.addEventListener('DOMContentLoaded', function () {
    initTheme();
    initSidebar();
});

/* ==========================================
   THEME MANAGEMENT
   ========================================== */
function initTheme() {
    const saved = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
    updateThemeIcon(saved);

    const toggle = document.getElementById('themeToggle');
    if (toggle) {
        toggle.addEventListener('click', function () {
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
            updateThemeIcon(next);
        });
    }
}

function updateThemeIcon(theme) {
    const btn = document.getElementById('themeToggle');
    if (btn) {
        const icon = btn.querySelector('i');
        icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
}

/* ==========================================
   SIDEBAR
   ========================================== */
function initSidebar() {
    const toggle = document.getElementById('sidebarToggle');
    const mobile = document.getElementById('mobileToggle');
    const sidebar = document.getElementById('sidebar');

    if (toggle) {
        toggle.addEventListener('click', function () {
            sidebar.classList.toggle('collapsed');
            document.body.classList.toggle('sidebar-collapsed');
        });
    }

    if (mobile) {
        mobile.addEventListener('click', function () {
            sidebar.classList.toggle('open');
        });

        // Dışına tıklayınca kapat
        document.addEventListener('click', function (e) {
            if (sidebar.classList.contains('open') &&
                !sidebar.contains(e.target) &&
                !mobile.contains(e.target)) {
                sidebar.classList.remove('open');
            }
        });
    }
}

/* ==========================================
   TOAST NOTIFICATION SYSTEM
   ========================================== */
function showToast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const icons = {
        success: 'fa-check-circle',
        error: 'fa-times-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i class="fas ${icons[type] || icons.info}"></i>
        <span>${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;

    container.appendChild(toast);

    // Otomatik kaldır
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(50px)';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

/* ==========================================
   UTILITY FUNCTIONS
   ========================================== */

// Formatlanmış tarih
function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('tr-TR', {
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit'
    });
}

// Dosya boyutu formatla
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + sizes[i];
}

// API çağrısı yardımcısı
async function apiCall(url, method = 'GET', data = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' }
    };
    if (data) options.body = JSON.stringify(data);

    try {
        const response = await fetch(url, options);
        return await response.json();
    } catch (error) {
        showToast('Bağlantı hatası: ' + error.message, 'error');
        return { success: false, error: error.message };
    }
}

// Confirm dialog
function confirmAction(message) {
    return window.confirm(message);
}

// Sayıyı kısalt (1000 -> 1K)
function abbreviateNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

console.log('%c🚀 DropShipPro Dashboard', 'font-size:18px;font-weight:bold;color:#667eea;');
console.log('%cPowered by AliExpress Dropshipping Pro', 'font-size:12px;color:#a0aec0;');
