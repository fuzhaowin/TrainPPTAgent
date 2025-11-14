import axios from './config'

// export const SERVER_URL = 'http://localhost:5000'
export const SERVER_URL = '/api'

function unpackErrorText(raw: string): string {
  try {
    const obj = JSON.parse(raw)
    const d = (obj as any).detail ?? (obj as any).message ?? (obj as any).error
    if (typeof d === 'string') {
      try {
        const inner = JSON.parse(d)
        return (inner.detail ?? inner.message ?? inner.error ?? d) as string
      }
      catch {
        return d
      }
    }
    if (d && typeof d === 'object') {
      return (d.detail ?? d.message ?? d.error ?? JSON.stringify(d)) as string
    }
    return JSON.stringify(obj)
  }
  catch {
    // 如果是 Nginx/网关生成的 HTML 错误页，转换为友好文案
    const lower = raw.toLowerCase()
    if (lower.includes('<html') || lower.includes('gateway time-out') || lower.includes('nginx')) {
      if (lower.includes('504')) {
        return '504 网关超时：后端耗时较长或代理超时，请稍后重试或检查后端服务状态。'
      }
      if (lower.includes('502')) {
        return '502 网关错误：后端服务不可达或异常，请检查后端服务。'
      }
      return '网关错误：请稍后重试或检查后端服务。'
    }
    return raw
  }
}

async function fetchStream(url: string, options: RequestInit): Promise<Response> {
  const res = await fetch(url, options)
  if (res.ok) return res
  const raw = await res.text()
  const msg = unpackErrorText(raw)
  const encoder = new TextEncoder()
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(encoder.encode(msg))
      controller.close()
    }
  })
  return new Response(stream, { status: 200, headers: { 'Content-Type': 'text/plain; charset=utf-8' } })
}

interface AIPPTOutlinePayload {
  content: string
  language: string
  model: string
}

interface AIPPTPayload {
  content: string
  language: string
  style?: string
  model?: string
  generateFromUploadedFile?: boolean
  generateFromWebSearch?: boolean
  sessionId?: string
}

interface AIWritingPayload {
  content: string
  command: string
}

interface AIByIDPayload {
  id: string|number
  language?: string
}


export default {
  getMockData(filename: string): Promise<any> {
    return axios.get(`./mocks/${filename}.json`)
  },

  getFileData(filename: string): Promise<any> {
    return axios.get(`${SERVER_URL}/data/${filename}.json`)
  },

  getTemplates(): Promise<any> {
    return axios.get(`${SERVER_URL}/templates`)
  },

  AIPPT_Outline({
    content,
    language,
    model,
  }: AIPPTOutlinePayload): Promise<any> {
    return fetchStream(`${SERVER_URL}/tools/aippt_outline`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        content,
        language,
        model,
        stream: true,
      }),
    })
  },

  AIPPT_Content({
    content,
    language,
    style,
    model,
    generateFromUploadedFile,
    generateFromWebSearch,
    sessionId,
  }: AIPPTPayload): Promise<any> {
    return fetchStream(`${SERVER_URL}/tools/aippt`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify({
        content,
        language,
        model,
        style,
        stream: true,
        generateFromUploadedFile,
        generateFromWebSearch,
        sessionId,
      }),
    })
  },

  AIPPTByID({
    id,
    language,
  }: AIByIDPayload): Promise<any> {
    return fetchStream(`${SERVER_URL}/tools/aippt_by_id`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        id,
        language,
      }),
    })
  },

  AI_Writing({
    content,
    command,
  }: AIWritingPayload): Promise<any> {
    return fetchStream(`${SERVER_URL}/tools/ai_writing`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        content,
        command,
        stream: true,
      }),
    })
  },

  AIPPT_Outline_From_File(file: File, user_id: string | number, language: string): Promise<any> {
    const formData = new FormData()
    formData.append('file', file)
    const num = typeof user_id === 'number' ? user_id : (/^\d+$/.test(String(user_id)) ? parseInt(String(user_id), 10) : 0)
    formData.append('user_id', String(Math.max(0, num)))
    formData.append('language', language)
    return fetchStream(`${SERVER_URL}/tools/aippt_outline_from_file`, {
      method: 'POST',
      body: formData,
    })
  },

  // =========================
  // 模板管理与自动标注接口（前端占位实现）
  // =========================
  /**
   * 注册模板（通过URL）
   * 后端尚未实现对应管理端点，这里按约定发送到 /admin/templates/register
   * 若后端未提供，将由拦截器显示友好错误。
   */
  registerTemplate(
    payload: { id: string; name?: string; json_url?: string; cover_url?: string },
    adminToken: string
  ): Promise<any> {
    return axios.post(
      `${SERVER_URL}/admin/templates/register`,
      payload,
      { headers: { 'X-Admin-Token': adminToken } }
    )
  },

  /**
   * 注册模板（上传文件）
   * 发送 multipart/form-data 到 /admin/templates/register/upload
   */
  registerTemplateUpload(fd: FormData, adminToken: string): Promise<any> {
    return axios.post(
      `${SERVER_URL}/admin/templates/register/upload`,
      fd,
      { headers: { 'X-Admin-Token': adminToken } }
    )
  },

  /**
   * 删除模板
   */
  deleteTemplate(id: string, adminToken: string): Promise<any> {
    return axios.delete(
      `${SERVER_URL}/admin/templates/${encodeURIComponent(id)}`,
      { headers: { 'X-Admin-Token': adminToken } }
    )
  },

  /**
   * 单页自动标注（图片+JSON）
   * 发送 multipart/form-data 到 /tools/annotate_template
   */
  annotateTemplate(fd: FormData): Promise<any> {
    return axios.post(`${SERVER_URL}/tools/annotate_template`, fd)
  },

  /**
   * 批量自动标注（PDF+JSON）
   * 发送 multipart/form-data 到 /tools/annotate_pdf
   */
  annotatePdf(fd: FormData): Promise<any> {
    return axios.post(`${SERVER_URL}/tools/annotate_pdf`, fd)
  },
}