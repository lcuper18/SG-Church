(function () {
    const csrf = document.body.dataset.csrf;
    const badge = document.getElementById('notificationBadge');
    const count = document.getElementById('notificationCount');
    const list = document.getElementById('notificationsList');
    const dropdown = document.getElementById('notificationsDropdown');
    const markAll = document.getElementById('markAllRead');

    function escapeHtml(value) {
        const div = document.createElement('div');
        div.textContent = value == null ? '' : String(value);
        return div.innerHTML;
    }

    // Solo se aceptan enlaces relativos o http(s) para evitar javascript: en href.
    function safeLink(url) {
        return /^(\/|https?:\/\/)/.test(url || '') ? url : '#';
    }

    // Solo clases de Bootstrap Icons.
    function safeIcon(icon) {
        return /^[\w -]+$/.test(icon || '') ? icon : 'bi-bell-fill';
    }

    async function fetchCount() {
        try {
            const response = await fetch('/api/v1/notifications/unread_count/', { credentials: 'same-origin' });
            const data = await response.json();
            if (data.unread_count > 0) {
                count.textContent = data.unread_count > 9 ? '9+' : data.unread_count;
                badge.classList.remove('d-none');
            } else {
                badge.classList.add('d-none');
            }
        } catch (error) {
            console.error('Error fetching notifications:', error);
        }
    }

    async function fetchList() {
        try {
            const response = await fetch('/api/v1/notifications/', { credentials: 'same-origin' });
            const data = await response.json();
            if (!data.notifications || data.notifications.length === 0) {
                return;
            }
            list.innerHTML = data.notifications.slice(0, 5).map(function (notif) {
                const message = String(notif.message || '');
                const preview = escapeHtml(message.substring(0, 50)) + (message.length > 50 ? '...' : '');
                const date = new Date(notif.created_at).toLocaleDateString('es');
                return '<a class="dropdown-item ' + (notif.is_read ? 'opacity-50' : '') + '" href="' + escapeHtml(safeLink(notif.link)) + '">' +
                    '<div class="d-flex align-items-start">' +
                    '<i class="' + escapeHtml(safeIcon(notif.icon)) + ' me-2 mt-1" aria-hidden="true"></i>' +
                    '<div class="flex-grow-1">' +
                    '<div class="fw-medium">' + escapeHtml(notif.title) + '</div>' +
                    '<small class="text-muted">' + preview + '</small>' +
                    '<br><small class="text-muted">' + escapeHtml(date) + '</small>' +
                    '</div></div></a>';
            }).join('');
        } catch (error) {
            console.error('Error fetching notifications:', error);
            list.innerHTML = '<p class="text-center text-muted small py-3 mb-0">No se pudieron cargar las notificaciones.</p>';
        }
    }

    async function markAllRead() {
        try {
            await fetch('/api/v1/notifications/mark_all_read/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrf, 'Content-Type': 'application/json' },
                credentials: 'same-origin',
            });
            fetchCount();
            fetchList();
        } catch (error) {
            console.error('Error marking notifications as read:', error);
        }
    }

    fetchCount();
    if (dropdown) {
        dropdown.addEventListener('show.bs.dropdown', fetchList);
    }
    if (markAll) {
        markAll.addEventListener('click', markAllRead);
    }
})();
