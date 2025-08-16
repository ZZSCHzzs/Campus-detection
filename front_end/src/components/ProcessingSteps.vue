<template>
  <div class="processing-steps" v-if="steps.length > 0">
    <div class="steps-timeline">
      <div 
        v-for="(step, index) in processedSteps" 
        :key="index"
        class="step-item"
        :class="{
          'step-error': step.type === 'error',
          'step-thinking': step.type === 'thought',
          'step-active': isActiveStep(step, index),
          'step-completed': isCompletedStep(step, index)
        }"
      >
        <!-- 指示器：仅最后一步显示加载/实心圆，其余步骤不再转圈 -->
        <div class="step-indicator">
          <div v-if="isLLMStreaming(step, index)" class="solid-dot"></div>
          <div v-else-if="isStepLoading(step, index)" class="spinner"></div>
          <el-icon v-else class="step-icon">
            <component :is="getStepIcon(step)" />
          </el-icon>
        </div>

        <div class="step-content">
          <div class="step-header">
            <span class="step-title">{{ getStepTitle(step) }}</span>
            <span v-if="step.intent" class="step-intent">({{ step.intent }})</span>
            <span v-if="step.tool" class="step-tool">({{ step.tool }})</span>
            <span v-if="step.model" class="step-model">({{ step.model }})</span>
            <span class="step-actions">
              <el-button
                v-if="shouldShowDetailToggle(step)"
                type="primary"
                link
                size="small"
                @click="toggleThought(index)"
              >
                {{ expandedThoughts.includes(index) ? '隐藏详情' : '查看详情' }}
              </el-button>
            </span>
          </div>

          <!-- 流式生成文本（仅非LLM步骤显示，且排除规划类，避免与规划区重复） -->
          <div v-if="step.content && !isLLMStep(step) && step.type !== 'agent_planning' && step.type !== 'agent_replanning'" class="step-streaming-content">
            <div class="content-label">AI回答：</div>
            <div class="content-text" v-html="formatContent(step.content)"></div>
          </div>


          <!-- 思考过程 -->
          <div v-if="step.type === 'thought' && step.data" class="thought-details">
            <!-- 移除按钮，保留展开内容 -->
            <div v-if="expandedThoughts.includes(index)" class="thought-content">
              <div v-if="typeof step.data === 'string'" class="thought-text">
                {{ step.data }}
              </div>
              <pre v-else-if="typeof step.data === 'object'" class="thought-json">{{ JSON.stringify(step.data, null, 2) }}</pre>
            </div>
          </div>

          <!-- 计划详情 -->
          <div v-if="step.type === 'plan' && step.data" class="thought-details">
            <!-- 移除按钮，保留展开内容 -->
            <div v-if="expandedThoughts.includes(index)" class="thought-content">
              <template v-if="typeof step.data === 'object'">
                <div class="thought-text" v-if="step.data.action">行动：{{ step.data.action }}</div>
                <div class="thought-text" v-if="step.data.iteration">迭代：第{{ step.data.iteration }}次</div>
                <!-- 新增：展示规划器提供的回答大纲 -->
                <div class="kv-block" v-if="Array.isArray(step.data.outline) && step.data.outline.length > 0">
                  <div class="kv-title">回答大纲</div>
                  <ul class="kv-list">
                    <li v-for="(item, i) in step.data.outline" :key="i" class="kv-item">
                      <span class="kv-val">{{ item }}</span>
                    </li>
                  </ul>
                </div>
                <div class="thought-text" v-if="Array.isArray(step.data.tool_calls) && step.data.tool_calls.length > 0">计划调用工具：</div>
                <ul v-if="Array.isArray(step.data.tool_calls) && step.data.tool_calls.length > 0" class="kv-list">
                  <li v-for="(call, i) in step.data.tool_calls" :key="i" class="kv-item">
                    <div class="kv-line">
                      <span class="kv-key">工具</span>
                      <span class="kv-sep">：</span>
                      <span class="kv-val">{{ extractToolCallName(call) || '未知工具' }}</span>
                    </div>
                    <div class="kv-sub" v-if="extractToolCallArgs(call)">
                      <div class="kv-sub-title">参数</div>
                      <ul class="kv-sub-list">
                        <li v-for="(val, key) in extractToolCallArgs(call)" :key="String(key)" class="kv-item">
                          <span class="kv-key">{{ String(key) }}</span>
                          <span class="kv-sep">：</span>
                          <span class="kv-val">{{ previewValue(val) }}</span>
                        </li>
                      </ul>
                    </div>
                  </li>
                </ul>
              </template>
              <div v-else class="thought-text">{{ String(step.data) }}</div>
            </div>
          </div>
          <div v-if="step.message">{{ step.message }}</div>
          <!-- 工具执行详情 -->
          <div v-if="step.type === 'tool_execution' && step.data" class="thought-details">
            <!-- 移除按钮，保留展开内容 -->
            <div v-if="expandedThoughts.includes(index)" class="thought-content">
              <template v-if="typeof step.data === 'object'">
                <div class="thought-text" v-if="step.tool">工具：{{ step.tool }}</div>
                <div class="thought-text" v-if="step.data.reasoning">理由：{{ step.data.reasoning }}</div>
                <div class="kv-block" v-if="step.data.parameters && typeof step.data.parameters === 'object'">
                  <div class="kv-title">参数</div>
                  <ul class="kv-list">
                    <li v-for="(val, key) in step.data.parameters" :key="String(key)" class="kv-item">
                      <span class="kv-key">{{ String(key) }}</span>
                      <span class="kv-sep">：</span>
                      <span class="kv-val">{{ previewValue(val) }}</span>
                    </li>
                  </ul>
                </div>
              </template>
              <div v-else class="thought-text">{{ String(step.data) }}</div>
            </div>
          </div>

          <!-- 观察结果详情 -->
          <div v-if="step.type === 'observation' && step.data" class="thought-details">
            <!-- 移除按钮，保留展开内容 -->
            <div v-if="expandedThoughts.includes(index)" class="thought-content">
              <template v-if="typeof step.data === 'object'">
                <div class="thought-text">结果：{{ step.data.success ? '成功' : '失败' }}</div>
                <div class="thought-text" v-if="step.data.error">错误：{{ step.data.error }}</div>
                <template v-if="step.data.result_preview && !step.data.error">
                  <div class="kv-title">结果预览</div>
                  <div v-if="typeof step.data.result_preview === 'string'" class="thought-text">{{ step.data.result_preview }}</div>
                  <ul v-else-if="typeof step.data.result_preview === 'object'" class="kv-list">
                    <li v-for="(val, key) in step.data.result_preview" :key="String(key)" class="kv-item">
                      <span class="kv-key">{{ String(key) }}</span>
                      <span class="kv-sep">：</span>
                      <span class="kv-val">{{ previewValue(val) }}</span>
                    </li>
                  </ul>
                </template>
              </template>
              <div v-else class="thought-text">{{ String(step.data) }}</div>
            </div>
          </div>

          <!-- 意图识别结果详细展示 -->
          <div v-if="step.type === 'chain_step' && step.step === 'intent_detected'" class="intent-details">
            <div class="kv-line">
              <span class="kv-key">识别意图</span><span class="kv-sep">：</span>
              <span class="kv-val">{{ step.intent || (step.data && step.data.intent) || '未知' }}</span>
            </div>
            <div class="kv-line" v-if="typeof (step.confidence ?? (step.data && step.data.confidence)) !== 'undefined'">
              <span class="kv-key">置信度</span><span class="kv-sep">：</span>
              <span class="kv-val">{{ Math.round(100 * (Number(step.confidence ?? (step.data && step.data.confidence)) || 0)) }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 结果指示 -->
      <div v-if="hasContent && !isChainRunning" class="step-result">
        <div class="step-indicator">
          <el-icon class="step-icon result-icon"><Check /></el-icon>
        </div>
        <div class="step-content">
          <div class="step-header"><span class="step-title">生成完成</span></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { 
  Search, 
  Tools, 
  CoffeeCup, 
  Finished, 
  CircleCheck, 
  Loading, 
  Warning,
  InfoFilled,
  Check
} from '@element-plus/icons-vue'
import { ref, computed } from 'vue'

// 定义步骤类型
interface ProcessingStep {
  type: string; 
  step?: string; 
  message: string; 
  intent?: string;
  confidence?: number;
  tool?: string;
  model?: string;
  data?: any; // 思考数据
  content?: string; // 新增：步骤内的流式内容
}

// 定义组件属性
const props = defineProps<{
  steps: ProcessingStep[],
  hasContent?: boolean  // 是否已有内容生成
}>()

// 追踪展开的思考过程
const expandedThoughts = ref<number[]>([])

// 处理后的步骤，按阶段分组
const processedSteps = computed(() => {
  // 获取所有步骤，按照它们在时间线上的顺序排列
  return props.steps.filter(step => 
    // 过滤掉内容输出，它会在消息正文中显示
    step.type !== 'content'
  )
})

// 判断链是否仍在运行
const isChainRunning = computed(() => {
  return !props.steps.some(step => step.type === 'chain_end')
})

// 切换思考过程显示/隐藏
const toggleThought = (index: number) => {
  const idx = expandedThoughts.value.indexOf(index)
  if (idx >= 0) {
    expandedThoughts.value.splice(idx, 1)
  } else {
    expandedThoughts.value.push(index)
  }
}

// 获取步骤标题 - 适配新的Agent步骤类型
const getStepTitle = (step: ProcessingStep): string => {
  // 新版Agent步骤类型
  if (step.type === 'chain_start') return '处理请求'
  if (step.type === 'agent_planning') return '分析与规划'
  if (step.type === 'plan') return '执行计划'
  if (step.type === 'tool_execution') return '执行工具'
  if (step.type === 'observation') return '观察结果'
  if (step.type === 'agent_replanning') return '重新规划'
  if (step.type === 'final_generation') return '生成最终回答'
  if (step.type === 'tools_available') return '可用工具'
  if (step.type === 'thought') {
    // 思考步骤根据context不同有不同名称
    if (step.step === 'agent_planning' || step.step === 'agent_replanning') return '规划思考'
    if (step.step === 'tool_execution') return '工具结果分析'
    if (step.step === 'final_generation') return '生成回答思考'
    return '思考过程'
  }
  if (step.type === 'chain_end') return '处理完成'
  if (step.type === 'error') return '发生错误'
  
  // 兼容旧版步骤类型
  if (step.type === 'chain_step') {
    if (step.step === 'intent_detected') return '意图识别结果'
    if (step.step === 'tool_call') return '调用工具'
    if (step.step === 'llm_generation' || step.step === 'llm_streaming') return '生成回答中'
  }
  
  return step.step || step.type
}

// 判断步骤是否正在加载：仅最后一步显示加载
const isStepLoading = (step: ProcessingStep, index: number) => {
  if (!(step.type === 'chain_start' || step.type === 'chain_step' || 
        step.type === 'agent_planning' || step.type === 'tool_execution' ||
        step.type === 'agent_replanning')) return false
  if (!isChainRunning.value) return false
  const lastIndex = processedSteps.value.length - 1
  // 仅最后一个步骤允许显示加载（且不是LLM流式，由 isLLMStreaming 控制）
  return index === lastIndex && !isLLMStreaming(step, index)
}

// 判断步骤是否是活动步骤（当前正在执行的）
const isActiveStep = (step: ProcessingStep, index: number) => {
  if (props.steps.length === 0) return false
  if (isChainRunning.value && index === processedSteps.value.length - 1) {
    return true
  }
  return false
}

// 判断步骤是否已完成：有"下一个步骤"时，之前的链式步骤视为完成
const isCompletedStep = (step: ProcessingStep, index: number) => {
  // 思考类直接视为完成（静态展示）
  if (step.type === 'thought') return true
  const isChainStep = (step.type === 'chain_start' || step.type === 'chain_step')
  
  // 当从getStepIcon调用时(index为-1)，我们只检查基于步骤自身属性的条件
  if (index === -1) {
    // 链已结束：所有链式步骤完成
    if (!isChainRunning.value && isChainStep) return true
    // 基于文案判断的完成态
    return (step.type === 'chain_end') || (
      !!step.message && (
        step.message.includes('完成') || 
        step.message.includes('✅') || 
        step.message.includes('成功')
      )
    )
  }
  
  const lastIndex = processedSteps.value.length - 1
  // 存在后续步骤：本步骤已完成
  if (isChainStep && index < lastIndex) return true
  // 链已结束：所有链式步骤完成
  if (!isChainRunning.value && isChainStep) return true
  // 其他基于文案判断的完成态
  return (step.type === 'chain_end') || (
    !!step.message && (
      step.message.includes('完成') || 
      step.message.includes('✅') || 
      step.message.includes('成功')
    )
  )
}

// 判定是否为进行中的LLM生成/流式步骤：仅最后一步显示实心圆
const isLLMStreaming = (step: ProcessingStep, index: number) => {
  const lastIndex = processedSteps.value.length - 1
  return (
    isChainRunning.value &&
    index === lastIndex &&
    (step.type === 'chain_step' || step.type === 'final_generation') &&
    (step.step === 'llm_generation' || step.step === 'llm_streaming' || 
     step.type === 'final_generation')
  )
}

// 判定是否为LLM步骤（无论是否还在运行）
const isLLMStep = (step: ProcessingStep) => {
  return step.step === 'llm_generation' || step.step === 'llm_streaming' || 
         step.type === 'final_generation'
}

// 根据步骤类型和名称获取图标
const getStepIcon = (step: ProcessingStep) => {
  if (step.type === 'error') return Warning
  if (step.type === 'thought') return InfoFilled
  if (isCompletedStep(step, -1)) return CircleCheck

  // 新版Agent步骤图标映射
  if (step.type === 'agent_planning' || step.type === 'agent_replanning' || step.type === 'plan') return Search
  if (step.type === 'tool_execution' || step.type === 'observation') return Tools
  if (step.type === 'final_generation') return CoffeeCup
  if (step.type === 'tools_available') return InfoFilled

  // 兼容旧版步骤
  if (step.step === 'agent_planning' || step.step === 'agent_replanning') return Search
  if (step.step === 'tool_execution') return Tools
  if (step.step === 'final_generation' || step.step === 'llm_generation' || step.step === 'llm_streaming') return CoffeeCup
  if (step.step === 'intent_detection') return Search
  if (step.step === 'intent_detected') return Finished
  if (step.step === 'tool_call') return Tools
  
  return Loading
}

// 简单的内容格式化（防注入 + 换行）
const formatContent = (content: string) => {
  const escapeHtml = (s: string) =>
    s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  return escapeHtml(content).replace(/\n/g, '<br/>')
}

// 友好的值预览：避免展示原始JSON，嵌套对象/数组显示为简要字符串
const previewValue = (val: any): string => {
  if (val === null || typeof val === 'undefined') return '—'
  if (typeof val === 'string') return val
  if (typeof val === 'number' || typeof val === 'boolean') return String(val)
  try {
    const s = JSON.stringify(val)
    return s.length > 160 ? s.slice(0, 160) + '…' : s
  } catch {
    return String(val)
  }
}

// 解析计划中的工具调用名称
const extractToolCallName = (call: any): string => {
  if (!call || typeof call !== 'object') return ''
  return call.tool || call.name || (call.function && (call.function.name || call.function)) || call.action || ''
}

// 解析计划中的工具调用参数对象
const extractToolCallArgs = (call: any): Record<string, any> | null => {
  if (!call || typeof call !== 'object') return null
  const args = call.arguments || call.args || call.parameters || (call.function && call.function.arguments) || null
  return (args && typeof args === 'object') ? args : null
}

// 新增：哪些步骤显示“详情”切换按钮（统一放到标题行右侧）
const shouldShowDetailToggle = (step: ProcessingStep) => {
  if (!step) return false
  if (step.type === 'thought') return !!step.data
  if (step.type === 'plan') return true
  if (step.type === 'tool_execution') return true
  if (step.type === 'observation') return true
  return false
}
</script>

<style scoped>
.processing-steps {
  margin-bottom: 8px;
  font-size: 13px;
  color: #606266;
}

.steps-timeline {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0;
  background: transparent;
  border: 0;
  box-shadow: none;
}

.step-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  background: #fbfbfd;
  border: 1px solid #edf0f5;
  border-radius: 10px;
  transition: background-color .2s ease, border-color .2s ease;
}

.step-item:hover {
  background: #f8fafc;
  border-color: #e6ebf1;
}

.step-indicator {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  margin-top: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #dcdfe6;
  border-top-color: #409EFF;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.solid-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #409EFF;
}

.step-icon { font-size: 14px; color: #909399; }
.step-title { font-weight: 600; color: #303133; }
.step-message { color: #606266; word-break: break-word; }

.step-item.step-active {
  background: rgba(64,158,255,0.06);
  border-left: 3px solid #409EFF;
  border-color: #d5e8ff;
}

.step-item.step-error {
  background: rgba(245,108,108,0.06);
  border-color: #fbd5d5;
}
.step-item.step-error .step-title,
.step-item.step-error .step-message,
.step-item.step-error .step-icon { color: #F56C6C; }

.step-item.step-thinking {
  background: rgba(144,147,153,0.06);
  border-color: #ececec;
  color: #606266;
}

.step-completed .step-icon { color: #67C23A; }

.step-intent { font-weight: 500; color: #409EFF; }
.step-tool { font-weight: 500; color: #67C23A; }
.step-model { font-weight: 500; color: #E6A23C; }

.thought-details { margin-top: 6px; }
.thought-content {
  margin-top: 6px;
  padding: 8px 10px;
  background: #fff;
  border-left: 2px solid #ebeef5;
  border-radius: 4px;
}
.thought-text { white-space: pre-wrap; font-size: 12px; }
.thought-json { font-size: 12px; margin: 0; white-space: pre-wrap; word-break: break-all; }

.step-streaming-content { margin-top: 4px; }
.content-label { font-size: 12px; color: #909399; margin-bottom: 2px; }
.content-text { font-size: 13px; color: #303133; }

.planning-progress-content { margin-top: 6px; }
.planning-label { font-size: 12px; color: #909399; margin-bottom: 2px; }
.planning-text { font-size: 12.5px; color: #606266; white-space: pre-wrap; }
.step-result .result-icon { color: #67C23A; }

.kv-block { margin-top: 8px; }
.kv-title { font-size: 12px; color: #909399; margin: 4px 0; }
.kv-list { list-style: none; padding-left: 0; margin: 4px 0; }
.kv-sub { margin-top: 6px; padding-left: 8px; border-left: 2px dashed #e6ebf1; }
.kv-sub-title { font-size: 12px; color: #909399; margin-bottom: 4px; }
.kv-sub-list { list-style: none; padding-left: 0; margin: 0; }
.kv-item { margin: 2px 0; }
.kv-line { margin: 2px 0; }
.kv-key { color: #606266; }
.kv-sep { color: #c0c4cc; margin: 0 4px; }
.kv-val { color: #303133; word-break: break-word; }

.intent-details { margin-top: 6px; padding: 8px 10px; background: #fff; border-left: 2px solid #ebeef5; border-radius: 4px; }

.step-header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.step-actions {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
}
</style>
