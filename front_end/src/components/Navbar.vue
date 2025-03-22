<template>
  <div class="header">
    <el-menu
        :default-active="activeIndex"
        class="el-menu-demo nav-container"
        mode="horizontal"
        :ellipsis="false"
        @select="handleSelect"
    >
      <el-menu-item index="0">
        <router-link to="/index">首页</router-link>
      </el-menu-item>
      <el-menu-item index="1">
        <router-link to="/areas">区域</router-link>
      </el-menu-item>
      <el-menu-item index="2">
        <router-link to="/data-screen">数据大屏</router-link>
      </el-menu-item>
    </el-menu>
  </div>


</template>

<script lang="ts" setup>
import { ref } from 'vue'

const activeIndex = ref('0')
const handleSelect = (key: string, keyPath: string[]) => {
  console.log(key, keyPath)
}
</script>

<style>

.nav-container {
  display: flex;
  width: 1200px;
  margin: 0 auto;
}
.el-menu-demo{
  border-bottom: 0px!important;
}
.header{
  border-bottom: 2px solid #eef1ff;
  width: 100%;
}
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
el-menu-item{
  text-decoration: none!important;
}
</style>
