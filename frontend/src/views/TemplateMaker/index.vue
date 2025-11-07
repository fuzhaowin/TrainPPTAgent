<template>
  <div class="aippt-page">
    <!-- 背景与容器与首页一致 -->
    <div class="page-bg" aria-hidden="true">
      <div class="tech-grid"></div>
      <div class="float-sphere s1"></div>
      <div class="float-sphere s2"></div>
      <div class="float-sphere s3"></div>
    </div>

    <div class="aippt-dialog">
      <div class="header-section">
        <div class="brand">
          <h1 class="title">
            <span class="title-main">模板制作</span>
            <span class="title-badge">AI</span>
          </h1>
          <div class="subtitle">LLM 初标注 + 编辑器校正 + 样例验证</div>
        </div>
      </div>

  <div class="setup-section">
        <!-- （0）一键上传 PPTX 自动截屏并初标注 -->
        <div class="section-card">
          <div class="section-title">
            <span class="title-text">（0）单页PPTX初标注</span>
            <span class="hint-text">自动解析 → 生成截图 → 初标注</span>
          </div>

          <div class="form-grid">
            <div class="form-item">
              <label class="form-label">PPTX 文件</label>
              <input type="file" accept=".pptx" @change="onPPTXUpload" />
            </div>
            <div class="form-item">
              <label class="form-label">页面索引(需要初标注页面在PPTX中的页码，从0开始)</label>
              <input type="number" min="0" :max="maxSlideIndex" v-model.number="pptxPageIndex" />
            </div>
          </div>

          <div class="action-group">
            <button class="act-btn primary" :disabled="pptxAnnotating || !pptxFile" @click="runPPTXOneClick">
              <span>{{ pptxAnnotating ? '处理中…' : '一键初标注' }}</span>
            </button>
            <button class="act-btn secondary" :disabled="pptxAnnotating || !annotateResult" @click="loadAnnotatedToEditor('pptx')">加载到编辑器</button>
          </div>

          <!-- 隐藏的缩略渲染容器，用于截图生成 -->
          <div class="thumb-stage" ref="thumbStageRef" aria-hidden="true">
            <ThumbnailSlide v-if="thumbSlide" :slide="thumbSlide" :size="1000" />
          </div>
        </div>

        <!-- 一、LLM 初标注 -->
        <div class="section-card">
          <div class="section-title">
            <span class="title-text">（1）单页JSON初标注</span>
            <span class="hint-text">上传幻灯片截图与未标注 JSON，自动生成模板草稿</span>
          </div>

          <div class="form-grid">
            <div class="form-item">
              <label class="form-label">幻灯片图片</label>
              <input type="file" accept="image/*" @change="onImageChange" />
            </div>
            <div class="form-item">
              <label class="form-label">未标注 JSON</label>
              <input type="file" accept="application/json" @change="onRawJsonChange" />
            </div>
          </div>

          <div class="action-group">
            <button class="act-btn primary" :disabled="annotating || !imageB64 || !rawSlideJson" @click="runAnnotate">
              <span>{{ annotating ? '初标注中…' : '执行初标注' }}</span>
            </button>
            <button class="act-btn secondary" :disabled="annotating || !annotateResult" @click="loadAnnotatedToEditor('json')">加载到编辑器</button>
          </div>

          

          
        </div>

        <!-- 二、生成标准化模板（批量） -->
        <div class="section-card">
          <div class="section-title">
            <span class="title-text">（2）生成标准化模板</span>
            <span class="hint-text">选择多个已初标注 JSON，重写并合并为一个模板</span>
          </div>
          <div class="form-grid">
            <div class="form-item">
              <label class="form-label">选择多个初标注 JSON（支持多选）</label>
              <input type="file" accept="application/json" multiple @change="onBatchAnnotatedJsonChange" />
            </div>
          </div>
          <div class="action-group">
            <button class="act-btn primary" :disabled="batchRewriting || batchAnnotatedJsonList.length === 0" @click="runBatchRewriteAndMerge">
              <span>{{ batchRewriting ? '重写并合并中…' : '标准化重写并合并' }}</span>
            </button>
            <button class="act-btn secondary" :disabled="!mergedTemplateJsonBatch" @click="downloadJson(mergedTemplateJsonBatch, 'template_merged.json')">下载合并模板JSON</button>
          </div>
          <div v-if="mergedTemplateJsonBatch" class="result-block">
            <div class="result-title">合并模板结果（JSON来源）</div>
            <pre class="json-view">{{ pretty(mergedTemplateJsonBatch) }}</pre>
          </div>
        </div>

        <!-- 三、一键生成标准化模板（从PPTX索引范围） -->
        <div class="section-card">
          <div class="section-title">
            <span class="title-text">（3）一键生成标准化模板</span>
            <span class="hint-text">从PPTX选择索引范围，自动执行 初标注→重写→合并→下载</span>
          </div>
          <div class="form-grid">
            <div class="form-item">
              <label class="form-label">PPTX 文件（批量）</label>
              <input type="file" accept=".pptx" @change="onBatchPPTXUpload" />
            </div>
            <div class="form-item">
              <label class="form-label">从PPTX选择索引范围（示例：0-3,5,7-8；从0开始）</label>
              <input type="text" placeholder="例如：0-3,5,7-8" v-model="batchIndexRangeInput" />
              <span class="hint-text">当前PPTX最大索引：{{ batchMaxSlideIndex }}</span>
            </div>
          </div>
          <div class="action-group">
            <button class="act-btn primary" :disabled="batchProcessing || !batchPPTXFile || !batchIndexRangeInput" @click="runBatchFromPptxRange">
              <span>{{ batchProcessing ? '批量生成中…' : '从PPTX索引范围批量生成' }}</span>
            </button>
            <button class="act-btn secondary" :disabled="!mergedTemplatePptxBatch" @click="downloadJson(mergedTemplatePptxBatch, 'template_merged_from_pptx.json')">下载合并模板JSON</button>
          </div>
          <div v-if="mergedTemplatePptxBatch" class="result-block">
            <div class="result-title">合并模板结果（PPTX来源）</div>
            <pre class="json-view">{{ pretty(mergedTemplatePptxBatch) }}</pre>
          </div>
        </div>

        <!-- 四、样例数据验证 -->
        <div class="section-card">
          <div class="section-title">
            <span class="title-text">（4）样例数据验证</span>
            <span class="hint-text">载入模板 JSON 与样例数据，生成并在编辑器预览</span>
          </div>

        <div class="form-grid">
          <div class="form-item">
            <label class="form-label">模板 JSON（包含 slides / theme）</label>
            <input type="file" accept="application/json" @change="onTemplateJsonChange" />
          </div>
          <div class="form-item">
            <label class="form-label">样例数据 JSON（数组：{type,data}）</label>
            <input type="file" accept="application/json" @change="onSampleJsonChange" />
          </div>
        </div>

        <div class="action-group">
          <button class="act-btn primary" :disabled="validating || !templateJson || !sampleData" @click="startValidation">
            <span>{{ validating ? '生成中…' : '开始验证并预览' }}</span>
          </button>
        </div>
      </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { nextTick, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSlidesStore, useMainStore } from '@/store'
import useAIPPT from '@/hooks/useAIPPT'
import useAddSlidesOrElements from '@/hooks/useAddSlidesOrElements'
import { SERVER_URL } from '@/services'
import { toPng } from 'html-to-image'
import ThumbnailSlide from '@/views/components/ThumbnailSlide/index.vue'
import useImport from '@/hooks/useImport'

const router = useRouter()
const slideStore = useSlidesStore()
const mainStore = useMainStore()
const { AIPPTGenerator } = useAIPPT()
const { addSlidesFromDataToEnd } = useAddSlidesOrElements()
const { importPPTXFile } = useImport()

// LLM 初标注
const imageB64 = ref<string>('')
const rawSlideJson = ref<any>(null)
const annotating = ref(false)
const annotateResult = ref<any>(null)
// 批量标准化重写与合并
const batchAnnotatedJsonList = ref<any[]>([])
const batchRewriting = ref(false)
const mergedTemplateJsonBatch = ref<any>(null)
// 批量：从PPTX按索引范围执行“初标注→重写→合并”
const batchPPTXFile = ref<File | null>(null)
const batchIndexRangeInput = ref('')
const batchProcessing = ref(false)
const batchMaxSlideIndex = ref<number>(0)
const mergedTemplatePptxBatch = ref<any>(null)

// 一键 PPTX 初标注
const pptxFile = ref<File | null>(null)
const pptxAnnotating = ref(false)
const pptxPageIndex = ref(0)
const thumbStageRef = ref<HTMLElement | null>(null)

// 统一清洗 DataURL，只返回纯 base64 内容，去除前缀与空白
const toPureBase64 = (dataUrl: string | null | undefined): string => {
  if (!dataUrl) return ''
  let s = String(dataUrl).trim()
  // data:image/png;base64,xxxx 或 data:image/jpeg;base64,xxxx
  if (s.startsWith('data:') && s.includes(',')) {
    s = s.split(',', 1)[0] ? s.split(',', 2)[1] : s
  }
  // 去除可能的换行/空白字符
  s = s.replace(/\s+/g, '')
  return s
}
const thumbSlide = ref<any>(null)
const maxSlideIndex = ref(0)

const onPPTXUpload = (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0] || null
  pptxFile.value = file
}

const runPPTXOneClick = async () => {
  if (!pptxFile.value) return
  pptxAnnotating.value = true
  try {
    const fileList = { 0: pptxFile.value, length: 1 } as unknown as FileList
    importPPTXFile(fileList, { cover: true, fixedViewport: true })
    await nextTick()

    const slides = slideStore.slides
    maxSlideIndex.value = Math.max(0, slides.length - 1)
    const idx = Math.min(Math.max(0, pptxPageIndex.value), maxSlideIndex.value)
    thumbSlide.value = slides[idx]
    await nextTick()

    if (!thumbStageRef.value) throw new Error('截图容器未就绪')
    const dataUrl = await toPng(thumbStageRef.value, { width: 800 })
    const image_b64 = toPureBase64(dataUrl)

    const json = {
      title: '未命名演示文稿',
      width: slideStore.viewportSize,
      height: slideStore.viewportSize * slideStore.viewportRatio,
      theme: slideStore.theme,
      slides: [thumbSlide.value],
    }

    const resp = await fetch(`${SERVER_URL}/template/annotate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_b64, slide_json: json })
    })
    if (!resp.ok) throw new Error(`后端错误：${resp.status}`)
    const data = await resp.json()
    annotateResult.value = data
  } catch (err) {
    console.error('一键初标注失败', err)
  } finally {
    pptxAnnotating.value = false
  }
}

const onImageChange = (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    imageB64.value = (reader.result as string) || ''
  }
  reader.readAsDataURL(file)
}

const onRawJsonChange = (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    try {
      rawSlideJson.value = JSON.parse(String(reader.result))
    } catch (err) {
      console.error('JSON 解析失败', err)
      rawSlideJson.value = null
    }
  }
  reader.readAsText(file, 'utf-8')
}

const runAnnotate = async () => {
  annotating.value = true
  annotateResult.value = null
  try {
    const resp = await fetch(`${SERVER_URL}/template/annotate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_b64: toPureBase64(imageB64.value), slide_json: rawSlideJson.value })
    })
    if (!resp.ok) throw new Error(`后端错误：${resp.status}`)
    const data = await resp.json()
    annotateResult.value = data
  } catch (err) {
    console.error(err)
  } finally {
    annotating.value = false
  }
}

const onBatchAnnotatedJsonChange = (e: Event) => {
  const files = (e.target as HTMLInputElement).files
  batchAnnotatedJsonList.value = []
  if (!files || files.length === 0) return
  const readers: Promise<void>[] = []
  for (let i = 0; i < files.length; i++) {
    const f = files[i]
    readers.push(new Promise((resolve) => {
      const reader = new FileReader()
      reader.onload = () => {
        try {
          const obj = JSON.parse(String(reader.result))
          batchAnnotatedJsonList.value.push(obj)
        } catch (err) {
          console.error('初标注JSON解析失败', err)
        }
        resolve()
      }
      reader.readAsText(f, 'utf-8')
    }))
  }
  Promise.all(readers).then(() => void 0)
}

const onBatchPPTXUpload = (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0] || null
  batchPPTXFile.value = file
}

const runBatchRewriteAndMerge = async () => {
  if (!batchAnnotatedJsonList.value.length) return
  batchRewriting.value = true
  mergedTemplateJsonBatch.value = null
  try {
    const slides: any[] = []
    let width: number | null = null
    let height: number | null = null
    let theme: any = null

    for (const src of batchAnnotatedJsonList.value) {
      // 兼容输入：可能是canonical、doc或单页slide
      let slideInput: any = null
      if (src?.canonical) {
        // 已是标准文档，取第一张作为单页输入继续重写（稳妥方式统一结构）
        slideInput = (src.canonical.slides && src.canonical.slides[0]) ? src.canonical.slides[0] : src.canonical
      } else if (Array.isArray(src?.slides)) {
        slideInput = src.slides[0] || src
      } else {
        slideInput = src
      }

      const body = { slide_json: slideInput, strict: false }
      const resp = await fetch(`${SERVER_URL}/template/rewrite`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })
      if (!resp.ok) throw new Error(`后端错误：${resp.status}`)
      const data = await resp.json()
      const canonical = data?.canonical
      const cs = Array.isArray(canonical?.slides) ? canonical.slides[0] : null
      if (cs) slides.push(cs)
      if (width == null) width = canonical?.width || null
      if (height == null) height = canonical?.height || null
      if (theme == null) theme = canonical?.theme || null
    }

    const merged = {
      width: width ?? 960,
      height: height ?? 540,
      theme: theme ?? null,
      slides,
    }
    mergedTemplateJsonBatch.value = merged
  } catch (err) {
    console.error('批量标准化重写与合并失败', err)
  } finally {
    batchRewriting.value = false
  }
}


// 解析索引范围字符串为索引数组（示例："0-3,5,7-8"）
const parseIndexRange = (input: string, maxIndex: number): number[] => {
  const result: number[] = []
  const parts = input.split(',').map(s => s.trim()).filter(Boolean)
  for (const p of parts) {
    if (p.includes('-')) {
      const [a, b] = p.split('-').map(x => Number(x))
      if (Number.isFinite(a) && Number.isFinite(b)) {
        const start = Math.max(0, Math.min(a, b))
        const end = Math.min(maxIndex, Math.max(a, b))
        for (let i = start; i <= end; i++) result.push(i)
      }
    } else {
      const n = Number(p)
      if (Number.isFinite(n) && n >= 0 && n <= maxIndex) result.push(n)
    }
  }
  // 去重并排序
  return Array.from(new Set(result)).sort((x, y) => x - y)
}

// 从PPTX选择索引范围，批量执行“初标注→重写→合并→下载”
const runBatchFromPptxRange = async () => {
  if (!batchPPTXFile.value || !batchIndexRangeInput.value) return
  batchProcessing.value = true
  mergedTemplatePptxBatch.value = null
  try {
    // 1) 导入PPTX并获取全部页面
    const fileList = { 0: batchPPTXFile.value, length: 1 } as unknown as FileList
    importPPTXFile(fileList, { cover: true, fixedViewport: true })
    await nextTick()

    const slides = slideStore.slides
    const maxIdx = Math.max(0, slides.length - 1)
    batchMaxSlideIndex.value = maxIdx

    // 2) 解析索引范围
    const indices = parseIndexRange(batchIndexRangeInput.value, maxIdx)
    if (!indices.length) throw new Error('索引范围为空或不合法')

    const outSlides: any[] = []
    let width: number | null = null
    let height: number | null = null
    let theme: any = null

    // 公共尺寸/主题数据（每次仅发送当前索引对应的单页）
    const docBase = {
      title: '批量生成演示文稿',
      width: slideStore.viewportSize,
      height: slideStore.viewportSize * slideStore.viewportRatio,
      theme: slideStore.theme,
    }

    // 3) 逐索引执行：截图→初标注→重写→收集canonical slide
    for (const idx of indices) {
      // 3.1 设置缩略图场景并截图
      thumbSlide.value = slides[idx]
      await nextTick()
      if (!thumbStageRef.value) throw new Error('截图容器未就绪')
      const dataUrl = await toPng(thumbStageRef.value, { width: 800 })
      const image_b64 = toPureBase64(dataUrl)

      // 3.2 初标注
      const resp1 = await fetch(`${SERVER_URL}/template/annotate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_b64, slide_json: { ...docBase, slides: [slides[idx]] } })
      })
      if (!resp1.ok) throw new Error(`后端错误：${resp1.status}`)
      const annotated = await resp1.json()
      const slideInput = annotated?.merged_slide || slides[idx]

      // 3.3 标准化重写
      const resp2 = await fetch(`${SERVER_URL}/template/rewrite`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slide_json: slideInput, strict: false })
      })
      if (!resp2.ok) throw new Error(`后端错误：${resp2.status}`)
      const data2 = await resp2.json()
      const canonical = data2?.canonical
      const cs = Array.isArray(canonical?.slides) ? canonical.slides[0] : canonical
      if (cs) outSlides.push(cs)
      if (width == null) width = canonical?.width || null
      if (height == null) height = canonical?.height || null
      if (theme == null) theme = canonical?.theme || null
    }

    // 4) 合并并提供下载
    const merged = {
      width: width ?? 960,
      height: height ?? 540,
      theme: theme ?? null,
      slides: outSlides,
    }
    mergedTemplatePptxBatch.value = merged
  } catch (err) {
    console.error('从PPTX索引范围批量生成失败', err)
  } finally {
    batchProcessing.value = false
  }
}


const downloadJson = (obj: any, filename: string) => {
  const blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

// 样例数据验证
const templateJson = ref<any>(null)
const sampleData = ref<any[]>([])
const validating = ref(false)

const onTemplateJsonChange = (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    try {
      templateJson.value = JSON.parse(String(reader.result))
    } catch (err) {
      console.error('模板 JSON 解析失败', err)
      templateJson.value = null
    }
  }
  reader.readAsText(file, 'utf-8')
}

const onSampleJsonChange = (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    try {
      const json = JSON.parse(String(reader.result))
      sampleData.value = Array.isArray(json) ? json : []
    } catch (err) {
      console.error('样例 JSON 解析失败', err)
      sampleData.value = []
    }
  }
  reader.readAsText(file, 'utf-8')
}

const startValidation = async () => {
  if (!templateJson.value || !sampleData.value.length) return
  validating.value = true
  try {
    const templateSlides = templateJson.value.slides || []
    const templateTheme = templateJson.value.theme || null
    if (templateTheme) {
      slideStore.setTheme(templateTheme)
    }
    slideStore.resetSlides()

    const generator = AIPPTGenerator(templateSlides, sampleData.value)
    for (const s of generator) {
      addSlidesFromDataToEnd([s])
    }
    // 跳转到编辑器预览结果
    router.push('/editor')
  } catch (err) {
    console.error('验证失败', err)
  } finally {
    validating.value = false
  }
}

// 将初标注结果加载到编辑器进行人工校对
const loadAnnotatedToEditor = async (source: 'pptx' | 'json') => {
  try {
    // 优先使用初标注返回的 merged_slide；如不存在则使用原始JSON
    const baseInput = annotateResult.value?.merged_slide || (source === 'json' ? rawSlideJson.value : null)
    if (!baseInput) {
      console.warn('暂无可加载的初标注结果')
      return
    }

    // 为保证与编辑器兼容，调用后端标准化重写为 canonical 文档结构
    const resp = await fetch(`${SERVER_URL}/template/rewrite`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slide_json: baseInput, strict: false })
    })
    if (!resp.ok) throw new Error(`后端错误：${resp.status}`)
    const data = await resp.json()
    const canonical = data?.canonical
    if (!canonical) {
      console.warn('标准化重写返回为空，无法加载到编辑器')
      return
    }

    // 应用主题并设置幻灯片到编辑器
    const slides = Array.isArray(canonical.slides) ? canonical.slides : [canonical]
    if (canonical.theme) {
      slideStore.setTheme(canonical.theme)
    }
    slideStore.setSlides(slides)
    slideStore.updateSlideIndex(0)

    // 打开编辑器进行人工校对
    router.push('/editor')
  } catch (err) {
    console.error('加载到编辑器失败', err)
  }
}

const pretty = (obj: any) => JSON.stringify(obj, null, 2)
</script>

<style scoped lang="scss">
/* 与首页保持完全一致的页面骨架与背景（除按钮外） */
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

  .tech-grid {
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(99, 102, 241, 0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(99, 102, 241, 0.03) 1px, transparent 1px);
    background-size: 40px 40px;
  }

  .float-sphere {
    position: absolute;
    border-radius: 50%;

    &.s1 {
      width: 400px;
      height: 400px;
      background: radial-gradient(circle at 30% 30%, rgba(99, 102, 241, 0.15), transparent 70%);
      top: -100px;
      left: -100px;
      animation: float1 20s ease-in-out infinite;
    }

    &.s2 {
      width: 300px;
      height: 300px;
      background: radial-gradient(circle at 70% 70%, rgba(168, 85, 247, 0.12), transparent 70%);
      bottom: -50px;
      right: -50px;
      animation: float2 15s ease-in-out infinite;
    }

    &.s3 {
      width: 250px;
      height: 250px;
      background: radial-gradient(circle at 50% 50%, rgba(236, 72, 153, 0.1), transparent 70%);
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      animation: float3 25s ease-in-out infinite;
    }
  }
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

.header-section {
  text-align: center;
  margin-bottom: 32px;

  .brand {
    margin-bottom: 24px;

    .title {
      display: inline-flex;
      align-items: center;
      gap: 12px;
      margin: 0 0 12px 0;

      .title-main {
        font-size: 42px;
        font-weight: 700;
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1px;
      }

      .title-badge {
        background: linear-gradient(135deg, #ec4899 0%, #f43f5e 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
      }
    }

    .subtitle {
      color: #64748b;
      font-size: 15px;
    }
  }
}

.setup-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.section-title {
  margin-bottom: 16px;

  .title-text {
    font-size: 14px;
    font-weight: 600;
    color: #334155;
    text-transform: uppercase;
    letter-spacing: 1px;
  }
}

.section-card {
  background: white;
  border-radius: 20px;
  padding: 28px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08);
}

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.form-item { display: flex; flex-direction: column; gap: 6px; }
.form-label { font-size: 13px; color: #64748b; font-weight: 500; }
.hint-text { color: #94a3b8; font-size: 12px; }

/* 保留按钮可差异化，故不强制统一按钮样式 */

.thumb-stage { position: absolute; left: -9999px; top: -9999px; width: 1000px; height: auto; overflow: hidden; }

.result-block { margin-top: 12px; }
.result-title { font-size: 13px; color: #334155; margin-bottom: 6px; }
.json-view { max-height: 260px; overflow: auto; background: #f8fafc; border: 2px solid #e2e8f0; border-radius: 12px; padding: 12px; color: #334155; }

/* 按钮与首页保持一致风格 */
.action-group {
  display: flex;
  gap: 16px;
}

.act-btn {
  padding: 14px 36px;
  border-radius: 100px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
  border: none;

  &.primary {
    background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
    color: white;
    box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);

    &:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4);
    }
  }

  &.secondary {
    background: #f1f5f9;
    color: #475569;

    &:hover:not(:disabled) {
      background: #e2e8f0;
    }
  }

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
}

@media (max-width: 768px) {
  .header-section {
    .brand .title .title-main { font-size: 32px; }
  }

  .form-grid { grid-template-columns: 1fr; }
}
</style>