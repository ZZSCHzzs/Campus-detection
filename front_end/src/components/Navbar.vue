<template>
  <div class="header">
    <el-menu :default-active="activeIndex" class="el-menu-demo nav-container" mode="horizontal" :ellipsis="false"
      @select="handleSelect">
      <img
        class="logo"
        src="/favicon256.ico"
        alt="Logo"></img>
      <el-menu-item v-for="item in content" :key="item.index" :index="item.index">
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
}

.el-menu-demo {
  border-bottom: 0px !important;
}

.header {
  border-bottom: 2px solid #eef1ff;
  width: 100%;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

el-menu-item {
  text-decoration: none !important;
}
</style>
