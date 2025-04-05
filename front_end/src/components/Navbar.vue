<template>
  <div class="header">
    <el-menu :default-active="activeIndex" class="el-menu-demo nav-container" mode="horizontal" :ellipsis="false"
      @select="handleSelect">
      <div class="logo-container">
        <img
          class="logo"
          src="/favicon256.ico"
          alt="Logo" />
      </div>
      <el-menu-item v-for="item in content" :key="item.index" :index="item.index" class="nav-item">
        {{ item.title }}
      </el-menu-item>
    </el-menu>
  </div>
</template>

<script lang="ts" setup>
import { ref } from 'vue'
import router from '../router'

const content = ref([
  {
    index: '0',
    title: '首页',
    path: '/index',
  },
  {
    index: '1',
    title: '区域',
    path: '/areas',
  },
  {
    index: '2',
    title: '数据大屏',
    path: '/screen',
  },
])

const activeIndex = ref('0')
const handleSelect = (key: string) => {
  activeIndex.value = key
  router.push(content.value.find(item => item.index === key)?.path || '/')
}
</script>

<style>
.nav-container {
  display: flex;
  width: 1400px;
  margin: 0 auto;
  border-radius: 4px;
  background-color: #ffffff;
}

.el-menu-demo {
  border-bottom: 0px !important;
}

.header {
  border-bottom: 2px solid #eef1ff;
  width: 100%;
  padding: 4px 0;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.nav-item {
  position: relative;
  transition: all 0.3s ease;
  font-weight: 500;
}

.nav-item:hover {
  background-color: #f0f2ff !important;
  color: #409EFF;
}

.nav-item:hover::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 30px;
  height: 3px;
  background-color: #409EFF;
  transition: width 0.3s ease;
}

.el-menu-item.is-active {
  color: #409EFF !important;
  font-weight: 700;
}

.el-menu-item.is-active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 40px;
  height: 3px;
  background-color: #409EFF;
}

.logo-container {
  display: flex;
  align-items: center;
  padding: 0 20px;
}

.logo {
  height: 40px;
  margin-right: 15px;
  transition: transform 0.3s ease;
}

.logo:hover {
  transform: scale(1.1);
}

el-menu-item {
  text-decoration: none !important;
}

/* 覆盖 Element Plus 默认活跃状态样式 */
.el-menu--horizontal > .el-menu-item.is-active {
  border-bottom: none !important;
  background-color: transparent !important;
}

/* 覆盖默认悬停效果 */
.el-menu--horizontal > .el-menu-item:not(.is-disabled):hover {
  background-color: #f0f2ff !important;
  border-bottom: none !important;
}

/* 确保自定义活跃样式优先级更高 */
.nav-container .el-menu-item.is-active {
  color: #409EFF !important;
  font-weight: 700;
  border-bottom: none !important;
}

/* 确保菜单项之间的分隔线不显示 */
.el-menu--horizontal > .el-menu-item {
  border-bottom: none !important;
}
</style>
