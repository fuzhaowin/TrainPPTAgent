import axios from 'axios'
import message from '@/utils/message'

const instance = axios.create({ timeout: 1000 * 300 })

function unpackDetail(input: unknown): string {
  try {
    if (typeof input === 'string') {
      const maybeObj = JSON.parse(input)
      return unpackDetail(maybeObj)
    }
    if (input && typeof input === 'object') {
      const obj: any = input
      const d = obj.detail ?? obj.message ?? obj.error
      if (typeof d === 'string') {
        try {
          const inner = JSON.parse(d)
          return unpackDetail(inner)
        } catch {
          return d
        }
      }
      if (d && typeof d === 'object') return unpackDetail(d)
      return JSON.stringify(obj)
    }
    return String(input ?? '')
  } catch {
    return typeof input === 'string' ? input : '请求失败'
  }
}

instance.interceptors.response.use(
  response => {
    if (response.status >= 200 && response.status < 400) {
      return Promise.resolve(response.data)
    }

    message.error('未知的请求错误！')
    return Promise.reject(response)
  },
  error => {
    if (error && error.response) {
      const status = error.response.status
      const raw = error.response.data
      const msg = unpackDetail(raw) || error.message || '请求失败'
      message.error(msg)
      return Promise.reject({ status, message: msg })
    }

    message.error('连接到服务器失败 或 服务器响应超时！')
    return Promise.reject({ message: '网络连接失败或超时' })
  }
)

export default instance