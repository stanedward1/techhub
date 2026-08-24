<template>
  <div>
    <h2 class="page-title">我的提交</h2>
    <p class="page-subtitle">查看你提交过的所有作业</p>

    <el-table :data="items" v-loading="loading" style="width: 100%">
      <el-table-column prop="assignment_title" label="作业任务" min-width="200" />
      <el-table-column label="内容预览" min-width="260">
        <template #default="{ row }">{{ (row.content || '').slice(0, 60) || '—' }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="提交时间" width="180" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="row.is_excellent ? 'success' : 'info'" size="small">
            {{ row.is_excellent ? '优秀作品' : '已提交' }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
    <div v-if="!loading && items.length === 0" class="empty">暂无提交记录</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { homeworkApi } from '../../api'

const items = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await homeworkApi.mySubmissions()
    items.value = res.items
  } catch (e) {
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.empty {
  text-align: center;
  color: #9ca3af;
  padding: 40px 0;
}
</style>
