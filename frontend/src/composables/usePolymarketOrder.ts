import { useAuthStore, useTaskStore, useToastStore } from '@/stores'
import { taskService } from '@/services/taskService'

const ORDER_TYPE = 'GTC'
const POLYMARKET_PRIVATE_KEY = 'POLYMARKET_PRIVATE_KEY'
const POLYMARKET_PROXY_ADDRESS = 'POLYMARKET_PROXY_ADDRESS'
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

export function getPolymarketConfig() {
  const privateKey = localStorage.getItem(POLYMARKET_PRIVATE_KEY)?.trim() ?? ''
  const proxyAddress = localStorage.getItem(POLYMARKET_PROXY_ADDRESS)?.trim() ?? ''
  return { privateKey, proxyAddress }
}

export function canPlaceOrder(): { ok: boolean; reason?: string } {
  const authStore = useAuthStore()
  if (!authStore.isAuthenticated || !authStore.token) return { ok: false, reason: '请先登录' }
  const { privateKey, proxyAddress } = getPolymarketConfig()
  if (!privateKey) return { ok: false, reason: '请先配置 Polymarket 私钥' }
  if (!proxyAddress) return { ok: false, reason: '请先配置 Polymarket 代理地址' }
  return { ok: true }
}

export async function submitOrder(payload: {
  tokenId: string
  side: 'BUY' | 'SELL'
  price: number
  size: number
}): Promise<void> {
  const authStore = useAuthStore()
  const { privateKey, proxyAddress } = getPolymarketConfig()

  const response = await fetch(`${API_BASE_URL}/api/v1/polymarket/orders`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${authStore.token}`,
    },
    body: JSON.stringify({
      token_id: payload.tokenId,
      side: payload.side,
      price: payload.price,
      size: payload.size,
      order_type: ORDER_TYPE,
      private_key: privateKey,
      proxy_address: proxyAddress,
    }),
  })

  if (!response.ok) {
    const data = await response.json().catch(() => null)
    throw new Error(data?.detail || '下单失败')
  }

  await response.json().catch(() => null)
}

export async function requestPositionRefresh(): Promise<void> {
  const taskStore = useTaskStore()
  const authStore = useAuthStore()
  const toastStore = useToastStore()

  if (!taskStore.currentTaskId) {
    toastStore.showToast('请先创建并订阅任务', 'warning')
    return
  }
  if (!authStore.token) {
    toastStore.showToast('请先登录', 'error')
    return
  }

  try {
    await taskService.refreshTaskPositions(taskStore.currentTaskId, authStore.token)
  } catch (error) {
    toastStore.showToast(error instanceof Error ? error.message : '刷新持仓失败', 'error')
  }
}
