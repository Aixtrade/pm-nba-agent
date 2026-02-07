import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

const AUTH_TOKEN_KEY = 'pm_nba_agent_auth_token'
const AUTH_USERNAME_KEY = 'pm_nba_agent_username'
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

function getStoredToken(): string {
  if (typeof window === 'undefined') return ''
  return localStorage.getItem(AUTH_TOKEN_KEY) || ''
}

function setStoredToken(token: string) {
  if (typeof window === 'undefined') return
  if (token) {
    localStorage.setItem(AUTH_TOKEN_KEY, token)
  } else {
    localStorage.removeItem(AUTH_TOKEN_KEY)
  }
}

function getStoredUsername(): string {
  if (typeof window === 'undefined') return ''
  return localStorage.getItem(AUTH_USERNAME_KEY) || ''
}

function setStoredUsername(username: string) {
  if (typeof window === 'undefined') return
  if (username) {
    localStorage.setItem(AUTH_USERNAME_KEY, username)
  } else {
    localStorage.removeItem(AUTH_USERNAME_KEY)
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(getStoredToken())
  const username = ref<string>(getStoredUsername())
  const lastError = ref<string | null>(null)

  const isAuthenticated = computed(() => token.value.length > 0)

  async function login(user: string, password: string): Promise<boolean> {
    lastError.value = null

    if (!user || !password) {
      lastError.value = '请输入用户名和密码'
      return false
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username: user, password }),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => null)
        lastError.value = data?.detail || '登录失败'
        return false
      }

      const data = await response.json()
      token.value = data.token || ''
      if (!token.value) {
        lastError.value = '登录失败：未返回令牌'
        return false
      }
      username.value = data.username || user
      setStoredToken(token.value)
      setStoredUsername(username.value)
      return true
    } catch (error) {
      lastError.value = error instanceof Error ? error.message : '登录失败'
      return false
    }
  }

  function logout() {
    token.value = ''
    username.value = ''
    lastError.value = null
    setStoredToken('')
    setStoredUsername('')
  }

  return {
    token,
    username,
    lastError,
    isAuthenticated,
    login,
    logout,
  }
})
