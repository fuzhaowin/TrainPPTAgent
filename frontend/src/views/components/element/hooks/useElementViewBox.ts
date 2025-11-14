import { computed, type Ref } from 'vue'
import type { PPTShapeElement } from '@/types/slides'

// 估算 path 的坐标范围，用于推断合理的 viewBox
const estimateExtentFromPath = (path: string): number | null => {
  if (!path) return null
  // 提取所有数字（包括负数与小数），用于估算坐标范围
  const nums = path.match(/-?\d+(?:\.\d+)?/g)
  if (!nums || nums.length < 2) return null

  const values = nums.map(n => parseFloat(n)).filter(n => Number.isFinite(n))
  if (values.length < 2) return null

  const min = Math.min(...values)
  const max = Math.max(...values)
  const extent = max - min
  if (extent <= 0) return null
  return extent
}

// 计算形状元素的安全 viewBox：
// - 若后端返回过大的 viewBox（相对元素尺寸不合理），则根据 path 的数值范围进行兜底
// - 若 viewBox 缺失或为 0，则使用元素宽高作为兜底
export default (element: Ref<PPTShapeElement>) => {
  const safeViewBox = computed<[number, number]>(() => {
    const vb = element.value.viewBox || [element.value.width, element.value.height]
    const vbX = vb?.[0] ?? element.value.width ?? 1
    const vbY = vb?.[1] ?? element.value.height ?? 1

    // 判断 viewBox 是否相对元素尺寸过大（>10倍），常见于重写后返回统一的 1000x1000
    const suspicious = (vbX > (element.value.width || 1) * 10) || (vbY > (element.value.height || 1) * 10)

    if (suspicious) {
      const extent = estimateExtentFromPath(element.value.path || '')
      // 若估算出的范围更合理，则使用该范围作为正方形的 viewBox
      if (extent && extent > 0 && extent < Math.max(vbX, vbY)) {
        return [extent, extent]
      }
    }

    const fallbackX = vbX > 0 ? vbX : (element.value.width || 1)
    const fallbackY = vbY > 0 ? vbY : (element.value.height || 1)
    return [fallbackX, fallbackY]
  })

  return { safeViewBox }
}