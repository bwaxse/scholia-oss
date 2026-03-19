/**
 * Settings page - allows users to configure Zotero credentials and Notion integration
 * Terracotta design system
 */

import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { authService, type AuthState } from '../services/auth';

interface ZoteroConfig {
  configured: boolean;
  library_id?: string;
  library_type?: string;
}

interface NotionConfig {
  configured: boolean;
  workspace_name?: string;
  workspace_id?: string;
}

@customElement('settings-page')
export class SettingsPage extends LitElement {
  @state() private authState: AuthState = {
    isAuthenticated: true,
    isLoading: false,
    user: null
  };

  @state() private zoteroConfig: ZoteroConfig = { configured: false };
  @state() private notionConfig: NotionConfig = { configured: false };
  @state() private saving = false;
  @state() private savingNotion = false;
  @state() private error = '';
  @state() private success = '';

  // Form fields
  @state() private apiKey = '';
  @state() private libraryId = '';
  @state() private libraryType = 'user';
  @state() private returnTo = '/';

  connectedCallback() {
    super.connectedCallback();
    authService.subscribe((state) => {
      this.authState = state;
    });

    // Read returnTo query parameter
    const params = new URLSearchParams(window.location.search);
    this.returnTo = params.get('returnTo') || '/';

    this.loadZoteroConfig();
    this.loadNotionConfig();
  }

  firstUpdated() {
    // Scroll to anchor if hash present in URL
    const hash = window.location.hash;
    if (hash) {
      setTimeout(() => {
        const element = this.shadowRoot?.querySelector(hash);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 100);
    }
  }

  static styles = css`
    :host {
      display: block;
      min-height: 100vh;
      background: var(--bg, #fdfaf8);
      color: var(--text, #3d2f2a);
      font-family: var(--sans, 'Lora', Georgia, serif);
    }

    /* Header - Glassmorphism */
    header {
      position: sticky;
      top: 0;
      z-index: 100;
      background: rgba(253, 250, 248, 0.9);
      backdrop-filter: blur(20px);
      border-bottom: 1px solid var(--border, #e8dfd9);
    }

    .header-inner {
      max-width: 1000px;
      margin: 0 auto;
      padding: 0.875rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .logo {
      display: flex;
      align-items: center;
      gap: 8px;
      font-family: var(--serif, Georgia, 'Times New Roman', serif);
      font-size: 1.25rem;
      font-weight: 500;
      text-decoration: none;
      color: var(--text, #3d2f2a);
    }

    .logo img {
      height: 20px;
      width: auto;
    }

    .back-link {
      color: var(--text-secondary, #6b574f);
      text-decoration: none;
      font-size: 0.875rem;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 0.25rem;
      transition: color 0.15s;
    }

    .back-link:hover {
      color: var(--text, #3d2f2a);
    }

    .container {
      max-width: 600px;
      margin: 0 auto;
      padding: 3rem 2rem;
    }

    h1 {
      font-family: var(--serif, Georgia, 'Times New Roman', serif);
      font-size: 1.875rem;
      font-weight: 400;
      margin: 0 0 2rem 0;
      color: var(--text, #3d2f2a);
    }

    .section {
      background: var(--bg-card, #ffffff);
      border: 1px solid var(--border, #e8dfd9);
      border-radius: 8px;
      padding: 1.5rem;
      margin-bottom: 1.5rem;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }

    .section h2 {
      font-family: var(--serif, Georgia, 'Times New Roman', serif);
      font-size: 1.25rem;
      font-weight: 600;
      margin: 0 0 0.75rem 0;
      color: var(--text, #3d2f2a);
    }

    .section p {
      color: var(--text-secondary, #6b574f);
      font-size: 0.875rem;
      margin: 0 0 1.25rem 0;
      line-height: 1.6;
    }

    .section a {
      color: var(--accent-warm, #a64b2d);
    }

    .user-info {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .user-details {
      flex: 1;
    }

    .user-name {
      font-weight: 600;
      margin-bottom: 0.25rem;
      color: var(--text, #3d2f2a);
    }

    .user-email {
      color: var(--text-secondary, #6b574f);
      font-size: 0.875rem;
    }

    .form-field {
      margin-bottom: 1rem;
    }

    .form-field label {
      display: block;
      margin-bottom: 0.375rem;
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--text, #3d2f2a);
    }

    .form-field input,
    .form-field select {
      width: 100%;
      padding: 0.625rem 0.75rem;
      border: 1px solid var(--border, #e8dfd9);
      border-radius: 6px;
      font-size: 0.875rem;
      font-family: inherit;
      box-sizing: border-box;
      background: var(--bg-card, #ffffff);
      color: var(--text, #3d2f2a);
      transition: border-color 0.15s;
    }

    .form-field input:focus,
    .form-field select:focus {
      outline: none;
      border-color: var(--accent, #c45d3a);
    }

    .form-field input::placeholder {
      color: var(--text-muted, #a08a80);
    }

    .form-field .hint {
      margin-top: 0.375rem;
      font-size: 0.75rem;
      color: var(--text-muted, #a08a80);
      line-height: 1.5;
    }

    .current-config {
      background: var(--bg-warm, #f9f3ef);
      border-radius: 6px;
      padding: 0.75rem 1rem;
      margin-bottom: 1rem;
      font-size: 0.8125rem;
      color: var(--text-secondary, #6b574f);
    }

    .current-config strong {
      color: var(--text, #3d2f2a);
    }

    .permissions-box {
      background: var(--bg-warm, #f9f3ef);
      border-radius: 6px;
      padding: 0.75rem 1rem;
      margin: 1rem 0;
      font-size: 0.8125rem;
    }

    .permissions-box strong {
      color: var(--text, #3d2f2a);
    }

    .permissions-box ul {
      margin: 0.5rem 0;
      padding-left: 1.25rem;
      color: var(--text-secondary, #6b574f);
    }

    .permissions-box li {
      margin-bottom: 0.25rem;
    }

    .permissions-box p {
      margin: 0.5rem 0 0 0;
      color: var(--text-muted, #a08a80);
      font-size: 0.8125rem;
    }

    .btn {
      padding: 0.625rem 1.25rem;
      border-radius: 6px;
      font-size: 0.875rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
      border: none;
      font-family: inherit;
    }

    .btn-primary {
      background: var(--text, #3d2f2a);
      color: white;
    }

    .btn-primary:hover {
      background: #2d211c;
    }

    .btn-primary:disabled {
      background: var(--text-muted, #a08a80);
      cursor: not-allowed;
    }

    .btn-secondary {
      background: var(--bg-card, #ffffff);
      color: var(--text-secondary, #6b574f);
      border: 1px solid var(--border, #e8dfd9);
    }

    .btn-secondary:hover {
      background: var(--bg-warm, #f9f3ef);
    }

    .btn-secondary:disabled {
      background: #e5ddd8;
      color: var(--text-muted, #a08a80);
      border-color: #d4ccc3;
      cursor: not-allowed;
    }

    .btn-danger {
      background: var(--bg-card, #ffffff);
      color: #c44b3a;
      border: 1px solid #c44b3a;
    }

    .btn-danger:hover {
      background: #fef2f0;
    }

    .button-row {
      display: flex;
      gap: 0.75rem;
      margin-top: 1.25rem;
    }

    .message {
      padding: 0.75rem 1rem;
      border-radius: 6px;
      margin-bottom: 1rem;
      font-size: 0.875rem;
    }

    .message.error {
      background: #fef2f0;
      color: #c44b3a;
      border: 1px solid rgba(196, 75, 58, 0.2);
    }

    .message.success {
      background: #f0f7f1;
      color: #5a8a5c;
      border: 1px solid rgba(90, 138, 92, 0.2);
    }

    @media (max-width: 600px) {
      .header-inner {
        padding: 0.75rem 1rem;
      }

      .container {
        padding: 1.5rem 1rem;
      }

      h1 {
        font-size: 1.5rem;
      }
    }
  `;

  private async loadZoteroConfig() {
    try {
      const response = await fetch('/api/settings/zotero');
      if (response.ok) {
        this.zoteroConfig = await response.json();
        if (this.zoteroConfig.library_id) {
          this.libraryId = this.zoteroConfig.library_id;
        }
        if (this.zoteroConfig.library_type) {
          this.libraryType = this.zoteroConfig.library_type;
        }
      }
    } catch (err) {
      console.error('Failed to load Zotero config:', err);
    }
  }

  private async handleSaveZotero() {
    if (!this.apiKey || !this.libraryId) {
      this.error = 'Please fill in all required fields';
      return;
    }

    this.saving = true;
    this.error = '';
    this.success = '';

    try {
      const response = await fetch('/api/settings/zotero', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: this.apiKey,
          library_id: this.libraryId,
          library_type: this.libraryType
        })
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to save settings');
      }

      this.zoteroConfig = await response.json();
      this.apiKey = ''; // Clear API key from form
      this.success = 'Zotero credentials saved successfully!';
    } catch (err) {
      this.error = err instanceof Error ? err.message : 'Failed to save settings';
    } finally {
      this.saving = false;
    }
  }

  private async handleRemoveZotero() {
    if (!confirm('Are you sure you want to remove your Zotero credentials?')) {
      return;
    }

    this.saving = true;
    this.error = '';
    this.success = '';

    try {
      const response = await fetch('/api/settings/zotero', {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error('Failed to remove Zotero credentials');
      }

      this.zoteroConfig = { configured: false };
      this.libraryId = '';
      this.success = 'Zotero credentials removed';
    } catch (err) {
      this.error = err instanceof Error ? err.message : 'Failed to remove settings';
    } finally {
      this.saving = false;
    }
  }

  private async loadNotionConfig() {
    try {
      const response = await fetch('/api/settings/notion');
      if (response.ok) {
        this.notionConfig = await response.json();
      }
    } catch (err) {
      console.error('Failed to load Notion config:', err);
    }
  }

  private async handleConnectNotion() {
    this.savingNotion = true;
    this.error = '';
    this.success = '';

    try {
      // Get the OAuth URL
      const response = await fetch('/api/notion/auth-url');
      if (!response.ok) {
        throw new Error('Failed to get Notion authorization URL');
      }

      const data = await response.json();

      // Redirect to Notion OAuth
      window.location.href = data.auth_url;
    } catch (err) {
      this.error = err instanceof Error ? err.message : 'Failed to connect to Notion';
      this.savingNotion = false;
    }
  }

  private async handleRemoveNotion() {
    if (!confirm('Are you sure you want to disconnect your Notion workspace?')) {
      return;
    }

    this.savingNotion = true;
    this.error = '';
    this.success = '';

    try {
      const response = await fetch('/api/settings/notion', {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error('Failed to remove Notion credentials');
      }

      this.notionConfig = { configured: false };
      this.success = 'Notion workspace disconnected';
    } catch (err) {
      this.error = err instanceof Error ? err.message : 'Failed to remove Notion connection';
    } finally {
      this.savingNotion = false;
    }
  }

  render() {
    const user = this.authState.user;

    return html`
      <header>
        <div class="header-inner">
          <a href="/" class="logo">
            <img src="/logo_small.png?v=2" alt="Scholia" />
            Scholia
          </a>
          <a href="${this.returnTo}" class="back-link">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
            ${this.returnTo === '/' ? 'Back to app' : 'Back to session'}
          </a>
        </div>
      </header>

      <div class="container">
        <h1>Settings</h1>

        ${this.error ? html`<div class="message error">${this.error}</div>` : ''}
        ${this.success ? html`<div class="message success">${this.success}</div>` : ''}

        <!-- Account Section -->
        <div class="section" id="account">
          <h2>Account</h2>
          ${user ? html`
            <div class="user-info">
              <div class="user-details">
                <div class="user-name">${user.name}</div>
                <div class="user-email">${user.email}</div>
              </div>
            </div>
          ` : html`<p>Loading...</p>`}
        </div>

        <!-- Zotero Section -->
        <div class="section" id="zotero">
          <h2>Zotero Integration</h2>
          <p>
            Connect your Zotero library to load papers directly. Visit
            <a href="https://www.zotero.org/settings/keys/new" target="_blank">Zotero settings</a>
            to create a new API key with the following permissions:
          </p>

          <div class="permissions-box">
            <strong>Required permissions for Personal Library:</strong>
            <ul>
              <li>&#10003; Allow library access</li>
              <li>&#10003; Allow notes access</li>
              <li>&#10003; Allow write access</li>
            </ul>
            <p>
              After clicking "Save Key", copy the API key immediately (it's only shown once!).
            </p>
          </div>

          ${this.zoteroConfig.configured ? html`
            <div class="current-config">
              <strong>Currently configured:</strong> Library ${this.zoteroConfig.library_id} (${this.zoteroConfig.library_type})
            </div>
          ` : ''}

          <div class="form-field">
            <label>API Key *</label>
            <input
              type="password"
              .value=${this.apiKey}
              @input=${(e: Event) => this.apiKey = (e.target as HTMLInputElement).value}
              placeholder="${this.zoteroConfig.configured ? 'Enter new API key to update' : 'Paste your Zotero API key'}"
            />
          </div>

          <div class="form-field">
            <label>Library ID *</label>
            <input
              type="text"
              .value=${this.libraryId}
              @input=${(e: Event) => this.libraryId = (e.target as HTMLInputElement).value}
              placeholder="Your numeric library ID"
            />
            <div class="hint">
              <strong>Personal Library:</strong> Visit <a href="https://www.zotero.org/settings/security" target="_blank" rel="noopener">zotero.org/settings/security</a> and find your User ID in the Applications section. It will look like: "Your user ID for use in API calls is 1234567"<br>
              <strong>Group Library:</strong> Copy the numeric part from your group URL (e.g., zotero.org/groups/<strong>6266196</strong>/group-name)
            </div>
          </div>

          <div class="form-field">
            <label>Library Type</label>
            <select
              .value=${this.libraryType}
              @change=${(e: Event) => this.libraryType = (e.target as HTMLSelectElement).value}
            >
              <option value="user">Personal Library</option>
              <option value="group">Group Library</option>
            </select>
            <div class="hint" style="color: rgb(136, 136, 136); margin-top: 8px;">
              <strong>Note:</strong> Scholia can only access one library at a time (either personal or group, not both).
            </div>
          </div>

          <div class="button-row">
            <button
              class="btn btn-primary"
              ?disabled=${this.saving}
              @click=${this.handleSaveZotero}
            >
              ${this.saving ? 'Saving...' : (this.zoteroConfig.configured ? 'Update Credentials' : 'Save Credentials')}
            </button>
            ${this.zoteroConfig.configured ? html`
              <button
                class="btn btn-danger"
                ?disabled=${this.saving}
                @click=${this.handleRemoveZotero}
              >
                Remove
              </button>
            ` : ''}
          </div>
        </div>

        <!-- Notion Section -->
        <div class="section" id="notion">
          <h2>Notion Integration</h2>
          <p>
            Connect your Notion workspace to export paper analyses directly to your research projects.
          </p>

          ${this.notionConfig.configured ? html`
            <div class="current-config">
              <strong>Connected workspace:</strong> ${this.notionConfig.workspace_name || 'Notion'}
            </div>

            <p style="font-size: 13px; color: #666; margin: 16px 0;">
              Your Notion workspace is connected. You can now export paper analyses to your Notion pages from the Concepts tab.
            </p>

            <div class="button-row">
              <button
                class="btn btn-danger"
                ?disabled=${this.savingNotion}
                @click=${this.handleRemoveNotion}
              >
                ${this.savingNotion ? 'Disconnecting...' : 'Disconnect Notion'}
              </button>
            </div>
          ` : html`
            <p style="font-size: 13px; color: #666; margin: 16px 0;">
              Click the button below to connect your Notion workspace. You'll be redirected to Notion to authorize Scholia to access your pages.
            </p>

            <div class="button-row">
              <button
                class="btn btn-primary"
                ?disabled=${this.savingNotion}
                @click=${this.handleConnectNotion}
              >
                ${this.savingNotion ? 'Connecting...' : 'Connect to Notion'}
              </button>
            </div>
          `}
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'settings-page': SettingsPage;
  }
}
