/**
 * CSRF helper for GPT Creator.
 * Provides consistent CSRF token retrieval for all fetch calls.
 */
function getCsrfToken() {
    // 1. Try meta tag
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute('content');

    // 2. Try cookie
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
        var c = cookies[i].trim();
        if (c.startsWith('csrftoken=')) {
            return decodeURIComponent(c.substring(10));
        }
    }

    // 3. Try hidden input
    var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (input) return input.value;

    // 4. Try template variable (fallback)
    if (typeof csrfToken !== 'undefined' && csrfToken) return csrfToken;

    return '';
}

/**
 * Wrapper around fetch that includes CSRF token automatically.
 */
function csrfFetch(url, options) {
    options = options || {};
    options.credentials = options.credentials || 'same-origin';
    options.headers = options.headers || {};

    if (options.method && options.method.toUpperCase() !== 'GET') {
        if (options.headers instanceof Headers) {
            options.headers.set('X-CSRFToken', getCsrfToken());
        } else {
            options.headers['X-CSRFToken'] = getCsrfToken();
        }
    }

    return fetch(url, options);
}
