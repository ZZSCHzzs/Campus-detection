<script setup lang="ts">
import { Link } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { defineProps } from 'vue'
import { ElMessage } from 'element-plus'


const props = defineProps<{
  module: string
  name: string
  no_padding?: boolean
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

const isNoPadding = props.no_padding || false

const className = isNoPadding ? 'no-padding' : ''

</script>

<template>
  <el-button :class="className" type="primary" size="small" @click="handleJump()" text>
    <el-icon><Link /></el-icon>
  </el-button>
</template>

<style scoped>
.no-padding {
  padding: 0;
}

</style>