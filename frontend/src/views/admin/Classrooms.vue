<template>
  <div>
    <div class="toolbar">
      <div class="spacer"></div>
      <el-button type="primary" @click="openCreate">新增班级</el-button>
    </div>
    <div class="page-card">
      <el-table :data="items" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="班级名称" min-width="180" />
        <el-table-column prop="code" label="班级代码" width="120" />
        <el-table-column prop="major" label="专业" width="160" />
        <el-table-column prop="grade" label="年级" width="100" />
        <el-table-column prop="student_count" label="学生数" width="90" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialog" :title="editing ? '编辑班级' : '新增班级'" width="480px">
      <el-form label-width="90px">
        <el-form-item label="班级名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="班级代码" required><el-input v-model="form.code" /></el-form-item>
        <el-form-item label="专业"><el-input v-model="form.major" /></el-form-item>
        <el-form-item label="年级">
          <el-select v-model="form.grade" style="width: 100%">
            <el-option v-for="g in ['一年级', '二年级', '三年级', '四年级', '五年级', '六年级']" :key="g" :label="g" :value="g" />
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
import { studentApi } from '../../api'

const items = ref([])
const loading = ref(false)
const dialog = ref(false)
const editing = ref(null)
const saving = ref(false)
const form = reactive({ name: '', code: '', major: '', grade: '一年级' })

onMounted(load)

async function load() {
  loading.value = true
  try {
    const res = await studentApi.classrooms()
    items.value = res.items
  } catch (e) {
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  Object.assign(form, { name: '', code: '', major: '', grade: '一年级' })
  dialog.value = true
}

function openEdit(row) {
  editing.value = row
  Object.assign(form, row)
  dialog.value = true
}

async function save() {
  if (!form.name || !form.code) return ElMessage.warning('请填写名称和代码')
  saving.value = true
  try {
    if (editing.value) await studentApi.updateClassroom(editing.value.id, form)
    else await studentApi.createClassroom(form)
    ElMessage.success('保存成功')
    dialog.value = false
    load()
  } catch (e) {
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  await ElMessageBox.confirm(`确定删除班级「${row.name}」吗？`, '提示', { type: 'warning' })
  await studentApi.deleteClassroom(row.id)
  ElMessage.success('删除成功')
  load()
}
</script>
