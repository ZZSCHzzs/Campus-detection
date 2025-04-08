<script setup lang="ts">
import { Link } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { defineProps } from 'vue'
import { ElMessage } from 'element-plus'
import {View} from "@element-plus/icons-vue";

const props = defineProps<{
  resource: string
  data: string
  id: number
}>()
const router = useRouter()
const handleJump = () => {
  try {
    router.replace(`/admin?module=${props.resource}&data=${props.data}&id=${props.id}`)
  } catch (error) {
    ElMessage.error('Navigation failed')
    console.error(error)
  }
}

</script>

<template>
  <el-button type="primary" size="small" @click="handleJump()" text>
    <el-icon><View /></el-icon>
  </el-button>
</template>

<style scoped>

</style>