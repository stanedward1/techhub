<template>
  <div>
    <div class="toolbar">
      <el-select v-model="action" placeholder="全部操作" clearable style="width: 180px" @change="load">
        <el-option v-for="a in actions" :key="a" :label="actionText(a)" :value="a" />
      </el-select>
      <el-input v-model="keyword" placeholder="搜索操作人/对象" clearable style="width: 220px" @keyup.enter="load" @clear="load" />
      <el-button @click="load">查询</el-button>
      <div class="spacer"></div>
    </div>

    <div class="page-card">
      <el-table :data="items" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="操作人" width="120" />
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="roleType(row.role)" size="small">{{ roleText(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <span>{{ actionText(row.action) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="target" label="操作对象" min-width="200" show-overflow-tooltip />
        <el-table-column prop="detail" label="详情" min-width="180" show-overflow-tooltip />
        <el-table-column prop="created_at" label="时间" width="170" />
      </el-table>
      <el-pagination
        style="margin-top: 16px; justify-content: flex-end"
        layout="total, prev, pager, next"
        :total="total" :page-size="pageSize" :current-page="page"
        @current-change="onPage"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { adminApi } from '../../api'

const items = ref([])
const action = ref('')
const keyword = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)
const loading = ref(false)

const actions = [
  'change_password', 'reset_password', 'delete_user', 'delete_student',
  'delete_classroom', 'delete_school', 'upgrade_grade', 'create_user',
  'create_classroom', 'create_student', 'import_students', 'import_scores'
]

function actionText(a) {
  return {
    change_password: '修改密码', reset_password: '重置密码', delete_user: '删除账号',
    delete_student: '删除学生', delete_classroom: '删除班级', delete_school: '删除学校',
    upgrade_grade: '年级升级', create_user: '创建账号', create_classroom: '创建班级',
    create_student: '创建学生', import_students: '导入学生', import_scores: '导入成绩'
  }[a] || a
}
function roleText(r) {
  return { admin: '管理员', teacher: '教师', student: '学生' }[r] || r
}
function roleType(r) {
  return { admin: 'danger', teacher: 'primary', student: 'info' }[r] || 'info'
}

onMounted(load)

async function load() {
  loading.value = true
  try {
    const res = await adminApi.auditLogs({ action: action.value, keyword: keyword.value, page: page.value, page_size: pageSize })
    items.value = res.items
    total.value = res.total
  } catch (e) {
  } finally {
    loading.value = false
  }
}

function onPage(p) {
  page.value = p
  load()
}
</script>
