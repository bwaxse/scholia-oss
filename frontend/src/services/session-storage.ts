/**
 * Session Storage Service
 * Manages UI preferences and state in LocalStorage
 */

export interface UIPreferences {
  lastSessionId?: string;
  activeTab: 'outline' | 'concepts' | 'ask';
  pdfZoom: number;
  theme: 'light' | 'dark';
  mobileView?: 'home' | 'paper' | 'discuss' | 'insights';
}

const STORAGE_KEY = 'paper-companion-prefs';

const DEFAULT_PREFERENCES: UIPreferences = {
  activeTab: 'ask',
  pdfZoom: 1.5,
  theme: 'light'
};

class SessionStorage {
  private preferences: UIPreferences;

  constructor() {
    this.preferences = this.load();
  }

  /**
   * Load preferences from LocalStorage
   */
  private load(): UIPreferences {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        return { ...DEFAULT_PREFERENCES, ...JSON.parse(stored) };
      }
    } catch (err) {
      console.error('Failed to load preferences:', err);
    }
    return { ...DEFAULT_PREFERENCES };
  }

  /**
   * Save preferences to LocalStorage
   */
  private save(): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.preferences));
    } catch (err) {
      console.error('Failed to save preferences:', err);
    }
  }

  /**
   * Get all preferences
   */
  getPreferences(): UIPreferences {
    return { ...this.preferences };
  }

  /**
   * Get last active session ID
   */
  getLastSessionId(): string | undefined {
    return this.preferences.lastSessionId;
  }

  /**
   * Set last active session ID
   */
  setLastSessionId(sessionId: string): void {
    this.preferences.lastSessionId = sessionId;
    this.save();
  }

  /**
   * Clear last session ID
   */
  clearLastSessionId(): void {
    this.preferences.lastSessionId = undefined;
    this.save();
  }

  /**
   * Get active tab preference
   */
  getActiveTab(): UIPreferences['activeTab'] {
    return this.preferences.activeTab;
  }

  /**
   * Set active tab preference
   */
  setActiveTab(tab: UIPreferences['activeTab']): void {
    this.preferences.activeTab = tab;
    this.save();
  }

  /**
   * Get PDF zoom level
   */
  getPdfZoom(): number {
    return this.preferences.pdfZoom;
  }

  /**
   * Set PDF zoom level
   */
  setPdfZoom(zoom: number): void {
    this.preferences.pdfZoom = Math.max(0.5, Math.min(3, zoom));
    this.save();
  }

  /**
   * Get theme preference
   */
  getTheme(): UIPreferences['theme'] {
    return this.preferences.theme;
  }

  /**
   * Set theme preference
   */
  setTheme(theme: UIPreferences['theme']): void {
    this.preferences.theme = theme;
    this.save();
  }

  /**
   * Get mobile view preference
   */
  getMobileView(): UIPreferences['mobileView'] {
    return this.preferences.mobileView;
  }

  /**
   * Set mobile view preference
   */
  setMobileView(view: UIPreferences['mobileView']): void {
    this.preferences.mobileView = view;
    this.save();
  }

  /**
   * Reset all preferences to defaults
   */
  reset(): void {
    this.preferences = { ...DEFAULT_PREFERENCES };
    this.save();
  }
}

// Export singleton instance
export const sessionStorage = new SessionStorage();
