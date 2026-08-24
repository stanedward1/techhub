import { createRouter, createWebHistory } from 'vue-router'
import { isStudent, isTeacher, getToken } from '../utils/auth'

const routes = [
  // ============ 学生端 ============
  {
    path: '/login',
    name: 'student-login',
    component: () => import('../views/student/Login.vue')
  },
  {
    path: '/',
    component: () => import('../layout/StudentLayout.vue'),
    meta: { requiresStudent: true },
    children: [
      { path: '', redirect: '/homework' },
      { path: 'homework', name: 'homework', component: () => import('../views/student/HomeworkList.vue') },
      { path: 'homework/:id', name: 'homework-detail', component: () => import('../views/student/HomeworkDetail.vue') },
      { path: 'excellent', name: 'excellent', component: () => import('../views/student/ExcellentList.vue') },
      { path: 'excellent/:id', name: 'excellent-detail', component: () => import('../views/student/ExcellentDetail.vue') },
      { path: 'my-submissions', name: 'my-submissions', component: () => import('../views/student/MySubmissions.vue') },
      { path: 'practice', name: 'practice', component: () => import('../views/student/Practice.vue') },
      { path: 'profile', name: 'profile', component: () => import('../views/student/Profile.vue') }
    ]
  },

  // ============ 管理端 ============
  {
    path: '/admin/login',
    name: 'admin-login',
    component: () => import('../views/admin/Login.vue')
  },
  {
    path: '/admin',
    component: () => import('../layout/AdminLayout.vue'),
    meta: { requiresTeacher: true },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard', name: 'dashboard', component: () => import('../views/admin/Dashboard.vue') },
      { path: 'homework', name: 'admin-homework', component: () => import('../views/admin/Assignments.vue') },
      { path: 'homework/:id/submissions', name: 'admin-submissions', component: () => import('../views/admin/AssignmentSubmissions.vue') },
      { path: 'students', name: 'admin-students', component: () => import('../views/admin/Students.vue') },
      { path: 'students/:id/profile', name: 'admin-student-profile', component: () => import('../views/admin/StudentProfile.vue') },
      { path: 'classrooms', name: 'admin-classrooms', component: () => import('../views/admin/Classrooms.vue') },
      { path: 'scores', name: 'admin-scores', component: () => import('../views/admin/Scores.vue') },
      { path: 'leaves', name: 'admin-leaves', component: () => import('../views/admin/Leaves.vue') },
      { path: 'points', name: 'admin-points', component: () => import('../views/admin/Points.vue') },
      { path: 'communications', name: 'admin-communications', component: () => import('../views/admin/Communications.vue') },
      { path: 'resources', name: 'admin-resources', component: () => import('../views/admin/Resources.vue') },
      { path: 'exams', name: 'admin-exams', component: () => import('../views/admin/Exams.vue') },
      { path: 'seats', name: 'admin-seats', component: () => import('../views/admin/Seats.vue') },
      { path: 'worklogs', name: 'admin-worklogs', component: () => import('../views/admin/WorkLogs.vue') },
      { path: 'plans', name: 'admin-plans', component: () => import('../views/admin/Plans.vue') },
      { path: 'schedules', name: 'admin-schedules', component: () => import('../views/admin/Schedules.vue') },
      { path: 'activities', name: 'admin-activities', component: () => import('../views/admin/Activities.vue') },
      { path: 'talks', name: 'admin-talks', component: () => import('../views/admin/Talks.vue') },
      { path: 'return-records', name: 'admin-return-records', component: () => import('../views/admin/ReturnRecords.vue') },
      { path: 'performances', name: 'admin-performances', component: () => import('../views/admin/Performances.vue') },
      { path: 'student-comments', name: 'admin-student-comments', component: () => import('../views/admin/StudentComments.vue') },
      { path: 'reports', name: 'admin-reports', component: () => import('../views/admin/WeeklyReport.vue') },
      { path: 'users', name: 'admin-users', component: () => import('../views/admin/Users.vue') },
      { path: 'settings', name: 'admin-settings', component: () => import('../views/admin/Settings.vue') }
    ]
  },

  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  const hasToken = !!getToken()

  // 管理端访问控制
  if (to.path.startsWith('/admin') && to.path !== '/admin/login') {
    if (!hasToken || !isTeacher()) {
      return { path: '/admin/login', query: { redirect: to.fullPath } }
    }
  }
  if (to.path === '/admin/login' && hasToken && isTeacher()) {
    return { path: '/admin' }
  }

  // 学生端访问控制
  if (to.meta.requiresStudent && (!hasToken || !isStudent())) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/login' && hasToken && isStudent()) {
    return { path: '/' }
  }

  // 已登录教师访问学生端时，跳转到后台
  if (hasToken && isTeacher() && !to.path.startsWith('/admin')) {
    return { path: '/admin' }
  }
  // 已登录学生访问后台时，跳转到学生端
  if (hasToken && isStudent() && to.path.startsWith('/admin')) {
    return { path: '/' }
  }

  return true
})

export default router
