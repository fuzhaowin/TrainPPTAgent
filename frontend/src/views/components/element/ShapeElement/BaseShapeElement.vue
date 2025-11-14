<template>
  <div 
    class="base-element-shape"
    :style="{
      top: elementInfo.top + 'px',
      left: elementInfo.left + 'px',
      width: elementInfo.width + 'px',
      height: elementInfo.height + 'px',
    }"
  >
    <div
      class="rotate-wrapper"
      :style="{ transform: `rotate(${elementInfo.rotate}deg)` }"
    >
      <div 
        class="element-content"
        :style="{
          opacity: elementInfo.opacity,
          filter: shadowStyle ? `drop-shadow(${shadowStyle})` : '',
          transform: flipStyle,
          color: text.defaultColor,
          fontFamily: text.defaultFontName,
        }"
      >
        <svg 
          overflow="visible" 
          :width="elementInfo.width"
          :height="elementInfo.height"
        >
          <defs>
            <PatternDefs
              v-if="elementInfo.pattern"
              :id="`base-pattern-${elementInfo.id}`" 
              :src="elementInfo.pattern"
            />
            <GradientDefs
              v-else-if="elementInfo.gradient"
              :id="`base-gradient-${elementInfo.id}`" 
              :type="elementInfo.gradient.type"
              :colors="elementInfo.gradient.colors"
              :rotate="elementInfo.gradient.rotate"
            />
          </defs>
          <g 
            :transform="`scale(${scaleX}, ${scaleY}) translate(0,0) matrix(1,0,0,1,0,0)`"
          >
            <path 
              vector-effect="non-scaling-stroke" 
              fill-rule="nonzero"
              stroke-linecap="butt" 
              stroke-miterlimit="8"
              :d="elementInfo.path" 
              :fill="fill"
              :stroke="outlineColor"
              :stroke-width="outlineWidth" 
              :stroke-dasharray="strokeDashArray" 
            ></path>
          </g>
        </svg>

        <div class="shape-text" :class="text.align">
          <div class="ProseMirror-static" v-html="text.content"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import type { PPTShapeElement, ShapeText } from '@/types/slides'
import { useSlidesStore } from '@/store'
import useElementOutline from '@/views/components/element/hooks/useElementOutline'
import useElementShadow from '@/views/components/element/hooks/useElementShadow'
import useElementFlip from '@/views/components/element/hooks/useElementFlip'
import useElementFill from '@/views/components/element/hooks/useElementFill'

import GradientDefs from './GradientDefs.vue'
import PatternDefs from './PatternDefs.vue'

const props = defineProps<{
  elementInfo: PPTShapeElement
}>()


const { theme } = storeToRefs(useSlidesStore())

const element = computed(() => props.elementInfo)
const { fill } = useElementFill(element, 'base')

const outline = computed(() => props.elementInfo.outline)
const { outlineWidth, outlineColor, strokeDashArray } = useElementOutline(outline)

const shadow = computed(() => props.elementInfo.shadow)
const { shadowStyle } = useElementShadow(shadow)

const flipH = computed(() => props.elementInfo.flipH)
const flipV = computed(() => props.elementInfo.flipV)
const { flipStyle } = useElementFlip(flipH, flipV)

const text = computed<ShapeText>(() => {
  const defaultText: ShapeText = {
    content: '',
    align: 'middle',
    defaultFontName: theme.value.fontName,
    defaultColor: theme.value.fontColor,
  }
  if (!props.elementInfo.text) return defaultText

  return props.elementInfo.text
})

// 计算安全的viewBox尺寸，避免后端返回异常viewBox导致缩放比极小
const safeViewBox = computed<[number, number]>(() => {
  const vb = props.elementInfo.viewBox
  const w = Array.isArray(vb) && Number(vb[0]) > 0 ? Number(vb[0]) : 1
  const h = Array.isArray(vb) && Number(vb[1]) > 0 ? Number(vb[1]) : 1
  return [w, h]
})

// 当path非常大且viewBox远大于元素尺寸时，测量未缩放路径的真实边界以校正缩放
let measuredViewBox: [number, number] | null = null
const measurePathBounds = () => {
  try {
    const d = props.elementInfo.path
    if (!d) return
    // 创建离屏SVG以测量未缩放路径的边界
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
    svg.setAttribute('width', '0')
    svg.setAttribute('height', '0')
    svg.style.position = 'absolute'
    svg.style.left = '-10000px'
    svg.style.top = '-10000px'
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path')
    path.setAttribute('d', d)
    svg.appendChild(path)
    document.body.appendChild(svg)
    const bbox = path.getBBox()
    document.body.removeChild(svg)
    const w = Math.max(1, bbox.width)
    const h = Math.max(1, bbox.height)
    // 仅当测得尺寸显著小于后端提供的viewBox时采用，以避免误判
    const [vw, vh] = safeViewBox.value
    const tooLarge = vw > props.elementInfo.width * 50 || vh > props.elementInfo.height * 50
    if (tooLarge) {
      measuredViewBox = [w, h]
    }
  }
  catch (_) {
    // 忽略测量异常，保留原始viewBox兜底
  }
}

onMounted(measurePathBounds)
watch(() => props.elementInfo.path, () => measurePathBounds())

const scaleX = computed(() => {
  const [vw] = measuredViewBox || safeViewBox.value
  return props.elementInfo.width / Math.max(1, vw)
})
const scaleY = computed(() => {
  const [, vh] = measuredViewBox || safeViewBox.value
  return props.elementInfo.height / Math.max(1, vh)
})
</script>

<style lang="scss" scoped>
.base-element-shape {
  position: absolute;
}
.rotate-wrapper {
  width: 100%;
  height: 100%;
}
.element-content {
  width: 100%;
  height: 100%;
  position: relative;

  svg {
    transform-origin: 0 0;
    overflow: visible;
    display: block;
  }
}
.shape-text {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  flex-direction: column;
  padding: 10px;
  line-height: 1.2;
  word-break: break-word;

  &.top {
    justify-content: flex-start;
  }
  &.middle {
    justify-content: center;
  }
  &.bottom {
    justify-content: flex-end;
  }
}
</style>
