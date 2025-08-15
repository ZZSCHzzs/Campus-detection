<template>
  <div class="llm-container">
    <div class="layout">
      <!-- 左侧侧边栏：新增折叠 -->
      <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
        <div class="sidebar-header">
          <!-- 改造品牌标题为"云小瞻" + 副标题 -->
          <div class="brand brand-beauty">
            <div class="brand-badge">云</div>
            <div class="brand-text">
              <div class="brand-name">云小瞻</div>
              <div class="brand-sub">Campus AI</div>
            </div>
          </div>
          <div class="actions">
            <!-- 折叠按钮 -->
            <el-button text class="collapse-btn" @click="sidebarCollapsed = !sidebarCollapsed" :title="sidebarCollapsed ? '展开' : '折叠'">
              <el-icon><component :is="sidebarCollapsed ? Expand : Fold" /></el-icon>
            </el-button>
          </div>
        </div>

        <el-scrollbar class="conversation-list-scrollbar">
          <div class="conversation-list">
            <!-- 新建对话项：样式与对话列表项一致 -->
            <div class="conversation-item new-conversation" @click="handleNewClick">
              <el-icon class="conv-icon"><Plus /></el-icon>
              <div class="conv-meta new-chat-meta">
                <div class="conv-title">新建对话</div>
              </div>
            </div>
            
            <!-- 已有对话列表 -->
            <div
              v-for="conv in conversations"
              :key="conv.id"
              class="conversation-item"
              :class="{ active: conv.id === activeId }"
              @click="switchConversation(conv.id)"
            >
              <el-icon class="conv-icon"><ChatDotRound /></el-icon>
              <div class="conv-meta">
                <div class="conv-title" :title="conv.title">{{ conv.title }}</div>
                <div class="conv-time">{{ formatTime(conv.createdAt) }}</div>
              </div>
              <el-button text class="conv-delete" @click.stop="deleteConversation(conv.id)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            
            <!-- 无对话提示 -->
            <div v-if="conversations.length === 0" class="conversation-empty">暂无对话，点击"新建对话"或直接开始输入</div>
          </div>
        </el-scrollbar>
      </aside>

      <!-- 主聊天区域 -->
      <div class="main-content">
        <!-- 使用 el-scrollbar 包裹聊天区 -->
        <el-scrollbar ref="chatContainer" class="chat-messages-scrollbar">
          <div class="chat-messages" :class="{ 'with-bottom-gap': activeId }">
            <!-- 欢迎页：仅在没有活动对话时显示 (修改逻辑：从messages.length判断改为activeId判断) -->
            <div v-if="!activeId" class="welcome-container">
              <!-- 欢迎标题与描述改为云小瞻 -->
              <div class="welcome-title">云小瞻</div>
              <div class="welcome-subtitle">智慧校园智能体，为您提供校园信息查询、数据分析与建议</div>
              
              <!-- 功能卡片区（精简版） -->
              <div class="features-grid">
                <div class="feature-card" v-for="(feature, index) in features" :key="index">
                  <el-icon class="feature-icon"><component :is="feature.icon" /></el-icon>
                  <div class="feature-text">
                    <div class="feature-title">{{ feature.title }}</div>
                    <div class="feature-description">{{ feature.desc }}</div>
                  </div>
                </div>
              </div>

              <!-- 建议问题卡片 -->
              <div class="suggestions-section">
                <div class="section-title">你可以这样问我</div>
                <div class="suggestions-grid">
                  <div
                    v-for="(suggestion, index) in suggestions"
                    :key="index"
                    class="suggestion-card"
                    @click="sendMessage(suggestion)"
                  >
                    <div class="suggestion-card-inner">{{ suggestion }}</div>
                  </div>
                </div>
              </div>
              
              <!-- 操作按钮 -->
              <div class="action-section">
                <el-button type="primary" class="new-chat-btn" @click="scrollToInput">
                  开始对话
                </el-button>
              </div>

              <!-- 修复：英雄输入框宽度与高度 -->
              <div class="hero-composer">
                <div class="composer">
                  <textarea
                    ref="composerRef"
                    v-model="userInput"
                    class="composer-textarea"
                    placeholder="开始对话吧..."
                    :disabled="isStreaming"
                    @input="autoResize"
                    @keydown="onComposerKeydown"
                    rows="1"
                  ></textarea>
                  <button class="composer-send" :disabled="!userInput.trim() || isStreaming" @click="sendMessage()">
                    <el-icon><Position /></el-icon>
                  </button>
                </div>
                <!-- 新增：模型切换按钮（默认分析，无需按钮） -->
                <div class="composer-toolbar">
                  <div class="model-toggle">
                    <button
                      class="model-btn"
                      :class="{ active: selectedModelType === 'fast' }"
                      @click="selectModel('fast')"
                      :disabled="isStreaming"
                    >快速</button>
                    <button
                      class="model-btn"
                      :class="{ active: selectedModelType === 'reasoning' }"
                      @click="selectModel('reasoning')"
                      :disabled="isStreaming"
                    >思考</button>
                    <button
                      class="model-btn"
                      :class="{ active: selectedModelType === 'deep_reasoning' }"
                      @click="selectModel('deep_reasoning')"
                      :disabled="isStreaming"
                    >深度推理</button>
                  </div>
                </div>
                <div class="input-hint">按回车键发送 / Shift+回车换行</div>
              </div>
            </div>
            
            <!-- 对话消息列表：在有活动对话时显示 (即使没有消息) -->
            <div v-else class="messages-container">
              <div 
                v-for="(msg, index) in messages" 
                :key="`msg-${index}-${msg.isUser}`"
                :class="['message-item', msg.isUser ? 'user-message' : 'ai-message']"
              >
                <div class="message-avatar">
                  <el-avatar :icon="msg.isUser ? User : Monitor" :size="28" />
                </div>
                <div class="message-content-wrapper">
                  <div :class="['message-bubble', msg.isUser ? 'bubble-user' : 'bubble-ai']">
                    <div class="message-sender">{{ msg.isUser ? '您' : '云小瞻' }}</div>

                    <!-- 新的布局：步骤组件显示在回答内容之前 -->
                    <processing-steps 
                      v-if="!msg.isUser && msg.processingSteps && msg.processingSteps.length > 0" 
                      :steps="msg.processingSteps"
                      :hasContent="!!msg.content" 
                    />
                    
                    <!-- 消息内容 -->
                    <div class="message-content markdown-body" v-html="renderMarkdown(msg.content)"></div>
                    
                    <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
                  </div>
                </div>
              </div>
              <!-- 添加：没有消息时显示的引导文本 -->
              <div v-if="messages.length === 0" class="empty-messages-guide">
                <div class="guide-text">您可以开始提问了...</div>
              </div>
            </div>
          </div>
        </el-scrollbar>

        <!-- 建议问题区域：在有活动对话时显示 -->
        <div v-if="activeId && !isStreaming" class="quick-suggestions">
          <div class="quick-suggestions-chips">
            <div
              v-for="(suggestion, index) in quickSuggestions"
              :key="index"
              class="quick-suggestion-chip"
              @click="sendMessage(suggestion)"
            >
              {{ suggestion }}
            </div>
          </div>
        </div>

        <!-- 吸底输入框：在有活动对话时显示 -->
        <div v-if="activeId" class="chat-input-container" ref="inputContainer">
          <div class="composer">
            <textarea
              ref="composerRef"
              v-model="userInput"
              class="composer-textarea"
              placeholder="输入您的问题..."
              :disabled="isStreaming"
              @input="autoResize"
              @keydown="onComposerKeydown"
              rows="1"
            ></textarea>
            <button class="composer-send" :disabled="!userInput.trim() || isStreaming" @click="sendMessage()">
              <el-icon><Position /></el-icon>
            </button>
          </div>
          <div class="composer-toolbar inline">
            <div class="model-toggle">
              <button
                class="model-btn"
                :class="{ active: selectedModelType === 'fast' }"
                @click="selectModel('fast')"
                :disabled="isStreaming"
              >快速</button>
              <button
                class="model-btn"
                :class="{ active: selectedModelType === 'reasoning' }"
                @click="selectModel('reasoning')"
                :disabled="isStreaming"
              >思考</button>
              <button
                class="model-btn"
                :class="{ active: selectedModelType === 'deep_reasoning' }"
                @click="selectModel('deep_reasoning')"
                :disabled="isStreaming"
              >深度推理</button>
            </div>
          </div>
          <div class="input-hint">按回车键发送 / Shift+回车换行</div>
        </div>
      </div>
    </div>

    <!-- 浮动操作按钮 -->
    <div class="floating-actions">
      <el-button 
        v-if="activeId"
        type="primary" 
        plain 
        size="small"
        @click="clearMessages"
        class="clear-button"
      >
        <el-icon><Delete /></el-icon>清空对话
      </el-button>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted, nextTick, watch, onBeforeUnmount, computed } from 'vue'
import { 
  Delete, Position, Monitor, User, Plus,
  DataAnalysis, OfficeBuilding, Connection, Warning,
  ChatDotRound, Fold, Expand, Loading
} from '@element-plus/icons-vue'
import { marked } from 'marked' // 引入markdown解析器
import DOMPurify from 'dompurify' // 引入DOM净化器，防止XSS攻击
import { ElMessage } from 'element-plus'
// 导入处理步骤组件
import ProcessingSteps from '../components/ProcessingSteps.vue'
// 修复：使用type导入类型
import { createChatStream } from '../services/LLM'
import type { ChatHistory } from '../services/LLM'

// 类型与状态
type Message = { content: string; isUser: boolean; timestamp: Date; processingSteps?: ProcessingStep[] }
type Conversation = { id: string; title: string; createdAt: Date; messages: Message[] }
// 处理步骤类型定义
type ProcessingStep = { 
  type: string; 
  step?: string; 
  message: string; 
  intent?: string;
  confidence?: number;
  tool?: string;
  model?: string;
  data?: any; // 新增：用于存储 thought 数据
  content?: string; // 新增：步骤内流式文本
}

// 添加缺少的ref定义
const chatContainer = ref<any>(null)
const composerRef = ref<HTMLTextAreaElement | null>(null)
const inputContainer = ref<HTMLElement | null>(null)

// 新增：添加abortController引用
const abortController = ref<AbortController | null>(null)

// 默认：分析（无需按钮）
const selectedModelType = ref<'fast' | 'reasoning' | 'deep_reasoning' | 'analysis'>('analysis')
const paramModelType = computed(() => selectedModelType.value || 'analysis')
const selectModel = (t: 'fast' | 'reasoning' | 'deep_reasoning') => {
  if (isStreaming.value) return
  // 再次点击当前按钮则回到默认“分析”
  selectedModelType.value = (selectedModelType.value === t) ? 'analysis' : t
}

// 预设特性卡片数据
const features = [
  { icon: 'DataAnalysis', title: '校园数据分析', desc: '获取人流、环境数据和设施使用情况' },
  { icon: 'OfficeBuilding', title: '区域信息查询', desc: '了解区域拥挤程度和环境条件' },
  { icon: 'Connection', title: '资源导航', desc: '查询校内资源和服务信息' },
  { icon: 'Warning', title: '智能提醒', desc: '获取拥挤预警和安全建议' }
]

const userInput = ref('')
const conversations = ref<Conversation[]>([])
const activeId = ref<string>('')
const messages = ref<Message[]>([])
const isStreaming = ref(false) // 替换为流式状态（用于禁用输入、隐藏快速建议）
// 当前处理步骤状态
const currentSteps = ref<ProcessingStep[]>([])
// 当前回复消息
const currentResponse = ref<string>('')
// 后端API基础URL
const apiBaseUrl = ref('/api/llm')
// 事件源
let eventSource: EventSource | null = null

// 折叠状态
const sidebarCollapsed = ref(false)

// 格式化时间函数 - 添加缺失的函数
const formatTime = (date: Date): string => {
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

// 修改：新建按钮行为变更为切换到欢迎页
const handleNewClick = () => {
  // 直接清空当前活动对话，切换到欢迎页
  activeId.value = ''
  messages.value = []
  nextTick(() => {
    // 聚焦到欢迎页的输入框
    scrollToInput()
  })
}

// 新建/切换/删除会话
const newConversation = () => {
  const id = String(Date.now())
  const conv: Conversation = { id, title: '新对话', createdAt: new Date(), messages: [] }
  conversations.value.unshift(conv)
  switchConversation(id)
}

const switchConversation = (id: string) => {
  activeId.value = id
  const conv = conversations.value.find(c => c.id === id)
  messages.value = conv ? conv.messages : []
  nextTick(scrollToBottom)
}

const deleteConversation = (id: string) => {
  const idx = conversations.value.findIndex(c => c.id === id)
  if (idx >= 0) {
    conversations.value.splice(idx, 1)
    if (activeId.value === id) {
      const nextActive = conversations.value[0]
      if (nextActive) {
        switchConversation(nextActive.id)
      } else {
        activeId.value = ''
        messages.value = []
      }
    }
  }
}

// 文本流：逐字符更新内容并滚动
const streamText = (msg: Message, fullText: string, stepMs = 12) => {
  return new Promise<void>((resolve) => {
    let i = 0
    const timer = setInterval(() => {
      i++
      msg.content = fullText.slice(0, i)
      if (chatContainer.value?.setScrollTop) chatContainer.value.setScrollTop(999999)
      if (i >= fullText.length) {
        clearInterval(timer)
        resolve()
      }
    }, stepMs)
  })
}

// 滚动到底部
const scrollToBottom = () => {
  if (chatContainer.value?.setScrollTop) chatContainer.value.setScrollTop(999999)
}

// 恢复示例问题建议
const suggestions = [
  "查询正心11的综合状态",
  "推荐3个现在人少的自习区域",
  "获取区域正心11在三天内的人流极值",
  "查询终端2的运行状态",
  "我要预约图书馆座位",
  "如何访问本科生教务系统"
]

// 快速跟进问题建议
const quickSuggestions = [
  "查看该区域的最近告警",
  "给我相关的资源链接入口",
  "继续推荐其它更空闲的区域",
  "解释上面趋势的意义与建议"
]

// 修改：发送消息方法，使用后端API
const sendMessage = async (text?: string) => {
  const messageContent = text || userInput.value.trim()
  if (!messageContent || isStreaming.value) return
  
  // 创建或获取对话
  let currentConv: Conversation
  
  // 如果没有活动对话ID或找不到对应对话，就创建新对话
  if (!activeId.value || !conversations.value.find(c => c.id === activeId.value)) {
    // 创建新对话
    const id = String(Date.now())
    currentConv = {
      id,
      title: messageContent.slice(0, 20),
      createdAt: new Date(),
      messages: []
    }
    
    // 添加到会话列表
    conversations.value.unshift(currentConv)
    activeId.value = id
  } else {
    // 使用现有对话
    currentConv = conversations.value.find(c => c.id === activeId.value)!
    
    // 如果是"新对话"，更新标题
    if (currentConv.title === '新对话') {
      currentConv.title = messageContent.slice(0, 20)
    }
  }
  
  // 添加用户消息
  currentConv.messages.push({
    content: messageContent,
    isUser: true,
    timestamp: new Date()
  })
  
  // 强制更新视图 - 创建新引用
  messages.value = [...currentConv.messages]
  
  // 清空输入框
  userInput.value = ''
  await nextTick()
  autoResize()
  scrollToBottom()
  
  // 清理可能存在的之前的控制器
  if (abortController.value) {
    abortController.value.abort();
    abortController.value = null;
  }
  
  // AI回复流式处理
  isStreaming.value = true
  currentSteps.value = []
  currentResponse.value = ''
  
  // 准备一个空消息对象，接收流式内容
  const aiMsg: Message = { 
    content: '', 
    isUser: false, 
    timestamp: new Date(),
    processingSteps: []
  }
  currentConv.messages.push(aiMsg)
  messages.value = [...currentConv.messages]
  
  // 准备聊天历史
  const chatHistory = formatChatHistory(currentConv.messages.slice(0, -1)) // 不包括最后添加的空AI消息
  
  try {
    // 使用创建的 LLM 服务发起流式请求
    abortController.value = createChatStream(
      messageContent,
      chatHistory,
      // 消息处理回调
      (data) => {
        processStreamData(data, aiMsg);
        currentConv.messages = [...currentConv.messages];
      },
      // 错误处理回调
      (error) => {
        console.error('流式请求错误', error);
        closeEventSource();
        if (!aiMsg.content) {
          aiMsg.content = '⚠️ 抱歉，连接服务器时出现问题，请稍后重试。';
          messages.value = [...currentConv.messages];
        }
      },
      // 结束处理回调
      () => {
        closeEventSource();
      },
      paramModelType.value
    );
  } catch (error) {
    console.error('发送消息失败', error);
    closeEventSource();
    aiMsg.content = `⚠️ 发送失败: ${error instanceof Error ? error.message : String(error)}`;
    messages.value = [...currentConv.messages];
    isStreaming.value = false;
  }
}

// 修改：处理流数据 - 支持所有Agent步骤事件类型
const processStreamData = (data: any, aiMsg: Message) => {
  if (!data) return
  
  // 文本内容更新（步骤内与最终答案同时流式展示）
  if (data.type === 'content') {
    const text = data.text || ''
    aiMsg.content += text
    currentResponse.value += text

    // 不再把生成文本同步到上面的步骤，避免与正式回答重复显示
    
    // 强制刷新视图
    messages.value = [...messages.value]
    
    // 始终滚动到底部
    nextTick(() => {
      scrollToBottom()
    })
    return
  }
  
  // 处理规划进度流式输出（新增）
  if (data.type === 'planning_progress') {
    const progressText = data.content || ''
    
    if (!aiMsg.processingSteps) {
      aiMsg.processingSteps = []
    }
    
    // 优先更新最近的 agent_planning；若不存在，则尝试 agent_replanning；若仍不存在，则创建占位规划步骤
    const typesOrder = ['agent_planning', 'agent_replanning']
    let targetIndex = -1
    for (const t of typesOrder) {
      const idx = aiMsg.processingSteps.map(s => s.type).lastIndexOf(t)
      if (idx >= 0) { targetIndex = idx; break }
    }

    if (targetIndex < 0) {
      // 创建占位规划步骤，确保不会丢失规划进度
      const placeholder: ProcessingStep = {
        type: 'agent_planning',
        message: getDefaultStepMessage('agent_planning'),
        content: ''
      }
      aiMsg.processingSteps.push(placeholder)
      targetIndex = aiMsg.processingSteps.length - 1
    }

    const planningStep = aiMsg.processingSteps[targetIndex]
    planningStep.content = (planningStep.content || '') + progressText
    
    // 强制刷新视图
    aiMsg.processingSteps = [...aiMsg.processingSteps]
    messages.value = [...messages.value]
    
    // 滚动到底部
    nextTick(() => {
      scrollToBottom()
    })
    return
  }
  
  // 处理所有步骤更新事件 - 支持完整的Agent步骤类型
  const stepEventTypes = [
    'chain_start', 'chain_step', 'chain_end', 'error', 'thought',
    'agent_planning', 'plan', 'tool_execution', 'observation', 
    'agent_replanning', 'final_generation'
  ]
  
  if (stepEventTypes.includes(data.type)) {
    // 统一思考数据映射：chains.py中的thought使用content字段
    let stepData: any = data.data
    if (data.type === 'thought') {
      stepData = (data.data !== undefined && data.data !== null) ? data.data : data.content
    }

    // 创建步骤对象，包含所有可能的属性
    const step: ProcessingStep = {
      type: data.type,
      step: data.step,
      message: data.message || getDefaultStepMessage(data.type),
      intent: data.intent,
      confidence: data.confidence,
      tool: data.tool,
      model: data.model,
      data: stepData // 存储思考数据、工具参数等
    }
    
    // 新增：为规划步骤携带本轮次 iteration，便于前端区分轮次
    if (data.type === 'agent_planning' || data.type === 'agent_replanning') {
      step.data = { ...(step.data || {}), iteration: data.iteration }
    }

    if (data.type === 'plan') {
      step.data = {
        action: data.action,
        tool_calls: data.tool_calls,
        iteration: data.iteration,
        outline: data.outline
      }
    } else if (data.type === 'tool_execution') {
      step.data = {
        parameters: data.parameters,
        reasoning: data.reasoning
      }
    } else if (data.type === 'observation') {
      step.data = {
        success: data.success,
        result_preview: data.result_preview,
        error: data.error
      }
    }
    
    // 更新当前步骤
    currentSteps.value.push(step)

    if (!aiMsg.processingSteps) {
      aiMsg.processingSteps = []
    }
    
    // 修改：重复步骤判定
    // - 对规划步骤（agent_planning/agent_replanning）：只有“同类型且iteration相同”才算重复，否则新增
    // - 其他类型：沿用原来的宽松重复判断
    let isDuplicateStep = false
    const isPlanningType = (step.type === 'agent_planning' || step.type === 'agent_replanning')
    if (isPlanningType) {
      const lastSameTypeIndex = aiMsg.processingSteps.map(s => s.type).lastIndexOf(step.type)
      if (lastSameTypeIndex >= 0) {
        const lastStep = aiMsg.processingSteps[lastSameTypeIndex] as any
        const lastIter = lastStep?.data?.iteration
        const currIter = (step as any)?.data?.iteration ?? data?.iteration
        isDuplicateStep = (typeof lastIter !== 'undefined' && typeof currIter !== 'undefined' && lastIter === currIter)
      } else {
        isDuplicateStep = false
      }
    } else {
      isDuplicateStep = aiMsg.processingSteps.some(
        existingStep => existingStep.type === step.type &&
                        existingStep.step === step.step &&
                        existingStep.tool === step.tool
      )
    }
    
    if (!isDuplicateStep) {
      aiMsg.processingSteps.push(step)
    } else {
      const lastIndex = aiMsg.processingSteps.map(s => s.type).lastIndexOf(step.type)
      if (lastIndex >= 0) {
        const existingStep = aiMsg.processingSteps[lastIndex] as any
        aiMsg.processingSteps[lastIndex] = { ...existingStep, ...step }
      }
    }
    
    aiMsg.processingSteps = [...aiMsg.processingSteps]
    messages.value = [...messages.value]
    
    nextTick(() => {
      scrollToBottom()
    })
    
    if (data.type === 'error') {
      aiMsg.content += `\n⚠️ ${data.message}`
      closeEventSource()
      messages.value = [...messages.value]
    } else if (data.type === 'chain_end') {
      setTimeout(() => {
        closeEventSource()
      }, 100)
    }
    
    return
  }
  
  // 兜底：记录未知数据类型，但仍尝试作为步骤处理
  console.log('未知数据类型，尝试作为步骤处理:', data)
  
  // 尝试将未知类型作为通用步骤处理
  if (data.message || data.type) {
    const genericStep: ProcessingStep = {
      type: data.type || 'unknown',
      message: data.message || `处理 ${data.type || '未知'} 事件`,
      data: data
    }
    
    if (!aiMsg.processingSteps) {
      aiMsg.processingSteps = []
    }
    
    aiMsg.processingSteps.push(genericStep)
    aiMsg.processingSteps = [...aiMsg.processingSteps]
    messages.value = [...messages.value]
    
    nextTick(() => {
      scrollToBottom()
    })
  }
}

// 辅助函数：为事件类型提供默认消息
const getDefaultStepMessage = (eventType: string): string => {
  const defaultMessages: Record<string, string> = {
    'chain_start': '开始处理您的请求...',
    'agent_planning': 'AI正在分析和规划...',
    'thought': '理解用户意图...',
    'plan': '制定执行计划...',
    'tool_execution': '根据参数执行工具...',
    'observation': '观察工具调用结果...',
    'agent_replanning': '根据信息重新规划流程...',
    'final_generation': '生成最终回答...',
    'chain_end': '✅ 处理完成',
    'error': '❌ 处理出错'
  }
  
  return defaultMessages[eventType] || `处理 ${eventType} 事件`
}

// 修复：格式化聊天历史为API需要的格式
const formatChatHistory = (messages: Message[]): ChatHistory => {
  return messages.map(msg => ({
    // 明确指定 role 类型以解决类型不匹配问题
    role: msg.isUser ? 'user' as const : 'assistant' as const,
    content: msg.content
  }))
}

// 修改：关闭事件源函数
const closeEventSource = () => {
  if (abortController.value) {
    abortController.value.abort();
    abortController.value = null;
  }
  isStreaming.value = false;
}

// 清空当前会话消息
const clearMessages = () => {
  closeEventSource() // 确保关闭任何活动连接
  
  const conv = conversations.value.find(c => c.id === activeId.value)
  if (conv) conv.messages = []
  messages.value = conv ? conv.messages : []
}

// 自动调整输入框高度
const autoResize = () => {
  const ta = composerRef.value
  if (!ta) return
  
  // 重置高度以便重新计算
  ta.style.height = 'auto'
  
  // 根据是否在欢迎页设置不同的最小高度
  const minH = !activeId.value ? 56 : 44 // 欢迎页使用更合适的单行高度
  
  // 计算高度，但限制最大高度为200px
  const calculatedHeight = Math.max(minH, Math.min(200, ta.scrollHeight))
  ta.style.height = `${calculatedHeight}px`
  
  // 如果内容高度超过设定的最大高度，启用滚动
  if (ta.scrollHeight > 200) {
    ta.style.overflowY = 'auto'
  } else {
    ta.style.overflowY = 'hidden'
  }
}

// 回车发送消息
const onComposerKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

// 滚动到输入框：优先聚焦英雄输入框，其次吸底输入框
const scrollToInput = () => {
  if (messages.value.length === 0 && composerRef.value) {
    composerRef.value.focus()
    return
  }
  if (inputContainer.value) {
    inputContainer.value.scrollIntoView({ behavior: 'smooth' })
    const input = inputContainer.value.querySelector('textarea') as HTMLTextAreaElement | null
    if (input) input.focus()
  }
}

// 改进的Markdown渲染函数，支持标题缩进
const renderMarkdown = (content: string): string => {
  try {
    // 防止空内容
    if (!content) return ''
    
    // 配置marked选项，启用更多功能
    marked.setOptions({
      gfm: true,
      breaks: true,
      // 使用类型断言解决TypeScript警告，同时保留功能
      headerIds: true,
      mangle: false,
    } as Parameters<typeof marked.setOptions>[0]);
    
    // 对文本进行安全转义，但保留markdown语法
    const escaped = content
      .replace(/&(?!amp;|lt;|gt;)/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
    
    // 使用marked解析为HTML
    const html = marked.parse(escaped) as string  // 添加类型断言

    // 使用DOMPurify净化HTML，保留足够的标签和属性
    const sanitized = DOMPurify.sanitize(html, {
      ALLOWED_TAGS: [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'a', 'ul', 'ol', 'li', 
        'b', 'i', 'strong', 'em', 'strike', 'code', 'pre', 'hr', 'br', 
        'div', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'blockquote',
        'span', 'img'
      ],
      ALLOWED_ATTR: ['href', 'target', 'title', 'class', 'id', 'style', 'src', 'alt'],
      ADD_ATTR: ['target'],
      FORBID_TAGS: ['style', 'script'],
      FORBID_ATTR: ['style', 'onerror', 'onload']
    })
    
    return sanitized
  } catch (error) {
    console.error('Markdown渲染错误:', error)
    return content || '' // 出错时返回原始内容
  }
}

onMounted(() => {
  nextTick(() => {
    autoResize()
    
    // 修正onMounted逻辑，确保activeId正确设置messages
    // 检查是否有活动会话，如果有则确保消息被加载
    if (activeId.value) {
      const activeConversation = conversations.value.find(conv => conv.id === activeId.value)
      if (activeConversation) {
        messages.value = [...activeConversation.messages]
      }
    }
  })
})

// 组件卸载时清理资源
onBeforeUnmount(() => {
  closeEventSource();
});
</script>

<style scoped>
/* 布局：保持满屏，使用全局背景 */
.llm-container {
  height: calc(100vh - 60px);
  width: 100%;
  position: relative;
  display: flex;
  overflow: hidden;
  background: transparent;
}

.layout {
  width: 100%;
  height: 100%;
  display: flex;
}

/* 侧边栏：增大内边距 */
.sidebar {
  width: 260px;
  background: transparent;
  border-right: 1px solid #e6e6e6;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  background-color: #ffffff;
}

.sidebar.collapsed { width: 64px; }

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px; /* 12px -> 16px */
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  gap: 8px;
}

.brand {
  font-weight: 600;
  color: #303133;
}

.actions {
  display: flex;
  gap: 6px;
}

/* 使用el-scrollbar替换原生滚动容器 */
.conversation-list-scrollbar {
  flex: 1;
  height: 0; /* 配合flex:1实现高度自适应 */
}

.conversation-list {
  padding: 16px; /* 8px -> 16px */
}

.conversation-empty {
  color: #909399;
  font-size: 13px;
  padding: 12px;
}

.conversation-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 10px; /* 略增内边距 */
  border-radius: 10px;
  cursor: pointer;
  margin-bottom: 6px;
  transition: background-color .2s, transform .15s;
}

.conversation-item:hover {
  background-color: #f5f7fa;
  transform: translateY(-1px);
}

.conversation-item.active {
  background-color: #ecf5ff;
  border: 1px solid #d9ecff;
}

.conv-icon {
  font-size: 16px;
  color: #409EFF;
  flex-shrink: 0;
}

.conv-meta {
  min-width: 0;
  flex: 1;
}

.conv-title {
  font-size: 13px;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conv-time {
  font-size: 12px;
  color: #909399;
}

/* 主内容区域 */
.main-content {
  flex: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
  background: transparent;
  /* 修复：不要隐藏溢出，否则 sticky 失效导致输入框悬浮 */
  overflow: visible;
}

/* 聊天区 */
.chat-messages-scrollbar { flex: 1; height: 0; }
.chat-messages {
  padding: 24px 100px 120px; /* 上右下内边距增大 */
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chat-messages.with-bottom-gap { padding-bottom: 140px; }

/* 欢迎屏幕（精简版） */
.welcome-container {
  max-width: 800px;
  margin: 0 auto;
  text-align: center;
  padding: 40px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.welcome-title {
  font-size: 2rem;
  font-weight: 800;
  margin-bottom: 10px;
  background: linear-gradient(90deg, #3352a3, #409EFF);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.welcome-subtitle {
  font-size: 1rem;
  color: #606266;
  margin-bottom: 28px;
}

/* 精简的功能卡片网格 */
.features-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 32px;
}

.feature-card {
  padding: 12px;
  border-radius: 8px;
  background-color: #f5f7fa;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.feature-card:hover {
  background-color: #ecf5ff;
  transform: translateY(-2px);
}

.feature-icon {
  font-size: 20px;
  color: #409EFF;
  margin-bottom: 8px;
}

.feature-text {
  width: 100%;
}

.feature-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
  margin-bottom: 4px;
}

.feature-description {
  color: #606266;
  font-size: 12px;
  line-height: 1.4;
}

/* 建议问题部分 */
.suggestions-section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
}

.suggestions-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.suggestion-card {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  cursor: pointer;
  background-color: #fff;
  transition: all 0.2s;
}

.suggestion-card:hover {
  background-color: #f5f7fa;
  border-color: #dcdfe6;
}

.suggestion-card-inner {
  padding: 10px 12px;
  font-size: 13px;
  color: #303133;
  text-align: left;
}

/* 操作按钮 */
.action-section {
  margin-top: 16px;
}

.new-chat-btn {
  padding: 10px 20px;
  font-size: 14px;
  border-radius: 6px;
}

/* 消息项样式 - 调整以适应新布局 */
.message-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 24px;
}

.user-message {
  flex-direction: row-reverse;
  animation: enterRight 220ms ease-out;
}

.ai-message {
  flex-direction: row;
  animation: enterLeft 220ms ease-out;
}

.message-content-wrapper {
  flex: 1;
  min-width: 0;
  display: flex;
}

.message-bubble {
  max-width: 78%;
  padding: 20px 24px; /* 减少水平内边距 */
  border-radius: 20px;
  box-shadow: 0 8px 22px rgba(0,0,0,0.06);
  border: 1px solid rgba(0,0,0,0.06);
  transform-origin: top left;
}

.bubble-ai {
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(4px);
}

.bubble-user {
  background: #ecf5ff;
  border-color: #d9ecff;
}

.user-message .message-content-wrapper {
  justify-content: flex-end;
}

.message-sender {
  font-weight: 600;
  font-size: 12px;
  color: #303133;
  margin-bottom: 4px;
}

.message-content {
  font-size: 14px;
  line-height: 1.7;
  color: #303133;
  overflow-wrap: break-word;
  word-break: break-word;
  margin-top: 12px; /* 添加上边距，与步骤组件分隔 */
}

.message-time {
  font-size: 11px;
  color: #909399;
  margin-top: 6px;
}

/* 入场动效 */
@keyframes enterLeft {
  from { opacity: 0; transform: translateX(-8px) scale(0.98); }
  to   { opacity: 1; transform: translateX(0) scale(1); }
}

@keyframes enterRight {
  from { opacity: 0; transform: translateX(8px) scale(0.98); }
  to   { opacity: 1; transform: translateX(0) scale(1); }
}

.chat-input-container {
  padding: 14px 24px 20px;
  background: transparent;
  border-top: none;
  position: sticky;
  bottom: 0;
  z-index: 5;
}

.hero-composer {
  width: 100%;
  max-width: 700px; /* 限制最大宽度 */
  margin: 18px auto 0;
  padding: 0 20px;
}

/* 输入卡片（大椭圆） */
.composer {
  position: relative;
  display: flex;
  align-items: flex-end;
  gap: 10px;
  width: 100%;
}

.composer-textarea {
  width: 100%;
  resize: none;
  outline: none;
  border: 1px solid #dcdfe6;
  padding: 16px 64px 16px 20px; /* 统一内边距 */
  border-radius: 22px; /* 适当调整圆角，使高度变化时看起来更协调 */
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(6px);
  box-shadow: 0 6px 18px rgba(0,0,0,0.06);
  font-size: 15px;
  line-height: 1.6;
  color: #303133;
  transition: box-shadow .2s, border-color .2s, background .2s;
  max-height: 200px; /* 最大高度限制 */
  overflow-y: hidden; /* 默认隐藏滚动条，超高时autoResize会改变这个属性 */
}

.composer-textarea:focus {
  border-color: #409EFF;
  box-shadow: 0 0 0 3px rgba(64,158,255,0.15);
  background: rgba(255,255,255,0.95);
}

.composer-send {
  position: absolute;
  right: 10px;
  bottom: 8px;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: none;
  background: linear-gradient(135deg, #409EFF, #66b1ff);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 6px 18px rgba(64,158,255,0.35);
  transition: transform .15s ease, box-shadow .2s ease, opacity .2s ease;
}

.composer-send:disabled {
  opacity: .5;
  cursor: not-allowed;
  box-shadow: none;
}

.composer-send:hover:not(:disabled) { transform: translateY(-1px); }
.composer-send:active:not(:disabled) { transform: translateY(0); }

.input-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
  text-align: right;
}

/* 快速建议 */
.quick-suggestions {
  padding: 0 16px 8px 16px;
}

.quick-suggestions-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quick-suggestion-chip {
  padding: 4px 10px;
  background-color: #f5f7fa;
  border: 1px solid #ebeef5;
  border-radius: 16px;
  font-size: 12px;
  color: #606266;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-suggestion-chip:hover {
  background-color: #ecf5ff;
  color: #409EFF;
  border-color: #d9ecff;
}

/* 浮动操作按钮 */
.floating-actions {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 10;
}

.clear-button {
  border-radius: 6px;
  font-size: 12px;
}

/* 侧边栏品牌美化 */
.brand-beauty {
  display: flex;
  align-items: center;
  gap: 10px;
}
.brand-badge {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409EFF, #66b1ff);
  color: #fff;
  font-weight: 700;
  font-size: 16px;
  display: grid;
  place-items: center;
  box-shadow: 0 4px 14px rgba(64, 158, 255, 0.3);
}
.brand-text { line-height: 1.1; }
.brand-name {
  font-weight: 800;
  letter-spacing: 1px;
  background: linear-gradient(90deg, #3352a3, #409EFF);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.brand-sub {
  font-size: 12px;
  color: #7a7f87;
}

/* 消息容器确保占满宽度 */
.messages-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 当消息为空时的引导文本 */
.empty-messages-guide {
  display: flex;
  justify-content: center;
  padding: 40px 0;
  color: #909399;
}

.guide-text {
  font-size: 16px;
  color: #909399;
  opacity: 0.8;
  background-color: #f9f9f9;
  padding: 12px 24px;
  border-radius: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

/* 增强处理步骤展示的样式 */
.processing-steps {
  margin-top: 8px;
  font-size: 12px;
  color: #606266;
  background: transparent;      /* 重置背景 */
  padding: 0;                   /* 重置内边距 */
  border-radius: 0;             /* 重置圆角 */
  animation: fadeIn 0.2s ease-in-out;
}

/* 避免外层再次增加卡片感 */
:deep(.processing-steps) {
  margin-top: 0;
  margin-bottom: 8px;
  background: transparent;
  padding: 0;
  border-radius: 0;
  max-width: 100%;
}

/* Markdown 样式 - 新增标题缩进样式 */
:deep(.markdown-body) {
  width: 100%;
}

:deep(.markdown-body h1),
:deep(.markdown-body h2),
:deep(.markdown-body h3),
:deep(.markdown-body h4),
:deep(.markdown-body h5),
:deep(.markdown-body h6) {
  position: relative;
  margin-top: 1em;
  margin-bottom: 0.5em;
  font-weight: 600;
  line-height: 1.25;
  overflow: visible;
}

:deep(.markdown-body h1) {
  font-size: 1.5em;
  padding-bottom: 0.3em;
  border-bottom: 1px solid rgba(0,0,0,0.07);
}

:deep(.markdown-body h2) {
  font-size: 1.3em;
  padding-bottom: 0.3em;
  border-bottom: 1px solid rgba(0,0,0,0.07);
  margin-left: 0.5em;
}

:deep(.markdown-body h3) {

margin-left: 1em;  font-size: 1.2em;

}  
:deep(.markdown-body h4) {
  font-size: 1.1em;
  margin-left: 1.5em;
}

:deep(.markdown-body h5) {
  font-size: 1em;
  margin-left: 2em;
}

:deep(.markdown-body h6) {
  font-size: 0.9em;
  margin-left: 2.5em;
  color: #6a737d;
}

:deep(.markdown-body ul),
:deep(.markdown-body ol) {
  padding-left: 2em;
  margin-top: 0.25em;
  margin-bottom: 0.25em;
}

:deep(.markdown-body li) {
  margin-bottom: 0.25em;
}

:deep(.markdown-body p) {
  margin-top: 0.5em;
  margin-bottom: 0.5em;
}

:deep(.markdown-body pre) {
  margin: 1em 0;
  padding: 1em;
  background-color: #f6f8fa;
  border-radius: 6px;
  overflow: auto;
}

:deep(.markdown-body code) {
  padding: 0.2em 0.4em;
  background-color: rgba(27, 31, 35, 0.05);
  border-radius: 3px;
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
}

:deep(.markdown-body pre code) {
  padding: 0;
  background-color: transparent;
}

/* 模型切换工具条 */
.composer-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-top: 6px;
}
.composer-toolbar.inline {
  margin-top: 8px;
}

.model-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-btn {
  padding: 4px 10px;
  font-size: 12px;
  border: 1px solid #dcdfe6;
  border-radius: 14px;
  background: #fff;
  color: #606266;
  cursor: pointer;
  transition: all .15s ease;
}
.model-btn:hover:not(:disabled) {
  background: #f5f7fa;
  border-color: #cfd6e4;
}
.model-btn.active {
  background: #ecf5ff;
  border-color: #d9ecff;
  color: #409EFF;
}
.model-btn:disabled {
  opacity: .5;
  cursor: not-allowed;
}
</style>