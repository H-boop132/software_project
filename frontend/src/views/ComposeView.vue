<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { createRipple, getHotTides } from '@/api/ripples'
import { uploadImage } from '@/api/upload'
import type { TopicOut } from '@/api/types'

const router = useRouter()
const userStore = useUserStore()

const content = ref('')
const topicId = ref<number | null>(null)
const emotionCode = ref<string | null>(null)
const topics = ref<TopicOut[]>([])
const submitting = ref(false)

/* ---------------- 配图（最多 9 张） ---------------- */
const images = ref<string[]>([])
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

async function handleUpload(file: File) {
  if (images.value.length >= MAX_IMAGES) {
    ElMessage.warning(`最多上传 ${MAX_IMAGES} 张图片`)
    return
  }
  const res = await uploadImage(file)
  images.value.push(res.url)
}

function openPreview(url: string) {
  previewUrl.value = url
  previewVisible.value = true
}

function removeImage(index: number) {
  images.value.splice(index, 1)
}

async function submit() {
  if (!content.value.trim()) {
    ElMessage.warning('写点内容再发吧')
    return
  }
  submitting.value = true
  try {
    await createRipple({
      content: content.value.trim(),
      topic_id: topicId.value,
      emotion_code: emotionCode.value,
      images: images.value,
    })
    ElMessage.success('微澜已发出，静待回声 🌊')
    router.push('/')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    const tides = await getHotTides()
    topics.value = tides.map((t) => t.topic)
  } catch {
    /* 忽略 */
  }
})
</script>

<template>
  <div class="card compose-card">
    <h2 class="page-title">发一朵微澜</h2>
    <p class="hint">≤200 字，说清此刻的想法即可。词不达意，也是涟漪的一部分。</p>

    <el-input
      v-model="content"
      type="textarea"
      :rows="5"
      maxlength="200"
      show-word-limit
      placeholder="例如：写代码时突然想通一件事……"
    />

    <!-- 配图 -->
    <div class="field">
      <div class="field-label">配图（可选，最多 9 张）</div>
      <div v-if="images.length" class="img-list">
        <div v-for="(url, i) in images" :key="i" class="img-item">
          <img :src="url" class="img-thumb" alt="" @click="openPreview(url)" />
          <button type="button" class="img-remove" @click="removeImage(i)">×</button>
        </div>
      </div>
      <el-upload
        :show-file-list="false"
        :http-request="(opt: any) => handleUpload(opt.file as File)"
        accept="image/jpeg,image/png,image/webp,image/gif"
        multiple
      >
        <el-button :disabled="images.length >= MAX_IMAGES">
          {{ images.length >= MAX_IMAGES ? '已达上限' : '+ 添加图片' }}
        </el-button>
      </el-upload>
    </div>

    <div class="field">
      <div class="field-label">话题</div>
      <el-select v-model="topicId" placeholder="选一个话题（可选）" clearable style="width: 220px">
        <el-option v-for="t in topics" :key="t.id" :label="t.name" :value="t.id" />
      </el-select>
    </div>

    <div class="field">
      <div class="field-label">此刻的情绪（可选）</div>
      <el-radio-group v-model="emotionCode">
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
      <el-button type="primary" :loading="submitting" @click="submit">
        发出微澜
      </el-button>
      <el-button @click="router.push('/')">取消</el-button>
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
}
</style>
