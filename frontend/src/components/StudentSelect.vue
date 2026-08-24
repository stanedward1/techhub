<template>
  <el-select
    :model-value="modelValue"
    filterable
    clearable
    :placeholder="placeholder"
    style="width: 100%"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <el-option v-for="s in students" :key="s.id" :label="`${s.name}（${s.student_no}）`" :value="s.id" />
  </el-select>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { studentApi } from '../api'

defineProps({
  modelValue: { type: [Number, String], default: null },
  placeholder: { type: String, default: '选择学生' }
})
defineEmits(['update:modelValue'])

const students = ref([])

onMounted(async () => {
  try {
    const res = await studentApi.list({ page: 1, page_size: 9999 })
    students.value = res.items
  } catch (e) {}
})
</script>
