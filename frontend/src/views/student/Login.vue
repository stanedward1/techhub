<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="brand">
        <div class="brand-mark">S</div>
        <div>
          <h1>StudyHub</h1>
          <p>在线作业提交平台</p>
        </div>
      </div>

      <el-tabs v-model="tab" class="tabs">
        <el-tab-pane label="学生登录" name="login">
          <el-form @submit.prevent="doLogin">
            <el-form-item>
              <el-select v-model="form.class_id" placeholder="选择班级" size="large" style="width: 100%">
                <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-input v-model="form.username" placeholder="姓名" size="large" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="form.password" type="password" placeholder="密码" size="large" show-password @keyup.enter="doLogin" />
            </el-form-item>
            <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="doLogin">
              登 录
            </el-button>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="学生注册" name="register">
          <el-form @submit.prevent="doRegister">
            <el-form-item>
              <el-select v-model="reg.class_id" placeholder="选择班级" size="large" style="width: 100%">
                <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-input v-model="reg.name" placeholder="姓名" size="large" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="reg.password" type="password" placeholder="密码（默认 123456）" size="large" show-password />
            </el-form-item>
            <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="doRegister">
              注 册
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <div class="hint">
        教师请前往 <router-link to="/admin/login">管理后台登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi, metaApi } from '../../api'
import { setAuth } from '../../utils/auth'

const router = useRouter()
const tab = ref('login')
const loading = ref(false)
const classes = ref([])

const form = reactive({ class_id: null, username: '', password: '' })
const reg = reactive({ class_id: null, name: '', password: '123456' })

onMounted(async () => {
  try {
    const res = await metaApi.classes()
    classes.value = res.items
  } catch (e) {}
})

async function doLogin() {
  if (!form.class_id || !form.username || !form.password) {
    return ElMessage.warning('请选择班级并填写姓名和密码')
  }
  loading.value = true
  try {
    const res = await authApi.login(form)
    setAuth(res.token, res.user)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e) {
  } finally {
    loading.value = false
  }
}

async function doRegister() {
  if (!reg.class_id || !reg.name) {
    return ElMessage.warning('请选择班级并填写姓名')
  }
  loading.value = true
  try {
    const res = await authApi.register({
      name: reg.name,
      class_id: reg.class_id,
      password: reg.password || '123456'
    })
    setAuth(res.token, res.user)
    ElMessage.success('注册成功')
    router.push('/')
  } catch (e) {
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #4f46e5 100%);
  padding: 20px;
}
.login-card {
  width: 400px;
  background: #fff;
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}
.brand-mark {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: linear-gradient(135deg, #2563eb, #4f46e5);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 700;
}
.brand h1 {
  margin: 0;
  font-size: 20px;
  color: #111827;
}
.brand p {
  margin: 2px 0 0;
  font-size: 13px;
  color: #6b7280;
}
.tabs {
  margin-top: 8px;
}
.hint {
  text-align: center;
  margin-top: 16px;
  font-size: 13px;
  color: #6b7280;
}
.hint a {
  color: #2563eb;
}
</style>
