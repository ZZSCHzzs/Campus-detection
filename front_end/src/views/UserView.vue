<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElLoading } from 'element-plus'
import { Plus, Lock, User, Message } from '@element-plus/icons-vue'
import { useRouter, useRoute } from 'vue-router'
import axios from '../axios'
import CryptoJS from 'crypto-js' // 添加加密库
import { useAuthStore } from '../stores/auth' // 引入认证store

// 获取认证store
const authStore = useAuthStore()

// 获取路由器实例用于导航
const router = useRouter()
const route = useRoute()

// 用于跟踪当前是登录还是注册视图
const isLogin = ref(true)

// 设置初始视图
const setViewMode = () => {
    if (route.query.mode === 'register') {
        isLogin.value = false
    } else {
        isLogin.value = true
    }
}

// 初始加载时设置视图
onMounted(() => {
    setViewMode()
})

// 监听路由查询参数的变化
watch(() => route.query.mode, (newMode) => {
    setViewMode()
}, { immediate: true })

// 切换登录/注册视图的方法
const toggleView = () => {
    isLogin.value = !isLogin.value
    // 更新URL中的查询参数，但不触发页面刷新
    const mode = isLogin.value ? 'login' : 'register'
    router.replace({ path: '/auth', query: { mode } })
}

// 登录表单的数据
const loginForm = ref({
    username: '',
    password: ''
})

// 注册表单的数据
const registerForm = ref({
    username: '',
    password: '',
    confirmPassword: '',
    email: ''
})

// 表单验证规则
const loginRules = reactive({
    username: [
        { required: true, message: '请输入用户名', trigger: 'blur' },
        { min: 3, max: 20, message: '长度在 3 到 20 个字符', trigger: 'blur' }
    ],
    password: [
        { required: true, message: '请输入密码', trigger: 'blur' },
        { min: 6, max: 20, message: '长度在 6 到 20 个字符', trigger: 'blur' }
    ]
})

const registerRules = reactive({
    username: [
        { required: true, message: '请输入用户名', trigger: 'blur' },
        { min: 3, max: 20, message: '长度在 3 到 20 个字符', trigger: 'blur' }
    ],
    password: [
        { required: true, message: '请输入密码', trigger: 'blur' },
        { min: 6, max: 20, message: '长度在 6 到 20 个字符', trigger: 'blur' }
    ],
    confirmPassword: [
        { required: true, message: '请再次输入密码', trigger: 'blur' },
        {
            validator: (rule, value, callback) => {
                if (value !== registerForm.value.password) {
                    callback(new Error('两次输入密码不一致'))
                } else {
                    callback()
                }
            },
            trigger: 'blur'
        }
    ],
    email: [
        { required: true, message: '请输入邮箱地址', trigger: 'blur' },
        { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
    ]
})

// 登录表单引用
const loginFormRef = ref()
// 注册表单引用
const registerFormRef = ref()

// 加载状态
const loading = ref(false)

// 密码加密函数
const encryptPassword = (password: string): string => {
    // 使用SHA-256加密密码
    return CryptoJS.SHA256(password).toString(CryptoJS.enc.Hex)
}

// Token相关功能
const refreshToken = async () => {
    try {
        const refresh = localStorage.getItem('refresh')
        if (!refresh) return null

        const response = await axios.post('/auth/jwt/refresh/', {
            refresh
        })

        const { access } = response.data
        localStorage.setItem('access', access)
        return access
    } catch (error) {
        console.error('刷新Token失败:', error)
        return null
    }
}

const verifyToken = async () => {
    try {
        const token = localStorage.getItem('access')
        if (!token) return false

        await axios.post('/auth/jwt/verify/', {
            token
        })
        return true
    } catch (error) {
        console.error('Token验证失败:', error)
        return false
    }
}

// 修改登录方法
const handleLogin = async () => {
    if (!loginFormRef.value) return
    await loginFormRef.value.validate(async (valid, fields) => {
        if (valid) {
            try {
                loading.value = true
                // 加密密码
                const encryptedPassword = encryptPassword(loginForm.value.password)

                // 发送登录请求到更新的JWT API端点
                const response = await axios.post('/auth/jwt/create/', {
                    username: loginForm.value.username,
                    password: encryptedPassword
                })

                // 处理JWT登录响应
                const { access, refresh } = response.data

                // 使用store保存认证信息
                authStore.setAuth({ access, refresh })

                // 获取用户信息
                try {
                    const userResponse = await axios.get('/auth/users/me/', {
                        headers: {
                            Authorization: `Bearer ${access}`
                        }
                    })
                    
                    console.log('获取到的用户信息:', userResponse.data)
                    
                    // 确保用户数据至少包含用户名
                    if (!userResponse.data.username) {
                        console.error('API返回的用户数据缺少username字段')
                        userResponse.data.username = loginForm.value.username
                    }
                    
                    // 使用store保存用户信息
                    authStore.setUser(userResponse.data)
                    
                    // 验证存储是否成功
                    console.log('存储后的用户信息:', authStore.user)
                } catch (userError) {
                    console.error('获取用户信息失败:', userError)
                    // 如果获取用户信息失败，至少保存用户名
                    authStore.setUser({ 
                        username: loginForm.value.username,
                        role: 'user' // 默认角色
                    })
                }

                ElMessage({
                    message: '登录成功',
                    type: 'success',
                    duration: 2000
                })

                // 延迟后跳转到首页或其他页面
                setTimeout(() => {
                    router.push('/')
                }, 1000)
            } catch (error) {
                console.error('登录失败:', error)
                ElMessage({
                    message: error.response?.data?.detail || '登录失败，请稍后再试',
                    type: 'error',
                    duration: 2000
                })
            } finally {
                loading.value = false
            }
        } else {
            console.log('验证失败', fields)
            ElMessage({
                message: '请正确填写表单',
                type: 'error',
                duration: 2000
            })
        }
    })
}

// 修改注册方法
const handleRegister = async () => {
    if (!registerFormRef.value) return
    await registerFormRef.value.validate(async (valid, fields) => {
        if (valid) {
            try {
                loading.value = true
                // 加密密码
                const encryptedPassword = encryptPassword(registerForm.value.password)

                // 发送注册请求到更新的API端点
                const response = await axios.post('/auth/users/', {
                    username: registerForm.value.username,
                    password: encryptedPassword,
                    email: registerForm.value.email
                })

                ElMessage({
                    message: '注册成功，请登录',
                    type: 'success',
                    duration: 2000
                })

                // 清空表单并切换到登录视图
                registerForm.value = {
                    username: '',
                    password: '',
                    confirmPassword: '',
                    email: ''
                }

                // 延迟后切换到登录视图
                setTimeout(() => {
                    isLogin.value = true
                }, 1000)
            } catch (error) {
                console.error('注册失败:', error)
                const errorMessage = error.response?.data?.username?.[0] ||
                    error.response?.data?.email?.[0] ||
                    error.response?.data?.password?.[0] ||
                    error.response?.data?.detail ||
                    '注册失败，请稍后再试'
                ElMessage({
                    message: errorMessage,
                    type: 'error',
                    duration: 2000
                })
            } finally {
                loading.value = false
            }
        } else {
            console.log('验证失败', fields)
            ElMessage({
                message: '请正确填写表单',
                type: 'error',
                duration: 2000
            })
        }
    })
}

// 在组件挂载时检查和刷新Token
onMounted(async () => {
    setViewMode()

    // 使用store验证token
    const isValid = await authStore.verifyToken()
    if (!isValid) {
        // 如果当前Token无效，尝试刷新
        const refreshSuccess = await authStore.refreshAccessToken()
        if (!refreshSuccess) {
            // 如果刷新也失败，清除认证信息
            authStore.logout()
        }
    }
})
</script>

<template>
    <div class="user-container">
        <el-card class="login-card" :body-style="{ padding: '0px' }">
            <div class="card-header">
                <h2>{{ isLogin ? '登录' : '注册' }}</h2>
            </div>

            <!-- 登录表单 -->
            <div v-if="isLogin" class="form-container">
                <el-form ref="loginFormRef" :model="loginForm" :rules="loginRules" label-position="top">
                    <el-form-item label="用户名" prop="username">
                        <el-input v-model="loginForm.username" placeholder="请输入用户名" :prefix-icon="User" />
                    </el-form-item>

                    <el-form-item label="密码" prop="password">
                        <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" :prefix-icon="Lock"
                            show-password />
                    </el-form-item>

                    <el-form-item>
                        <el-button type="primary" class="submit-btn" @click="handleLogin" :loading="loading">
                            {{ loading ? '登录中...' : '登录' }}
                        </el-button>
                    </el-form-item>
                </el-form>

                <div class="toggle-view">
                    还没有账号？<el-button type="text" @click="toggleView">立即注册</el-button>
                </div>
            </div>

            <!-- 注册表单 -->
            <div v-else class="form-container">
                <el-form ref="registerFormRef" :model="registerForm" :rules="registerRules" label-position="top">
                    <el-form-item label="用户名" prop="username">
                        <el-input v-model="registerForm.username" placeholder="请输入用户名" :prefix-icon="User" />
                    </el-form-item>

                    <el-form-item label="邮箱" prop="email">
                        <el-input v-model="registerForm.email" placeholder="请输入邮箱" :prefix-icon="Message" />
                    </el-form-item>

                    <el-form-item label="密码" prop="password">
                        <el-input v-model="registerForm.password" type="password" placeholder="请输入密码"
                            :prefix-icon="Lock" show-password />
                    </el-form-item>

                    <el-form-item label="确认密码" prop="confirmPassword">
                        <el-input v-model="registerForm.confirmPassword" type="password" placeholder="请再次输入密码"
                            :prefix-icon="Lock" show-password />
                    </el-form-item>

                    <el-form-item>
                        <el-button type="primary" class="submit-btn" @click="handleRegister" :loading="loading">
                            {{ loading ? '注册中...' : '注册' }}
                        </el-button>
                    </el-form-item>
                </el-form>

                <div class="toggle-view">
                    已有账号？<el-button type="text" @click="toggleView">立即登录</el-button>
                </div>
            </div>
        </el-card>
    </div>
</template>

<style scoped>
.user-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 90vh;
    background-color: #ffffff;
}

.login-card {
    width: 450px;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.card-header {
    padding: 20px;
    background-color: var(--el-color-primary-light-8);
    text-align: center;
    color: var(--el-color-primary);
    border-bottom: 1px solid var(--el-border-color-light);
}

.form-container {
    padding: 30px;
}

.submit-btn {
    width: 100%;
    padding: 12px 0;
    font-size: 16px;
    margin-top: 10px;
}

.toggle-view {
    margin-top: 20px;
    text-align: center;
    color: var(--el-text-color-secondary);
}
</style>