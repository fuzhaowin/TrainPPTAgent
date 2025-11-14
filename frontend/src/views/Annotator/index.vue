<template>
  <div class="aippt-page">
    <!-- 背景：与主页一致的网格与漂浮效果 -->
    <div class="page-bg" aria-hidden="true">
      <div class="tech-grid"></div>
      <div class="float-sphere s1"></div>
      <div class="float-sphere s2"></div>
      <div class="float-sphere s3"></div>
    </div>

    <div class="aippt-dialog">
      <!-- 头部品牌：与主页一致 -->
      <div class="header-section">
        <div class="brand">
          <h1 class="title">
            <span class="title-main">PPTAgent</span>
            <span class="title-badge">AI</span>
          </h1>
          <div class="subtitle">模板自动标注 · 支持 PDF+JSON 与 图片+JSON</div>
        </div>
      </div>

      <!-- 内容区：两种标注模式卡片 -->
      <section class="annotator-section" aria-label="模板自动标注">
        <div class="form-card">
          <h3 class="card-title">单页标注（图片 + JSON）</h3>
          <label class="form-field">
            <span class="label">页面截图（PNG/JPG）</span>
            <div class="file-row">
              <button type="button" class="btn btn-secondary" @click="triggerImagePick">选择文件</button>
              <span class="file-name">{{ imageName }}</span>
              <input ref="imageInputRef" class="hidden-input" type="file" accept="image/*" @change="onPickImage" />
            </div>
          </label>
          <label class="form-field">
            <span class="label">未标注 JSON（整文件或单页）</span>
            <div class="file-row">
              <button type="button" class="btn btn-secondary" @click="triggerJsonPick">选择文件</button>
              <span class="file-name">{{ jsonName }}</span>
              <input ref="jsonInputRef" class="hidden-input" type="file" accept="application/json" @change="onPickJson" />
            </div>
          </label>
          <div class="row">
            <label class="form-field">
              <span class="label">页索引</span>
              <input type="number" v-model.number="pageIndex" min="0" />
            </label>
            <label class="form-field">
              <span class="label">IoU 阈值</span>
              <input type="number" step="0.05" v-model.number="iou" min="0" max="1" />
            </label>
            <label class="form-field">
              <span class="label">可视化</span>
              <select v-model="viz">
                <option value="bbox">bbox</option>
                <option value="points">points</option>
              </select>
            </label>
          </div>
          <button class="btn btn-primary" :disabled="!canRun || running" @click="runAnnotate">
            <span>{{ running ? '运行中…' : '运行标注' }}</span>
          </button>
        </div>

        <div class="form-card">
          <h3 class="card-title">批量标注（PDF + JSON）</h3>
          <label class="form-field">
            <span class="label">模板 PDF（整份文件）</span>
            <div class="file-row">
              <button type="button" class="btn btn-secondary" @click="triggerPdfPick">选择文件</button>
              <span class="file-name">{{ pdfName }}</span>
              <input ref="pdfInputRef" class="hidden-input" type="file" accept="application/pdf" @change="onPickPdf" />
            </div>
          </label>
          <label class="form-field">
            <span class="label">未标注 JSON（整文件）</span>
            <div class="file-row">
              <button type="button" class="btn btn-secondary" @click="triggerJsonPick">选择文件</button>
              <span class="file-name">{{ jsonName }}</span>
              <input ref="jsonInputRef2" class="hidden-input" type="file" accept="application/json" @change="onPickJson" />
            </div>
          </label>
          <div class="row">
            <label class="form-field">
              <span class="label">IoU 阈值</span>
              <input type="number" step="0.05" v-model.number="iou" min="0" max="1" />
            </label>
            <label class="form-field">
              <span class="label">可视化</span>
              <select v-model="viz">
                <option value="bbox">bbox</option>
                <option value="points">points</option>
              </select>
            </label>
          </div>
          <button class="btn btn-primary" :disabled="!canRunBatch || batchRunning" @click="runBatchAnnotate">
            <span>{{ batchRunning ? '批量运行中…' : '批量标注整份模板' }}</span>
          </button>
          <div v-if="batchPages" class="hint">已标注页数：{{ batchPages }}</div>
        </div>

        <div class="result" v-if="resultJson || visB64">
          <div v-if="visB64" class="preview">
            <h3 class="card-title">识别可视化</h3>
            <img :src="'data:image/png;base64,' + visB64" alt="viz" />
          </div>
          <div v-if="resultJson" class="json">
            <h3 class="card-title">标注后的 JSON</h3>
            <textarea readonly :value="prettyJson" rows="18"></textarea>
            <button class="btn btn-secondary" @click="downloadJson">下载 JSON</button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import api from '@/services'

const imageFile = ref<File | null>(null)
const jsonFile = ref<File | null>(null)
const pageIndex = ref<number>(0)
const viz = ref<'bbox' | 'points'>('bbox')
const iou = ref<number>(0.25)
const running = ref(false)

const resultJson = ref<any | null>(null)
const visB64 = ref<string | null>(null)

// 批量（PDF+JSON）
const pdfFile = ref<File | null>(null)
const batchRunning = ref(false)
const batchPages = ref<number | null>(null)

// 文件选择器引用与触发
const imageInputRef = ref<HTMLInputElement | null>(null)
const jsonInputRef = ref<HTMLInputElement | null>(null)
const jsonInputRef2 = ref<HTMLInputElement | null>(null)
const pdfInputRef = ref<HTMLInputElement | null>(null)

function triggerImagePick() {
  imageInputRef.value?.click() 
}
function triggerJsonPick() {
  (jsonInputRef.value ?? jsonInputRef2.value)?.click() 
}
function triggerPdfPick() {
  pdfInputRef.value?.click() 
}

function onPickImage(e: Event) {
  const el = e.target as HTMLInputElement
  imageFile.value = el.files?.[0] ?? null
}
function onPickJson(e: Event) {
  const el = e.target as HTMLInputElement
  jsonFile.value = el.files?.[0] ?? null
}
function onPickPdf(e: Event) {
  const el = e.target as HTMLInputElement
  pdfFile.value = el.files?.[0] ?? null
}

const imageName = computed(() => imageFile.value?.name || '未选择文件')
const jsonName = computed(() => jsonFile.value?.name || '未选择文件')
const pdfName = computed(() => pdfFile.value?.name || '未选择文件')

const canRun = computed(() => !!imageFile.value && !!jsonFile.value)

async function runAnnotate() {
  if (!canRun.value || running.value) return
  running.value = true
  try {
    const fd = new FormData()
    if (imageFile.value) fd.append('image', imageFile.value)
    if (jsonFile.value) fd.append('in_json', jsonFile.value)
    fd.append('page_index', String(pageIndex.value))
    fd.append('viz', viz.value)
    fd.append('iou', String(iou.value))
    const resp = await api.annotateTemplate(fd)
    resultJson.value = resp?.annotated ?? null
    visB64.value = resp?.viz_image_base64 ?? null
  }
  catch (e) {
    // 错误提示由 axios 拦截器处理
  }
  finally {
    running.value = false
  }
}

const prettyJson = computed(() => JSON.stringify(resultJson.value, null, 2))

function downloadJson() {
  if (!resultJson.value) return
  const blob = new Blob([JSON.stringify(resultJson.value, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'annotated_template.json'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

const canRunBatch = computed(() => !!pdfFile.value && !!jsonFile.value)

async function runBatchAnnotate() {
  if (!canRunBatch.value || batchRunning.value) return
  batchRunning.value = true
  try {
    const fd = new FormData()
    if (pdfFile.value) fd.append('pdf', pdfFile.value)
    if (jsonFile.value) fd.append('in_json', jsonFile.value)
    fd.append('viz', viz.value)
    fd.append('iou', String(iou.value))
    const resp = await api.annotatePdf(fd)
    resultJson.value = resp?.annotated ?? null
    batchPages.value = resp?.pages ?? null
    visB64.value = null // 批量暂不返回可视化图
  }
  catch (e) {
    // 错误提示由 axios 拦截器处理
  }
  finally {
    batchRunning.value = false
  }
}
</script>

<style scoped>
/* 与主页保持一致的页面骨架与背景 */
.aippt-page {
  position: relative;
  min-height: 100dvh;
  background: linear-gradient(135deg, #f6f9fc 0%, #ffffff 100%);
  overflow: hidden;
}

.page-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}
.page-bg .tech-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(99, 102, 241, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(99, 102, 241, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
}
.page-bg .float-sphere {
  position: absolute;
  border-radius: 50%;
}
.page-bg .float-sphere.s1 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle at 30% 30%, rgba(99, 102, 241, 0.15), transparent 70%);
  top: -100px;
  left: -100px;
  animation: float1 20s ease-in-out infinite;
}
.page-bg .float-sphere.s2 {
  width: 300px;
  height: 300px;
  background: radial-gradient(circle at 70% 70%, rgba(168, 85, 247, 0.12), transparent 70%);
  bottom: -50px;
  right: -50px;
  animation: float2 15s ease-in-out infinite;
}
.page-bg .float-sphere.s3 {
  width: 250px;
  height: 250px;
  background: radial-gradient(circle at 50% 50%, rgba(236, 72, 153, 0.1), transparent 70%);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation: float3 25s ease-in-out infinite;
}

@keyframes float1 {
  0%, 100% { transform: translate(0, 0) rotate(0deg); }
  33% { transform: translate(30px, -30px) rotate(120deg); }
  66% { transform: translate(-20px, 20px) rotate(240deg); }
}
@keyframes float2 {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-30px, -30px); }
}
@keyframes float3 {
  0%, 100% { transform: translate(-50%, -50%) scale(1); }
  50% { transform: translate(-50%, -50%) scale(1.1); }
}

.aippt-dialog {
  position: relative;
  z-index: 1;
  max-width: 1100px;
  margin: 0 auto;
  padding: 40px 20px;
}

.header-section { text-align: center; margin-bottom: 40px; position: relative; }
.header-section .brand { margin-bottom: 20px; }
.header-section .title { display: inline-flex; align-items: center; gap: 12px; margin: 0 0 12px 0; }
.header-section .title-main {
  font-size: 38px;
  font-weight: 700;
  background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -1px;
}
.header-section .title-badge {
  background: linear-gradient(135deg, #ec4899 0%, #f43f5e 100%);
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}
.header-section .subtitle { color: #64748b; font-size: 15px; }

.annotator-section { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.form-card {
  background: #fff;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 12px 30px rgba(0,0,0,.06);
}
.card-title { margin: 0 0 12px 0; font-size: 18px; color: #0f172a; }
.form-field { display: flex; flex-direction: column; gap: 10px; }
.form-field .label { font-size: 13px; color: #475569; }
.row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; align-items: center; }
.hint { margin-top: 8px; color: #64748b; }

/* 统一文件输入与按钮风格，增加与文本的间距 */
.hidden-input { display: none; }
.file-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.file-name { color: #64748b; font-size: 13px; }

/* 控件外观统一高度与圆角，减少拥挤感 */
.form-card input[type="number"],
.form-card select {
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  height: 36px;
}

/* 与按钮的间距 */
.form-card .btn { margin-top: 8px; }

.btn { display: inline-flex; align-items: center; justify-content: center; padding: 10px 18px; border: 0; border-radius: 999px; cursor: pointer; font-weight: 500; transition: all .3s; }
.btn-primary { background: linear-gradient(135deg, #667eea 0%, #a855f7 100%); color: #fff; box-shadow: 0 4px 15px rgba(102,126,234,.3); }
.btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(102,126,234,.4); }
.btn-secondary { background: #f1f5f9; color: #475569; }
.btn-secondary:hover { background: #e2e8f0; }

.result { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 20px; }
.preview img { max-width: 100%; border: 1px solid #e2e8f0; border-radius: 10px; }
.json textarea { width: 100%; border: 1px solid #e2e8f0; border-radius: 10px; padding: 8px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }

@media (max-width: 768px) {
  .annotator-section { grid-template-columns: 1fr; }
}
.annotator-page {
  --control-height: 40px;
}

/* 统一控件高度与圆角：button、number 输入、select 一致 */
.annotator-page .btn,
.annotator-page input[type="number"],
.annotator-page select {
  height: var(--control-height);
  line-height: calc(var(--control-height) - 2px);
  padding: 0 12px;
  border-radius: 10px;
  box-sizing: border-box;
}

/* 分隔线：button 与 span(label) 之间 */
.annotator-page .btn + .label,
.annotator-page .btn + span.label {
  position: relative;
  margin-left: 12px;
  padding-left: 12px;
}
.annotator-page .btn + .label::before,
.annotator-page .btn + span.label::before {
  content: "";
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 1px;
  height: 60%;
  background: rgba(255, 255, 255, 0.25);
}

/* 分隔线：button 与 button 之间 */
.annotator-page .btn + .btn {
  position: relative;
  margin-left: 12px;
  padding-left: 12px;
}
.annotator-page .btn + .btn::before {
  content: "";
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 1px;
  height: 60%;
  background: rgba(255, 255, 255, 0.25);
}

/* 保持 number 输入文本居中对齐的视觉一致性 */
.annotator-page input[type="number"] {
  -moz-appearance: textfield;
}
.annotator-page input[type="number"]::-webkit-outer-spin-button,
.annotator-page input[type="number"]::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

/* select 的文字与箭头布局优化 */
.annotator-page select {
  background-color: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.18);
}

</style>