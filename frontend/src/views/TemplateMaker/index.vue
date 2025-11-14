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
            <button class="act-btn secondary" :disabled="pptxAnnotating || !annotateResult || !annotateResult.merged_slide" @click="downloadJson(annotateResult.merged_slide, 'annotated_slide.json')">下载初标注 JSON</button>
          </div>

          <!-- 在新标签打开编辑器的开关（避免离开页面后无法查看重写诊断） -->
          <div class="inline-option">
            <label><input type="checkbox" v-model="openEditorInNewTab" /> 在新标签打开编辑器</label>
          </div>

          <!-- （调试）初标注与重写关键字段折叠区：复用于 PPTX 初标注块 -->
          <div class="section-card debug-card">
            <div class="section-title">
              <span class="title-text">调试信息（PPTX 初标注）</span>
              <span class="hint-text">初标注与重写的关键字段</span>
            </div>
            <details class="debug-collapse">
              <summary>展开 / 收起</summary>
              <div class="debug-content">
                <div class="debug-block">
                  <div class="debug-title">截图预览</div>
                  <div v-if="screenshotDebug && screenshotDebug.url" class="debug-image-wrap">
                    <img :src="screenshotDebug.url" alt="初标注截图" class="debug-image" />
                  <div class="debug-caption">截图尺寸：{{ screenshotDebug.sizeText }}</div>
                    <div class="debug-actions"><a :href="screenshotDebug.url" target="_blank">在新标签打开原图</a><a href="#" @click.prevent="downloadScreenshot">下载截图 PNG</a></div>
                  </div>
                  <div v-else class="debug-empty">暂无截图</div>
                </div>
                <div class="debug-block">
                  <div class="debug-title">初标注（/template/annotate）</div>
                  <div v-if="annotatedDebug" class="debug-list">
                    <div class="debug-item"><span class="debug-key">页面尺寸</span><span class="debug-val">{{ annotatedDebug.size }}</span></div>
                    <div class="debug-item"><span class="debug-key">画布尺寸</span><span class="debug-val">{{ annotatedDebug.canvas }}</span></div>
                    <div class="debug-item"><span class="debug-key">页面类型</span><span class="debug-val">{{ annotatedDebug.pageType }}</span></div>
                    <div class="debug-item"><span class="debug-key">元素数量</span><span class="debug-val">{{ annotatedDebug.elementCount }}</span></div>
                    <div class="debug-item"><span class="debug-key">元素类型分布</span><span class="debug-val">{{ annotatedDebug.elementTypes }}</span></div>
                    <div class="debug-item"><span class="debug-key">平均面积(px²)</span><span class="debug-val">{{ annotatedDebug.avgArea }}</span></div>
                    <div class="debug-item"><span class="debug-key">最小尺寸</span><span class="debug-val">{{ annotatedDebug.minSize }}</span></div>
                    <div class="debug-item"><span class="debug-key">最大尺寸</span><span class="debug-val">{{ annotatedDebug.maxSize }}</span></div>
                    <div class="debug-item"><span class="debug-key">文本行数统计</span><span class="debug-val">{{ annotatedDebug.textLines }}</span></div>
                  </div>
                  <div v-else class="debug-empty">暂无初标注结果</div>
                </div>
                <div class="debug-block">
                  <div class="debug-title">标准化重写（/template/rewrite）</div>
                  <div v-if="rewriteDebug" class="debug-list">
                    <div class="debug-item"><span class="debug-key">文档尺寸</span><span class="debug-val">{{ rewriteDebug.docSize }}</span></div>
                    <div class="debug-item"><span class="debug-key">页数</span><span class="debug-val">{{ rewriteDebug.slideCount }}</span></div>
                    <div class="debug-item"><span class="debug-key">每页元素数量</span><span class="debug-val">{{ rewriteDebug.elementsPerSlide }}</span></div>
                    <div class="debug-item"><span class="debug-key">主题规范化</span><span class="debug-val">{{ rewriteDebug.normalizedTheme }}</span></div>
                  </div>
                  <div v-else class="debug-empty">暂无重写诊断信息</div>
                </div>
              </div>
            </details>
          </div>

          <!-- 隐藏的缩略渲染容器，用于截图生成（宽高与当前画布一致） -->
          <div class="thumb-stage" ref="thumbStageRef" aria-hidden="true" :style="{ width: slideStore.viewportSize + 'px', height: (slideStore.viewportSize * slideStore.viewportRatio) + 'px' }">
            <ThumbnailSlide v-if="thumbSlide" :slide="thumbSlide" :size="slideStore.viewportSize" />
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
            <button class="act-btn secondary" :disabled="annotating || !annotateResult || !annotateResult.merged_slide" @click="downloadJson(annotateResult.merged_slide, 'annotated_slide.json')">下载初标注 JSON</button>
          </div>

          <!-- 在新标签打开编辑器的开关（避免离开页面后无法查看重写诊断） -->
          <div class="inline-option">
            <label><input type="checkbox" v-model="openEditorInNewTab" /> 在新标签打开编辑器</label>
          </div>

          <!-- （调试）初标注与重写关键字段折叠区：元素数量、尺寸、page_type 等 -->
          <div class="section-card debug-card">
            <div class="section-title">
              <span class="title-text">调试信息</span>
              <span class="hint-text">初标注与重写的关键字段</span>
            </div>
            <details class="debug-collapse">
              <summary>展开 / 收起</summary>
              <div class="debug-content">
                <div class="debug-block">
                  <div class="debug-title">截图预览</div>
                  <div v-if="screenshotDebug && screenshotDebug.url" class="debug-image-wrap">
                    <img :src="screenshotDebug.url" alt="初标注截图" class="debug-image" />
                    <div class="debug-caption">截图尺寸：{{ screenshotDebug.sizeText }}</div>
                    <div class="debug-actions"><a :href="screenshotDebug.url" target="_blank">在新标签打开原图</a></div>
                  </div>
                  <div v-else class="debug-empty">暂无截图</div>
                </div>
                <div class="debug-block">
                  <div class="debug-title">初标注（/template/annotate）</div>
                  <div v-if="annotatedDebug" class="debug-list">
                    <div class="debug-item"><span class="debug-key">页面尺寸</span><span class="debug-val">{{ annotatedDebug.size }}</span></div>
                    <div class="debug-item"><span class="debug-key">画布尺寸</span><span class="debug-val">{{ annotatedDebug.canvas }}</span></div>
                    <div class="debug-item"><span class="debug-key">页面类型</span><span class="debug-val">{{ annotatedDebug.pageType }}</span></div>
                    <div class="debug-item"><span class="debug-key">元素数量</span><span class="debug-val">{{ annotatedDebug.elementCount }}</span></div>
                    <div class="debug-item"><span class="debug-key">元素类型分布</span><span class="debug-val">{{ annotatedDebug.elementTypes }}</span></div>
                  </div>
                  <div v-else class="debug-empty">暂无初标注结果</div>
                </div>
                <div class="debug-block">
                  <div class="debug-title">标准化重写（/template/rewrite）</div>
                  <div v-if="rewriteDebug" class="debug-list">
                    <div class="debug-item"><span class="debug-key">文档尺寸</span><span class="debug-val">{{ rewriteDebug.docSize }}</span></div>
                    <div class="debug-item"><span class="debug-key">页数</span><span class="debug-val">{{ rewriteDebug.slideCount }}</span></div>
                    <div class="debug-item"><span class="debug-key">每页元素数量</span><span class="debug-val">{{ rewriteDebug.elementsPerSlide }}</span></div>
                    <div class="debug-item"><span class="debug-key">主题规范化</span><span class="debug-val">{{ rewriteDebug.normalizedTheme }}</span></div>
                  </div>
                  <div v-else class="debug-empty">暂无重写诊断信息</div>
                </div>
              </div>
            </details>
          </div>

          <!-- 重写诊断信息展示：帮助定位空白画布或元素被过滤问题 -->
          <div v-if="rewriteDiagnostics" class="result-block">
            <div class="result-title">重写诊断信息</div>
            <pre class="json-view">{{ pretty(rewriteDiagnostics) }}</pre>
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

      <!-- 五、模板注册（管理端） -->
      <div class="section-card">
        <div class="section-title">
          <span class="title-text">（5）模板注册</span>
          <span class="hint-text">将上方合并结果或自有 JSON 注册到服务端模板库</span>
        </div>

        <!-- 管理员令牌设置 -->
        <div class="form-grid">
          <div class="form-item">
            <label class="form-label">管理员令牌（X-Admin-Token）</label>
            <input v-model="adminToken" type="text" placeholder="请输入管理员令牌" />
            <span class="hint-text">用于调用管理接口，仅在本地浏览器保存</span>
          </div>
          <div class="form-item">
            <label class="form-label">令牌操作</label>
            <div class="action-group">
              <button class="act-btn secondary" @click="saveAdminToken">保存令牌</button>
              <button class="act-btn secondary" @click="clearAdminToken">清除令牌</button>
            </div>
          </div>
        </div>

        <!-- 快速注册：使用上方合并结果 -->
        <div class="section-title" style="margin-top:12px">
          <span class="title-text">快速注册（使用合并结果）</span>
          <span class="hint-text">直接将第（2）或第（3）步的合并JSON注册为模板</span>
        </div>
        <div class="form-grid">
          <div class="form-item">
            <label class="form-label">模板ID（字母、数字、短横线、下划线）</label>
            <input v-model="quickRegister.id" type="text" placeholder="例如：my-template-001" />
          </div>
          <div class="form-item">
            <label class="form-label">模板名称（可选）</label>
            <input v-model="quickRegister.name" type="text" placeholder="例如：我的模板v1" />
          </div>
        </div>
        <div class="action-group">
          <button class="act-btn primary" :disabled="!canQuickRegisterBatch || !adminToken" @click="submitQuickRegister('json')">使用第（2）步结果注册</button>
          <button class="act-btn secondary" :disabled="!canQuickRegisterPptx || !adminToken" @click="submitQuickRegister('pptx')">使用第（3）步结果注册</button>
        </div>

        <!-- 通过地址注册 -->
        <div class="section-title" style="margin-top:20px">
          <span class="title-text">通过地址注册</span>
          <span class="hint-text">适用于已有线上JSON与封面地址的情况</span>
        </div>
        <div class="form-grid">
          <div class="form-item">
            <label class="form-label">模板ID</label>
            <input v-model="registerByUrl.id" type="text" placeholder="my-template-001" />
          </div>
          <div class="form-item">
            <label class="form-label">模板名称（可选）</label>
            <input v-model="registerByUrl.name" type="text" />
          </div>
          <div class="form-item">
            <label class="form-label">JSON地址</label>
            <input v-model="registerByUrl.json_url" type="text" placeholder="https://example.com/template.json" />
          </div>
          <div class="form-item">
            <label class="form-label">封面地址（可选）</label>
            <input v-model="registerByUrl.cover_url" type="text" placeholder="https://example.com/cover.png" />
          </div>
        </div>
        <div class="action-group">
          <button class="act-btn primary" :disabled="!adminToken" @click="submitRegisterByUrl">注册模板</button>
        </div>

        <!-- 上传/粘贴注册 -->
        <div class="section-title" style="margin-top:20px">
          <span class="title-text">通过上传或粘贴注册</span>
          <span class="hint-text">上传JSON文件、封面或直接粘贴JSON文本</span>
        </div>
        <div class="form-grid">
          <div class="form-item">
            <label class="form-label">模板ID</label>
            <input v-model="registerByUpload.id" type="text" placeholder="my-template-001" />
          </div>
          <div class="form-item">
            <label class="form-label">模板名称（可选）</label>
            <input v-model="registerByUpload.name" type="text" />
          </div>
          <div class="form-item">
            <label class="form-label">上传JSON文件</label>
            <input type="file" accept="application/json" @change="onUploadJsonFile" />
          </div>
          <div class="form-item">
            <label class="form-label">或粘贴JSON文本</label>
            <textarea v-model="registerByUpload.json_text" rows="4" placeholder="粘贴完整模板JSON"></textarea>
          </div>
          <div class="form-item">
            <label class="form-label">上传封面（可选）</label>
            <input type="file" accept="image/*" @change="onUploadCoverFile" />
          </div>
        </div>
        <div class="action-group">
          <button class="act-btn primary" :disabled="!adminToken" @click="submitRegisterByUpload">注册模板</button>
        </div>
      </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { nextTick, ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useSlidesStore, useMainStore } from '@/store'
import useAIPPT from '@/hooks/useAIPPT'
import useAddSlidesOrElements from '@/hooks/useAddSlidesOrElements'
import api, { SERVER_URL } from '@/services'
import message from '@/utils/message'
import { toPng } from 'html-to-image'
import ThumbnailSlide from '@/views/components/ThumbnailSlide/index.vue'
import useImport from '@/hooks/useImport'
import { nanoid } from 'nanoid'

const router = useRouter()
const slideStore = useSlidesStore()
const mainStore = useMainStore()
const { AIPPTGenerator } = useAIPPT()
const { addSlidesFromDataToEnd } = useAddSlidesOrElements()
// 导入 PPTX：拿到 exporting 标志以等待导入完成
const { importPPTXFile, exporting: importing } = useImport()

// LLM 初标注
const imageB64 = ref<string>('')
const rawSlideJson = ref<any>(null)
const annotating = ref(false)
const annotateResult = ref<any>(null)
// 最近一次用于初标注的截图（DataURL），用于调试预览
const lastScreenshotDataUrl = ref<string>('')
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

// 重写诊断信息（用于定位空白画布或元素被过滤问题）
const rewriteDiagnostics = ref<any>(null)
// 是否在新标签打开编辑器，默认 true，避免离开当前页面看不到重写诊断
const openEditorInNewTab = ref<boolean>(true)

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

// ======================== 模板注册（管理端） ========================
const ADMIN_TOKEN_KEY = 'ADMIN_TOKEN'
const adminToken = ref<string>('')
onMounted(() => {
  const saved = localStorage.getItem(ADMIN_TOKEN_KEY)
  if (saved) adminToken.value = saved
  // 恢复重写诊断与打开方式
  const lastDiag = localStorage.getItem('TM_LAST_REWRITE_DIAGNOSTICS')
  if (lastDiag) {
    try {
      rewriteDiagnostics.value = JSON.parse(lastDiag) 
    }
    catch {
      void 0 
    }
  }
  const openInNewTab = localStorage.getItem('TM_OPEN_EDITOR_IN_NEW_TAB')
  if (openInNewTab) openEditorInNewTab.value = openInNewTab === '1'
})

// 持久化打开方式开关
watch(openEditorInNewTab, (v) => {
  localStorage.setItem('TM_OPEN_EDITOR_IN_NEW_TAB', v ? '1' : '0')
})

const saveAdminToken = () => {
  localStorage.setItem(ADMIN_TOKEN_KEY, adminToken.value)
  message.success('管理员令牌已保存')
}
const clearAdminToken = () => {
  localStorage.removeItem(ADMIN_TOKEN_KEY)
  adminToken.value = ''
  message.success('管理员令牌已清除')
}

// 快速注册（使用合并结果）
const quickRegister = ref<{ id: string; name?: string }>({ id: '', name: '' })
const canQuickRegisterBatch = computed(() => !!mergedTemplateJsonBatch.value)
const canQuickRegisterPptx = computed(() => !!mergedTemplatePptxBatch.value)

const submitQuickRegister = async (source: 'json'|'pptx') => {
  if (!adminToken.value) {
    message.error('请先填写并保存管理员令牌'); return 
  }
  const id = quickRegister.value.id.trim()
  if (!id || !/^[a-zA-Z0-9_-]+$/.test(id)) {
    message.error('模板ID格式不合法'); return 
  }
  const name = quickRegister.value.name?.trim() || ''
  const jsonObj = source === 'json' ? mergedTemplateJsonBatch.value : mergedTemplatePptxBatch.value
  if (!jsonObj) {
    message.error('没有可用的合并结果'); return 
  }
  const fd = new FormData()
  fd.append('tpl_id', id)
  if (name) fd.append('name', name)
  fd.append('json_text', JSON.stringify(jsonObj))
  try {
    await api.registerTemplateUpload(fd, adminToken.value)
    message.success('模板注册成功')
    quickRegister.value = { id: '', name: '' }
  }
  catch (e) {
    // 错误已由全局拦截器处理
  }
}

// 通过地址注册
const registerByUrl = ref<{ id: string; name?: string; json_url?: string; cover_url?: string }>({ id: '', name: '', json_url: '', cover_url: '' })
const submitRegisterByUrl = async () => {
  if (!adminToken.value) {
    message.error('请先填写并保存管理员令牌'); return 
  }
  const id = registerByUrl.value.id.trim()
  if (!id || !/^[a-zA-Z0-9_-]+$/.test(id)) {
    message.error('模板ID格式不合法'); return 
  }
  const payload = {
    id,
    name: registerByUrl.value.name?.trim() || undefined,
    json_url: registerByUrl.value.json_url?.trim() || undefined,
    cover_url: registerByUrl.value.cover_url?.trim() || undefined,
  }
  if (!payload.json_url) {
    message.error('请填写JSON地址'); return 
  }
  try {
    await api.registerTemplate(payload, adminToken.value)
    message.success('模板注册成功')
    registerByUrl.value = { id: '', name: '', json_url: '', cover_url: '' }
  }
  catch (e) {
    // 错误已由全局拦截器处理
  }
}

// 上传/粘贴注册
const registerByUpload = ref<{ id: string; name?: string; json_file?: File | null; json_text?: string; cover_file?: File | null }>({ id: '', name: '', json_file: null, json_text: '', cover_file: null })
const onUploadJsonFile = (ev: Event) => {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0] || null
  registerByUpload.value.json_file = file
}
const onUploadCoverFile = (ev: Event) => {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0] || null
  registerByUpload.value.cover_file = file
}
const submitRegisterByUpload = async () => {
  if (!adminToken.value) {
    message.error('请先填写并保存管理员令牌'); return 
  }
  const id = registerByUpload.value.id.trim()
  if (!id || !/^[a-zA-Z0-9_-]+$/.test(id)) {
    message.error('模板ID格式不合法'); return 
  }
  const fd = new FormData()
  fd.append('tpl_id', id)
  const name = registerByUpload.value.name?.trim() || ''
  if (name) fd.append('name', name)
  if (registerByUpload.value.json_file) fd.append('json_file', registerByUpload.value.json_file)
  if (registerByUpload.value.json_text) fd.append('json_text', registerByUpload.value.json_text!)
  if (registerByUpload.value.cover_file) fd.append('cover', registerByUpload.value.cover_file)
  if (!fd.has('json_file') && !fd.has('json_text')) {
    message.error('请上传JSON文件或粘贴JSON文本'); return 
  }
  try {
    await api.registerTemplateUpload(fd, adminToken.value)
    message.success('模板注册成功')
    registerByUpload.value = { id: '', name: '', json_file: null, json_text: '', cover_file: null }
  }
  catch (e) {
    // 错误已由全局拦截器处理
  }
}

const onPPTXUpload = (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0] || null
  pptxFile.value = file
}

// 简易等待工具：等待条件满足或超时
const waitUntil = async (cond: () => boolean, timeoutMs = 10000, intervalMs = 50) => {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    if (cond()) return true
    await new Promise(r => setTimeout(r, intervalMs))
  }
  return cond()
}

const waitForRenderedThumb = async (timeoutMs = 10000) => {
  const node = thumbStageRef.value as HTMLElement | null
  if (!node) return false
  const start = Date.now()
  const raf = () => new Promise(requestAnimationFrame)
  await raf(); await raf()
  const imgs = Array.from(node.querySelectorAll('img'))
  const imgPromises = imgs.map(async (img) => {
    if (img.complete && img.naturalWidth > 0) return true
    try {
      if (typeof (img as any).decode === 'function') await (img as any).decode() 
    }
    catch {
      void 0 
    }
    return await new Promise<boolean>((resolve) => {
      const done = () => resolve(img.naturalWidth > 0)
      img.addEventListener('load', done, { once: true })
      img.addEventListener('error', () => resolve(false), { once: true })
    })
  })
  const bgUrls: string[] = []
  const allNodes = Array.from(node.querySelectorAll('*')) as HTMLElement[]
  allNodes.forEach((el) => {
    const bi = getComputedStyle(el).backgroundImage
    if (bi && /url\(/i.test(bi)) {
      const matches = bi.match(/url\(([^)]+)\)/gi) || []
      matches.forEach((m) => {
        const u = m.replace(/^url\(["']?/, '').replace(/["']?\)$/, '')
        if (u) bgUrls.push(u)
      })
    }
  })
  const bgPromises = bgUrls.map((u) => new Promise<boolean>((resolve) => {
    try {
      const i = new Image()
      i.crossOrigin = 'anonymous'
      i.onload = () => resolve(true)
      i.onerror = () => resolve(false)
      i.src = u
    }
    catch {
      resolve(false) 
    }
  }))
  const fontsReady = (document as any).fonts && typeof (document as any).fonts.ready === 'object'
    ? (document as any).fonts.ready
    : Promise.resolve()
  await Promise.all([Promise.all(imgPromises), Promise.all(bgPromises), fontsReady])
  while (Date.now() - start < timeoutMs) {
    const ok = node.clientWidth > 0 && node.clientHeight > 0 && node.querySelector('*') !== null
    if (ok) return true
    await new Promise(r => setTimeout(r, 50))
  }
  return node.clientWidth > 0 && node.clientHeight > 0
}

// 合并图表到 canonical 单页，避免图表在重写或标注后被矩形替换
const mergeChartsIntoSlide = (canonicalSlide: any, original: any) => {
  try {
    if (!canonicalSlide) return canonicalSlide
    const originalSlide = Array.isArray(original?.slides) ? (original.slides[0] || original) : original
    const charts = Array.isArray(originalSlide?.elements)
      ? originalSlide.elements.filter((e: any) => e && e.type === 'chart')
      : []
    if (!charts.length) return canonicalSlide

    const iou = (a: any, b: any): number => {
      const ax1 = Number(a.left) || 0
      const ay1 = Number(a.top) || 0
      const ax2 = ax1 + (Number(a.width) || 0)
      const ay2 = ay1 + (Number(a.height) || 0)
      const bx1 = Number(b.left) || 0
      const by1 = Number(b.top) || 0
      const bx2 = bx1 + (Number(b.width) || 0)
      const by2 = by1 + (Number(b.height) || 0)
      const ix1 = Math.max(ax1, bx1)
      const iy1 = Math.max(ay1, by1)
      const ix2 = Math.min(ax2, bx2)
      const iy2 = Math.min(ay2, by2)
      const iw = Math.max(0, ix2 - ix1)
      const ih = Math.max(0, iy2 - iy1)
      const inter = iw * ih
      const areaA = Math.max(0, (ax2 - ax1)) * Math.max(0, (ay2 - ay1))
      const areaB = Math.max(0, (bx2 - bx1)) * Math.max(0, (by2 - by1))
      const union = areaA + areaB - inter
      return union > 0 ? inter / union : 0
    }

    const canonicalEls: any[] = Array.isArray(canonicalSlide.elements) ? canonicalSlide.elements.slice() : []
    const kept = canonicalEls.filter((e: any) => {
      if (!e) return false
      // 仅移除与图表边界高度重合的矩形形状（避免误删其他设计形状）
      if (e.type === 'shape') {
        const overlapped = charts.some((c: any) => iou(e, c) > 0.9)
        if (overlapped) return false
      }
      return true
    })

    const merged = kept.slice()
    charts.forEach((c: any) => {
      const exists = merged.some((e: any) => e && e.type === 'chart' && iou(e, c) > 0.8)
      if (!exists) merged.push(c)
    })
    return { ...canonicalSlide, elements: merged }
  }
  catch (err) {
    console.warn('mergeChartsIntoSlide 失败，返回原 canonical', err)
    return canonicalSlide
  }
}

const runPPTXOneClick = async () => {
  if (!pptxFile.value) return
  pptxAnnotating.value = true
  try {
    const fileList = { 0: pptxFile.value, length: 1 } as unknown as FileList
    importPPTXFile(fileList, { cover: true, fixedViewport: true })
    // 等待导入完成并且 slides 已填充，避免截到空白图
    await waitUntil(() => !importing.value && slideStore.slides.length > 0)
    await nextTick()

    const slides = slideStore.slides
    maxSlideIndex.value = Math.max(0, slides.length - 1)
    const idx = Math.min(Math.max(0, pptxPageIndex.value), maxSlideIndex.value)
    thumbSlide.value = slides[idx]
    await nextTick()

    if (!thumbStageRef.value) throw new Error('截图容器未就绪')
    const prevPos = (thumbStageRef.value as HTMLElement).style.position
    const prevLeft = (thumbStageRef.value as HTMLElement).style.left
    const prevTop = (thumbStageRef.value as HTMLElement).style.top
    ;(thumbStageRef.value as HTMLElement).style.position = 'fixed'
    ;(thumbStageRef.value as HTMLElement).style.left = '0px'
    ;(thumbStageRef.value as HTMLElement).style.top = '0px'
    await waitForRenderedThumb()
    const w = slideStore.viewportSize
    const h = slideStore.viewportSize * slideStore.viewportRatio
    const target = thumbStageRef.value.querySelector('.elements') || thumbStageRef.value
    const dataUrl = await toPng(target as HTMLElement, { width: w, height: h, backgroundColor: '#ffffff', cacheBust: true, pixelRatio: (window.devicePixelRatio || 1) })
    ;(thumbStageRef.value as HTMLElement).style.position = prevPos
    ;(thumbStageRef.value as HTMLElement).style.left = prevLeft
    ;(thumbStageRef.value as HTMLElement).style.top = prevTop
    // 记录截图以便在调试区展示
    lastScreenshotDataUrl.value = dataUrl
    const image_b64 = toPureBase64(dataUrl)
    const ok = await validateScreenshot(dataUrl)
    if (ok) {
      message.success('截图生成成功') 
    }
    else {
      message.error('截图生成失败') 
    }

    // 传单页结构并携带画布尺寸，保证后端匹配逻辑使用一致的坐标基准
    const slideInput = {
      ...thumbSlide.value,
      width: slideStore.viewportSize,
      height: slideStore.viewportSize * slideStore.viewportRatio,
    }

    const resp = await fetch(`${SERVER_URL}/template/annotate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_b64, slide_json: slideInput })
    })
    if (!resp.ok) throw new Error(`后端错误：${resp.status}`)
    const data = await resp.json()
    annotateResult.value = data
    message.success('PPTX 初标注完成，可加载到编辑器进行校正')
  }
  catch (err) {
    console.error('一键初标注失败', err)
    message.error('一键初标注失败，请检查 PPTX 文件或重试')
  }
  finally {
    pptxAnnotating.value = false
  }
}

const onImageChange = (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    imageB64.value = (reader.result as string) || ''
    // 记录用户上传的截图，便于调试预览
    lastScreenshotDataUrl.value = imageB64.value
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
    }
    catch (err) {
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
  }
  catch (err) {
    console.error(err)
  }
  finally {
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
        }
        catch (err) {
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
      }
      else if (Array.isArray(src?.slides)) {
        slideInput = src.slides[0] || src
      }
      else {
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
      let cs = Array.isArray(canonical?.slides) ? canonical.slides[0] : null
      // 合并原始图表，避免矩形替换
      cs = mergeChartsIntoSlide(cs, src)
      if (cs) slides.push(cs)
      if (width === null || width === undefined) width = canonical?.width || null
      if (height === null || height === undefined) height = canonical?.height || null
      if (theme === null || theme === undefined) theme = canonical?.theme || null
    }

    const merged = {
      width: width ?? 960,
      height: height ?? 540,
      theme: theme ?? null,
      slides,
    }
    mergedTemplateJsonBatch.value = merged
  }
  catch (err) {
    console.error('批量标准化重写与合并失败', err)
  }
  finally {
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
    }
    else {
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
    // 等待导入流程完全结束，确保 slides 数组与画布尺寸已就绪
    await waitUntil(() => !importing.value && slideStore.slides.length > 0)
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
      const prevPos = (thumbStageRef.value as HTMLElement).style.position
      const prevLeft = (thumbStageRef.value as HTMLElement).style.left
      const prevTop = (thumbStageRef.value as HTMLElement).style.top
      ;(thumbStageRef.value as HTMLElement).style.position = 'fixed'
      ;(thumbStageRef.value as HTMLElement).style.left = '0px'
      ;(thumbStageRef.value as HTMLElement).style.top = '0px'
      await waitForRenderedThumb()
      const w = slideStore.viewportSize
      const h = slideStore.viewportSize * slideStore.viewportRatio
      const target = thumbStageRef.value.querySelector('.elements') || thumbStageRef.value
      const dataUrl = await toPng(target as HTMLElement, { width: w, height: h, backgroundColor: '#ffffff', cacheBust: true, pixelRatio: (window.devicePixelRatio || 1) })
      ;(thumbStageRef.value as HTMLElement).style.position = prevPos
      ;(thumbStageRef.value as HTMLElement).style.left = prevLeft
      ;(thumbStageRef.value as HTMLElement).style.top = prevTop
      const ok = await validateScreenshot(dataUrl)
      if (!ok) throw new Error('截图生成失败')
      
      const image_b64 = toPureBase64(dataUrl)

      // 3.2 初标注
      const resp1 = await fetch(`${SERVER_URL}/template/annotate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // 单页结构 + 公共尺寸，避免后端在整文档上找不到 elements
        body: JSON.stringify({ image_b64, slide_json: { ...slides[idx], width: docBase.width, height: docBase.height } })
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
      let cs = Array.isArray(canonical?.slides) ? canonical.slides[0] : canonical
      // 将原始图表合并回 canonical 单页，避免被矩形替换
      cs = mergeChartsIntoSlide(cs, slides[idx])
      if (cs) outSlides.push(cs)
      if (width === null || width === undefined) width = canonical?.width || null
      if (height === null || height === undefined) height = canonical?.height || null
      if (theme === null || theme === undefined) theme = canonical?.theme || null
    }

    // 4) 合并并提供下载
    const merged = {
      width: width ?? 960,
      height: height ?? 540,
      theme: theme ?? null,
      slides: outSlides,
    }
    mergedTemplatePptxBatch.value = merged
  }
  catch (err) {
    console.error('从PPTX索引范围批量生成失败', err)
  }
  finally {
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
    }
    catch (err) {
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
    }
    catch (err) {
      console.error('样例 JSON 解析失败', err)
      sampleData.value = []
    }
  }
  reader.readAsText(file, 'utf-8')
}

const startValidation = () => {
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
  }
  catch (err) {
    console.error('验证失败', err)
  }
  finally {
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
      message.warning('暂无可加载的初标注结果，请先执行初标注或选择正确的JSON文件')
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
    // 记录重写阶段的诊断信息
    rewriteDiagnostics.value = data?.diagnostics || null
    const canonical = data?.canonical
    if (!canonical) {
      console.warn('标准化重写返回为空，无法加载到编辑器')
      message.error('标准化重写返回为空，无法加载到编辑器')
      return
    }

    // 读取文档尺寸并同步编辑器视口（优先使用初标注的几何基准，避免背景加载后偏移）
    const srcW = Number((baseInput as any)?.width)
    const srcH = Number((baseInput as any)?.height)
    const docWidth = (Number.isFinite(srcW) && srcW > 0) ? srcW : (Number(canonical.width) || 1280)
    const docHeight = (Number.isFinite(srcH) && srcH > 0) ? srcH : (Number(canonical.height) || 720)
    const ratio = docHeight / docWidth
    slideStore.setViewportSize(docWidth)
    slideStore.setViewportRatio(ratio)

    // 应用主题
    if (canonical.theme) {
      slideStore.setTheme(canonical.theme)
    }

    // 规范化 slides：保证数组与必要字段存在；先合并图表再规范化
    const baseSlideForMerge = Array.isArray((baseInput as any)?.slides) ? (baseInput as any).slides[0] : baseInput
    const incomingSlides = Array.isArray(canonical.slides) ? canonical.slides : [canonical]
    const mergedSlides = incomingSlides.map((s: any) => mergeChartsIntoSlide(s, baseSlideForMerge))
    const normalizedSlides = mergedSlides.map((s: any) => {
      const slideId = String(s.id || nanoid())
      const elements = Array.isArray(s.elements) ? s.elements : []
      const fixedElements = elements.map((e: any) => ({
        id: String(e.id || nanoid()),
        rotate: e.rotate ?? 0,
        ...e,
      }))
      return {
        id: slideId,
        elements: fixedElements,
        background: s.background,
        animations: s.animations,
        turningMode: s.turningMode,
        sectionTag: s.sectionTag,
        type: s.type || 'content',
      }
    })

    if (!normalizedSlides.length) {
      console.warn('标准化后没有任何页面可加载')
      message.error('标准化后没有任何页面可加载，请检查初标注JSON结构或后端返回值')
      return
    }

    // 持久化本次重写诊断，便于返回页面后查看
    if (rewriteDiagnostics.value) {
      try {
        localStorage.setItem('TM_LAST_REWRITE_DIAGNOSTICS', JSON.stringify(rewriteDiagnostics.value)) 
      }
      catch {
        void 0 
      }
    }

    slideStore.setSlides(normalizedSlides)
    slideStore.updateSlideIndex(0)
    message.success('初标注结果已加载到编辑器')

    // 打开编辑器进行人工校对（支持在新标签打开）
    const route = router.resolve('/editor')
    if (openEditorInNewTab.value) {
      window.open(route.href, '_blank')
    }
    else {
      router.push('/editor')
    }
  }
  catch (err) {
    console.error('加载到编辑器失败', err)
    message.error(`加载到编辑器失败：${(err as Error).message}`)
  }
}

const pretty = (obj: any) => JSON.stringify(obj, null, 2)

// ======================== 调试信息（初标注 / 重写） ========================
const validateScreenshot = async (dataUrl: string): Promise<boolean> => {
  try {
    const okPrefix = /^data:image\/(png|jpeg);base64,/i.test(dataUrl)
    if (!okPrefix) return false
    const payload = toPureBase64(dataUrl)
    if (!payload || payload.length < 64) return false
    const img = await new Promise<HTMLImageElement>((resolve, reject) => {
      const i = new Image()
      i.onload = () => resolve(i)
      i.onerror = () => reject(new Error('img load error'))
      i.src = dataUrl
    })
    if (!(img.width > 0 && img.height > 0)) return false
    const canvas = document.createElement('canvas')
    canvas.width = img.width
    canvas.height = img.height
    const ctx = canvas.getContext('2d')
    if (!ctx) return true
    ctx.drawImage(img, 0, 0)
    const sample = 12
    let nonWhite = 0
    for (let y = 0; y < sample; y++) {
      for (let x = 0; x < sample; x++) {
        const px = Math.floor((x + 0.5) * img.width / sample)
        const py = Math.floor((y + 0.5) * img.height / sample)
        const data = ctx.getImageData(px, py, 1, 1).data
        const [r, g, b, a] = data
        const isWhite = r > 250 && g > 250 && b > 250 && a > 0
        if (!isWhite) nonWhite++
      }
    }
    return nonWhite > Math.floor(sample * sample * 0.05)
  }
  catch {
    return false
  }
}

const downloadScreenshot = async () => {
  try {
    const url = lastScreenshotDataUrl.value
    if (!url) {
      message.error('没有可下载的截图'); return 
    }
    const blob = await (await fetch(url)).blob()
    if (!(blob.type === 'image/png' && blob.size > 0)) {
      message.error('截图文件为空'); return 
    }
    const objUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = objUrl
    a.download = 'screenshot.png'
    a.click()
    URL.revokeObjectURL(objUrl)
  }
  catch {
    message.error('下载截图失败')
  }
}

// 已取消自动保存；保留手动下载按钮（downloadScreenshot）
// 初标注摘要：元素数量、尺寸、page_type、类型分布
const annotatedDebug = computed(() => {
  const s = annotateResult.value?.merged_slide
  if (!s) return null
  const w = Number(s.width) || Number(s.__canvas_width) || 0
  const h = Number(s.height) || Number(s.__canvas_height) || 0
  const cw = Number(s.__canvas_width) || (Number(s.width) || 0)
  const ch = Number(s.__canvas_height) || (Number(s.height) || 0)
  const els: any[] = Array.isArray(s.elements) ? s.elements : []
  const typeCount: Record<string, number> = {}
  // 面积、尺寸统计
  let areaSum = 0
  let areaCnt = 0
  let minArea = Number.POSITIVE_INFINITY
  let maxArea = 0
  let minWH: string | null = null
  let maxWH: string | null = null
  // 文本行数统计
  let textLines = 0
  els.forEach((e: any) => {
    const t = String(e?.type || 'unknown')
    typeCount[t] = (typeCount[t] || 0) + 1
    const w = Number(e?.width) || 0
    const h = Number(e?.height) || 0
    const a = w * h
    if (w > 0 && h > 0) {
      areaSum += a
      areaCnt += 1
      if (a < minArea) {
        minArea = a; minWH = `${w} × ${h}` 
      }
      if (a > maxArea) {
        maxArea = a; maxWH = `${w} × ${h}` 
      }
    }
    if (t === 'text') {
      const txt = String((e && (e.content ?? e.text ?? e.value)) || '')
      if (txt) {
        const lines = txt.split(/\r?\n/).length
        textLines += lines
      }
    }
  })
  const dist = Object.entries(typeCount).map(([k, v]) => `${k}:${v}`).join(', ')
  return {
    size: `${w} × ${h}`,
    canvas: `${cw} × ${ch}`,
    pageType: String(s.type || 'unknown'),
    elementCount: els.length,
    elementTypes: dist || '—',
    avgArea: areaCnt > 0 ? Math.round(areaSum / areaCnt) : 0,
    minSize: minWH || '—',
    maxSize: maxWH || '—',
    textLines
  }
})

// 重写诊断摘要：文档尺寸、页数、每页元素数量、主题规范化
const rewriteDebug = computed(() => {
  const d = rewriteDiagnostics.value
  if (!d) return null
  const w = Number(d.width) || 0
  const h = Number(d.height) || 0
  const cnt = Number(d.slide_count) || 0
  const eps = Array.isArray(d.elements_per_slide) ? d.elements_per_slide.join(', ') : '—'
  const norm = (d.normalized_theme === true) ? '是' : (d.normalized_theme === false ? '否' : '未知')
  return {
    docSize: `${w} × ${h}`,
    slideCount: cnt,
    elementsPerSlide: eps,
    normalizedTheme: norm,
  }
})

// 最近截图调试：提供尺寸与打开入口
const screenshotDebug = computed(() => {
  const url = lastScreenshotDataUrl.value
  if (!url) return null
  const w = slideStore.viewportSize
  const h = slideStore.viewportSize * slideStore.viewportRatio
  return { url, sizeText: `${w} × ${h}` }
})
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

.thumb-stage { position: absolute; left: -9999px; top: -9999px; width: auto; height: auto; overflow: hidden; }

.result-block { margin-top: 12px; }
.result-title { font-size: 13px; color: #334155; margin-bottom: 6px; }
.json-view { max-height: 260px; overflow: auto; background: #f8fafc; border: 2px solid #e2e8f0; border-radius: 12px; padding: 12px; color: #334155; }

/* 按钮与首页保持一致风格 */
.action-group {
  display: flex;
  gap: 16px;
}

/* 调试信息折叠区样式 */
.debug-card { margin-top: 16px; }
.debug-collapse {
  border: 2px dashed #e2e8f0;
  border-radius: 12px;
  padding: 10px 12px;
  background: #f8fafc;
}
.debug-collapse > summary {
  cursor: pointer;
  color: #475569;
  font-size: 13px;
  font-weight: 600;
}
.debug-content { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 12px; }
.debug-block { background: #ffffff; border: 2px solid #e2e8f0; border-radius: 12px; padding: 12px; }
.debug-title { font-size: 13px; color: #334155; margin-bottom: 8px; }
.debug-list { display: flex; flex-direction: column; gap: 6px; }
.debug-item { display: flex; justify-content: space-between; gap: 12px; font-size: 13px; color: #334155; }
.debug-key { color: #64748b; }
.debug-val { color: #334155; font-weight: 600; }
.debug-empty { color: #94a3b8; font-size: 13px; }

/* 截图预览样式 */
.debug-image-wrap { display: flex; flex-direction: column; gap: 8px; }
.debug-image { max-width: 100%; border: 1px solid #eaecf0; border-radius: 8px; box-shadow: 0 1px 2px rgba(16, 24, 40, 0.06); }
.debug-caption { font-size: 12px; color: #667085; }
.debug-actions a { font-size: 12px; color: #3b82f6; text-decoration: none; }
.debug-actions a:hover { text-decoration: underline; }

/* 轻量内联选项 */
.inline-option { margin-top: 8px; color: #64748b; font-size: 13px; }
.inline-option input { vertical-align: middle; margin-right: 6px; }

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
