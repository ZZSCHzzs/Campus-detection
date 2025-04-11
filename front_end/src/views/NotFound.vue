<template>
  <div class="not-found-container">
    <div class="not-found-content">
      <img src="/favicon256.ico" alt="Logo" class="logo-image" />
      <h1 class="error-code">404</h1>
      <h2 class="error-title">页面未找到</h2>
      <p class="error-description">抱歉，您访问的页面不存在或已被移除</p>
      <div class="actions">
        <el-button type="primary" @click="goToHome" class="home-button">
          <el-icon class="button-icon"><HomeFilled /></el-icon>
          返回首页
        </el-button>
        <el-button @click="goBack" class="back-button">
          <el-icon class="button-icon"><Back /></el-icon>
          返回上一页
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { HomeFilled, Back } from '@element-plus/icons-vue'

const router = useRouter()

const goToHome = () => {
  router.push('/')
}

const goBack = () => {
  router.back()
}
</script>

<style scoped>
.not-found-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 90vh;
  padding: 20px;
  background-color: #f9fafc;
}

.not-found-content {
  text-align: center;
  max-width: 600px;
  padding: 40px;
  background-color: #ffffff;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  animation: fade-in 0.5s ease-out;
}

@keyframes fade-in {
  from { opacity: 0; transform: translateY(-20px); }
  to { opacity: 1; transform: translateY(0); }
}

.logo-image {
  width: 80px;
  height: 80px;
  margin-bottom: 20px;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.05); }
  100% { transform: scale(1); }
}

.error-code {
  font-size: 72px;
  font-weight: 700;
  color: #409EFF;
  margin: 10px 0;
  text-shadow: 2px 2px 4px rgba(64, 158, 255, 0.2);
}

.error-title {
  font-size: 28px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 15px;
}

.error-description {
  font-size: 16px;
  color: #606266;
  margin-bottom: 30px;
  line-height: 1.5;
}

.actions {
  display: flex;
  gap: 16px;
  justify-content: center;
}

.home-button, .back-button {
  padding: 12px 24px;
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s ease;
}

.button-icon {
  font-size: 18px;
}

.home-button:hover, .back-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
}
</style>
