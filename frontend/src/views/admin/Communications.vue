<template>
  <div>
    <div class="toolbar">
      <StudentSelect v-model="studentId" placeholder="按学生筛选" style="width: 220px" @update:model-value="load" />
      <SortBar v-model="order" />
      <div class="spacer"></div>
      <el-button type="primary" @click="openCreate">新增沟通</el-button>
    </div>

    <div class="page-card">
      <el-table :data="items" v-loading="loading" style="width: 100%">
        <el-table-column prop="student_name" label="学生" width="120" />
        <el-table-column prop="method" label="方式" width="90">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.method }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="content" label="沟通内容" min-width="220" />
        <el-table-column prop="feedback" label="反馈" min-width="180" />
        <el-table-column prop="created_at" label="时间" width="170" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        style="margin-top: 16px; justify-content: flex-end"
        layout="total, prev, pager, next"
        :total="total" :page-size="pageSize" :current-page="page"
        @current-change="onPage"
      />
    </div>

    <el-dialog v-model="dialog" title="新增沟通记录" width="500px">
      <el-form label-width="80px">
        <el-form-item label="学生" required><StudentSelect v-model="form.student_id" /></el-form-item>
        <el-form-item label="方式">
          <el-select v-model="form.method" style="width: 100%">
            <el-option v-for="m in ['电话', '微信', '面谈', '其他']" :key="m" :label="m" :value="m" />
          </el-select>
        </el-form-item>
        <el-form-item label="沟通内容"><el-input v-model="form.content" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="反馈"><el-input v-model="form.feedback" type="textarea" :rows="2" /></el-form-item>
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
import StudentSelect from '../../components/StudentSelect.vue'
import SortBar from '../../components/SortBar.vue'
import { useSort } from '../../composables/useSort'
import { communicationApi } from '../../api'

const rawItems = ref([])
const { order, useSorted } = useSort('communications')
const items = useSorted(rawItems)
const studentId = ref(null)
const page = ref(1)
const pageSize = 20
const total = ref(0)
const loading = ref(false)
const dialog = ref(false)
const saving = ref(false)
const form = reactive({ student_id: null, method: '电话', content: '', feedback: '' })

onMounted(load)

async function load() {
  loading.value = true
  try {
    const res = await communicationApi.list({ page: page.value, page_size: pageSize, student_id: studentId.value })
    rawItems.value = res.items
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

function openCreate() {
  Object.assign(form, { student_id: null, method: '电话', content: '', feedback: '' })
  dialog.value = true
}

async function save() {
  if (!form.student_id) return ElMessage.warning('请选择学生')
  saving.value = true
  try {
    await communicationApi.create(form)
    ElMessage.success('保存成功')
    dialog.value = false
    load()
  } catch (e) {
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  await ElMessageBox.confirm('确定删除该记录吗？', '提示', { type: 'warning' })
  await communicationApi.remove(row.id)
  ElMessage.success('删除成功')
  load()
}
</script>
