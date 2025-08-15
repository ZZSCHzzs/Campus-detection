/**
 * LLM 服务模块
 * 提供与 LLM 后端 API 通信的功能
 */
import { http } from '../network';

// 聊天消息格式
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

// 聊天历史
export type ChatHistory = ChatMessage[];

// API 响应类型
interface LLMChatResponse {
  response?: string;
  message?: string;
  status?: string;
}

interface LLMRecommendationResponse {
  data?: any[];
  message?: string;
  status?: string;
}

// LLM 基础 URL - 本地开发用
const LLM_BASE_URL = 'http://127.0.0.1:8000/api/llm';

/**
 * 发送聊天消息（非流式）
 * @param message 用户消息
 * @param history 聊天历史
 * @returns Promise<string> AI响应
 */
export async function sendChatMessage(message: string, history: ChatHistory = []): Promise<string> {
  try {
    // 添加类型断言解决属性访问问题
    const response = await http.post<LLMChatResponse>(`${LLM_BASE_URL}/chat/`, { message, history });
    return response.response || '';
  } catch (error) {
    console.error('LLM API请求失败:', error);
    throw error;
  }
}

/**
 * 创建SSE流式聊天连接
 * 完全重构，匹配后端响应格式，并增强思考过程数据处理
 */
export function createChatStream(
  message: string,
  history: ChatHistory = [],
  onMessage: (data: any) => void,
  onError: (error: any) => void,
  onEnd: () => void,
  modelType?: string
): AbortController {
  // 创建中止控制器
  const controller = new AbortController();
  const signal = controller.signal;

  // 发送请求
  (async () => {
    try {
      console.log('发送LLM请求', { message, history, modelType });

      const bodyPayload: any = { message, history };
      if (modelType) bodyPayload.model_type = modelType;

      const response = await fetch(`${LLM_BASE_URL}/chat/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify(bodyPayload),
        credentials: 'include',
        signal
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // 使用ReadableStream处理流式响应
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('无法读取响应流');
      }

      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      
      // 处理流式响应
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        // 解码二进制数据
        buffer += decoder.decode(value, { stream: true });
        
        // 处理完整的SSE消息 - 支持多种换行符
        const lines = buffer.split(/\n+/);
        buffer = lines.pop() || ''; // 保留可能不完整的最后一行
        
        for (const line of lines) {
          // 识别SSE数据行
          if (line.startsWith('data:')) {
            const data = line.substring(5).trim();
            
            // 检查是否为结束标记
            if (data === '[DONE]') {
              onEnd();
              return;
            }
            
            try {
              // 解析JSON数据并处理
              const parsedData = JSON.parse(data);
              
              // 特殊处理思考过程数据，确保前端能有效展示
              if (parsedData.type === 'thought' && parsedData.data) {
                // 确保思考数据能被正确传递和展示
                try {
                  if (typeof parsedData.data === 'string') {
                    // 如果是字符串，尝试解析为JSON
                    const jsonData = JSON.parse(parsedData.data);
                    parsedData.data = jsonData;
                  }
                } catch (e) {
                  // 如果解析失败，保持原样
                  console.debug('思考数据解析失败，保持原始格式', e);
                }
              }
              
              // 添加步骤类型或状态的提示消息
              if (!parsedData.message && parsedData.type) {
                switch (parsedData.type) {
                  case 'chain_start':
                    parsedData.message = '开始处理请求...';
                    break;
                  case 'chain_end':
                    parsedData.message = '处理完成';
                    break;
                  case 'thought':
                    parsedData.message = '思考中...';
                    break;
                }
              }
              
              // 立即调用回调，确保前端能实时更新
              onMessage(parsedData);
            } catch (e) {
              console.warn('SSE数据解析失败', e, data);
              // 即使解析失败也尝试传递原始文本
              onMessage({ type: 'content', text: data });
            }
          }
        }
      }
      
      // 流已读取完毕
      onEnd();
    } catch (error) {
      // 忽略中止错误
      if ((error as Error).name !== 'AbortError') {
        console.error('SSE流处理错误:', error);
        onError(error);
      }
    }
  })();

  return controller;
}

/**
 * 获取区域信息
 * 使用通用 HTTP 工具
 */
export async function getAreaInfo(areaId: number): Promise<any> {
  try {
    return await http.get(`/api/areas/${areaId}/`);
  } catch (error) {
    console.error('获取区域信息失败:', error);
    throw error;
  }
}

/**
 * 获取推荐区域
 * 使用通用 HTTP 工具
 */
export async function getSuggestedAreas(limit: number = 5): Promise<any[]> {
  try {
    // 添加类型断言解决属性访问问题
    const response = await http.get<LLMRecommendationResponse>(`${LLM_BASE_URL}/recommendations/user/`, { limit });
    return response.data || [];
  } catch (error) {
    console.error('获取推荐区域失败:', error);
    throw error;
  }
}

/**
 * 获取LLM模型信息
 * 使用通用 HTTP 工具
 */
export async function getModelInfo(): Promise<any> {
  try {
    return await http.get(`${LLM_BASE_URL}/model-info/`);
  } catch (error) {
    console.error('获取模型信息失败:', error);
    throw error;
  }
}

