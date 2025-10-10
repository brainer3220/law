/**
 * Workspace API Client
 * 프로젝트 관리 API와 통신하는 클라이언트
 */

import { z } from 'zod'

const API_BASE = process.env.NEXT_PUBLIC_WORKSPACE_API_URL || 'http://localhost:8001'

// ========================================================================
// Schemas (Zod validation matching backend Pydantic models)
// ========================================================================

export const ProjectSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  description: z.string().nullable(),
  visibility: z.string(),
  org_id: z.string().uuid().nullable(),
  archived: z.boolean(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  created_by: z.string().uuid(),
})

export const ProjectListItemSchema = ProjectSchema.extend({
  member_count: z.number().optional(),
  file_count: z.number().optional(),
  message_count: z.number().optional(),
})

export const ProjectCreateSchema = z.object({
  name: z.string().max(255),
  description: z.string().optional(),
  visibility: z.enum(['private', 'team', 'public']).default('private'),
  org_id: z.string().uuid().optional(),
  template_id: z.string().uuid().optional(),
  budget_quota: z.number().optional(),
})

export const MessageSchema = z.object({
  id: z.string().uuid(),
  chat_id: z.string().uuid(),
  role: z.enum(['user', 'assistant', 'system']),
  content: z.string(),
  created_at: z.string().datetime(),
  metadata: z.record(z.string(), z.any()).nullable(),
})

export const ChatSchema = z.object({
  id: z.string().uuid(),
  project_id: z.string().uuid(),
  title: z.string().nullable(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
})

export const FileSchema = z.object({
  id: z.string().uuid(),
  project_id: z.string().uuid(),
  filename: z.string(),
  size_bytes: z.number(),
  mime_type: z.string().nullable(),
  uploaded_at: z.string().datetime(),
  uploaded_by: z.string().uuid(),
  indexed: z.boolean(),
})

export const MemorySchema = z.object({
  id: z.string().uuid(),
  project_id: z.string().uuid(),
  key: z.string(),
  value: z.string(),
  memory_type: z.enum(['fact', 'preference', 'context', 'decision']),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
})

export const ActivitySchema = z.object({
  id: z.string().uuid(),
  project_id: z.string().uuid(),
  actor_id: z.string().uuid(),
  action: z.string(),
  resource_type: z.string(),
  resource_id: z.string().uuid().nullable(),
  metadata: z.record(z.string(), z.any()).nullable(),
  created_at: z.string().datetime(),
})

// ========================================================================
// Types
// ========================================================================

export type Project = z.infer<typeof ProjectSchema>
export type ProjectListItem = z.infer<typeof ProjectListItemSchema>
export type ProjectCreate = z.infer<typeof ProjectCreateSchema>
export type Message = z.infer<typeof MessageSchema>
export type Chat = z.infer<typeof ChatSchema>
export type File = z.infer<typeof FileSchema>
export type Memory = z.infer<typeof MemorySchema>
export type Activity = z.infer<typeof ActivitySchema>

// ========================================================================
// Client
// ========================================================================

export class WorkspaceClient {
  private baseUrl: string
  private userId: string | null = null

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl
  }

  setUserId(userId: string) {
    this.userId = userId
  }

  private async fetch<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers = new Headers(options.headers)
    if (this.userId) {
      headers.set('X-User-ID', this.userId)
    }
    headers.set('Content-Type', 'application/json')

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }

    return response.json()
  }

  // ========================================================================
  // Projects
  // ========================================================================

  async listProjects(params?: {
    archived?: boolean
    org_id?: string
    limit?: number
    offset?: number
  }): Promise<ProjectListItem[]> {
    const query = new URLSearchParams()
    if (params?.archived !== undefined) query.set('archived', String(params.archived))
    if (params?.org_id) query.set('org_id', params.org_id)
    if (params?.limit) query.set('limit', String(params.limit))
    if (params?.offset) query.set('offset', String(params.offset))

    const data = await this.fetch<{ projects: ProjectListItem[] }>(
      `/v1/projects?${query.toString()}`
    )
    return data.projects
  }

  async getProject(projectId: string): Promise<Project> {
    return this.fetch<Project>(`/v1/projects/${projectId}`)
  }

  async createProject(data: ProjectCreate): Promise<Project> {
    return this.fetch<Project>('/v1/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateProject(
    projectId: string,
    data: Partial<ProjectCreate>
  ): Promise<Project> {
    return this.fetch<Project>(`/v1/projects/${projectId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  }

  async archiveProject(projectId: string): Promise<void> {
    await this.fetch<void>(`/v1/projects/${projectId}`, {
      method: 'PATCH',
      body: JSON.stringify({ archived: true }),
    })
  }

  async deleteProject(projectId: string): Promise<void> {
    await this.fetch<void>(`/v1/projects/${projectId}`, {
      method: 'DELETE',
    })
  }

  // ========================================================================
  // Chats & Messages
  // ========================================================================

  async listChats(projectId: string): Promise<Chat[]> {
    const data = await this.fetch<{ chats: Chat[] }>(
      `/v1/projects/${projectId}/chats`
    )
    return data.chats
  }

  async createChat(projectId: string, title?: string): Promise<Chat> {
    return this.fetch<Chat>(`/v1/projects/${projectId}/chats`, {
      method: 'POST',
      body: JSON.stringify({ title }),
    })
  }

  async listMessages(chatId: string): Promise<Message[]> {
    const data = await this.fetch<{ messages: Message[] }>(
      `/v1/chats/${chatId}/messages`
    )
    return data.messages
  }

  async sendMessage(
    chatId: string,
    content: string,
    role: 'user' | 'assistant' = 'user'
  ): Promise<Message> {
    return this.fetch<Message>(`/v1/chats/${chatId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content, role }),
    })
  }

  // ========================================================================
  // Files
  // ========================================================================

  async listFiles(projectId: string): Promise<File[]> {
    const data = await this.fetch<{ files: File[] }>(
      `/v1/projects/${projectId}/files`
    )
    return data.files
  }

  async uploadFile(
    projectId: string,
    file: globalThis.File
  ): Promise<File> {
    const formData = new FormData()
    formData.append('file', file)

    const headers = new Headers()
    if (this.userId) {
      headers.set('X-User-ID', this.userId)
    }

    const response = await fetch(
      `${this.baseUrl}/v1/projects/${projectId}/files`,
      {
        method: 'POST',
        headers,
        body: formData,
      }
    )

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }

    return response.json()
  }

  async deleteFile(fileId: string): Promise<void> {
    await this.fetch<void>(`/v1/files/${fileId}`, {
      method: 'DELETE',
    })
  }

  // ========================================================================
  // Memories
  // ========================================================================

  async listMemories(projectId: string): Promise<Memory[]> {
    const data = await this.fetch<{ memories: Memory[] }>(
      `/v1/projects/${projectId}/memories`
    )
    return data.memories
  }

  async createMemory(
    projectId: string,
    data: {
      key: string
      value: string
      memory_type: 'fact' | 'preference' | 'context' | 'decision'
    }
  ): Promise<Memory> {
    return this.fetch<Memory>(`/v1/projects/${projectId}/memories`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateMemory(
    memoryId: string,
    data: { value: string }
  ): Promise<Memory> {
    return this.fetch<Memory>(`/v1/memories/${memoryId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  }

  async deleteMemory(memoryId: string): Promise<void> {
    await this.fetch<void>(`/v1/memories/${memoryId}`, {
      method: 'DELETE',
    })
  }

  // ========================================================================
  // Activity (Audit logs)
  // ========================================================================

  async listActivities(
    projectId: string,
    params?: { limit?: number; offset?: number }
  ): Promise<Activity[]> {
    const query = new URLSearchParams()
    if (params?.limit) query.set('limit', String(params.limit))
    if (params?.offset) query.set('offset', String(params.offset))

    const data = await this.fetch<{ activities: Activity[] }>(
      `/v1/projects/${projectId}/activities?${query.toString()}`
    )
    return data.activities
  }
}

// Singleton instance
export const workspaceClient = new WorkspaceClient()
