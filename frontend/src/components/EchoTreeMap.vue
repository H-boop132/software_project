<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Minus, Plus, RefreshLeft } from '@element-plus/icons-vue'
import type { EchoOut, RippleOut } from '@/api/types'

const props = defineProps<{ ripple: RippleOut; echoes: EchoOut[]; selectedId: number | null }>()
const emit = defineEmits<{ select: [echo: EchoOut | null] }>()

const viewport = ref<HTMLElement>()
const zoom = ref(100)
const collapsed = ref(new Set<number>())
const nodeWidth = 204
const columnStep = 252
const gutter = 22

type TreeNode = {
  key: string
  depth: number
  x: number
  y: number
  echo: EchoOut | null
  author: string
  avatar: string | null
  preview: string
  hasChildren: boolean
  selectedPath: boolean
}

const graph = computed(() => {
  const nodes: TreeNode[] = []
  const edges: { key: string; path: string; active: boolean }[] = []
  let leaf = 0
  let maxDepth = 0

  function visit(echo: EchoOut | null, depth: number): TreeNode {
    maxDepth = Math.max(depth, maxDepth)
    const children = echo ? echo.children : props.echoes
    const visible = echo && collapsed.value.has(echo.id) ? [] : children
    const next = visible.map(child => visit(child, depth + 1))
    const y = next.length ? (next[0].y + next[next.length - 1].y) / 2 : 90 + leaf++ * 94
    const node: TreeNode = {
      key: echo ? 'echo-' + echo.id : 'ripple',
      depth,
      x: gutter + depth * columnStep,
      y,
      echo,
      author: echo ? echo.user.nickname : props.ripple.user.nickname,
      avatar: echo ? echo.user.avatar_url : props.ripple.user.avatar_url,
      preview: echo ? echo.content : props.ripple.content,
      hasChildren: children.length > 0,
      selectedPath: (echo !== null && echo.id === props.selectedId) || next.some(child => child.selectedPath),
    }
    nodes.push(node)
    for (const child of next) {
      const start = node.x + nodeWidth
      const middle = (start + child.x) / 2
      edges.push({
        key: node.key + '-' + child.key,
        path: ['M', start, y, 'C', middle, y, middle, child.y, child.x, child.y].join(' '),
        active: child.selectedPath,
      })
    }
    return node
  }

  visit(null, 0)
  nodes.sort((a, b) => a.depth - b.depth || a.y - b.y)
  return {
    nodes, edges, maxDepth,
    width: gutter * 2 + maxDepth * columnStep + nodeWidth,
    height: Math.max(190, 142 + (leaf - 1) * 94),
  }
})

function toggle(id: number) {
  const next = new Set(collapsed.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  collapsed.value = next
}

function resize(step: number) {
  zoom.value = Math.min(150, Math.max(50, zoom.value + step))
}

function reset() {
  zoom.value = 100
  collapsed.value = new Set()
  viewport.value?.scrollTo({ left: 0, top: 0 })
}

watch(() => props.ripple.id, reset)
</script>

<template>
  <section class="tree-map" aria-label="回声涟漪树图">
    <header class="map-toolbar">
      <div class="map-guide">
        <strong>回声关系图</strong>
        <span>选择节点查看内容 · 用 ＋／− 展开或收起分支</span>
      </div>
      <div class="map-controls" role="group" aria-label="涟漪树缩放">
        <button type="button" :disabled="zoom <= 50" aria-label="缩小涟漪树" @click="resize(-10)"><Minus aria-hidden="true" /></button>
        <output aria-label="当前缩放比例">{{ zoom }}%</output>
        <button type="button" :disabled="zoom >= 150" aria-label="放大涟漪树" @click="resize(10)"><Plus aria-hidden="true" /></button>
        <button type="button" class="reset-view" @click="reset"><RefreshLeft aria-hidden="true" />重置视图</button>
      </div>
    </header>
    <div ref="viewport" class="map-viewport" tabindex="0" aria-label="可滚动的涟漪树图">
      <div class="map-frame" :style="{ width: (graph.width * zoom / 100) + 'px', height: (graph.height * zoom / 100) + 'px' }">
        <div class="map-surface" :style="{ width: graph.width + 'px', height: graph.height + 'px', transform: 'scale(' + zoom / 100 + ')' }">
          <span v-for="depth in graph.maxDepth + 1" :key="depth" class="map-depth" :style="{ left: (gutter + (depth - 1) * columnStep) + 'px' }">
            {{ depth === 1 ? '原始微澜' : '第 ' + (depth - 1) + ' 层回声' }}
          </span>
          <svg class="map-edges" :viewBox="'0 0 ' + graph.width + ' ' + graph.height" aria-hidden="true">
            <path v-for="edge in graph.edges" :key="edge.key" :d="edge.path" :class="{ 'edge-active': edge.active }" />
          </svg>
          <div v-for="node in graph.nodes" :key="node.key" class="map-node-wrap"
            :style="{ left: node.x + 'px', top: node.y + 'px', width: nodeWidth + 'px' }">
            <button type="button" class="map-node" :class="{ 'map-root': !node.echo, 'map-selected': node.echo && node.echo.id === selectedId }"
              :aria-label="(node.echo ? '回声' : '原始微澜') + '，' + node.author + '，' + node.preview"
              :aria-pressed="(node.echo?.id ?? null) === selectedId" @click="emit('select', node.echo)">
              <span class="node-avatar" aria-hidden="true">
                <img v-if="node.avatar" :src="node.avatar" alt="" class="node-avatar-img" />
                <template v-else>{{ Array.from(node.author)[0] }}</template>
              </span>
              <span class="node-copy">
                <strong>{{ node.author }}</strong>
                <span>{{ node.preview }}</span>
              </span>
            </button>
            <button v-if="node.echo && node.hasChildren" type="button" class="branch-control"
              :aria-expanded="!collapsed.has(node.echo.id)"
              :aria-label="(collapsed.has(node.echo.id) ? '展开' : '收起') + ' ' + node.author + ' 的回声分支'"
              @click="toggle(node.echo.id)">
              <Plus v-if="collapsed.has(node.echo.id)" aria-hidden="true" />
              <Minus v-else aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>
    </div>
    <footer class="map-legend">
      <span><i></i>原始微澜</span>
      <span><i></i>所选回复路径</span>
      <span class="map-scroll-hint">图超出边界时可滚动查看</span>
    </footer>
  </section>
</template>

<style scoped>
.tree-map { border: 1px solid #d8e5dd; border-radius: 18px; background: #fff; }
.map-toolbar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; padding: 13px 16px; }
.map-guide { display: grid; gap: 4px; }
.map-guide strong { color: var(--wl-ink); font-size: 15px; }
.map-guide span, .map-legend { font-size: 12px; color: var(--wl-muted); }
.map-controls { display: flex; align-items: center; gap: 5px; }
.map-controls button { min-width: 34px; min-height: 34px; display: inline-flex; align-items: center; justify-content: center; gap: 5px; border: 1px solid #dbe7df; border-radius: 8px; background: #f7faf8; color: #295d50; cursor: pointer; font: inherit; font-size: 12px; padding: 5px 8px; }
.map-controls button:hover:not(:disabled) { background: #eaf2eb; }
.map-controls button:disabled { color: #87968e; cursor: default; }
.map-controls button svg { width: 13px; height: 13px; }
.map-controls output { min-width: 40px; text-align: center; color: #35584c; font-size: 12px; font-variant-numeric: tabular-nums; }
.reset-view { margin-left: 3px; }
.map-viewport { min-height: 176px; max-height: min(490px, 65vh); overflow: auto; border-block: 1px solid #d8e5dd; background: radial-gradient(circle, #709b892c 1px, transparent 1.25px) 0 0 / 17px 17px, #eef5ef; }
.map-frame { position: relative; overflow: clip; }
.map-surface { transform-origin: top left; position: relative; }
.map-edges { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
.map-edges path { fill: none; stroke: #8eaea0; stroke-width: 2; }
.map-edges .edge-active { stroke: #236358; stroke-width: 3; }
.map-depth { position: absolute; top: 17px; color: #4b685c; background: #f7faf7; padding: 2px 7px; border: 1px solid #dce7df; border-radius: 6px; font-size: 11px; white-space: nowrap; }
.map-node-wrap { position: absolute; transform: translateY(-50%); }
.map-node { display: flex; align-items: center; width: 100%; height: 65px; gap: 9px; padding: 9px 15px 9px 10px; text-align: left; background: #fff; border: 1px solid #bdcfc3; border-radius: 11px; box-shadow: 0 2px 5px #1b4a3720; color: var(--wl-ink); cursor: pointer; font: inherit; }
.map-root { background: #215c50; border-color: #215c50; color: #f5fcf7; }
.map-node:hover { border-color: #5d8f7c; }
.map-selected { box-shadow: 0 0 0 2px #317c68; border-color: #317c68; background: #f4fbf5; }
.node-avatar { width: 32px; height: 32px; flex: 0 0 32px; display: grid; place-items: center; border-radius: 9px; color: #245b4d; background: #e6f0e8; font-size: 14px; font-weight: 650; overflow: hidden; }
.node-avatar-img { width: 100%; height: 100%; object-fit: cover; }
.map-root .node-avatar { background: #ffffff25; color: #f5fcf7; }
.node-copy { min-width: 0; display: grid; gap: 3px; }
.node-copy :is(strong, span) { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.node-copy strong { font-size: 13px; }
.node-copy span { font-size: 12px; color: #506a60; }
.map-root .node-copy span { color: #d5eae0; }
.branch-control { display: grid; place-items: center; position: absolute; right: -11px; top: 50%; transform: translateY(-50%); width: 22px; height: 22px; border: 1px solid #a8c4b8; border-radius: 50%; background: #fff; color: #285e50; cursor: pointer; padding: 3px; }
.branch-control:hover { background: #dceee2; }
.branch-control svg { width: 13px; height: 13px; }
.map-controls button:focus-visible, .map-node:focus-visible, .branch-control:focus-visible, .map-viewport:focus-visible { outline: 2px solid #936020; outline-offset: 2px; }
.map-legend { display: flex; gap: 7px 15px; align-items: center; flex-wrap: wrap; padding: 10px 16px; }
.map-legend span { display: inline-flex; gap: 6px; align-items: center; }
.map-legend i { width: 10px; height: 10px; border-radius: 3px; background: #215c50; }
.map-legend span:nth-child(2) i { width: 17px; height: 3px; }
.map-scroll-hint { margin-left: auto; }
@media (max-width: 465px) {
  .map-scroll-hint { margin-left: 0; width: 100%; }
}
</style>
