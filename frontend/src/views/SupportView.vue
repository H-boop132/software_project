<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getMySupport, type SupportItem } from '@/api/support'

const route = useRoute()
const router = useRouter()
const kind = computed(() => route.query.tab === 'appeals' ? 'appeals' : 'reports')
const status = ref('')
const page = ref(1)
const pageSize = 10
const items = ref<SupportItem[]>([])
const total = ref(0)
const loading = ref(true)
const failed = ref(false)
let requestVersion = 0
const pages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

const states: Record<string, string> = {
  pending: '待处理', uphold: '举报成立', dismissed: '举报已关闭',
  approved: '申诉通过', rejected: '申诉驳回',
}
const reasons: Record<string, string> = {
  spam: '广告引流', abuse: '攻击骚扰', misinformation: '不实信息', illegal: '违法违规', other: '其他',
}
const statuses = computed(() => kind.value === 'reports' ? ['pending', 'uphold', 'dismissed'] : ['pending', 'approved', 'rejected'])

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN')
}

function changeTab(tab: 'reports' | 'appeals') {
  void router.replace({ name: 'support', query: { tab } })
}

async function load() {
  const version = ++requestVersion
  loading.value = true
  failed.value = false
  try {
    const result = await getMySupport(kind.value, {
      status: statuses.value.includes(status.value) ? status.value : undefined,
      limit: pageSize, offset: (page.value - 1) * pageSize,
    })
    if (version !== requestVersion) return
    const lastPage = Math.max(1, Math.ceil(result.total / pageSize))
    if (page.value > lastPage) {
      page.value = lastPage
      return
    }
    items.value = result.items
    total.value = result.total
  } catch {
    if (version === requestVersion) failed.value = true
  } finally {
    if (version === requestVersion) loading.value = false
  }
}

watch(kind, () => { status.value = ''; page.value = 1 })
watch(status, () => { page.value = 1 })
watch([kind, status, page], load, { immediate: true })
onBeforeUnmount(() => { requestVersion++ })
</script>

<template>
  <section class="support-page">
    <header class="support-heading">
      <div><h1>举报与申诉记录</h1><p>查看你提交的事项、处理进度与结果。</p></div>
      <router-link to="/profile">返回个人中心</router-link>
    </header>
    <div class="support-controls">
      <div class="support-tabs" role="group" aria-label="记录类型">
        <button type="button" :aria-pressed="kind === 'reports'" @click="changeTab('reports')">我的举报</button>
        <button type="button" :aria-pressed="kind === 'appeals'" @click="changeTab('appeals')">我的申诉</button>
      </div>
      <label>处理状态
        <select v-model="status"><option value="">全部状态</option><option v-for="item in statuses" :key="item" :value="item">{{ states[item] }}</option></select>
      </label>
      <el-button :disabled="loading" @click="load">刷新记录</el-button>
    </div>

    <div :aria-busy="loading">
      <p v-if="loading" class="support-notice" role="status">正在读取记录…</p>
      <div v-else-if="failed" class="support-notice"><p>记录加载失败。</p><el-button @click="load">重试</el-button></div>
      <template v-else>
        <p class="support-count">共 {{ total }} 条{{ kind === 'reports' ? '举报' : '申诉' }}记录</p>
        <p v-if="!items.length" class="support-notice">暂无{{ status ? '符合筛选条件的' : '' }}{{ kind === 'reports' ? '举报' : '申诉' }}记录。</p>
        <ol v-else class="support-list">
          <li v-for="item in items" :key="kind + item.id" class="support-item">
            <header>
              <strong>{{ kind === 'reports' ? '举报' : '申诉' }} #{{ item.id }}</strong>
              <span class="support-status" :data-status="item.status">{{ states[item.status] }}</span>
            </header>
            <p class="support-content">{{ item.ripple_preview ?? '该内容当前不可查看' }}</p>
            <dl>
              <div><dt>提交理由</dt><dd>{{ kind === 'reports' ? reasons[item.reason_code ?? 'other'] : item.reason }}</dd></div>
              <div v-if="item.detail"><dt>补充说明</dt><dd>{{ item.detail }}</dd></div>
              <div v-if="item.handle_note"><dt>处理反馈</dt><dd>{{ item.handle_note }}</dd></div>
            </dl>
            <ol class="progress">
              <li><span class="progress-dot"></span><strong>已提交</strong><time :datetime="item.created_at">{{ formatTime(item.created_at) }}</time></li>
              <li :class="{ pending: item.status === 'pending' }"><span class="progress-dot"></span><strong>{{ item.status === 'pending' ? '等待管理员处理' : '处理完成' }}</strong><time v-if="item.handled_at" :datetime="item.handled_at">{{ formatTime(item.handled_at) }}</time></li>
            </ol>
            <router-link v-if="item.can_open" :to="{ name: 'ripple-detail', params: { id: item.ripple_id } }">查看相关微澜</router-link>
          </li>
        </ol>
        <nav v-if="total > pageSize" class="support-pagination" aria-label="记录分页">
          <button type="button" :disabled="page === 1" @click="page--">上一页</button>
          <span>{{ page }} / {{ pages }}</span>
          <button type="button" :disabled="page === pages" @click="page++">下一页</button>
        </nav>
      </template>
    </div>
  </section>
</template>

<style scoped>
.support-heading { display: flex; justify-content: space-between; gap: 16px; align-items: end; flex-wrap: wrap; padding-bottom: 19px; border-bottom: 2px solid var(--wl-ink); }
.support-heading h1 { margin: 0; font-size: clamp(25px, 4vw, 36px); }
.support-heading p { margin: 8px 0 0; font-size: 13px; color: var(--wl-muted); }
.support-page a { color: var(--wl-primary); font-size: 13px; text-underline-offset: 4px; }
.support-controls { display: flex; gap: 12px 18px; align-items: center; flex-wrap: wrap; padding-block: 18px; }
.support-tabs { display: flex; border: 1px solid var(--wl-border); border-radius: 8px; padding: 3px; background: #eaf0eb; gap: 3px; }
.support-tabs button, .support-pagination button { font: inherit; font-size: 13px; padding: 7px 10px; border: 0; border-radius: 6px; background: transparent; color: var(--wl-muted); cursor: pointer; }
.support-tabs button[aria-pressed=true] { color: var(--wl-primary); background: white; font-weight: 650; }
.support-controls label { font-size: 13px; color: var(--wl-muted); display: flex; gap: 8px; align-items: center; }
.support-controls select { font: inherit; padding: 6px 8px; border: 1px solid var(--wl-border); border-radius: 6px; color: var(--wl-ink); background: white; }
.support-count { font-size: 12px; color: var(--wl-muted); margin: 0 0 12px; }
.support-list { list-style: none; padding: 0; margin: 0; display: grid; gap: 14px; }
.support-item { padding: 20px; border: 1px solid var(--wl-border); border-radius: 11px; background: white; min-width: 0; }
.support-item header { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.support-item header strong { font-size: 14px; }
.support-status { font-size: 12px; color: #255f50; background: #e5f0e8; padding: 3px 7px; border-radius: 5px; }
.support-status[data-status=pending] { color: #805d29; background: #fbf1dc; }
.support-status[data-status=rejected], .support-status[data-status=dismissed] { color: #5e6871; background: #edf0f2; }
.support-content { font-size: 14px; line-height: 1.65; overflow-wrap: anywhere; }
.support-item dl { font-size: 13px; margin: 12px 0 17px; display: grid; gap: 7px; }
.support-item dl > div { display: grid; grid-template-columns: 65px minmax(0, 1fr); gap: 5px; }
.support-item dt { color: var(--wl-muted); }
.support-item dd { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; }
.progress { list-style: none; padding: 0; margin: 0 0 12px; display: grid; gap: 10px; }
.progress li { display: grid; grid-template-columns: 10px minmax(0, 1fr); gap: 4px 8px; align-items: center; font-size: 12px; }
.progress strong { font-weight: 500; color: var(--wl-ink); }
.progress time { color: var(--wl-muted); grid-column: 2; }
.progress-dot { width: 7px; height: 7px; border-radius: 50%; background: #3a7864; }
.pending .progress-dot { background: white; border: 1px solid #9eaf9e; }
.support-notice { padding-block: 30px; text-align: center; font-size: 14px; color: var(--wl-muted); }
.support-pagination { display: flex; justify-content: center; gap: 15px; align-items: center; margin-top: 20px; font-size: 13px; }
.support-pagination button { background: white; border: 1px solid var(--wl-border); color: var(--wl-primary); }
.support-pagination button:disabled { cursor: default; color: var(--wl-muted); }
@media (max-width: 450px) {
  .support-item { padding: 14px; }
}
</style>
