<script setup lang="ts">
import { Link } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { defineProps } from 'vue'
import { ElMessage } from 'element-plus'


const props = defineProps<{
  module: string
  name: string
}>()

const router = useRouter()

const handleJump = () => {
  try {
    router.replace(`/admin?module=${props.module}&search=${props.name}`)
  } catch (error) {
    ElMessage.error('Navigation failed')
    console.error(error)
  }
}

</script>

<template>
            <el-button type="primary" size="small" @click="handleJump()" text>
              <el-icon><Link /></el-icon>
            </el-button>
</template>

<style scoped>


</style>