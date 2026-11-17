<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { createRipple, getHotTides } from '@/api/ripples'
import { uploadImage } from '@/api/upload'
import type { TopicOut } from '@/api/types'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const content = ref('')
const topicId = ref<number | null>(null)
const emotionCode = ref<string | null>(null)
const topics = ref<TopicOut[]>([])
const submitting = ref(false)

/* ---------------- 配图（最多 9 张） ---------------- */
const images = ref<string[]>([])
const uploadsPending = ref(0)
const previewVisible = ref(false)
const previewUrl = ref('')

const MAX_IMAGES = 9

const emotions = [
  { code: 'joy', name: '喜悦', color: '#F5A623' },
  { code: 'anger', name: '愤怒', color: '#E74C3C' },
  { code: 'sorrow', name: '悲伤', color: '#5C7CFA' },
  { code: 'fear', name: '恐惧', color: '#9B59B6' },
  { code: 'think', name: '思考', color: '#2ECC71' },
  { code: 'calm', name: '平静', color: '#7F8C8D' },
]

const draftKey = computed(() => userStore.user && `weilan_ripple_draft:${userStore.user.id}`)
const hasDraft = computed(() => Boolean(
  content.value || topicId.value != null || emotionCode.value || images.value.length,
))
const draftStatus = ref('')
let restoringDraft = false

function resetForm() {
  content.value = ''
  topicId.value = null
  emotionCode.value = null
  images.value = []
}

watch(draftKey, (key) => {
  restoringDraft = true
  try {
    resetForm()
    draftStatus.value = ''
    if (!key) return
    const saved = localStorage.getItem(key)
    if (!saved) return
    const draft = JSON.parse(saved)
    content.value = typeof draft?.content === 'string' ? draft.content.slice(0, 200) : ''
    topicId.value = Number.isSafeInteger(draft?.topicId) && draft.topicId > 0 ? draft.topicId : null
    emotionCode.value = emotions.find((emotion) => emotion.code === draft?.emotionCode)?.code ?? null
    if (Array.isArray(draft?.images)) {
      images.value = draft.images.filter(
        (url: unknown): url is string => typeof url === 'string' && url.startsWith('/uploads/'),
      ).slice(0, MAX_IMAGES)
    }
    if (hasDraft.value) draftStatus.value = '已恢复此浏览器中的草稿'
  } catch {
    draftStatus.value = '无法读取此浏览器中的草稿'
  } finally {
    restoringDraft = false
  }
}, { immediate: true, flush: 'sync' })

watch([content, topicId, emotionCode, images], () => {
  const key = draftKey.value
  if (!key || restoringDraft) return
  try {
    if (hasDraft.value) {
      localStorage.setItem(key, JSON.stringify({
        content: content.value,
        topicId: topicId.value,
        emotionCode: emotionCode.value,
        images: images.value,
      }))
      draftStatus.value = '草稿已保存到此浏览器'
    } else {
      localStorage.removeItem(key)
      draftStatus.value = ''
    }
  } catch {
    draftStatus.value = '草稿保存失败，请在离开前复制正文'
  }
}, { flush: 'sync' })

onBeforeRouteLeave(() => {
  if (!submitting.value && !uploadsPending.value) return
  ElMessage.info('请等当前操作完成后再离开')
  return false
})

async function discardDraft() {
  const key = draftKey.value
  try {
    await ElMessageBox.confirm('确定清空这份草稿？', '丢弃草稿', {
      type: 'warning',
      confirmButtonText: '丢弃',
      cancelButtonText: '继续编辑',
    })
  } catch {
    return
  }
  if (draftKey.value === key) resetForm()
}

async function handleUpload(file: File) {
  if (images.value.length + uploadsPending.value >= MAX_IMAGES) {
    ElMessage.warning(`最多上传 ${MAX_IMAGES} 张图片`)
    return
  }
  const key = draftKey.value
  uploadsPending.value++
  try {
    const res = await uploadImage(file)
    if (draftKey.value === key) images.value = [...images.value, res.url]
  } finally {
    uploadsPending.value--
  }
}

function openPreview(url: string) {
  previewUrl.value = url
  previewVisible.value = true
}

function removeImage(index: number) {
  images.value = images.value.filter((_, imageIndex) => imageIndex !== index)
}

async function submit() {
  const key = draftKey.value
  if (!key || submitting.value || uploadsPending.value) return
  if (!content.value.trim()) {
    ElMessage.warning('写点内容再发吧')
    return
  }
  submitting.value = true
  try {
    await createRipple({
      content: content.value.trim(),
      topic_id: topicId.value ?? null,
      emotion_code: emotionCode.value,
      images: images.value,
    })
    if (draftKey.value !== key) return
    resetForm()
    ElMessage.success('微澜已发出，静待回声 🌊')
    submitting.value = false
    router.push('/')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  const accountDraft = draftKey.value
  const currentTopic = topicId.value
  const requestedTopic = typeof route.query.topic === 'string' ? Number(route.query.topic) : undefined
  try {
    const tides = await getHotTides()
    topics.value = tides.map((t) => t.topic)
    const match = topics.value.find((topic) => topic.id === requestedTopic)
    if (match && accountDraft === draftKey.value && topicId.value === currentTopic) topicId.value = match.id
  } catch {
    /* 忽略 */
  }
})
</script>

<template>
  <div v-if="draftKey" class="card compose-card">
    <h2 class="page-title">发一朵微澜</h2>
    <p class="hint">≤200 字，说清此刻的想法即可。词不达意，也是涟漪的一部分。</p>

    <el-input
      v-model="content"
      type="textarea"
      :rows="5"
      maxlength="200"
      show-word-limit
      aria-label="微澜正文"
      :disabled="submitting"
      placeholder="例如：写代码时突然想通一件事……"
    />

    <!-- 配图 -->
    <div class="field">
      <div class="field-label">配图（可选，最多 9 张）</div>
      <div v-if="images.length" class="img-list">
        <div v-for="(url, i) in images" :key="i" class="img-item">
          <img :src="url" class="img-thumb" alt="" @click="openPreview(url)" />
          <button type="button" class="img-remove" aria-label="移除配图" :disabled="submitting" @click="removeImage(i)">×</button>
        </div>
      </div>
      <el-upload
        :show-file-list="false"
        :http-request="(opt: any) => handleUpload(opt.file as File)"
        :disabled="submitting || images.length + uploadsPending >= MAX_IMAGES"
        accept="image/jpeg,image/png,image/webp,image/gif"
        multiple
      >
        <el-button :disabled="submitting || images.length + uploadsPending >= MAX_IMAGES">
          {{ images.length >= MAX_IMAGES ? '已达上限' : '+ 添加图片' }}
        </el-button>
      </el-upload>
    </div>

    <div class="field">
      <div class="field-label">话题</div>
      <el-select v-model="topicId" placeholder="选一个话题（可选）" :disabled="submitting" clearable style="width: 220px">
        <el-option v-for="t in topics" :key="t.id" :label="t.name" :value="t.id" />
      </el-select>
    </div>

    <div class="field">
      <div class="field-label">此刻的情绪（可选）</div>
      <el-radio-group v-model="emotionCode" :disabled="submitting">
        <el-radio-button
          v-for="e in emotions"
          :key="e.code"
          :value="e.code"
          :style="{ '--el-radio-button-checked-bg-color': e.color }"
        >
          {{ e.name }}
        </el-radio-button>
      </el-radio-group>
    </div>

    <div class="actions">
      <el-button type="primary" :loading="submitting" :disabled="uploadsPending > 0" @click="submit">
        发出微澜
      </el-button>
      <el-button :disabled="submitting || uploadsPending > 0" @click="router.push('/')">返回时间线</el-button>
      <el-button v-if="hasDraft" text :disabled="submitting || uploadsPending > 0" @click="discardDraft">丢弃草稿</el-button>
      <span class="draft-status" role="status">{{ draftStatus }}</span>
    </div>

    <!-- 大图预览 -->
    <el-image-viewer
      v-if="previewVisible"
      :url-list="[previewUrl]"
      @close="previewVisible = false"
    />
  </div>
</template>

<style scoped>
.compose-card {
  max-width: 640px;
  margin: 0 auto;
}

.hint {
  color: #78909c;
  font-size: 13px;
  margin: -8px 0 16px;
}

.field {
  margin: 18px 0;
}

.field-label {
  font-size: 13px;
  color: #546e7a;
  margin-bottom: 8px;
}

.img-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.img-item {
  position: relative;
  width: 84px;
  height: 84px;
  border-radius: 8px;
  overflow: hidden;
}

.img-thumb {
  width: 100%;
  height: 100%;
  /* contain：保持原始比例，不裁切 */
  object-fit: contain;
  background: #f2f6f8;
  cursor: zoom-in;
}

.img-remove {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 20px;
  height: 20px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 14px;
  line-height: 20px;
  cursor: pointer;
}

.actions {
  margin-top: 24px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.draft-status {
  flex-basis: 100%;
  font-size: 13px;
  color: #546e7a;
}
</style>
