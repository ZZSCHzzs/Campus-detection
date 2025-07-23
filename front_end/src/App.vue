<script setup lang="ts">
import Navbar from "./components/Navbar.vue";
import Footer from "./components/Footer.vue";
import { useRoute } from 'vue-router';
import { computed } from 'vue';

const route = useRoute();

// 检查当前是否是认证页面
const isAuthPage = computed(() => {
  return route.path === '/login' || route.path === '/register';
});

// 检查当前是否是数据大屏页面
const isScreenPage = computed(() => {
  return route.path === '/screen';
});

const isAdminPage = computed(() => {
  return route.path.startsWith('/admin');
});
</script>

<template>
  <div class="app-wrapper">
    <div class="background-decoration left"></div>
    <div class="background-decoration right"></div>
    
    <!-- 边缘装饰元素 -->
    <div class="side-decorations">
      <div class="side-element left-top"></div>
      <div class="side-element left-middle"></div>
      <div class="side-element left-bottom"></div>
      <div class="side-element right-top"></div>
      <div class="side-element right-middle"></div>
      <div class="side-element right-bottom"></div>
    </div>
    
    <!-- 重新调整位置的浮动形状 -->
    <div class="floating-shapes">
      <div class="shape circle left-side"></div>
      <div class="shape triangle left-side"></div>
      <div class="shape square right-side"></div>
      <div class="shape rectangle right-side"></div>
    </div>
    <div class="geometric-lines">
      <div class="line line-1"></div>
      <div class="line line-2"></div>
      <div class="line line-3"></div>
    </div>
    
    <el-scrollbar style="height: 100vh">
      <div class="page-container" :class="{ 'auth-page': isAuthPage, 'screen-page': isScreenPage }">
        
        <div class="main-content">
          <Navbar />
          <router-view />
        </div>
        <Footer v-if="!isScreenPage && !isAdminPage" />
      </div>
      <div class="el-message-container"></div>
    </el-scrollbar>
  </div>
</template>

<style scoped>
.app-wrapper {
  position: relative;
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #f8fafc 100%);
  overflow-x: hidden;
}

.page-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.main-content {
  flex: 1;
  position: relative;
  z-index: 1;
}

/* 登录/注册页面特殊处理 */
.auth-page {
  position: relative;
}

/* 数据大屏页面特殊处理 */
.screen-page {
  padding: 0;
  margin: 0;
  max-width: 100%;
  width: 100%;
  overflow: hidden;
}

.screen-page .main-content {
  padding: 0;
  margin: 0;
  width: 100%;
}


.background-decoration {
  position: fixed;
  top: 0;
  width: 35%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
  opacity: 0.4;
}

.background-decoration.left {
  left: 0;
  background: radial-gradient(circle at 10% 30%, rgba(64, 158, 255, 0.05) 0%, rgba(64, 158, 255, 0) 70%),
              radial-gradient(circle at 0% 50%, rgba(26, 188, 156, 0.03) 0%, rgba(26, 188, 156, 0) 60%),
              radial-gradient(circle at 5% 80%, rgba(155, 89, 182, 0.04) 0%, rgba(155, 89, 182, 0) 65%);
}

.background-decoration.right {
  right: 0;
  background: radial-gradient(circle at 90% 20%, rgba(64, 158, 255, 0.05) 0%, rgba(64, 158, 255, 0) 70%),
              radial-gradient(circle at 100% 60%, rgba(26, 188, 156, 0.03) 0%, rgba(26, 188, 156, 0) 60%),
              radial-gradient(circle at 95% 90%, rgba(155, 89, 182, 0.04) 0%, rgba(155, 89, 182, 0) 65%);
}

/* 边缘装饰元素 */
.side-decorations {
  position: fixed;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}

.side-element {
  position: absolute;
  opacity: 0.3;
  background: linear-gradient(135deg, #409eff30, #1ab2b230);
  border-radius: 50%;
  filter: blur(2px);
}

.side-element.left-top {
  width: 150px;
  height: 150px;
  top: 5%;
  left: 0;
  transform: translateX(-50%);
  animation: pulse 10s infinite alternate;
}

.side-element.left-middle {
  width: 200px;
  height: 200px;
  top: 40%;
  left: 0;
  transform: translateX(-60%);
  animation: pulse 15s infinite alternate-reverse;
  background: linear-gradient(135deg, #9b59b630, #8e44ad30);
}

.side-element.left-bottom {
  width: 180px;
  height: 180px;
  bottom: 8%;
  left: 0;
  transform: translateX(-40%);
  animation: pulse 12s infinite alternate;
  background: linear-gradient(135deg, #27ae6030, #2ecc7130);
}

.side-element.right-top {
  width: 180px;
  height: 180px;
  top: 8%;
  right: 0;
  transform: translateX(50%);
  animation: pulse 14s infinite alternate-reverse;
  background: linear-gradient(135deg, #e74c3c30, #c0392b30);
}

.side-element.right-middle {
  width: 220px;
  height: 220px;
  top: 45%;
  right: 0;
  transform: translateX(65%);
  animation: pulse 16s infinite alternate;
  background: linear-gradient(135deg, #f39c1230, #e67e2230);
}

.side-element.right-bottom {
  width: 160px;
  height: 160px;
  bottom: 5%;
  right: 0;
  transform: translateX(40%);
  animation: pulse 11s infinite alternate-reverse;
  background: linear-gradient(135deg, #3498db30, #2980b930);
}

/* 增强可见性的浮动形状 */
.floating-shapes {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.shape {
  position: absolute;
  opacity: 0.25; /* 提高不透明度 */
  pointer-events: none;
  z-index: 0;
}

/* 左侧形状 */
.shape.left-side {
  left: 5%;
}

/* 右侧形状 */
.shape.right-side {
  right: 5%;
}

.shape.circle {
  width: 100px; /* 增大尺寸 */
  height: 100px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409eff, #1ab2b2);
  top: 15%;
  left: 5%;
  animation: float-shape 20s infinite ease-in-out;
  box-shadow: 0 0 30px rgba(64, 158, 255, 0.2); /* 添加发光效果 */
}

.shape.triangle {
  width: 0;
  height: 0;
  border-left: 50px solid transparent; /* 增大尺寸 */
  border-right: 50px solid transparent;
  border-bottom: 85px solid rgba(155, 89, 182, 0.3); /* 提高颜色强度 */
  bottom: 20%;
  left: 8%;
  animation: float-shape 25s infinite ease-in-out reverse;
  animation-delay: 3s;
  filter: drop-shadow(0 0 10px rgba(155, 89, 182, 0.3)); /* 添加发光效果 */
}

.shape.square {
  width: 80px; /* 增大尺寸 */
  height: 80px;
  background: rgba(26, 188, 156, 0.3); /* 提高颜色强度 */
  top: 25%;
  right: 8%;
  transform: rotate(45deg);
  animation: float-shape 18s infinite ease-in-out;
  animation-delay: 7s;
  box-shadow: 0 0 20px rgba(26, 188, 156, 0.2); /* 添加发光效果 */
}

.shape.rectangle {
  width: 120px; /* 增大尺寸 */
  height: 50px;
  background: rgba(64, 158, 255, 0.25);
  bottom: 15%;
  right: 7%;
  transform: rotate(-15deg);
  animation: float-shape 22s infinite ease-in-out;
  animation-delay: 10s;
  box-shadow: 0 0 15px rgba(64, 158, 255, 0.2); /* 添加发光效果 */
}

/* 几何线条装饰 */
.geometric-lines {
  position: fixed;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}

.line {
  position: absolute;
  background: linear-gradient(90deg, transparent, rgba(64, 158, 255, 0.1), transparent);
  height: 1px;
  width: 100%;
  transform-origin: left center;
}

.line-1 {
  top: 20%;
  transform: rotate(-5deg);
  animation: line-fade 15s infinite ease-in-out;
}

.line-2 {
  top: 50%;
  transform: rotate(3deg);
  animation: line-fade 18s infinite ease-in-out;
  animation-delay: 5s;
}

.line-3 {
  bottom: 25%;
  transform: rotate(-7deg);
  animation: line-fade 20s infinite ease-in-out;
  animation-delay: 10s;
}

/* 边缘装饰元素动画 */
@keyframes pulse {
  0% {
    transform: translateX(-50%) scale(1);
    opacity: 0.2;
  }
  100% {
    transform: translateX(-50%) scale(1.1);
    opacity: 0.4;
  }
}

/* 形状浮动动画增强 */
@keyframes float-shape {
  0% { transform: translateY(0) rotate(0deg); opacity: 0.2; }
  25% { transform: translateY(-20px) rotate(5deg); opacity: 0.3; }
  50% { transform: translateY(0) rotate(10deg); opacity: 0.25; }
  75% { transform: translateY(20px) rotate(5deg); opacity: 0.3; }
  100% { transform: translateY(0) rotate(0deg); opacity: 0.2; }
}

/* 线条淡入淡出动画 */
@keyframes line-fade {
  0%, 100% { opacity: 0.1; }
  50% { opacity: 0.3; }
}

/* 适配移动设备 */
@media (max-width: 768px) {
  .shape {
    opacity: 0.15;
    transform: scale(0.6);
  }
  
  .side-element {
    opacity: 0.2;
    transform: scale(0.7);
  }
}
</style>
