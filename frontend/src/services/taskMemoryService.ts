const NANOCLAW_BASE_URL = import.meta.env.VITE_NANOCLAW_BASE_URL ?? ""

export interface UpdateGroupMemoryResponse {
  status: string
  groupId: string
  path: string
  bytes: number
}

interface UpdateGroupMemoryParams {
  groupId: string
  content: string
  token: string
  signal?: AbortSignal
}

function mapHttpError(status: number): string {
  if (status === 400) return "记忆内容格式错误"
  if (status === 401) return "认证失败，请重新登录"
  if (status === 403) return "无权限更新该任务记忆"
  if (status === 404) return "任务记忆分组不存在"
  return `记忆更新失败 (${status})`
}

export async function updateGroupMemory(params: UpdateGroupMemoryParams): Promise<UpdateGroupMemoryResponse> {
  const { groupId, content, token, signal } = params

  const response = await fetch(`${NANOCLAW_BASE_URL}/api/groups/${encodeURIComponent(groupId)}/memory`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ content }),
    signal,
  })

  if (!response.ok) {
    throw new Error(mapHttpError(response.status))
  }

  return response.json()
}
