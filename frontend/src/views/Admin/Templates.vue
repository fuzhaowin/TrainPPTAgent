<template>
  <div class="admin-page">
    <div class="card">
      <h2>模板管理（管理员）</h2>
      <div class="token-row">
        <input v-model="adminToken" class="input" placeholder="请输入管理员令牌 X-Admin-Token" />
        <button class="btn" @click="saveToken">设置令牌</button>
      </div>
      <div v-if="!adminToken" class="hint">请先设置管理员令牌以执行管理操作</div>
    </div>

    <div class="card">
      <h3>当前模板</h3>
      <div class="grid">
        <div v-for="tpl in templates" :key="tpl.id" class="tpl-card">
          <img :src="tpl.cover" alt="cover" class="cover" />
          <div class="meta">
            <div class="name">{{ tpl.name || tpl.id }}</div>
            <div class="id">ID: {{ tpl.id }}</div>
          </div>
          <div class="actions">
            <button class="btn secondary" @click="previewJson(tpl.id)">查看JSON</button>
            <button class="btn danger" :disabled="!adminToken" @click="removeTemplate(tpl.id)">删除</button>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <h3>注册模板（通过地址）</h3>
      <div class="form">
        <input v-model="registerByUrl.id" class="input" placeholder="模板ID（字母、数字、短横线、下划线）" />
        <input v-model="registerByUrl.name" class="input" placeholder="模板名称（可选）" />
        <input v-model="registerByUrl.json_url" class="input" placeholder="JSON地址（必填其一）" />
        <input v-model="registerByUrl.cover_url" class="input" placeholder="封面图片地址（可选）" />
        <button class="btn" :disabled="!adminToken" @click="submitRegisterByUrl">注册模板</button>
      </div>
    </div>

    <div class="card">
      <h3>注册模板（上传文件）</h3>
      <div class="form">
        <input v-model="registerByUpload.id" class="input" placeholder="模板ID（字母、数字、短横线、下划线）" />
        <input v-model="registerByUpload.name" class="input" placeholder="模板名称（可选）" />
        <div class="file-row">
          <label class="label">上传JSON文件：</label>
          <input type="file" accept="application/json" @change="onJsonFileChange" />
        </div>
        <textarea v-model="registerByUpload.json_text" class="input" rows="6" placeholder="或直接粘贴JSON文本"></textarea>
        <div class="file-row">
          <label class="label">上传封面图片（可选）：</label>
          <input type="file" accept="image/*" @change="onCoverFileChange" />
        </div>
        <button class="btn" :disabled="!adminToken" @click="submitRegisterByUpload">注册模板</button>
      </div>
    </div>

    <div v-if="jsonPreview.visible" class="modal">
      <div class="modal-body">
        <div class="modal-header">
          <div class="title">模板 JSON 预览 - {{ jsonPreview.id }}</div>
          <button class="btn small" @click="closePreview">关闭</button>
        </div>
        <pre class="json">{{ jsonPreview.content }}</pre>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue'
import api from '@/services'
import message from '@/utils/message'

interface TemplateItem {
  id: string
  name?: string
  cover?: string
}

const adminToken = ref<string>('')
const templates = ref<TemplateItem[]>([])

const jsonPreview = ref<{ visible: boolean; id: string; content: string }>({ visible: false, id: '', content: '' })

const registerByUrl = ref<{ id: string; name?: string; json_url?: string; cover_url?: string }>({ id: '', name: '', json_url: '', cover_url: '' })
const registerByUpload = ref<{ id: string; name?: string; json_file?: File | null; json_text?: string; cover_file?: File | null }>({ id: '', name: '', json_file: null, json_text: '', cover_file: null })

const LOCALSTORAGE_KEY = 'ADMIN_TOKEN'

onMounted(() => {
  const saved = localStorage.getItem(LOCALSTORAGE_KEY)
  if (saved) adminToken.value = saved
  loadTemplates()
})

const saveToken = () => {
  localStorage.setItem(LOCALSTORAGE_KEY, adminToken.value)
  message.success('管理员令牌已设置')
}

const loadTemplates = async () => {
  try {
    const resp = await api.getTemplates()
    templates.value = resp?.data || []
  } catch (e) {
    // 已有全局拦截提示
  }
}

const previewJson = async (id: string) => {
  try {
    const json = await api.getFileData(id)
    jsonPreview.value = { visible: true, id, content: JSON.stringify(json, null, 2) }
  } catch (e) {
    // 已有全局拦截提示
  }
}

const closePreview = () => {
  jsonPreview.value.visible = false
}

const submitRegisterByUrl = async () => {
  if (!adminToken.value) {
    message.error('请先设置管理员令牌')
    return
  }
  const id = registerByUrl.value.id.trim()
  const { name, json_url, cover_url } = registerByUrl.value
  if (!id || !/^[a-zA-Z0-9_-]+$/.test(id)) {
    message.error('模板ID格式不合法')
    return
  }
  if (!json_url && !registerByUpload.value.json_text) {
    message.error('请填写JSON地址或切换到上传方式')
    return
  }
  try {
    await api.registerTemplate({ id, name, json_url, cover_url }, adminToken.value)
    message.success('模板注册成功')
    registerByUrl.value = { id: '', name: '', json_url: '', cover_url: '' }
    await loadTemplates()
  } catch (e) {
    // 已有全局拦截提示
  }
}

const onJsonFileChange = (ev: Event) => {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  registerByUpload.value.json_file = file || null
}

const onCoverFileChange = (ev: Event) => {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  registerByUpload.value.cover_file = file || null
}

const submitRegisterByUpload = async () => {
  if (!adminToken.value) {
    message.error('请先设置管理员令牌')
    return
  }
  const id = registerByUpload.value.id.trim()
  const { name, json_file, json_text, cover_file } = registerByUpload.value
  if (!id || !/^[a-zA-Z0-9_-]+$/.test(id)) {
    message.error('模板ID格式不合法')
    return
  }
  if (!json_file && !json_text) {
    message.error('请上传JSON文件或填写JSON文本')
    return
  }
  const fd = new FormData()
  fd.append('tpl_id', id)
  if (name) fd.append('name', name)
  if (json_file) fd.append('json_file', json_file)
  if (json_text) fd.append('json_text', json_text)
  if (cover_file) fd.append('cover', cover_file)
  try {
    await api.registerTemplateUpload(fd, adminToken.value)
    message.success('模板注册成功')
    registerByUpload.value = { id: '', name: '', json_file: null, json_text: '', cover_file: null }
    await loadTemplates()
  } catch (e) {
    // 已有全局拦截提示
  }
}

const removeTemplate = async (id: string) => {
  if (!adminToken.value) {
    message.error('请先设置管理员令牌')
    return
  }
  try {
    await api.deleteTemplate(id, adminToken.value)
    message.success('模板已删除')
    await loadTemplates()
  } catch (e) {
    // 已有全局拦截提示
  }
}
</script>

<style scoped>
.admin-page {
  padding: 24px;
}
.card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 20px rgba(0,0,0,.06);
  padding: 16px;
  margin-bottom: 20px;
}
.token-row { display: flex; gap: 8px; align-items: center; }
.hint { color: #64748b; font-size: 13px; margin-top: 8px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; }
.tpl-card { border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px; background: #fafafa; }
.cover { width: 100%; height: 140px; object-fit: cover; border-radius: 6px; background: #f1f5f9; }
.meta { margin-top: 8px; }
.name { font-weight: 600; color: #334155; }
.id { font-size: 12px; color: #64748b; }
.actions { display: flex; gap: 8px; margin-top: 8px; }
.form { display: flex; flex-direction: column; gap: 8px; }
.file-row { display: flex; align-items: center; gap: 8px; }
.label { font-size: 13px; color: #334155; }
.input { width: 100%; padding: 8px 10px; border: 1px solid #e2e8f0; border-radius: 8px; outline: none; }
.btn { background: linear-gradient(135deg, #667eea, #764ba2); color: #fff; border: none; padding: 8px 14px; border-radius: 8px; cursor: pointer; }
.btn.secondary { background: #475569; }
.btn.danger { background: #ef4444; }
.btn.small { padding: 6px 10px; }
.modal { position: fixed; inset: 0; background: rgba(0,0,0,.45); display: flex; align-items: center; justify-content: center; }
.modal-body { background: #fff; border-radius: 10px; width: 80%; max-width: 800px; padding: 12px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.title { font-weight: 600; color: #334155; }
.json { max-height: 60vh; overflow: auto; background: #f8fafc; padding: 12px; border-radius: 8px; }
</style>