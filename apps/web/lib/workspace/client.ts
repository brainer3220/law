/**
 * Workspace API Client
 * 프로젝트 관리 API와 통신하는 클라이언트
 */

const API_BASE = process.env.NEXT_PUBLIC_WORKSPACE_API_URL || 'http://localhost:8001'

export const PERMISSION_ROLES = [
  'owner',
  'maintainer',
  'editor',
  'commenter',
  'viewer',
] as const

// ========================================================================
// Types
// ========================================================================

export type PermissionRole = (typeof PERMISSION_ROLES)[number]

export interface Project {
  id: string
  name: string
  description: string | null
  status?: string | null
  org_id: string | null
  archived: boolean
  created_at: string
  updated_at: string
  created_by: string
}

export interface ProjectListResponse {
  projects: Project[]
  total: number
}

export interface ProjectCreate {
  name: string
  description?: string
  status?: string
  org_id?: string
}

export interface ProjectUpdate {
  name?: string
  description?: string
  status?: string
  org_id?: string
}

export interface ProjectClone {
  name: string
}

export interface Member {
  user_id: string
  role: PermissionRole
  invited_by: string | null
  created_at: string
}

export interface MemberAdd {
  user_id: string
  role: PermissionRole
}

export interface MemberUpdate {
  role: PermissionRole
}

export interface Instruction {
  project_id: string
  version: number
  content: string
  created_by: string
  created_at: string
}

export interface InstructionCreate {
  content: string
}

export interface LatestInstructionsResponse {
  instructions: Record<string, Instruction | null>
}

export interface Update {
  id: string
  project_id: string | null
  body: string | null
  created_by: string | null
  created_at: string | null
  project_update_file_id: string | null
}

export interface UpdateCreate {
  body?: string
  project_update_file_id?: string
}

function validateUpdateCreate(data: UpdateCreate): UpdateCreate {
  if (!data.body && !data.project_update_file_id) {
    throw new Error('body or project_update_file_id is required')
  }
  return data
}

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

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers = new Headers(options.headers)
    if (this.userId) {
      headers.set('X-User-ID', this.userId)
    }
    const isFormData = options.body instanceof FormData
    if (!headers.has('Content-Type') && !isFormData) {
      headers.set('Content-Type', 'application/json')
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const errorPayload = await response
        .json()
        .catch(() => ({ detail: 'Unknown error' }))
      throw new Error(errorPayload.detail || `HTTP ${response.status}`)
    }

    if (response.status === 204) {
      return undefined as T
    }

    const contentType = response.headers.get('content-type') || ''
    if (!contentType.includes('application/json')) {
      return undefined as T
    }

    const data = (await response.json()) as unknown
    return data as T
  }

  // ======================================================================
  // Projects
  // ======================================================================

  async listProjects(params?: {
    archived?: boolean
    org_id?: string
    limit?: number
    offset?: number
  }): Promise<ProjectListResponse> {
    const query = new URLSearchParams()
    if (params?.archived !== undefined) query.set('archived', String(params.archived))
    if (params?.org_id) query.set('org_id', params.org_id)
    if (params?.limit) query.set('limit', String(params.limit))
    if (params?.offset) query.set('offset', String(params.offset))

    const suffix = query.toString() ? `?${query.toString()}` : ''
    return this.request<ProjectListResponse>(`/v1/projects${suffix}`)
  }

  async getProject(projectId: string): Promise<Project> {
    return this.request<Project>(`/v1/projects/${projectId}`)
  }

  async createProject(data: ProjectCreate): Promise<Project> {
    return this.request<Project>(
      '/v1/projects',
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    )
  }

  async updateProject(projectId: string, data: ProjectUpdate): Promise<Project> {
    return this.request<Project>(
      `/v1/projects/${projectId}`,
      {
        method: 'PATCH',
        body: JSON.stringify(data),
      }
    )
  }

  async deleteProject(projectId: string, options?: { hardDelete?: boolean }): Promise<void> {
    const suffix = options?.hardDelete ? '?hard_delete=true' : ''
    await this.request<void>(`/v1/projects/${projectId}${suffix}`, {
      method: 'DELETE',
    })
  }

  async cloneProject(projectId: string, data: ProjectClone): Promise<Project> {
    return this.request<Project>(
      `/v1/projects/${projectId}/clone`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    )
  }

  // ======================================================================
  // Project members
  // ======================================================================

  async listMembers(projectId: string): Promise<Member[]> {
    return this.request<Member[]>(
      `/v1/projects/${projectId}/members`,
      {}
    )
  }

  async addMember(projectId: string, data: MemberAdd): Promise<Member> {
    return this.request<Member>(
      `/v1/projects/${projectId}/members`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    )
  }

  async updateMemberRole(
    projectId: string,
    memberUserId: string,
    data: MemberUpdate
  ): Promise<Member> {
    return this.request<Member>(
      `/v1/projects/${projectId}/members/${memberUserId}`,
      {
        method: 'PATCH',
        body: JSON.stringify(data),
      }
    )
  }

  async removeMember(projectId: string, memberUserId: string): Promise<void> {
    await this.request<void>(`/v1/projects/${projectId}/members/${memberUserId}`, {
      method: 'DELETE',
    })
  }

  // ======================================================================
  // Updates
  // ======================================================================

  async listUpdates(projectId: string): Promise<Update[]> {
    return this.request<Update[]>(
      `/v1/projects/${projectId}/updates`,
      {}
    )
  }

  async getUpdate(projectId: string, updateId: string): Promise<Update> {
    return this.request<Update>(
      `/v1/projects/${projectId}/updates/${updateId}`
    )
  }

  async createUpdate(projectId: string, data: UpdateCreate): Promise<Update> {
    const payload = validateUpdateCreate(data)
    return this.request<Update>(
      `/v1/projects/${projectId}/updates`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    )
  }

  async deleteUpdate(projectId: string, updateId: string): Promise<void> {
    await this.request<void>(`/v1/projects/${projectId}/updates/${updateId}`, {
      method: 'DELETE',
    })
  }

  // ======================================================================
  // Instructions
  // ======================================================================

  async listInstructions(projectId: string): Promise<Instruction[]> {
    return this.request<Instruction[]>(
      `/v1/projects/${projectId}/instructions`,
      {}
    )
  }

  async latestInstructions(projectIds: string[]): Promise<LatestInstructionsResponse> {
    return this.request<LatestInstructionsResponse>(
      '/v1/instructions/latest',
      {
        method: 'POST',
        body: JSON.stringify({ project_ids: projectIds }),
      }
    )
  }

  async getInstruction(projectId: string, version: number): Promise<Instruction> {
    return this.request<Instruction>(
      `/v1/projects/${projectId}/instructions/${version}`
    )
  }

  async createInstruction(projectId: string, data: InstructionCreate): Promise<Instruction> {
    return this.request<Instruction>(
      `/v1/projects/${projectId}/instructions`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    )
  }
}

// Singleton instance
export const workspaceClient = new WorkspaceClient()
