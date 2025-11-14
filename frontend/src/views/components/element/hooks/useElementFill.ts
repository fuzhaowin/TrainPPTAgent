import type { PPTShapeElement } from '@/types/slides'
import { computed, type Ref } from 'vue'
import { useSlidesStore } from '@/store'
import { storeToRefs } from 'pinia'

// 计算元素的填充样式
export default (element: Ref<PPTShapeElement>, source: string) => {
  const { theme } = storeToRefs(useSlidesStore())
  const fill = computed(() => {
    if (element.value.pattern) return `url(#${source}-pattern-${element.value.id})`
    if (element.value.gradient) return `url(#${source}-gradient-${element.value.id})`
    // 当后端重写返回缺失 fill 时，使用主题首色作为兜底，避免出现仅描边或未完全填充
    return element.value.fill || theme.value?.themeColors?.[0] || '#000'
  })

  return {
    fill,
  }
}