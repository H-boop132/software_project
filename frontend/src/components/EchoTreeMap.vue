<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { EchoOut, RippleOut } from '@/api/types'

const props = defineProps<{ ripple: RippleOut; echoes: EchoOut[]; selectedId: number | null }>()
const emit = defineEmits<{ select: [echo: EchoOut | null] }>()
const zoom = ref(1)
const collapsed = ref(new Set<number>())
type Node = { key: string; x: number; y: number; label: string; content: string; echo: EchoOut | null; children: EchoOut[] }

const graph = computed(() => {
  const nodes: Node[] = []
  const edges: { key: string; path: string }[] = []
  let leaf = 0
  function visit(echo: EchoOut | null, depth: number): Node {
    const children = echo ? echo.children : props.echoes
    const visible = echo && collapsed.value.has(echo.id) ? [] : children
    const next = visible.map((child) => visit(child, depth + 1))
    const y = next.length ? (next[0].y + next[next.length - 1].y) / 2 : 46 + leaf++ * 96
    const node: Node = {
      key: echo ? `echo-${echo.id}` : 'ripple', x: 20 + depth * 250, y,
      label: echo ? echo.user.nickname : `微澜 · ${props.ripple.user.nickname}`,
      content: echo ? echo.content : props.ripple.content, echo, children,
    }
    nodes.push(node)
    for (const child of next) edges.push({
      key: `${node.key}-${child.key}`,
      path: `M ${node.x + 200} ${y} C ${node.x + 225} ${y}, ${child.x - 25} ${child.y}, ${child.x} ${child.y}`,
    })
    return node
  }
  visit(null, 0)
  return { nodes, edges, width: Math.max(...nodes.map((node) => node.x)) + 225, height: Math.max(220, leaf * 96 + 10) }
})

function toggle(id: number) {
  const next = new Set(collapsed.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  collapsed.value = next
}
function reset() { zoom.value = 1; collapsed.value = new Set() }
function shorten(value: string) {
  const chars = Array.from(value.replace(/\s+/g, ' '))
  return chars.slice(0, 15).join('') + (chars.length > 15 ? '…' : '')
}
watch(() => props.ripple.id, reset)
</script>

<template>
  <section aria-label="回声涟漪树图">
    <div class="map-toolbar">
      <span>点击节点查看内容与回复，点击圆点展开或收起分支</span>
      <div>
        <el-button :disabled="zoom <= 0.5" aria-label="缩小涟漪树" @click="zoom = Math.max(0.5, zoom - 0.1)">−</el-button>
        <span class="zoom-label">{{ Math.round(zoom * 100) }}%</span>
        <el-button :disabled="zoom >= 1.5" aria-label="放大涟漪树" @click="zoom = Math.min(1.5, zoom + 0.1)">＋</el-button>
        <el-button @click="reset">重置视图</el-button>
      </div>
    </div>
    <div class="map-viewport" tabindex="0" aria-label="可滚动的涟漪树图">
      <svg :viewBox="`0 0 ${graph.width} ${graph.height}`" :width="graph.width * zoom" :height="graph.height * zoom" aria-label="微澜及回声回复关系">
        <path v-for="edge in graph.edges" :key="edge.key" :d="edge.path" fill="none" stroke="#a7ced6" stroke-width="2" />
        <g v-for="node in graph.nodes" :key="node.key" class="map-node" role="button" tabindex="0"
          :aria-label="`${node.echo ? '回声' : '根微澜'}节点：${node.label}，${node.content}`"
          @click="emit('select', node.echo)" @keydown.enter="emit('select', node.echo)" @keydown.space.prevent="emit('select', node.echo)">
          <rect :x="node.x" :y="node.y - 33" width="200" height="66" rx="10"
            :fill="node.echo ? '#ffffff' : '#e7f5f7'"
            :stroke="(node.echo?.id ?? null) === selectedId ? '#1f7a8c' : '#c9dfe4'" :stroke-width="(node.echo?.id ?? null) === selectedId ? 3 : 1" />
          <text :x="node.x + 12" :y="node.y - 8" class="map-author">{{ shorten(node.label) }}</text>
          <text :x="node.x + 12" :y="node.y + 16" class="map-content">{{ shorten(node.content) }}</text>
          <g v-if="node.echo && node.children.length" role="button" tabindex="0"
            :aria-label="`${collapsed.has(node.echo.id) ? '展开' : '收起'}回声分支 ${node.echo.id}`"
            @click.stop="toggle(node.echo.id)" @keydown.enter.stop.prevent="toggle(node.echo.id)" @keydown.space.stop.prevent="toggle(node.echo.id)">
            <circle :cx="node.x + 200" :cy="node.y" r="10" fill="#1f7a8c" />
            <text :x="node.x + 200" :y="node.y + 4" text-anchor="middle" fill="white" font-size="14">{{ collapsed.has(node.echo.id) ? '+' : '−' }}</text>
          </g>
        </g>
      </svg>
    </div>
  </section>
</template>

<style scoped>
.map-toolbar { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; margin: 12px 0; }
.map-toolbar > span { font-size: 12px; color: #78909c; }
.map-toolbar > div { display: flex; align-items: center; gap: 6px; }
.zoom-label { color: #607d8b; min-width: 42px; text-align: center; font-size: 12px; }
.map-viewport { max-height: 480px; overflow: auto; background: #f5fafb; border: 1px solid var(--wl-border); border-radius: 12px; }
.map-node { cursor: pointer; outline: none; }
.map-node:focus-visible rect { stroke: #e89b1b; stroke-width: 3; }
.map-author { font-size: 13px; font-weight: 600; fill: #1f7a8c; }
.map-content { font-size: 12px; fill: #546e7a; }
</style>
