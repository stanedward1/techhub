<template>
  <div>
    <div class="toolbar">
      <el-input v-model="subject" placeholder="按科目筛选" clearable style="width: 180px" @clear="load" />
      <StudentSelect v-model="studentId" placeholder="按学生筛选" style="width: 220px" @update:model-value="load" />
      <el-button @click="load">查询</el-button>
      <div class="spacer"></div>
      <el-button @click="downloadTemplate">下载模板</el-button>
      <el-button type="success" @click="openImport">批量导入</el-button>
      <el-button @click="exportExcel">导出成绩单</el-button>
      <el-button type="primary" @click="openCreate">录入成绩</el-button>
      <SortBar v-model="order" />
    </div>

    <div class="page-card">
      <el-table :data="items" v-loading="loading" style="width: 100%">
        <el-table-column prop="student_name" label="学生" width="120" />
        <el-table-column prop="student_no" label="学号" width="120" />
        <el-table-column prop="subject" label="科目" width="160" />
        <el-table-column prop="score" label="成绩" width="100" />
        <el-table-column prop="exam_name" label="考试名称" width="140" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
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

    <el-dialog v-model="dialog" :title="editing ? '编辑成绩' : '录入成绩'" width="440px">
      <el-form label-width="80px">
        <el-form-item label="学生" required><StudentSelect v-model="form.student_id" /></el-form-item>
        <el-form-item label="科目" required><el-input v-model="form.subject" /></el-form-item>
        <el-form-item label="成绩" required><el-input-number v-model="form.score" :min="0" :max="100" /></el-form-item>
        <el-form-item label="考试名称"><el-input v-model="form.exam_name" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 批量导入成绩弹窗 -->
    <el-dialog v-model="importDialog" title="批量导入成绩" width="560px" @close="resetImport">
      <el-form label-width="80px">
        <el-form-item label="导入模板">
          <el-button type="primary" link @click="downloadTemplate">下载标准模板</el-button>
          <span style="color: #909399; font-size: 12px; margin-left: 8px;">请按模板格式填写数据</span>
        </el-form-item>
        <el-form-item label="选择文件">
          <el-upload
            ref="importUploadRef"
            :auto-upload="false"
            :limit="1"
            :on-change="onImportFileChange"
            :on-remove="onImportFileRemove"
            :before-upload="() => false"
            accept=".xlsx,.xls"
            drag
          >
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="upload-text">将 Excel 文件拖到此处，或<em>点击选择</em></div>
            <template #tip>
              <div class="upload-tip">仅支持 .xlsx / .xls 格式</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <div v-if="importResult" class="import-result">
        <el-alert
          :title="`导入完成：成功 ${importResult.success} 条，失败 ${importResult.errors?.length || 0} 条`"
          :type="importResult.errors?.length ? 'warning' : 'success'"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
        />
        <div v-if="importResult.errors?.length" class="error-list">
          <div v-for="(err, i) in importResult.errors" :key="i" class="error-item">{{ err }}</div>
        </div>
      </div>
      <template #footer>
        <el-button @click="importDialog = false">关闭</el-button>
        <el-button type="primary" :loading="importing" @click="doImport">
          {{ importing ? '导入中...' : '开始导入' }}
        </el-button>
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
import { scoreApi } from '../../api'

const rawItems = ref([])
const { order, useSorted } = useSort('scores')
const items = useSorted(rawItems)
const subject = ref('')
const studentId = ref(null)
const page = ref(1)
const pageSize = 20
const total = ref(0)
const loading = ref(false)
const dialog = ref(false)
const editing = ref(null)
const saving = ref(false)
const form = reactive({ student_id: null, subject: '', score: 0, exam_name: '' })

// 批量导入
const importDialog = ref(false)
const importUploadRef = ref(null)
const importing = ref(false)
const importFile = ref(null)
const importResult = ref(null)

onMounted(load)

async function load() {
  loading.value = true
  try {
    const res = await scoreApi.list({ page: page.value, page_size: pageSize, subject: subject.value, student_id: studentId.value })
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
  editing.value = null
  Object.assign(form, { student_id: null, subject: '', score: 0, exam_name: '' })
  dialog.value = true
}

function openEdit(row) {
  editing.value = row
  Object.assign(form, row)
  dialog.value = true
}

async function save() {
  if (!form.student_id || !form.subject) return ElMessage.warning('请选择学生并填写科目')
  saving.value = true
  try {
    if (editing.value) await scoreApi.update(editing.value.id, form)
    else await scoreApi.create(form)
    ElMessage.success('保存成功')
    dialog.value = false
    load()
  } catch (e) {
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  await ElMessageBox.confirm('确定删除该成绩记录吗？', '提示', { type: 'warning' })
  await scoreApi.remove(row.id)
  ElMessage.success('删除成功')
  load()
}

async function exportExcel() {
  const res = await scoreApi.export({ student_id: studentId.value })
  const blob = new Blob([res], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = '成绩单.xlsx'
  a.click()
  URL.revokeObjectURL(url)
}

// 批量导入
function downloadTemplate() {
  scoreApi.template().then(res => {
    const blob = new Blob([res], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '成绩导入模板.xlsx'
    a.click()
    URL.revokeObjectURL(url)
  })
}

function openImport() {
  resetImport()
  importDialog.value = true
}

function resetImport() {
  importFile.value = null
  importResult.value = null
  importUploadRef.value?.clearFiles()
}

function onImportFileChange(file) {
  importFile.value = file.raw
  importResult.value = null
}

function onImportFileRemove() {
  importFile.value = null
}

async function doImport() {
  if (!importFile.value) return ElMessage.warning('请选择文件')
  importing.value = true
  try {
    const fd = new FormData()
    fd.append('file', importFile.value)
    const res = await scoreApi.import(fd)
    importResult.value = res
    if (res.success > 0) {
      ElMessage.success(`成功导入 ${res.success} 条数据`)
      load()
    }
  } catch (e) {
  } finally {
    importing.value = false
  }
}
</script>

<style scoped>
.upload-icon {
  font-size: 48px;
  color: var(--brand-light);
}
.upload-text {
  color: var(--text-secondary);
  font-size: 14px;
  margin-top: 8px;
}
.upload-text em {
  color: var(--brand);
  font-style: normal;
}
.upload-tip {
  color: var(--text-tertiary);
  font-size: 12px;
  margin-top: 4px;
}
.import-result {
  margin-top: 16px;
}
.error-list {
  max-height: 200px;
  overflow-y: auto;
  background: #fef2f2;
  border-radius: 8px;
  padding: 12px;
}
.error-item {
  font-size: 13px;
  color: #dc2626;
  line-height: 1.8;
  padding: 2px 0;
}
</style>