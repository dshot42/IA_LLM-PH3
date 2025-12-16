const TOKEN_KEY = 'token_123'
export const auth = {
  getToken(): string | null { return localStorage.getItem(TOKEN_KEY) },
  setToken(token: string) { localStorage.setItem(TOKEN_KEY, token) },
  logout() { localStorage.removeItem(TOKEN_KEY) },
  isAuthenticated(): boolean { return !!localStorage.getItem(TOKEN_KEY) }
}
