<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Lock, User, Message } from '@element-plus/icons-vue'
import { useRouter, useRoute } from 'vue-router'
import authApi from '../services/authApi'
import CryptoJS from 'crypto-js' 
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

const router = useRouter()
const route = useRoute()

const isLogin = ref(true)

const setViewMode = () => {
    isLogin.value = route.path !== '/register';
}

onMounted(() => {
    setViewMode()
})

watch(() => route.path, () => {
    setViewMode()
}, { immediate: true })

const toggleView = () => {
    isLogin.value = !isLogin.value
    
    const path = isLogin.value ? '/login' : '/register'
    const redirect = route.query.redirect
    router.replace({ 
        path: path, 
        query: redirect ? { redirect: redirect.toString() } : {} 
    })
}

const loginForm = ref({
    username: '',
    password: ''
})

const registerForm = ref({
    username: '',
    password: '',
    confirmPassword: '',
    email: ''
})

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

const loginFormRef = ref()

const registerFormRef = ref()

const loading = ref(false)

const encryptPassword = (password: string): string => {
    return CryptoJS.SHA256(password).toString(CryptoJS.enc.Hex)
}

const refreshToken = async () => {
    try {
        const refresh = localStorage.getItem('refresh')
        if (!refresh) return null

        const response = await authApi.refreshToken({
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

        await authApi.verifyToken({
            token
        })
        return true
    } catch (error) {
        console.error('Token验证失败:', error)
        return false
    }
}

const handleLogin = async () => {
    if (!loginFormRef.value) return
    await loginFormRef.value.validate(async (valid, fields) => {
        if (valid) {
            try {
                loading.value = true
                
                const encryptedPassword = encryptPassword(loginForm.value.password)

                console.log('尝试登录...')
                const response = await authApi.login(
                    loginForm.value.username, 
                    encryptedPassword
                )

                const { access, refresh } = response.data
                
                console.log('登录成功，设置token')
                
                localStorage.removeItem('access')
                localStorage.removeItem('refresh')
                
                
                authStore.setAuth({ access, refresh })

                
                await new Promise(resolve => setTimeout(resolve, 200))
                
                
                const storedToken = localStorage.getItem('access')
                if (storedToken !== access) {
                    console.error('Token存储异常，手动同步')
                    localStorage.setItem('access', access)
                }

                try {
                    console.log('获取用户信息中...')
                    
                    const userInfo = await authApi.getUserInfo()
                    
                    if (userInfo) {
                        console.log('用户信息获取成功:', userInfo)
                        authStore.setUser(userInfo)
                        
                        ElMessage({
                            message: '登录成功',
                            type: 'success',
                            duration: 2000
                        })
                        
                        setTimeout(() => {
                            const redirectPath = route.query.redirect?.toString() || '/'
                            router.push(redirectPath)
                        }, 1000)
                    } else {
                        throw new Error('无法获取用户信息')
                    }
                } catch (userError) {
                    console.error('获取用户信息失败:', userError)
                    ElMessage({
                        message: '登录成功，但无法获取用户信息',
                        type: 'warning',
                        duration: 2000
                    })
                    
                    setTimeout(() => {
                        const redirectPath = route.query.redirect?.toString() || '/'
                        router.push(redirectPath)
                    }, 1000)
                }
            } catch (error) {
                console.error('登录失败:', error)
                let errorMessage = '登录失败，请检查用户名和密码'
                
                if (error.response) {
                    if (error.response.data?.detail) {
                        errorMessage = error.response.data.detail
                    } else if (error.response.status === 401) {
                        errorMessage = '用户名或密码错误'
                    } else if (error.response.status === 400) {
                        errorMessage = '请求参数错误，请检查输入'
                    }
                }
                
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

const handleRegister = async () => {
    if (!registerFormRef.value) return
    await registerFormRef.value.validate(async (valid, fields) => {
        if (valid) {
            try {
                loading.value = true
                
                const encryptedPassword = encryptPassword(registerForm.value.password)

                await authApi.register({
                    username: registerForm.value.username,
                    password: encryptedPassword,
                    email: registerForm.value.email
                })

                ElMessage({
                    message: '注册成功，请登录',
                    type: 'success',
                    duration: 2000
                })

                loginForm.value.username = registerForm.value.username
                
                registerForm.value = {
                    username: '',
                    password: '',
                    confirmPassword: '',
                    email: ''
                }

                setTimeout(() => {
                    isLogin.value = true
                    router.replace({ path: '/login' })
                }, 1000)
            } catch (error) {
                console.error('注册失败:', error)
                
                let errorMessage = '注册失败，请稍后再试'
                
                if (error.response?.data) {
                    const errors = error.response.data
                    
                    if (errors.username && errors.username.length > 0) {
                        errorMessage = `用户名: ${errors.username[0]}`
                    } else if (errors.email && errors.email.length > 0) {
                        errorMessage = `邮箱: ${errors.email[0]}`
                    } else if (errors.password && errors.password.length > 0) {
                        errorMessage = `密码: ${errors.password[0]}`
                    } else if (errors.detail) {
                        errorMessage = errors.detail
                    }
                }
                
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

onMounted(async () => {
    setViewMode()

    const isValid = await authStore.verifyToken()
    if (!isValid) {
        const refreshSuccess = await authStore.refreshAccessToken()
        if (!refreshSuccess) {
            authStore.logout()
        }
    }
})
</script>

<template>
    <div class="user-container">
        <div class="flip-container" :class="{ 'flipped': !isLogin }">
            <div class="flipper">

                <div class="front">
                    <el-card class="login-card" :body-style="{ padding: '0px' }">
                        <div class="card-header">
                            <h2>登录</h2>
                        </div>
                        <div class="form-container">
                            <div class="welcome-section">
                                <div class="campus-logo">
                                    <img src="/favicon256.ico" alt="校园标志"/>
                                </div>
                                <div class=welcome-text>
                                    <h3>欢迎回来</h3>
                                    <p>校园检测系统将为您提供安全、便捷的服务</p>
                                </div>
                            </div>
                            
                            <el-form ref="loginFormRef" :model="loginForm" :rules="loginRules" label-position="top">
                                <el-form-item label="用户名" prop="username">
                                    <el-input v-model="loginForm.username" placeholder="请输入用户名" :prefix-icon="User" />
                                </el-form-item>

                                <el-form-item label="密码" prop="password">
                                    <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" :prefix-icon="Lock"
                                        show-password />
                                </el-form-item>


                                <div class="forgot-password">
                                    <el-button type="text" size="small">忘记密码?</el-button>
                                </div>

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
                    </el-card>
                </div>


                <div class="back">
                    <el-card class="login-card" :body-style="{ padding: '0px' }">
                        <div class="card-header">
                            <h2>注册</h2>
                        </div>
                        <div class="form-container">
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
            </div>
        </div>
    </div>
</template>

<style scoped>
.user-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 90vh;
    background-color: #ffffff;
    padding: 15px;
}

/* 翻转容器 */
.flip-container {
    perspective: 1000px;
    width: 450px;
    height: 600px;
    max-width: 100%;
}

/* 翻转动画类 */
.flip-container.flipped .flipper {
    transform: rotateY(180deg);
}

/* 非翻转状态的动画 - 新增 */
.flip-container:not(.flipped) {
    animation: pulse 0.5s ease-out;
}

/* 翻转器 */
.flipper {
    transition: 0.4s;
    transform-style: preserve-3d;
    position: relative;
    width: 100%;
    height: 100%;
}

/* 前后两面共同样式 */
.front, .back {
    backface-visibility: hidden;
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
}

/* 前面样式 */
.front {
    z-index: 2;
    transform: rotateY(0deg);
}

/* 背面样式 */
.back {
    transform: rotateY(180deg);
}

.login-card {
    width: 100%;
    height: 100%;
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

/* 添加一些动画效果强调 */
.flip-container.flipped {
    animation: pulse 0.5s ease-out;
}

@keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.03); }
    100% { transform: scale(1); }
}

/* 确保表单元素在翻转时更流畅 */
.form-container {
    transition: opacity 0.3s;
}

.flipped .front .form-container {
    opacity: 0;
}

.flipped .back .form-container {
    opacity: 1;
}

/* 新增样式以优化登录表单空间 */
.welcome-section {
    text-align: center;
    margin-bottom: 20px;
}

.campus-logo {
    margin: 0 auto 15px;
    width: 80px;
    height: 80px;
    border-radius: 50%;
    overflow: hidden;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.campus-logo img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.welcome-text h3 {
    color: var(--el-color-primary);
    margin-bottom: 8px;
    font-size: 18px;
}

.welcome-text p {
    color: var(--el-text-color-secondary);
    font-size: 14px;
    line-height: 1.5;
    margin-bottom: 15px;
}

.forgot-password {
    text-align: right;
    margin: -5px 0 15px;
}

/* 调整登录表单间距，让内容更均匀分布 */
.front .form-container .el-form-item {
    margin-bottom: 20px;
}

.front .submit-btn {
    margin-top: 5px;
}

.toggle-view {
    margin-top: 15px;
    text-align: center;
    color: var(--el-text-color-secondary);
}

/* 确保前后两面保持对齐 */
.form-container {
    padding: 20px 30px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    height: calc(100% - 60px); /* 减去header高度 */
}

/* 移动端适配样式 */
@media (max-width: 768px) {
    .flip-container {
        width: 100%;
        height: auto;
        min-height: 550px;
    }
    
    .login-card {
        height: auto;
        min-height: 550px;
    }
    
    .form-container {
        padding: 15px 20px;
    }
    
    .campus-logo {
        width: 60px;
        height: 60px;
    }
    
    .welcome-text h3 {
        font-size: 16px;
    }
    
    .welcome-text p {
        font-size: 12px;
    }
    
    .card-header {
        padding: 15px;
    }
    
    .submit-btn {
        padding: 10px 0;
    }
    
    .el-form-item {
        margin-bottom: 15px !important;
    }
}

/* 超小屏幕适配 */
@media (max-width: 480px) {
    .user-container {
        padding: 10px;
        min-height: 85vh;
    }
    
    .flip-container {
        min-height: 520px;
    }
    
    .login-card {
        min-height: 520px;
    }
    
    .form-container {
        padding: 10px 15px;
    }
    
    .card-header h2 {
        font-size: 18px;
    }
    
    .campus-logo {
        width: 50px;
        height: 50px;
        margin-bottom: 10px;
    }
    
    .welcome-section {
        margin-bottom: 10px;
    }
    
    .toggle-view {
        font-size: 14px;
    }
    
    /* 确保输入框在小屏幕上更易点击 */
    :deep(.el-input__inner) {
        height: 40px;
        font-size: 14px;
    }
    
    :deep(.el-form-item__label) {
        font-size: 14px;
        padding-bottom: 4px;
    }
}

/* 横屏模式适配 */
@media (max-height: 600px) and (orientation: landscape) {
    .user-container {
        padding: 5px;
    }
    
    .flip-container {
        height: auto;
        min-height: 450px;
    }
    
    .login-card {
        height: auto;
        min-height: 450px;
    }
    
    .welcome-section {
        margin-bottom: 5px;
    }
    
    .campus-logo {
        width: 40px;
        height: 40px;
        margin-bottom: 5px;
    }
    
    .welcome-text h3 {
        margin-bottom: 2px;
        font-size: 14px;
    }
    
    .welcome-text p {
        font-size: 12px;
        margin-bottom: 5px;
    }
    
    .form-container .el-form-item {
        margin-bottom: 8px !important;
    }
    
    .forgot-password {
        margin: -3px 0 8px;
    }
}
</style>