/**
 * GPT Creator — Chatbot Editor
 * Handles creation, editing, and chat preview.
 */

class ChatbotEditor {
  constructor(options = {}) {
    this.mode = options.mode || 'create'; // 'create' or 'edit'
    this.slug = options.slug || null;
    this.csrfToken = options.csrfToken || '';
    this.apiBase = '/api/chatbots/';
    this.chatbotData = {};

    // DOM elements
    this.form = document.getElementById('chatbot-form');
    this.previewIcon = document.getElementById('preview-icon');
    this.previewIcon2 = document.getElementById('preview-icon-2');
    this.previewName = document.getElementById('preview-name');
    this.previewModel = document.getElementById('preview-model');
    this.previewTier = document.getElementById('preview-tier');
    this.previewVisibility = document.getElementById('preview-visibility');
    this.chatMessages = document.getElementById('preview-chat-messages');
    this.chatInput = document.getElementById('preview-chat-input');
    this.saveBtn = document.getElementById('save-btn');

    this.init();
  }

  init() {
    this.bindFormEvents();
    this.bindIconFile();
    this.bindModelSelector();
    this.bindVisibilityToggle();
    this.bindSectionToggles();
    this.bindChatInput();

    if (this.mode === 'edit' && this.slug) {
      this.loadChatbot();
    } else {
      this.updatePreview();
    }
  }

  // ── Form Events ──────────────────────────────────────────────────────
  bindFormEvents() {
    if (!this.form) return;

    // Real-time preview updates
    const fields = ['nombre', 'descripcion', 'modelo', 'soul', 'instructions', 'funciones', 'suggestions'];
    fields.forEach(field => {
      const el = this.form.querySelector(`[name="${field}"]`);
      if (el) {
        el.addEventListener('input', () => this.updatePreview());
      }
    });

    // Save button
    if (this.saveBtn) {
      this.saveBtn.addEventListener('click', (e) => {
        e.preventDefault();
        this.save();
      });
    }
  }

  // ── Icon File Preview ─────────────────────────────────────────────────
  bindIconFile() {
    const input = this.form ? this.form.querySelector('[name="icon"]') : null;
    if (!input) return;
    input.addEventListener('change', () => {
      const file = input.files && input.files[0];
      if (file && this.previewIcon) {
        const url = URL.createObjectURL(file);
        this.previewIcon.innerHTML = `<img src="${url}" style="max-height:32px;border-radius:50%;object-fit:cover;">`;
        if (this.previewIcon2) {
          this.previewIcon2.innerHTML = `<img src="${url}" style="max-height:32px;border-radius:50%;object-fit:cover;">`;
        }
      }
      this.updatePreview();
    });
  }

  // ── Model Selector ───────────────────────────────────────────────────
  bindModelSelector() {
    const grid = document.getElementById('model-grid');
    if (!grid) return;

    grid.querySelectorAll('.model-option').forEach(option => {
      option.addEventListener('click', () => {
        grid.querySelectorAll('.model-option').forEach(o => o.classList.remove('selected'));
        option.classList.add('selected');
        const input = this.form.querySelector('[name="modelo"]');
        if (input) input.value = option.dataset.model;
        this.updatePreview();
      });
    });
  }

  // ── Visibility Toggle ────────────────────────────────────────────────
  bindVisibilityToggle() {
    const toggle = document.getElementById('visibility-toggle');
    if (!toggle) return;

    toggle.querySelectorAll('.visibility-option').forEach(option => {
      option.addEventListener('click', () => {
        toggle.querySelectorAll('.visibility-option').forEach(o => o.classList.remove('selected'));
        option.classList.add('selected');
        const input = this.form.querySelector('[name="is_public"]');
        if (input) input.value = option.dataset.public;
        this.updatePreview();
      });
    });
  }

  // ── Section Toggles ──────────────────────────────────────────────────
  bindSectionToggles() {
    document.querySelectorAll('.editor-section-header').forEach(header => {
      header.addEventListener('click', (e) => {
        // Don't toggle if clicking the edit button
        if (e.target.closest('.section-edit-btn')) return;

        const body = header.nextElementSibling;
        const icon = header.querySelector('.toggle-icon');
        if (body) body.classList.toggle('hidden');
        if (icon) icon.classList.toggle('collapsed');
        header.classList.toggle('collapsed');
      });
    });
  }

  // ── Chat Input ───────────────────────────────────────────────────────
  bindChatInput() {
    if (!this.chatInput) return;

    this.chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendTestMessage();
      }
    });

    const sendBtn = document.getElementById('preview-send-btn');
    if (sendBtn) {
      sendBtn.addEventListener('click', () => this.sendTestMessage());
    }
  }

  // ── Update Preview ───────────────────────────────────────────────────
  updatePreview() {
    if (!this.form) return;

    const getData = (name) => {
      const el = this.form.querySelector(`[name="${name}"]`);
      return el ? el.value : '';
    };

    // Icon
    const updateIconEl = (el) => {
      if (!el) return;
      const iconVal = getData('icon');
      if (iconVal && typeof iconVal === 'string' && (iconVal.includes('/') || iconVal.includes('.')) && iconVal !== '🤖') {
        el.innerHTML = `<img src="${iconVal}" style="max-height:32px;border-radius:50%;object-fit:cover;">`;
      } else {
        el.textContent = getData('icon') || '🤖';
      }
    };
    
    updateIconEl(this.previewIcon);
    updateIconEl(this.previewIcon2);

    // Name
    if (this.previewName) {
      this.previewName.textContent = getData('nombre') || 'Tu Chatbot';
    }

    // Model
    const modelo = getData('modelo');
    const selectedOption = this.form.querySelector(`.model-option[data-model="${modelo}"]`);
    if (this.previewModel && selectedOption) {
      this.previewModel.textContent = selectedOption.querySelector('.model-name').textContent;
    }

    // Tier
    if (this.previewTier) {
      const isFree = selectedOption?.dataset.tier === 'free';
      this.previewTier.textContent = isFree ? 'Gratis' : 'Pago';
      this.previewTier.className = `model-tier-badge ${isFree ? 'free' : 'paid'}`;
    }

    // Visibility
    if (this.previewVisibility) {
      const isPublic = getData('is_public') === 'true';
      this.previewVisibility.textContent = isPublic ? '🌐 Público' : '🔒 Privado';
    }
  }

  // ── Load Chatbot (Edit Mode) ─────────────────────────────────────────
  async loadChatbot() {
    try {
      const response = await fetch(`${this.apiBase}${this.slug}/`);
      if (!response.ok) throw new Error('Error loading chatbot');
      this.chatbotData = await response.json();
      this.populateForm(this.chatbotData);
      this.updatePreview();
    } catch (err) {
      console.error('Error loading chatbot:', err);
      this.showNotification('Error al cargar el chatbot', 'error');
    }
  }

  // ── Populate Form ────────────────────────────────────────────────────
  populateForm(data) {
    const fields = ['nombre', 'icon', 'descripcion', 'modelo', 'soul', 'instructions', 'funciones', 'suggestions'];
    fields.forEach(field => {
      const el = this.form.querySelector(`[name="${field}"]`);
      if (el && data[field] !== undefined) {
        el.value = data[field];
      }
    });

    // Icon: if it's a URL/path from server, show image in preview; else emoji
    if (data.icon) {
      if (this.previewIcon || this.previewIcon2) {
        if (typeof data.icon === 'string' && (data.icon.includes('/') || data.icon.includes('.')) && data.icon !== '🤖') {
          const imgHtml = `<img src="${data.icon}" style="max-height:32px;border-radius:50%;object-fit:cover;">`;
          if (this.previewIcon) this.previewIcon.innerHTML = imgHtml;
          if (this.previewIcon2) this.previewIcon2.innerHTML = imgHtml;
        } else {
          if (this.previewIcon) this.previewIcon.textContent = data.icon;
          if (this.previewIcon2) this.previewIcon2.textContent = data.icon;
        }
      }
    }

    // Model selection
    if (data.modelo) {
      const modelOption = document.querySelector(`.model-option[data-model="${data.modelo}"]`);
      if (modelOption) {
        document.querySelectorAll('.model-option').forEach(o => o.classList.remove('selected'));
        modelOption.classList.add('selected');
      }
    }

    // Visibility
    const visOption = document.querySelector(`.visibility-option[data-public="${data.is_public}"]`);
    if (visOption) {
      document.querySelectorAll('.visibility-option').forEach(o => o.classList.remove('selected'));
      visOption.classList.add('selected');
    }
  }

  // ── Save ─────────────────────────────────────────────────────────────
  async save() {
    if (!this.form) return;

    const nombre = this.form.querySelector('[name="nombre"]')?.value?.trim();
    if (!nombre) {
      this.showNotification('El nombre es obligatorio', 'error');
      return;
    }

    this.setSaving(true);

    const iconInput = this.form.querySelector('[name="icon"]');
    const docInput = this.form.querySelector('[name="documents"]');
    const hasNewIcon = iconInput && iconInput.files.length > 0;
    const hasNewDocs = docInput && docInput.files.length > 0;
    const hasFiles = hasNewIcon || hasNewDocs;

    try {
      const url = this.mode === 'edit' && this.slug
        ? `${this.apiBase}${this.slug}/`
        : this.apiBase;

      const method = this.mode === 'edit' ? 'PUT' : 'POST';

      if (hasFiles) {
        const formData = new FormData(this.form);
        // Only send icon if user selected a new file
        if (!hasNewIcon) formData.delete('icon');
        // Only send documents if user selected new files
        if (!hasNewDocs) formData.delete('documents');
        // Always remove is_public from FormData (handled separately)
        formData.delete('is_public');
        formData.append('is_public', this.form.querySelector('[name="is_public"]')?.value || 'false');

        const response = await fetch(url, {
          method,
          headers: {
            'X-CSRFToken': this.csrfToken,
          },
          body: formData,
        });
        if (!response.ok) {
          const err = await response.json();
          throw new Error(err.detail || JSON.stringify(err));
        }
        const result = await response.json();
        this.chatbotData = result;
        this.slug = result.slug;
        this.showNotification('Chatbot guardado correctamente.', 'success');
      } else {
        // No files — send JSON
        const data = {};
        data.nombre = nombre;
        data.descripcion = this.form.querySelector('[name="descripcion"]')?.value || '';
        data.modelo = this.form.querySelector('[name="modelo"]')?.value || '';
        data.soul = this.form.querySelector('[name="soul"]')?.value || '';
        data.instructions = this.form.querySelector('[name="instructions"]')?.value || '';
        data.is_public = this.form.querySelector('[name="is_public"]')?.value === 'true';

        // Collect funciones checkboxes
        const funcChecks = this.form.querySelectorAll('[name="funciones"]:checked');
        data.funciones = Array.from(funcChecks).map(cb => cb.value);

        // IMPORTANT: Do NOT send 'icon' field when no new file is selected.
        // Sending icon: "" tells DRF to clear the existing image.

        const response = await fetch(url, {
          method,
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.csrfToken,
          },
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          const err = await response.json();
          throw new Error(err.detail || JSON.stringify(err));
        }

        const result = await response.json();
        this.chatbotData = result;
        this.slug = result.slug;
      }

      this.showNotification(
        this.mode === 'edit' ? 'Chatbot actualizado' : 'Chatbot creado',
        'success'
      );

      // Update URL for create mode
      if (this.mode === 'create') {
        this.mode = 'edit';
        window.history.replaceState({}, '', `/editar-chatbot/${result.slug}/`);
      }
    } catch (err) {
      console.error('Error saving:', err);
      this.showNotification(`Error: ${err.message}`, 'error');
    } finally {
      this.setSaving(false);
    }
  }

  // ── Send Test Message ────────────────────────────────────────────────
  async sendTestMessage() {
    if (!this.chatInput) return;
    const question = this.chatInput.value.trim();
    if (!question) return;

    // Show user message
    this.addChatMessage(question, 'user');
    this.chatInput.value = '';

    // Show loading
    const loadingId = this.addChatMessage('Pensando...', 'assistant', true);

    try {
      let answer;

      if (this.mode === 'edit' && this.slug) {
        // Use real API if chatbot is saved
        const response = await fetch(`/api/chatbots/${this.slug}/ask/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.csrfToken,
          },
          body: JSON.stringify({ question }),
        });

        if (!response.ok) throw new Error('Error en la API');
        const data = await response.json();
        answer = data.answer;
      } else {
        // Simulate response for unsaved chatbot
        await new Promise(resolve => setTimeout(resolve, 1000));
        answer = '💡 Guarda tu chatbot primero para probarlo con la API real. ' +
                 'Haz clic en "Guardar" y luego podrás conversar aquí.';
      }

      this.removeChatMessage(loadingId);
      this.addChatMessage(answer, 'assistant');
    } catch (err) {
      this.removeChatMessage(loadingId);
      this.addChatMessage('Error al conectar. Intenta de nuevo.', 'assistant');
    }
  }

  // ── Chat Helpers ─────────────────────────────────────────────────────
  addChatMessage(text, role, isLoading = false) {
    if (!this.chatMessages) return null;

    const id = 'msg-' + Date.now();
    const div = document.createElement('div');
    div.className = `chat-message ${role}`;
    div.id = id;

    const icon = role === 'user' ? '👤' : (this.chatbotData.icon || '🤖');
    div.innerHTML = `
      <div class="chat-avatar">${icon}</div>
      <div class="chat-bubble ${isLoading ? 'loading' : ''}">${role === 'assistant' ? (typeof renderMarkdown !== 'undefined' ? renderMarkdown(text) : text.replace(/\n/g, '<br>')) : text.replace(/</g, '&lt;').replace(/\n/g, '<br>')}</div>
    `;

    this.chatMessages.appendChild(div);
    this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    return id;
  }

  removeChatMessage(id) {
    if (!id) return;
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  // ── UI Helpers ───────────────────────────────────────────────────────
  setSaving(saving) {
    if (!this.saveBtn) return;
    this.saveBtn.disabled = saving;
    this.saveBtn.classList.toggle('saving', saving);
    this.saveBtn.textContent = saving ? 'Guardando...' : 'Guardar';
  }

  showNotification(message, type = 'info') {
    // Remove existing notifications
    document.querySelectorAll('.editor-notification').forEach(n => n.remove());

    const div = document.createElement('div');
    div.className = `alert alert-${type} editor-notification`;
    div.textContent = message;
    div.style.position = 'fixed';
    div.style.top = '100px';
    div.style.right = '20px';
    div.style.zIndex = '1000';
    div.style.maxWidth = '400px';
    div.style.animation = 'fadeInUp 0.3s ease';

    document.body.appendChild(div);

    setTimeout(() => {
      div.style.opacity = '0';
      div.style.transform = 'translateY(-10px)';
      div.style.transition = 'all 0.3s ease';
      setTimeout(() => div.remove(), 300);
    }, 3000);
  }
}

// ── Initialize on DOM Ready ────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const editorEl = document.getElementById('chatbot-editor');
  if (editorEl) {
    window.chatbotEditor = new ChatbotEditor({
      mode: editorEl.dataset.mode || 'create',
      slug: editorEl.dataset.slug || null,
      csrfToken: editorEl.dataset.csrf || '',
    });

    // In create mode, all sections start enabled
    if (editorEl.dataset.mode === 'create') {
      document.querySelectorAll('.editor-section-body').forEach(body => {
        body.classList.add('editing');
      });
      document.querySelectorAll('.section-edit-btn').forEach(btn => {
        btn.style.display = 'none';
      });
    }
  }
});
