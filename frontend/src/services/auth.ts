/**
 * Authentication service for local-first Scholia.
 * No OAuth required — always returns a hardcoded local user.
 */

export interface User {
  id: string;
  email: string;
  name: string;
  picture?: string;
  isBanned: boolean;
  isAdmin: boolean;
}

export interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: User | null;
}

type AuthSubscriber = (state: AuthState) => void;

const LOCAL_USER: User = {
  id: 'local-user',
  email: 'local@localhost',
  name: 'Local User',
  isBanned: false,
  isAdmin: true,
};

class AuthService {
  private state: AuthState = {
    isAuthenticated: true,
    isLoading: false,
    user: LOCAL_USER,
  };

  private subscribers: Set<AuthSubscriber> = new Set();

  subscribe(callback: AuthSubscriber): () => void {
    this.subscribers.add(callback);
    callback(this.state);
    return () => {
      this.subscribers.delete(callback);
    };
  }

  async checkAuth(): Promise<AuthState> {
    // Always authenticated locally
    return this.state;
  }

  login(): void {
    // No-op in local mode
  }

  async logout(): Promise<void> {
    // No-op in local mode
  }

  getState(): AuthState {
    return this.state;
  }
}

export const authService = new AuthService();
