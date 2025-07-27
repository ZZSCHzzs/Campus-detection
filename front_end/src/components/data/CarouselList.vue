<template>
  <div class="info-list-container">
    <div class="tech-corners"></div>
    <div class="section-header">
      <h2>{{ title }}</h2>
      <div class="subtitle">{{ subtitle }}</div>
    </div>
    <div class="list-wrapper" ref="listWrapper">
      <div class="list-content" ref="listContent">
        <div v-for="(item, index) in items" :key="index" class="list-item">
          <slot name="item" :item="item"></slot>
        </div>
        <!-- Duplicate for seamless scroll -->
        <div v-for="(item, index) in items" :key="'duplicate-' + index" class="list-item">
          <slot name="item" :item="item"></slot>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted, onUnmounted, toRefs } from 'vue';

// The interface is now generic, or you can remove it if you pass any object
interface ListItem {
  [key: string]: any;
}

const props = defineProps({
  title: {
    type: String,
    required: true,
  },
  subtitle: {
    type: String,
    required: true,
  },
  items: {
    type: Array as () => ListItem[],
    required: true,
  },
});

const { items } = toRefs(props);
const listWrapper = ref<HTMLElement | null>(null);
const listContent = ref<HTMLElement | null>(null);
let animationFrameId: number;

// These functions are no longer needed here as the rendering is delegated to the parent.
// const getStatusClass = ...
// const formatStatus = ...

const startScrolling = () => {
  if (!listWrapper.value || !listContent.value) return;

  const wrapperHeight = listWrapper.value.offsetHeight;
  const contentHeight = listContent.value.scrollHeight / 2; // Height of original items

  if (contentHeight <= wrapperHeight) return; // No need to scroll

  let scrollTop = 0;
  const scroll = () => {
    scrollTop += 0.5; // Adjust speed here
    if (scrollTop >= contentHeight) {
      scrollTop = 0;
    }
    if (listContent.value) {
        listContent.value.style.transform = `translateY(-${scrollTop}px)`;
    }
    animationFrameId = requestAnimationFrame(scroll);
  };

  scroll();
};

onMounted(() => {
  startScrolling();
});

onUnmounted(() => {
  cancelAnimationFrame(animationFrameId);
});
</script>

<style scoped>
.info-list-container {
  border: 1px solid rgba(56, 189, 248, 0.3);
  padding: 12px;
  position: relative;
  overflow: hidden;
  height: 300px; /* Fixed height for the container */
}

.list-wrapper {
  height: calc(100% - 50px); /* Adjust based on header height */
  overflow: hidden;
}

.list-content {
  transition: transform 0.5s linear;
}

.list-item {
  display: flex;
  justify-content: space-between;

  border-bottom: 1px solid rgba(56, 189, 248, 0.1);
  font-size: 14px;
  color: #e0f2fe;
}

.list-item:last-child {
  border-bottom: none;
}

/* Remove status-badge styles as they will be defined in the parent (DataScreen.vue) */

.section-header {
  margin-bottom: 10px;
}

h2 {
  color: #e0f2fe;
  font-size: 18px;
  margin: 0;
}

.subtitle {
  color: #94a3b8;
  font-size: 12px;
}
</style>