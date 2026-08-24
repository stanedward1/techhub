<template>
  <div>
    <!-- 统计卡片（可点击跳转） -->
    <el-row :gutter="16" class="stat-row">
      <el-col v-for="s in stats" :key="s.label" :xs="12" :sm="6" :lg="3">
        <div class="stat-card" @click="navigateTo(s.route)">
          <div class="stat-icon-box" :style="{ background: s.bg }">
            <el-icon class="stat-icon"><component :is="s.icon" /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ s.value }}</div>
            <div class="stat-label">{{ s.label }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 请假趋势图表 + 详情 -->
    <div class="page-card chart-card">
      <h3 class="card-title">近 7 天请假趋势</h3>
      <div ref="trendRef" style="width: 100%; height: 280px;"></div>
      <!-- 请假人员详情 -->
      <div v-if="leaveDetailDays.length" style="margin-top: 16px;">
        <el-collapse>
          <el-collapse-item v-for="day in leaveDetailDays" :key="day.date" :title="`${day.date} 日 — ${day.count} 人请假`">
            <el-table :data="day.items" size="small" v-if="day.items.length">
              <el-table-column prop="name" label="姓名" width="100" />
              <el-table-column prop="reason" label="请假原因" min-width="160" />
              <el-table-column label="时长" width="80">
                <template #default="{ row }">{{ row.duration }} 天</template>
              </el-table-column>
              <el-table-column label="时间段" width="220">
                <template #default="{ row }">{{ row.start }} ~ {{ row.end }}</template>
              </el-table-column>
            </el-table>
            <div v-else style="color: #9ca3af; padding: 8px;">暂无记录</div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>

    <!-- 成绩分布 -->
    <div class="page-card chart-card">
      <h3 class="card-title">成绩分布</h3>
      <div ref="distRef" style="width: 100%; height: 300px;"></div>
    </div>

    <!-- 最近动态 -->
    <div class="page-card">
      <h3 class="card-title">最近班级动态</h3>
      <el-timeline v-if="data.recent?.length" style="margin-top: 8px">
        <el-timeline-item v-for="(r, i) in data.recent" :key="i" :timestamp="r.time" placement="top">
          <el-tag size="small" :type="r.type === '请假' ? 'warning' : 'info'" effect="plain" style="margin-right: 8px">{{ r.type }}</el-tag>
          {{ r.text }}
        </el-timeline-item>
      </el-timeline>
      <div v-else class="empty-state">暂无动态</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { adminApi } from '../../api'

const router = useRouter()
const data = ref({ counts: {}, leave_trend: [], leave_details: [], score_dist: {}, recent: [] })
const trendRef = ref(null)
const distRef = ref(null)
let trendChart = null
let distChart = null

const statCards = [
  { icon: 'User', bg: 'linear-gradient(135deg, #2563eb, #4f46e5)', key: 'student', route: '/admin/students' },
  { icon: 'School', bg: 'linear-gradient(135deg, #0ea5e9, #0284c7)', key: 'class', route: '/admin/classrooms' },
  { icon: 'Document', bg: 'linear-gradient(135deg, #8b5cf6, #7c3aed)', key: 'assignment', route: '/admin/homework' },
  { icon: 'Upload', bg: 'linear-gradient(135deg, #f59e0b, #d97706)', key: 'submission', route: '/admin/homework' },
  { icon: 'Calendar', bg: 'linear-gradient(135deg, #ef4444, #dc2626)', key: 'leave', route: '/admin/leaves' },
  { icon: 'Folder', bg: 'linear-gradient(135deg, #10b981, #059669)', key: 'resource', route: '/admin/resources' },
  { icon: 'Tickets', bg: 'linear-gradient(135deg, #f43f5e, #e11d48)', key: 'exam', route: '/admin/exams' },
  { icon: 'Bell', bg: 'linear-gradient(135deg, #64748b, #475569)', key: 'today_leave', route: '/admin/leaves' },
]

const stats = computed(() => {
  const c = data.value.counts || {}
  return statCards.map(s => ({
    label: { student: '学生总数', class: '班级数', assignment: '作业任务', submission: '提交总数', leave: '请假记录', resource: '教学资源', exam: '试卷数', today_leave: '今日请假' }[s.key],
    value: c[s.key] || 0,
    icon: s.icon,
    bg: s.bg,
    route: s.route,
  }))
})

const leaveDetailDays = computed(() => data.value.leave_details || [])

function navigateTo(route) {
  if (route) router.push(route)
}

onMounted(async () => {
  try {
    data.value = await adminApi.dashboard()
  } catch (e) {}
  await nextTick()
  setTimeout(() => renderCharts(), 0)
  window.addEventListener('resize', resize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  if (trendChart) { trendChart.dispose(); trendChart = null }
  if (distChart) { distChart.dispose(); distChart = null }
})

function resize() {
  trendChart?.resize()
  distChart?.resize()
}

function renderCharts() {
  if (trendRef.value) {
    if (trendChart) trendChart.dispose()
    trendChart = echarts.init(trendRef.value)
    trendChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 40, right: 20, top: 20, bottom: 30 },
      xAxis: {
        type: 'category',
        data: (data.value.leave_trend || []).map(t => t.date),
        axisLine: { lineStyle: { color: '#e5e7eb' } },
        axisTick: { show: false },
        axisLabel: { color: '#9ca3af', fontSize: 11 }
      },
      yAxis: {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: '#f3f4f6' } },
        axisLabel: { color: '#9ca3af', fontSize: 11 }
      },
      series: [{
        type: 'line',
        smooth: true,
        data: (data.value.leave_trend || []).map(t => t.count),
        areaStyle: { color: 'rgba(37,99,235,0.15)' },
        lineStyle: { color: '#2563eb', width: 2 },
        itemStyle: { color: '#2563eb' },
        symbol: 'circle',
        symbolSize: 6
      }]
    })
  }

  if (distRef.value) {
    if (distChart) distChart.dispose()
    distChart = echarts.init(distRef.value)
    const dist = data.value.score_dist || {}
    const distData = Object.entries(dist).map(([name, val]) => ({
      name,
      value: val.count || 0,
      percent: val.percent || 0,
    }))
    const total = distData.reduce((s, d) => s + d.value, 0) || 1
    distChart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: (p) => `${p.name}<br/>人数：${p.value} 人<br/>占比：${p.percent}%`
      },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '50%'],
        data: distData,
        color: ['#10b981', '#2563eb', '#f59e0b', '#ef4444'],
        label: {
          color: '#4b5563',
          fontSize: 12,
          formatter: '{b}\n{d}%（{c}人）'
        },
        itemStyle: { borderColor: '#fff', borderWidth: 2 }
      }]
    })
  }
}
</script>

<style scoped>
.stat-row { margin-bottom: 16px; }
.stat-card {
  background: #fff; border-radius: var(--radius-lg); padding: 18px 16px;
  display: flex; align-items: center; gap: 14px;
  box-shadow: var(--shadow-card); transition: all var(--transition-fast);
  cursor: pointer; margin-bottom: 16px;
}
.stat-card:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); }
.stat-icon-box { width: 44px; height: 44px; border-radius: var(--radius-md); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.stat-icon { font-size: 22px; color: #fff; }
.stat-info { min-width: 0; }
.stat-value { font-size: 24px; font-weight: 700; color: var(--text-primary); line-height: 1.2; }
.stat-label { font-size: 12px; color: var(--text-tertiary); margin-top: 2px; }
.chart-card { margin-bottom: 16px; }
</style>