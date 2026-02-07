/**
 * 任务管理 API 服务
 */

import type {
  CreateTaskRequest,
  CreateTaskResponse,
  TaskListResponse,
  TaskStatus,
  TaskConfigResponse,
  UpdateTaskConfigRequest,
} from '@/types/task'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

class TaskService {
  private getHeaders(token?: string): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }
    return headers
  }

  /**
   * 创建后台任务
   */
  async createTask(request: CreateTaskRequest, token?: string): Promise<CreateTaskResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/tasks/create`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(error.detail || `创建任务失败: ${response.status}`)
    }

    return response.json()
  }

  /**
   * 获取任务列表
   */
  async listTasks(token?: string): Promise<TaskListResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/tasks/`, {
      method: 'GET',
      headers: this.getHeaders(token),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(error.detail || `获取任务列表失败: ${response.status}`)
    }

    return response.json()
  }

  /**
   * 获取单个任务状态
   */
  async getTask(taskId: string, token?: string): Promise<TaskStatus> {
    const response = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}`, {
      method: 'GET',
      headers: this.getHeaders(token),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(error.detail || `获取任务失败: ${response.status}`)
    }

    return response.json()
  }

  async getTaskConfig(taskId: string, token?: string): Promise<TaskConfigResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}/config`, {
      method: 'GET',
      headers: this.getHeaders(token),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(error.detail || `获取任务配置失败: ${response.status}`)
    }

    return response.json()
  }

  /**
   * 取消任务
   */
  async cancelTask(taskId: string, token?: string): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}/cancel`, {
      method: 'POST',
      headers: this.getHeaders(token),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(error.detail || `取消任务失败: ${response.status}`)
    }

    return response.json()
  }

  /**
   * 删除任务（仅终态）
   */
  async deleteTask(taskId: string, token?: string): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}`, {
      method: 'DELETE',
      headers: this.getHeaders(token),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(error.detail || `删除任务失败: ${response.status}`)
    }

    return response.json()
  }

  async updateTaskConfig(
    taskId: string,
    request: UpdateTaskConfigRequest,
    token?: string
  ): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}/config`, {
      method: 'PATCH',
      headers: this.getHeaders(token),
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(error.detail || `更新任务配置失败: ${response.status}`)
    }

    return response.json()
  }

  async refreshTaskPositions(taskId: string, token?: string): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}/positions/refresh`, {
      method: 'POST',
      headers: this.getHeaders(token),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(error.detail || `刷新持仓失败: ${response.status}`)
    }

    return response.json()
  }
}

export const taskService = new TaskService()
