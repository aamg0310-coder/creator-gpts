/**
 * Markdown renderer for chat messages.
 * Uses marked.js + highlight.js for code blocks.
 */
function renderMarkdown(text) {
    if (!text) return '';

    // Security: escape HTML first to prevent XSS from raw markdown
    let escaped = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Configure marked with syntax highlighting
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            gfm: true,
            breaks: true,
            headerIds: false,
            mangle: false,
            highlight: function(code, lang) {
                if (lang && typeof hljs !== 'undefined' && hljs.getLanguage && hljs.getLanguage(lang)) {
                    return hljs.highlight(code, { language: lang }).value;
                }
                if (typeof hljs !== 'undefined' && hljs.highlightAuto) {
                    return hljs.highlightAuto(code).value;
                }
                return code;
            }
        });
        return marked.parse(escaped);
    }

    // Fallback if marked not loaded
    return escaped.replace(/\n/g, '<br>');
}

/**
 * Render streaming tokens incrementally.
 * Keeps a buffer and renders full markdown on each append.
 */
class MarkdownStreamRenderer {
    constructor(element) {
        this.element = element;
        this.buffer = '';
    }

    appendToken(token) {
        this.buffer += token;
        if (this.element) {
            this.element.innerHTML = renderMarkdown(this.buffer);
        }
    }

    reset() {
        this.buffer = '';
        if (this.element) {
            this.element.innerHTML = '';
        }
    }

    getBuffer() {
        return this.buffer;
    }
}
