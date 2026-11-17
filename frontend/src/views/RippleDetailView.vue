<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { InputInstance } from 'element-plus'
import { createEcho, deleteEcho, getRippleDetail } from '@/api/ripples'
import type { CollectionOut, EchoOut, LikeOut, RippleDetail } from '@/api/types'
import ImageViewer from '@/components/ImageViewer.vue'
import LikeButton from '@/components/LikeButton.vue'
import CollectionButton from '@/components/CollectionButton.vue'
import EchoNode from '@/components/EchoNode.vue'
import EchoTreeMap from '@/components/EchoTreeMap.vue'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const detail = ref<RippleDetail | null>(null)
const loading = ref(false)
const failed = ref(false)
const store = useUserStore()
const posting = ref(false)
const deleting = ref(false)
const echoView = ref('discussion')
const selectedEcho = ref<EchoOut | null>(null)
const replyTarget = ref<EchoOut | null>(null)
const content = ref('')
const emotion = ref<string | null>(null)
const composer = ref<HTMLElement | null>(null)
const input = ref<InputInstance>()
const interactive = computed(() => detail.value?.ripple.status === 'published' && !posting.value && !deleting.value && !loading.value)
const canDeleteSelected = computed(() => selectedEcho.value && (selectedEcho.value.user.id === store.user?.id || store.user?.role === 'admin'))
let requestVersion = 0

function depthOf(id: number, nodes = detail.value?.echoes || [], level = 1): number {
  for (const node of nodes) {
    if (node.id === id) return level
    const depth = depthOf(id, node.children, level + 1)
    if (depth) return depth
  }
  return 0
}

async function loadDetail() {
  const id = Number(route.params.id)
  const version = ++requestVersion
  loading.value = true
  failed.value = false
  try {
    const result = await getRippleDetail(id)
    if (version === requestVersion) detail.value = result
  } catch {
    if (version === requestVersion) failed.value = true
  } finally {
    if (version === requestVersion) loading.value = false
  }
}

async function reply(echo: EchoOut | null) {
  replyTarget.value = echo
  await nextTick()
  composer.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  input.value?.focus()
}

async function submitEcho() {
  if (!interactive.value) return
  const text = content.value.trim()
  if (!text) { ElMessage.warning('回声内容不能为空'); return }
  const id = Number(route.params.id)
  posting.value = true
  try {
    await createEcho(id, { content: text, parent_echo_id: replyTarget.value?.id ?? null, emotion_code: emotion.value || null })
    if (Number(route.params.id) !== id) return
    content.value = ''
    emotion.value = null
    replyTarget.value = null
    selectedEcho.value = null
    await loadDetail()
    ElMessage.success('回声已发出')
  } catch { /* 全局提示；保留未提交成功的内容 */ }
  finally { if (Number(route.params.id) === id) posting.value = false }
}

async function removeEcho(echo: EchoOut) {
  try {
    await ElMessageBox.confirm('删除这条回声及其所有回复？此操作无法撤销。', '删除回声', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning',
    })
  } catch { return }
  const id = Number(route.params.id)
  deleting.value = true
  try {
    await deleteEcho(echo.id)
    if (Number(route.params.id) !== id) return
    replyTarget.value = null
    selectedEcho.value = null
    await loadDetail()
    ElMessage.success('回声及其回复已删除')
  } catch { /* 全局提示 */ }
  finally { if (Number(route.params.id) === id) deleting.value = false }
}

function updateLike(state: LikeOut) {
  if (detail.value && detail.value.ripple.id === state.ripple_id) {
    detail.value.ripple.is_liked = state.is_liked
    detail.value.ripple.like_count = state.like_count
  }
}

function updateCollection(state: CollectionOut) {
  if (detail.value && detail.value.ripple.id === state.ripple_id) {
    detail.value.ripple.is_collected = state.is_collected
  }
}

/* ---------- 图片放大预览 ---------- */
const viewer = reactive({
  visible: false,
  urls: [] as string[],
  index: 0,
})

function openViewer(urls: string[], index: number) {
  viewer.urls = urls
  viewer.index = index
  viewer.visible = true
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

watch(() => route.params.id, () => {
  detail.value = null
  replyTarget.value = null
  selectedEcho.value = null
  content.value = ''
  emotion.value = null
  posting.value = false
  deleting.value = false
  viewer.visible = false
  void loadDetail()
}, { immediate: true })
onBeforeUnmount(() => { requestVersion++ })
</script>

<template>
  <div v-loading="loading">
    <div v-if="failed" class="empty-tip"><p>微澜不存在、不可查看或加载失败</p><el-button @click="loadDetail">重新加载</el-button></div>
    <template v-if="detail">
      <div class="card">
        <div class="rc-head">
          <router-link :to="`/users/${detail.ripple.user.id}`" class="rc-nickname">{{ detail.ripple.user.nickname }}</router-link>
          <span class="rc-time">{{ formatTime(detail.ripple.created_at) }}</span>
          <span
            v-if="detail.ripple.emotion"
            class="rc-emotion"
            :style="{ color: detail.ripple.emotion.color }"
          >
            ● {{ detail.ripple.emotion.name }}
          </span>
        </div>
        <p class="rc-content">{{ detail.ripple.content }}</p>
        <div v-if="detail.ripple.images?.length" class="rd-images">
          <img
            v-for="(url, i) in detail.ripple.images"
            :key="i"
            :src="url"
            class="rd-img"
            alt="配图"
            @click="openViewer(detail.ripple.images, i)"
          />
        </div>
        <div class="rc-foot">
          <span v-if="detail.ripple.topic" class="rc-topic"># {{ detail.ripple.topic.name }}</span>
          <span>💬 {{ detail.ripple.echo_count }}</span>
          <LikeButton :ripple="detail.ripple" @updated="updateLike" />
          <CollectionButton :ripple="detail.ripple" @updated="updateCollection" />
        </div>
      </div>

      <ImageViewer
        v-if="viewer.visible"
        :urls="viewer.urls"
        :index="viewer.index"
        @close="viewer.visible = false"
      />

      <div class="echo-toolbar">
        <h3>回声 · 涟漪树 <small>{{ detail.ripple.echo_count }}</small></h3>
        <el-radio-group v-model="echoView" aria-label="回声展示方式">
          <el-radio-button value="discussion">讨论列表</el-radio-button>
          <el-radio-button value="tree">涟漪树</el-radio-button>
        </el-radio-group>
        <el-button :disabled="loading || posting || deleting" @click="selectedEcho = null; loadDetail()">刷新回声</el-button>
      </div>
      <div v-if="detail.echoes.length === 0" class="empty-tip">
        还没有回声，等待第一个共鸣者。
      </div>

      <ul v-if="echoView === 'discussion'" class="echo-list" aria-label="回声讨论">
        <EchoNode v-for="echo in detail.echoes" :key="echo.id" :echo="echo" :interactive="interactive" @reply="reply" @remove="removeEcho" />
      </ul>
      <template v-else>
        <EchoTreeMap :ripple="detail.ripple" :echoes="detail.echoes" :selected-id="selectedEcho?.id ?? null" @select="selectedEcho = $event" />
        <article v-if="selectedEcho" class="card selected-echo">
          <router-link :to="`/users/${selectedEcho.user.id}`">{{ selectedEcho.user.nickname }}</router-link>
          <p>{{ selectedEcho.content }}</p>
          <el-button type="primary" :disabled="!interactive || depthOf(selectedEcho.id) >= 8" @click="reply(selectedEcho)">回复此回声</el-button>
          <el-button v-if="canDeleteSelected" type="danger" plain :disabled="!interactive" @click="removeEcho(selectedEcho)">删除此回声</el-button>
        </article>
      </template>

      <section v-if="detail.ripple.status === 'published'" ref="composer" class="card echo-composer" aria-label="发表回声">
        <div class="reply-heading">
          <strong>{{ replyTarget ? `回复 ${replyTarget.user.nickname}` : '回应这条微澜' }}</strong>
          <el-button v-if="replyTarget" link @click="replyTarget = null">取消回复</el-button>
        </div>
        <p v-if="replyTarget" class="reply-preview">{{ replyTarget.content }}</p>
        <el-input ref="input" v-model="content" type="textarea" :rows="3" maxlength="200" show-word-limit placeholder="写下你的回声，最多 200 字…" :disabled="posting || deleting" aria-label="回声内容" />
        <div class="composer-actions">
          <el-select v-model="emotion" clearable placeholder="选择情绪（可选）" aria-label="回声情绪" style="width: 190px" :disabled="posting">
            <el-option v-for="item in [{ value: 'joy', label: '喜悦' }, { value: 'anger', label: '愤怒' }, { value: 'sorrow', label: '悲伤' }, { value: 'fear', label: '恐惧' }, { value: 'think', label: '思考' }, { value: 'calm', label: '平静' }]" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-button type="primary" :loading="posting" :disabled="!interactive || !content.trim()" @click="submitEcho">{{ replyTarget ? '发送回复' : '发表回声' }}</el-button>
        </div>
        <small>支持最多 8 层回复，点击作者昵称可进入主页。</small>
      </section>
      <p v-else class="empty-tip">当前微澜未公开，回声仅供查看。</p>
    </template>
  </div>
</template>

<style scoped>
.rc-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.rc-nickname {
  font-weight: 600;
  color: #37474f;
  text-decoration: none;
}

.rc-time {
  font-size: 12px;
  color: #90a4ae;
}

.rc-emotion {
  font-size: 12px;
  margin-left: auto;
}

.rc-content {
  font-size: 16px;
  line-height: 1.8;
  margin: 0 0 12px;
}

.rd-images {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.rd-img {
  max-width: 100%;
  max-height: 320px;
  border-radius: 10px;
  /* contain：按原始比例完整显示，不裁切不变形 */
  object-fit: contain;
  background: #f2f6f8;
  cursor: zoom-in;
}

.rc-foot {
  font-size: 13px;
  color: #78909c;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 14px;
}

.rc-topic {
  color: var(--wl-primary);
}

.echo-toolbar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin: 24px 0 12px; }
.echo-toolbar h3 { font-size: 17px; margin: 0 auto 0 0; }
.echo-toolbar small { color: #78909c; }
.echo-list { padding: 0; list-style: none; }
.echo-composer { margin-top: 20px; }
.reply-heading, .composer-actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
.composer-actions { margin-top: 14px; }
.reply-preview { padding: 10px; border-left: 3px solid #9bc8d2; background: #f5fafb; color: #607d8b; overflow-wrap: anywhere; }
.echo-composer small { color: #90a4ae; }
.selected-echo { margin-top: 12px; }
.selected-echo a { color: var(--wl-primary); text-decoration: none; }
.selected-echo p { white-space: pre-wrap; overflow-wrap: anywhere; }
</style>
