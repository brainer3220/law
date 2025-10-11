/**
 * Workspace API Client
 * 프로젝트 관리 API와 통신하는 클라이언트
 */

import { z } from 'zod'

const API_BASE = process.env.NEXT_PUBLIC_WORKSPACE_API_URL || 'http://localhost:8001'

// ========================================================================
// Schemas (align with backend Pydantic models)
// ========================================================================

export const PermissionRoleSchema = z.enum([
  'owner',
  'maintainer',
  'editor',
  'commenter',
  'viewer',
])

export const ProjectSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  description: z.string().nullable(),
  status: z.string().nullable().optional(),
  org_id: z.string().uuid().nullable(),
  archived: z.boolean(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  created_by: z.string().uuid(),
})

export const ProjectListResponseSchema = z.object({
  projects: z.array(ProjectSchema),
  total: z.number(),
})

export const ProjectCreateSchema = z.object({
  name: z.string().max(255),
  description: z.string().optional(),
  status: z.string().default('active'),
  org_id: z.string().uuid().optional(),
})

export const ProjectUpdateSchema = z.object({
  name: z.string().max(255).optional(),
  description: z.string().optional(),
  status: z.string().optional(),
  org_id: z.string().uuid().optional(),
})

export const ProjectCloneSchema = z.object({
  name: z.string().max(255),
})

export const MemberSchema = z.object({
  user_id: z.string().uuid(),
  role: PermissionRoleSchema,
  invited_by: z.string().uuid().nullable(),
  created_at: z.string().datetime(),
})

export const MemberAddSchema = z.object({
  user_id: z.string().uuid(),
  role: PermissionRoleSchema,
})

export const MemberUpdateSchema = z.object({
  role: PermissionRoleSchema,
})

export const InstructionSchema = z.object({
  project_id: z.string().uuid(),
  version: z.number(),
  content: z.string(),
  created_by: z.string().uuid(),
  created_at: z.string().datetime(),
})

export const InstructionCreateSchema = z.object({
  content: z.string().min(1),
})

export const UpdateSchema = z.object({
  id: z.string().uuid(),
  project_id: z.string().uuid().nullable(),
  body: z.string().nullable(),
  created_by: z.string().uuid().nullable(),
  created_at: z.string().datetime().nullable(),
  project_update_file_id: z.string().uuid().nullable(),
})

export const UpdateCreateSchema = z
  .object({
    body: z.string().min(1).optional(),
    project_update_file_id: z.string().uuid().optional(),
  })
  .superRefine((data, ctx) => {
    if (!data.body && !data.project_update_file_id) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'body or project_update_file_id is required',
        path: ['body'],
      })
    }
  })

// ========================================================================
// Types
// ========================================================================

export type PermissionRole = z.infer<typeof PermissionRoleSchema>
export type Project = z.infer<typeof ProjectSchema>
export type ProjectListResponse = z.infer<typeof ProjectListResponseSchema>
export type ProjectCreate = z.infer<typeof ProjectCreateSchema>
export type ProjectUpdate = z.infer<typeof ProjectUpdateSchema>
export type ProjectClone = z.infer<typeof ProjectCloneSchema>
export type Member = z.infer<typeof MemberSchema>
export type MemberAdd = z.infer<typeof MemberAddSchema>
export type MemberUpdate = z.infer<typeof MemberUpdateSchema>
export type Instruction = z.infer<typeof InstructionSchema>
export type InstructionCreate = z.infer<typeof InstructionCreateSchema>
export type Update = z.infer<typeof UpdateSchema>
export type UpdateCreate = z.infer<typeof UpdateCreateSchema>

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
    options: RequestInit = {},
    schema?: z.ZodType<T>
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
    return schema ? schema.parse(data) : (data as T)
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
    return this.request(`/v1/projects${suffix}`, {}, ProjectListResponseSchema)
  }

  async getProject(projectId: string): Promise<Project> {
    return this.request(`/v1/projects/${projectId}`, {}, ProjectSchema)
  }

  async createProject(data: ProjectCreate): Promise<Project> {
    return this.request(
      '/v1/projects',
      {
        method: 'POST',
        body: JSON.stringify(data),
      },
      ProjectSchema
    )
  }

  async updateProject(projectId: string, data: ProjectUpdate): Promise<Project> {
    return this.request(
      `/v1/projects/${projectId}`,
      {
        method: 'PATCH',
        body: JSON.stringify(data),
      },
      ProjectSchema
    )
  }

  async deleteProject(projectId: string, options?: { hardDelete?: boolean }): Promise<void> {
    const suffix = options?.hardDelete ? '?hard_delete=true' : ''
    await this.request<void>(`/v1/projects/${projectId}${suffix}`, {
      method: 'DELETE',
    })
  }

  async cloneProject(projectId: string, data: ProjectClone): Promise<Project> {
    return this.request(
      `/v1/projects/${projectId}/clone`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      },
      ProjectSchema
    )
  }

  // ======================================================================
  // Project members
  // ======================================================================

  async listMembers(projectId: string): Promise<Member[]> {
    return this.request(
      `/v1/projects/${projectId}/members`,
      {},
      z.array(MemberSchema)
    )
  }

  async addMember(projectId: string, data: MemberAdd): Promise<Member> {
    return this.request(
      `/v1/projects/${projectId}/members`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      },
      MemberSchema
    )
  }

  async updateMemberRole(
    projectId: string,
    memberUserId: string,
    data: MemberUpdate
  ): Promise<Member> {
    return this.request(
      `/v1/projects/${projectId}/members/${memberUserId}`,
      {
        method: 'PATCH',
        body: JSON.stringify(data),
      },
      MemberSchema
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
    return this.request(
      `/v1/projects/${projectId}/updates`,
      {},
      z.array(UpdateSchema)
    )
  }

  async getUpdate(projectId: string, updateId: string): Promise<Update> {
    return this.request(
      `/v1/projects/${projectId}/updates/${updateId}`,
      {},
      UpdateSchema
    )
  }

  async createUpdate(projectId: string, data: UpdateCreate): Promise<Update> {
    const payload = UpdateCreateSchema.parse(data)
    return this.request(
      `/v1/projects/${projectId}/updates`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      UpdateSchema
    )
  }

  // ======================================================================
  // Instructions
  // ======================================================================

  async listInstructions(projectId: string): Promise<Instruction[]> {
    return this.request(
      `/v1/projects/${projectId}/instructions`,
      {},
      z.array(InstructionSchema)
    )
  }

  async getInstruction(projectId: string, version: number): Promise<Instruction> {
    return this.request(
      `/v1/projects/${projectId}/instructions/${version}`,
      {},
      InstructionSchema
    )
  }

  async createInstruction(projectId: string, data: InstructionCreate): Promise<Instruction> {
    return this.request(
      `/v1/projects/${projectId}/instructions`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      },
      InstructionSchema
    )
  }
}

// Singleton instance
export const workspaceClient = new WorkspaceClient()
