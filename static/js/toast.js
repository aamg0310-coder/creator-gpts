/**
 * Toast notification system for GPT Creator.
 * Usage: showToast('Message', 'success'|'error'|'warning'|'info', duration_ms)
 */
function showToast(message, type, duration) {
    type = type || 'info';
    duration = duration || 3000;

    // Remove existing toasts
    document.querySelectorAll('.gc-toast').forEach(function(t) { t.remove(); });

    var icons = {
        success: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
        error: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" x2="9" y1="9" y2="15"/><line x1="9" x2="15" y1="9" y2="15"/></svg>',
        warning: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/></svg>',
        info: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="16" y2="12"/><line x1="12" x2="12.01" y1="8" y2="8"/></svg>'
    };

    var colors = {
        success: 'var(--success)',
        error: 'var(--error)',
        warning: 'var(--warning)',
        info: 'var(--info)'
    };

    var div = document.createElement('div');
    div.className = 'gc-toast';
    div.style.cssText = 'position:fixed;top:80px;right:20px;z-index:9999;max-width:400px;padding:12px 16px;border-radius:var(--radius-md);background:var(--bg-card);border:1px solid ' + colors[type] + ';box-shadow:var(--shadow-lg);display:flex;align-items:center;gap:10px;font-size:0.9rem;color:var(--text-primary);animation:gc-toast-in 0.3s ease;';
    div.innerHTML = '<span style="color:' + colors[type] + ';flex-shrink:0;">' + (icons[type] || icons.info) + '</span><span>' + message.replace(/</g, '&lt;') + '</span>';

    document.body.appendChild(div);

    setTimeout(function() {
        div.style.opacity = '0';
        div.style.transform = 'translateX(20px)';
        div.style.transition = 'all 0.3s ease';
        setTimeout(function() { div.remove(); }, 300);
    }, duration);
}

// Add animation keyframes
if (!document.getElementById('gc-toast-styles')) {
    var style = document.createElement('style');
    style.id = 'gc-toast-styles';
    style.textContent = '@keyframes gc-toast-in{from{opacity:0;transform:translateX(20px);}to{opacity:1;transform:translateX(0);}}';
    document.head.appendChild(style);
}
