<script setup lang="ts">

import Navbar from "./components/Navbar.vue";
</script>

<template>
  <el-scrollbar style="height: 100vh">
  <Navbar />
  <router-view />
  <div class="el-message-container"></div>
  </el-scrollbar>
</template>

<style scoped>
.el-message-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 0;
  z-index: 9000;
  pointer-events: none;
}
</style>
