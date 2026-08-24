<template>
  <div>
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索姓名/学号" clearable style="width: 220px" @keyup.enter="load" @clear="load" />
      <el-select v-model="classId" placeholder="全部班级" clearable style="width: 180px" @change="load">
        <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
      </el-select>
      <el-button @click="load">查询</el-button>
      <SortBar v-model="order" />
      <div class="spacer"></div>
      <el-button @click="downloadTemplate">下载模板</el-button>
      <el-button type="success" @click="openImport">批量导入</el-button>
      <el-button @click="exportExcel">导出花名册</el-button>
      <el-button type="primary" @click="openCreate">添加学生</el-button>
    </div>

    <!-- 通学生/寄宿生人数对比图表 -->
    <div class="page-card" v-if="classId">
      <div style="font-weight: 500; margin-bottom: 12px;">通学生与寄宿生人数对比</div>
      <div ref="chartRef" style="width: 100%; height: 320px;"></div>
    </div>

    <div class="page-card">
      <el-table :data="items" v-loading="loading" style="width: 100%">
        <el-table-column prop="student_no" label="学号" width="120" />
        <el-table-column label="头像" width="70">
          <template #default="{ row }">
            <el-upload
              :show-file-list="false"
              :before-upload="(f) => beforeAvatarUpload(f, row)"
              :http-request="(opt) => handleStudentAvatar(opt, row)"
              accept=".jpg,.jpeg,.png,.gif,.webp"
            >
              <el-avatar :size="32" :src="row.avatar" style="cursor: pointer; background: linear-gradient(135deg, #2563eb, #4f46e5); color: #fff; font-weight: 600; font-size: 13px;">
                {{ row.name?.[0] }}
              </el-avatar>
            </el-upload>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="gender" label="性别" width="70" />
        <el-table-column prop="class_name" label="班级" width="160" />
        <el-table-column prop="major" label="专业" width="140" />
        <el-table-column prop="parent_name" label="家长姓名" width="100" />
        <el-table-column prop="parent_phone" label="家长电话" width="130" />
        <el-table-column label="类型" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.student_type === 'day' ? 'info' : 'warning'">
              {{ row.student_type === 'day' ? '通学生' : '寄宿生' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="success" @click="$router.push(`/admin/students/${row.id}/profile`)">画像</el-button>
            <el-button link type="warning" @click="openPassword(row)">密码</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        style="margin-top: 16px; justify-content: flex-end"
        layout="total, prev, pager, next"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        @current-change="onPage"
      />
    </div>

    <el-dialog v-model="dialog" :title="editing ? '编辑学生' : '添加学生'" width="560px">
      <el-form label-width="90px">
        <el-form-item label="学号" required><el-input v-model="form.student_no" /></el-form-item>
        <el-form-item label="姓名" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="form.gender"><el-radio value="男">男</el-radio><el-radio value="女">女</el-radio></el-radio-group>
        </el-form-item>
        <el-form-item label="班级">
          <el-select v-model="form.class_id" clearable style="width: 100%">
            <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="专业"><el-input v-model="form.major" /></el-form-item>
        <el-form-item label="出生日期"><el-input v-model="form.birth_date" placeholder="如 2008-05-12" /></el-form-item>
        <el-form-item label="家长姓名"><el-input v-model="form.parent_name" /></el-form-item>
        <el-form-item label="家长电话"><el-input v-model="form.parent_phone" /></el-form-item>
        <el-form-item label="学生类型">
          <el-radio-group v-model="form.student_type">
            <el-radio value="day">通学生</el-radio><el-radio value="boarding">寄宿生</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 通学生/寄宿生明细弹窗 -->
    <el-dialog v-model="detailDialog" :title="detailTitle" width="560px">
      <el-table :data="detailList" max-height="400" style="width: 100%">
        <el-table-column prop="student_no" label="学号" width="120" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="gender" label="性别" width="70" />
        <el-table-column prop="class_name" label="班级" width="160" />
        <el-table-column prop="major" label="专业" min-width="140" />
      </el-table>
    </el-dialog>

    <!-- 学生密码管理弹窗 -->
    <el-dialog v-model="pwdDialog" title="学生密码管理" width="440px">
      <el-form label-width="80px">
        <el-form-item label="学生">
          <span style="font-weight: 500;">{{ pwdTarget?.name }}（{{ pwdTarget?.student_no }}）</span>
        </el-form-item>
        <el-form-item label="重置密码">
          <el-button type="warning" @click="resetPassword">重置为默认密码（123456）</el-button>
        </el-form-item>
        <el-divider />
        <el-form-item label="修改密码">
          <el-input
            v-model="pwdForm.password"
            placeholder="请输入新密码"
            show-password
            style="width: 220px"
          />
          <el-button type="primary" style="margin-left: 8px;" :loading="pwdSaving" @click="modifyPassword">确定修改</el-button>
        </el-form-item>
      </el-form>
    </el-dialog>

    <!-- 批量导入学生弹窗 -->
    <el-dialog v-model="importDialog" title="批量导入学生" width="560px" @close="resetImport">
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
      <!-- 导入结果 -->
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
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import SortBar from '../../components/SortBar.vue'
import { useSort } from '../../composables/useSort'
import { studentApi, metaApi } from '../../api'

const rawItems = ref([])
const classes = ref([])
const keyword = ref('')
const classId = ref(null)
const page = ref(1)
const pageSize = 20
const total = ref(0)
const loading = ref(false)
const dialog = ref(false)
const editing = ref(null)
const saving = ref(false)

// 通学生/寄宿生图表
const chartRef = ref(null)
let chartInstance = null
const detailDialog = ref(false)
const detailTitle = ref('')
const detailList = ref([])

// 密码管理
const pwdDialog = ref(false)
const pwdTarget = ref(null)
const pwdSaving = ref(false)
const pwdForm = reactive({ password: '' })

// 批量导入
const importDialog = ref(false)
const importUploadRef = ref(null)
const importing = ref(false)
const importFile = ref(null)
const importResult = ref(null)
const { order, useSorted } = useSort('students')
const items = useSorted(rawItems)

const form = reactive({
  student_no: '', name: '', gender: '男', class_id: null, major: '', birth_date: '',
  parent_name: '', parent_phone: '', student_type: 'day'
})

onMounted(async () => {
  const res = await metaApi.classes()
  classes.value = res.items
  load()
})

async function load() {
  loading.value = true
  try {
    const res = await studentApi.list({ page: page.value, page_size: pageSize, keyword: keyword.value, class_id: classId.value })
    rawItems.value = res.items
    total.value = res.total
  } catch (e) {
  } finally {
    loading.value = false
  }
  // 加载通学生/寄宿生统计
  if (classId.value) {
    loadBoardTypeStats()
  }
}

function onPage(p) {
  page.value = p
  load()
}

function openCreate() {
  editing.value = null
  Object.assign(form, { student_no: '', name: '', gender: '男', class_id: classId.value, major: '', birth_date: '', parent_name: '', parent_phone: '', student_type: 'day' })
  dialog.value = true
}

function openEdit(row) {
  editing.value = row
  Object.assign(form, row)
  dialog.value = true
}

async function save() {
  if (!form.name || !form.student_no) return ElMessage.warning('请填写姓名和学号')
  saving.value = true
  try {
    if (editing.value) await studentApi.update(editing.value.id, form)
    else await studentApi.create(form)
    ElMessage.success('保存成功')
    dialog.value = false
    load()
  } catch (e) {
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  await ElMessageBox.confirm(`确定删除学生「${row.name}」吗？`, '提示', { type: 'warning' })
  await studentApi.remove(row.id)
  ElMessage.success('删除成功')
  load()
}

async function exportExcel() {
  const res = await studentApi.export({ class_id: classId.value })
  const blob = new Blob([res], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = '学生花名册.xlsx'
  a.click()
  URL.revokeObjectURL(url)
}

// 加载通学生/寄宿生统计数据并渲染图表
async function loadBoardTypeStats() {
  try {
    const stats = await studentApi.boardTypeStats({ class_id: classId.value })
    await nextTick()
    setTimeout(() => renderChart(stats), 0)
  } catch (e) {
    // ignore
  }
}

function renderChart(stats) {
  if (!chartRef.value) return
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(chartRef.value)

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} 人 ({d}%)'
    },
    legend: {
      bottom: 0
    },
    series: [
      {
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          formatter: '{b}\n{c} 人 ({d}%)'
        },
        emphasis: {
          label: { fontSize: 18, fontWeight: 'bold' }
        },
        data: [
          { value: stats.day_count, name: '通学生', itemStyle: { color: '#409EFF' } },
          { value: stats.boarding_count, name: '寄宿生', itemStyle: { color: '#E6A23C' } }
        ]
      }
    ]
  }

  chartInstance.setOption(option)

  // 点击图表跳转明细
  chartInstance.on('click', (params) => {
    if (params.name === '通学生') {
      detailTitle.value = '通学生名单'
      detailList.value = stats.day || []
    } else if (params.name === '寄宿生') {
      detailTitle.value = '寄宿生名单'
      detailList.value = stats.boarding || []
    }
    detailDialog.value = true
  })
}

// 密码管理
function openPassword(row) {
  pwdTarget.value = row
  pwdForm.password = ''
  pwdDialog.value = true
}

async function resetPassword() {
  try {
    await ElMessageBox.confirm(
      `确定将「${pwdTarget.value.name}」的密码重置为默认密码（123456）吗？`,
      '确认重置',
      { type: 'warning' }
    )
  } catch {
    return
  }
  pwdSaving.value = true
  try {
    await studentApi.resetPassword(pwdTarget.value.id, { password: '123456' })
    ElMessage.success('密码已重置为 123456')
    pwdDialog.value = false
  } catch (e) {
  } finally {
    pwdSaving.value = false
  }
}

async function modifyPassword() {
  if (!pwdForm.password) return ElMessage.warning('请输入新密码')
  if (pwdForm.password.length < 6) return ElMessage.warning('密码长度至少6位')
  pwdSaving.value = true
  try {
    await studentApi.resetPassword(pwdTarget.value.id, { password: pwdForm.password })
    ElMessage.success('密码修改成功')
    pwdDialog.value = false
  } catch (e) {
  } finally {
    pwdSaving.value = false
  }
}

// 批量导入
function downloadTemplate() {
  studentApi.template().then(res => {
    const blob = new Blob([res], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '学生导入模板.xlsx'
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
    const res = await studentApi.import(fd)
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

// 头像上传
function beforeAvatarUpload(file, row) {
  const allowed = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
  if (!allowed.includes(file.type)) {
    ElMessage.error('仅支持 JPG/PNG/GIF/WebP 格式')
    return false
  }
  if (file.size > 2 * 1024 * 1024) {
    ElMessage.error('头像不能超过 2MB')
    return false
  }
  return true
}

async function handleStudentAvatar(options, row) {
  try {
    const fd = new FormData()
    fd.append('file', options.file)
    const res = await studentApi.uploadAvatar(row.id, fd)
    row.avatar = res.avatar
    ElMessage.success('头像更新成功')
  } catch (e) {
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
