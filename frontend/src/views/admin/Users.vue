<template>
  <div>
    <div class="toolbar">
      <el-select v-model="role" placeholder="全部角色" clearable style="width: 160px" @change="load">
        <el-option label="管理员" value="admin" />
        <el-option label="教师" value="teacher" />
        <el-option label="学生" value="student" />
      </el-select>
      <el-input v-model="keyword" placeholder="搜索姓名/用户名" clearable style="width: 200px" @keyup.enter="load" @clear="load" />
      <el-button @click="load">查询</el-button>
      <div class="spacer"></div>
      <el-button type="primary" @click="openCreate">新增账号</el-button>
    </div>

    <div class="page-card">
      <el-table :data="items" v-loading="loading" style="width: 100%">
        <el-table-column prop="username" label="用户名" width="140" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="roleType(row.role)" size="small">{{ roleText(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="phone" label="电话" width="140" />
        <el-table-column prop="class_name" label="班级" width="160" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="warning" @click="resetPwd(row)">重置密码</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialog" :title="editing ? '编辑账号' : '新增账号'" width="460px">
      <el-form label-width="80px">
        <el-form-item label="用户名" required><el-input v-model="form.username" :disabled="!!editing" /></el-form-item>
        <el-form-item v-if="!editing" label="密码"><el-input v-model="form.password" placeholder="默认 123456" /></el-form-item>
        <el-form-item label="姓名" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width: 100%" :disabled="!!editing && editing.role === 'admin'">
            <el-option label="管理员" value="admin" />
            <el-option label="教师" value="teacher" />
            <el-option label="学生" value="student" />
          </el-select>
        </el-form-item>
        <el-form-item label="电话"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item v-if="form.role === 'student'" label="班级">
          <el-select v-model="form.class_id" clearable style="width: 100%">
            <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi, metaApi } from '../../api'

const items = ref([])
const classes = ref([])
const role = ref('')
const keyword = ref('')
const loading = ref(false)
const dialog = ref(false)
const editing = ref(null)
const saving = ref(false)
const form = reactive({ username: '', password: '', name: '', role: 'teacher', phone: '', class_id: null })

onMounted(async () => {
  const res = await metaApi.classes()
  classes.value = res.items
  load()
})

async function load() {
  loading.value = true
  try {
    const res = await adminApi.users({ role: role.value, keyword: keyword.value })
    items.value = res.items
  } catch (e) {
  } finally {
    loading.value = false
  }
}

function roleType(r) {
  return { admin: 'danger', teacher: 'primary', student: 'info' }[r]
}
function roleText(r) {
  return { admin: '管理员', teacher: '教师', student: '学生' }[r]
}

function openCreate() {
  editing.value = null
  Object.assign(form, { username: '', password: '', name: '', role: 'teacher', phone: '', class_id: null })
  dialog.value = true
}

function openEdit(row) {
  editing.value = row
  Object.assign(form, { username: row.username, name: row.name, role: row.role, phone: row.phone, class_id: row.class_id })
  dialog.value = true
}

async function save() {
  if (!form.username || !form.name) return ElMessage.warning('请填写用户名和姓名')
  saving.value = true
  try {
    if (editing.value) await adminApi.updateUser(editing.value.id, form)
    else await adminApi.createUser(form)
    ElMessage.success('保存成功')
    dialog.value = false
    load()
  } catch (e) {
  } finally {
    saving.value = false
  }
}

async function resetPwd(row) {
  await ElMessageBox.confirm(`确定将「${row.name}」的密码重置为 123456 吗？`, '提示', { type: 'warning' })
  await adminApi.resetPassword(row.id, { password: '123456' })
  ElMessage.success('密码已重置为 123456')
}

async function remove(row) {
  await ElMessageBox.confirm(`确定删除账号「${row.name}」吗？`, '提示', { type: 'warning' })
  await adminApi.removeUser(row.id)
  ElMessage.success('删除成功')
  load()
}
</script>
