<template>
  <div>
    <div class="toolbar">
      <StudentSelect v-model="studentId" placeholder="按学生筛选" style="width: 220px" @update:model-value="load" />
      <div class="spacer"></div>
      <el-button type="primary" @click="openCreate">录入积分</el-button>
      <SortBar v-model="order" />
    </div>

    <div class="page-card">
      <el-table :data="items" v-loading="loading" style="width: 100%">
        <el-table-column prop="student_name" label="学生" width="140" />
        <el-table-column prop="student_no" label="学号" width="120" />
        <el-table-column label="积分" width="100">
          <template #default="{ row }">
            <span :style="{ color: row.points >= 0 ? '#16a34a' : '#dc2626', fontWeight: 600 }">
              {{ row.points >= 0 ? '+' : '' }}{{ row.points }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="事由" min-width="200" />
        <el-table-column prop="created_at" label="时间" width="180" />
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

    <el-dialog v-model="dialog" title="录入积分" width="440px">
      <el-form label-width="80px">
        <el-form-item label="学生" required><StudentSelect v-model="form.student_id" /></el-form-item>
        <el-form-item label="积分" required>
          <el-input-number v-model="form.points" :min="-100" :max="100" />
          <span style="margin-left: 8px; color: #9ca3af; font-size: 12px">正数加分，负数扣分</span>
        </el-form-item>
        <el-form-item label="事由"><el-input v-model="form.reason" /></el-form-item>
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
import { useSort } from '../../composables/useSort.js'
import { pointApi } from '../../api'

const rawItems = ref([])
const { order, useSorted } = useSort('points')
const items = useSorted(rawItems)
const studentId = ref(null)
const page = ref(1)
const pageSize = 20
const total = ref(0)
const loading = ref(false)
const dialog = ref(false)
const saving = ref(false)
const form = reactive({ student_id: null, points: 1, reason: '' })

onMounted(load)

async function load() {
  loading.value = true
  try {
    const res = await pointApi.list({ page: page.value, page_size: pageSize, student_id: studentId.value })
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
  Object.assign(form, { student_id: null, points: 1, reason: '' })
  dialog.value = true
}

async function save() {
  if (!form.student_id) return ElMessage.warning('请选择学生')
  saving.value = true
  try {
    await pointApi.create(form)
    ElMessage.success('保存成功')
    dialog.value = false
    load()
  } catch (e) {
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  await ElMessageBox.confirm('确定删除该积分记录吗？', '提示', { type: 'warning' })
  await pointApi.remove(row.id)
  ElMessage.success('删除成功')
  load()
}
</script>
