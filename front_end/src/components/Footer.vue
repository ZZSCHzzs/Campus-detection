<template>
  <footer class="app-footer">
    <div class="footer-content">
      <div class="footer-links">
        <a href="#" class="footer-link">关于我们</a>
        <span class="divider">|</span>
        <a href="#" class="footer-link">使用指南</a>
        <span class="divider">|</span>
        <a href="#" class="footer-link">隐私政策</a>
        <span class="divider">|</span>
        <a href="#" class="footer-link">联系我们</a>
      </div>
      <div class="copyright">
        © {{ currentYear }} 智慧校园人员检测系统 版权所有
      </div>
      <div class="icp-info">
        <a href="https://beian.miit.gov.cn/" target="_blank" class="icp-link">冀ICP备2024063729号</a>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const currentYear = computed(() => new Date().getFullYear());
</script>

<style scoped>
.app-footer {
  padding: 20px 0;
  background: linear-gradient(to right, #f8f9fa, #e9ecef, #f8f9fa);
  margin-top: 40px;
  position: relative;
  overflow: hidden;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}



.footer-content {
  max-width: 1200px;
  margin: 0 auto;
  text-align: center;
  position: relative;
  z-index: 1;
}

.footer-links {
  margin-bottom: 12px;
}

.footer-link {
  color: #606266;
  text-decoration: none;
  transition: color 0.3s;
  font-size: 14px;
}

.footer-link:hover {
  color: #409EFF;
  text-decoration: underline;
}

.divider {
  margin: 0 10px;
  color: #dcdfe6;
}

.copyright {
  color: #909399;
  font-size: 14px;
  margin-bottom: 8px;
}

.icp-info {
  font-size: 12px;
}

.icp-link {
  color: #909399;
  text-decoration: none;
  transition: color 0.3s;
}

.icp-link:hover {
  color: #409EFF;
}

@media (max-width: 768px) {
  .app-footer {
    padding: 15px 0;
    margin-top: 20px;
  }
  
  .footer-link, .copyright {
    font-size: 12px;
  }
  
  .icp-info {
    font-size: 11px;
  }
  
  .divider {
    margin: 0 5px;
  }
}
</style>
