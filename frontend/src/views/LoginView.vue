<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from '@/utils/toast'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const mode = ref<'login' | 'register'>('login')
const form = reactive({
  username: '',
  nickname: '',
  password: '',
})
const submitting = ref(false)

async function submit() {
  const username = form.username.trim()
  const nickname = form.nickname.trim()
  if (!username || !form.password) {
    toast.warning('请填写用户名和密码')
    return
  }
  if (username.length < 3) {
    toast.warning('用户名至少 3 个字符')
    return
  }
  if (username.length > 50) {
    toast.warning('用户名最多 50 个字符')
    return
  }
  if (!/^[A-Za-z0-9]+$/.test(username)) {
    toast.warning('用户名只能包含字母和数字')
    return
  }
  if (form.password.length < 6) {
    toast.warning('密码至少 6 位')
    return
  }
  if (mode.value === 'register' && nickname.length > 50) {
    toast.warning('昵称最多 50 个字符')
    return
  }
  form.username = username
  submitting.value = true
  try {
    if (mode.value === 'login') {
      await userStore.login(username, form.password)
      toast.success('欢迎回来 🌊')
    } else {
      await userStore.register(username, nickname || username, form.password)
      toast.success('注册成功，欢迎来到微澜 🌊')
    }
    // 登录成功后跳回原目标页（无则回首页）
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    router.push(redirect)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="login-brand">
        <span class="login-logo">🌊</span>
        <h1>微澜</h1>
        <p>捕捉每一朵思想涟漪</p>
      </div>

      <el-tabs v-model="mode" class="auth-tabs" stretch>
        <el-tab-pane label="登录" name="login" />
        <el-tab-pane label="注册" name="register" />
      </el-tabs>

      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input
            v-model="form.username"
            :placeholder="mode === 'register' ? '3-50 位字母或数字' : 'demo（种子账号，密码 demo123456）'"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-form-item v-if="mode === 'register'" label="昵称">
          <el-input v-model="form.nickname" placeholder="大家怎么称呼你" @keyup.enter="submit" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="≥6 位"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          class="submit-btn"
          :loading="submitting"
          @click="submit"
        >
          {{ mode === 'login' ? '进入微澜' : '注册并进入' }}
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
}

.login-card {
  width: 100%;
  max-width: 380px;
  background: #fff;
  border: 1px solid var(--wl-border);
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 8px 32px rgba(31, 122, 140, 0.08);
}

.login-brand {
  text-align: center;
  margin-bottom: 20px;
}

.login-logo {
  font-size: 40px;
}

.login-brand h1 {
  margin: 8px 0 4px;
  font-size: 26px;
  color: var(--wl-primary);
}

.login-brand p {
  margin: 0;
  color: #90a4ae;
  font-size: 13px;
}

.auth-tabs {
  margin-bottom: 16px;
}

.submit-btn {
  width: 100%;
  margin-top: 8px;
}
</style>
