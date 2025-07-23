<template>
  <footer class="app-footer">
    <div class="footer-content">
      <div class="footer-links">
        <a href="#" class="footer-link" @click.prevent="openModal('about')">关于我们</a>
        <span class="divider">|</span>
        <a href="#" class="footer-link" @click.prevent="openModal('guide')">使用指南</a>
        <span class="divider">|</span>
        <a href="#" class="footer-link" @click.prevent="openModal('privacy')">隐私政策</a>
        <span class="divider">|</span>
        <a href="#" class="footer-link" @click.prevent="openModal('contact')">联系我们</a>
      </div>
      <div class="copyright">
        © {{ currentYear }} 智慧校园人员检测系统 版权所有
      </div>
      <div class="icp-info">
        <a href="https://beian.miit.gov.cn/" target="_blank" class="icp-link">冀ICP备2024063729号</a>
      </div>
    </div>

    <InfoModal
      :visible="isModalVisible"
      :title="modalTitle"
      :content="modalContent"
      @close="closeModal"
    />
  </footer>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import InfoModal from './InfoModal.vue';

const currentYear = computed(() => new Date().getFullYear());

// 弹出窗口状态
const isModalVisible = ref(false);
const modalTitle = ref('');
const modalContent = ref('');

// 内容库
const contentMap = {
  about: {
    title: '关于我们',
    content: `
      <div>
        <h4>慧感云瞻</h4>
        <p>我们是来自哈尔滨工业大学的创新技术团队，专注于智能感知与云计算技术的研发与应用。</p>
        <p>"慧感云瞻"致力于打造新一代智慧校园解决方案，将前沿AI技术与实际场景深度融合，为高校提供高效、智能的人员流动监测与资源优化服务。</p>
        <p>我们的团队由计算机视觉、嵌入式系统与数据分析专家组成，共同构建面向未来的智慧校园生态系统。</p>
      </div>
    `
  },
  guide: {
    title: '使用指南',
    content: `
      <div>
        <h4>系统使用指南</h4>
        <p><strong>基本功能：</strong></p>
        <ul>
          <li>实时人员监测：查看校园各区域实时人流量</li>
          <li>数据统计分析：浏览历史数据和趋势分析</li>
          <li>智能资源分配：根据人流情况提供资源调配建议</li>
          <li>系统设置：根据需求自定义监测参数和通知设置</li>
        </ul>
        <p>如需更详细的使用说明，请联系我们获取完整用户手册。</p>
      </div>
    `
  },
  privacy: {
    title: '隐私政策',
    content: `
      <div>
        <h4>隐私政策</h4>
        <p><strong>信息收集与使用：</strong></p>
        <p>本系统收集的所有图像和数据仅用于人流量统计和资源优化目的，不会识别或存储个人身份信息。所有图像处理在本地完成，仅将匿名统计数据上传至安全服务器。</p>
        
        <p><strong>数据安全：</strong></p>
        <p>我们采用严格的安全措施保护所有收集的数据，包括加密传输、安全存储和定期数据清理。系统设计遵循"隐私优先"原则，确保用户隐私不受侵犯。</p>
        
        <p><strong>数据保留：</strong></p>
        <p>匿名统计数据将保留用于分析和优化目的，原始图像数据会在本地处理后立即删除。</p>
        
        <p><strong>政策更新：</strong></p>
        <p>我们可能会不时更新本隐私政策，更新后的政策将在本页面公布。</p>
      </div>
    `
  },
  contact: {
    title: '联系我们',
    content: `
      <div>
        <h4>联系方式</h4>
        <p>如有任何问题、建议或合作意向，请通过以下方式联系我们：</p>
        <p><strong>邮箱：</strong> 1742782025@qq.com</p>
        <p><strong>地址：</strong> 黑龙江省哈尔滨市南岗区西大直街92号 哈尔滨工业大学</p>
        <p>我们欢迎您的反馈和建议，以帮助我们不断改进系统。</p>
        <p>我们将在工作日内尽快回复您的咨询。</p>
      </div>
    `
  }
};

// 打开弹出窗口
const openModal = (type: keyof typeof contentMap) => {
  const content = contentMap[type];
  if (content) {
    modalTitle.value = content.title;
    modalContent.value = content.content;
    isModalVisible.value = true;
  }
};

// 关闭弹出窗口
const closeModal = () => {
  isModalVisible.value = false;
};
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
