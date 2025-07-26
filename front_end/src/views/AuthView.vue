<script setup lang="ts">
import { ref, reactive, onMounted, watch, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { Lock, User, Message } from '@element-plus/icons-vue'
import { useRouter, useRoute } from 'vue-router'
import AuthService from '../services/AuthService'
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
// 添加用于取消异步操作的标志
const isComponentMounted = ref(true)

const encryptPassword = (password: string): string => {
    return CryptoJS.SHA256(password).toString(CryptoJS.enc.Hex)
}


const handleLogin = async () => {
    if (!loginFormRef.value || !isComponentMounted.value) return
    await loginFormRef.value.validate(async (valid, fields) => {
        if (!isComponentMounted.value) return
        if (valid) {
            try {
                loading.value = true
                
                const encryptedPassword = encryptPassword(loginForm.value.password)


                const response = await AuthService.login(
                    loginForm.value.username, 
                    encryptedPassword
                )
                
                if (!isComponentMounted.value) return

                const { access, refresh } = response
                

                
                localStorage.removeItem('access')
                localStorage.removeItem('refresh')

                authStore.setAuth({ access, refresh })

                await new Promise(resolve => setTimeout(resolve, 200))
                
                if (!isComponentMounted.value) return

                const storedToken = localStorage.getItem('access')
                if (storedToken !== access) {
                    console.error('Token存储异常，手动同步')
                    localStorage.setItem('access', access)
                }

                try {

                    
                    const userInfo = await AuthService.getUserInfo()
                    
                    if (!isComponentMounted.value) return
                    
                    if (userInfo) {
                        console.log('用户信息获取成功:', userInfo)
                        authStore.setUser(userInfo)
                        
                        ElMessage({
                            message: '登录成功',
                            type: 'success',
                            duration: 2000
                        })
                        
                        if (isComponentMounted.value) {
                            setTimeout(() => {
                                if (isComponentMounted.value) {
                                    const redirectPath = route.query.redirect?.toString() || '/'
                                    router.push(redirectPath)
                                }
                            }, 1000)
                        }
                    } else {
                        throw new Error('无法获取用户信息')
                    }
                } catch (userError) {
                    if (!isComponentMounted.value) return
                    
                    console.error('获取用户信息失败:', userError)
                    ElMessage({
                        message: '登录成功，但无法获取用户信息',
                        type: 'warning',
                        duration: 2000
                    })
                    
                    if (isComponentMounted.value) {
                        setTimeout(() => {
                            if (isComponentMounted.value) {
                                const redirectPath = route.query.redirect?.toString() || '/'
                                router.push(redirectPath)
                            }
                        }, 1000)
                    }
                }
            } catch (error) {
                if (!isComponentMounted.value) return
                
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
                
                if (isComponentMounted.value) {
                    ElMessage({
                        message: errorMessage,
                        type: 'error',
                        duration: 2000
                    })
                }
            } finally {
                if (isComponentMounted.value) {
                    loading.value = false
                }
            }
        } else {
            console.log('验证失败', fields)
            if (isComponentMounted.value) {
                ElMessage({
                    message: '请正确填写表单',
                    type: 'error',
                    duration: 2000
                })
            }
        }
    })
}

const handleRegister = async () => {
    if (!registerFormRef.value || !isComponentMounted.value) return
    await registerFormRef.value.validate(async (valid, fields) => {
        if (!isComponentMounted.value) return
        if (valid) {
            try {
                loading.value = true
                
                const encryptedPassword = encryptPassword(registerForm.value.password)

                await AuthService.register({
                    username: registerForm.value.username,
                    password: encryptedPassword,
                    email: registerForm.value.email
                })
                
                if (!isComponentMounted.value) return

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

                if (isComponentMounted.value) {
                    setTimeout(() => {
                        if (isComponentMounted.value) {
                            isLogin.value = true
                            router.replace({ path: '/login' })
                        }
                    }, 1000)
                }
            } catch (error) {
                if (!isComponentMounted.value) return
                
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
                
                if (isComponentMounted.value) {
                    ElMessage({
                        message: errorMessage,
                        type: 'error',
                        duration: 2000
                    })
                }
            } finally {
                if (isComponentMounted.value) {
                    loading.value = false
                }
            }
        } else {
            console.log('验证失败', fields)
            if (isComponentMounted.value) {
                ElMessage({
                    message: '请正确填写表单',
                    type: 'error',
                    duration: 2000
                })
            }
        }
    })
}

onMounted(async () => {
    isComponentMounted.value = true
    setViewMode()

    if (isComponentMounted.value) {
        const isValid = await authStore.verifyToken()
        if (!isComponentMounted.value) return
        
        if (!isValid) {
            const refreshSuccess = await authStore.refreshAccessToken()
            if (!isComponentMounted.value) return
            
            if (!refreshSuccess) {
                authStore.logout()
            }
        }
    }
})

onBeforeUnmount(() => {
    // 设置标志，防止异步操作在组件卸载后继续执行
    isComponentMounted.value = false

})
</script>

<template>
    <div class="user-container">
        <div class="auth-card" :class="{'login-form': isLogin, 'register-form': !isLogin}">
            <div class="image-side">
                <img src="/hit1.jpg" alt="校园风景" />
                <div class="image-overlay">
                    <div class="campus-logo">
                        <img src="/favicon256.ico" alt="校园标志"/>
                    </div>
                    <h2>校园慧感</h2>
                    <p>为您提供安全、便捷的校园服务</p>
                </div>
            </div>

            <div class="form-side">
                <div class="form-container">
                    <transition name="form-fade" mode="out-in">
                        <div v-if="isLogin" key="login" class="form-wrapper">
                            <h2>登录</h2>
                            <el-form ref="loginFormRef" :model="loginForm" :rules="loginRules" label-position="top">
                                <el-form-item label="用户名" prop="username">
                                    <el-input v-model="loginForm.username" placeholder="请输入用户名" :prefix-icon="User" />
                                </el-form-item>

                                <el-form-item label="密码" prop="password">
                                    <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" 
                                        :prefix-icon="Lock" show-password />
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

                        <div v-else key="register" class="form-wrapper">
                            <h2>注册</h2>
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
                    </transition>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.user-container {
    display: flex;
    justify-content: center;
    min-height: calc(100vh - 160px); /* 减去footer高度和上下间距 */
    overflow: hidden;
    padding: 0 40px 60px; /* 增加底部间距给footer留空间 */
    box-sizing: border-box;
    width: 100%;
    /* 移除 position: fixed，改为相对定位 */
    position: relative;
}

.auth-card {
    display: flex;
    width: 900px;
    height: 600px;
    max-width: 100%;
    margin-top: 30px;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
    transition: height 0.5s ease 0.1s, margin-top 0.3s ease 0.1s;
}

.image-side {
    position: relative;
    width: 45%;
    overflow: hidden;
    transition: height 0.2s ease 0.1s, width 0.2s ease;
}

.image-side img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.image-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(24, 78, 155, 0.7);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    color: white;
    padding: 20px;
    text-align: center;
}

.image-overlay h2 {
    font-size: 28px;
    margin: 15px 0;
}

.image-overlay p {
    font-size: 16px;
    opacity: 0.9;
}

.campus-logo {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    overflow: hidden;
    background-color: white;
    padding: 5px;
    margin-bottom: 20px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    display: flex;
    justify-content: center;
    align-items: center;
}

.campus-logo img {
    width: 90%;
    height: 90%;
    object-fit: contain;
}

.form-side {
    width: 55%;
    background-color: white;
    padding: 40px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    transition: height 0.3s ease 0.1s, padding 0.2s ease, width 0.3s ease;
}

.form-wrapper {
    max-width: 400px;
    width: 100%;
    margin: 0 auto;
}

.form-wrapper h2 {
    text-align: center;
    color: var(--el-color-primary);
    margin-bottom: 30px;
    font-size: 24px;
}

.submit-btn {
    width: 100%;
    padding: 12px 0;
    font-size: 16px;
    margin-top: 10px;
}

.forgot-password {
    text-align: right;
    margin: -5px 0 15px;
}

.toggle-view {
    margin-top: 20px;
    text-align: center;
    color: var(--el-text-color-secondary);
}

.form-container {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: height 0.6s ease 0.5s;
}

.form-fade-enter-active,
.form-fade-leave-active {
    transition: all 0.3s ease;
}

.form-fade-enter-from {
    opacity: 0;
    transform: translateX(50px);
}

.form-fade-leave-to {
    opacity: 0;
    transform: translateX(-50px);
}

@media (max-width: 768px) {
    .user-container {
        padding: 20px 20px 80px; /* 调整底部间距 */
        min-height: calc(100vh - 180px);
    }
    
    .auth-card {
        flex-direction: column;
        border-radius: 10px;
    }
    
    .image-side {
        width: 100%;
        height: 180px;
    }
    
    .form-side {
        width: 100%;
        padding: 25px 20px;
    }
    
    .image-overlay h2 {
        font-size: 24px;
        margin: 10px 0;
    }
    
    .campus-logo {
        width: 60px;
        height: 60px;
        min-height: 60px;
        margin-bottom: 10px;
        padding: 3px;
    }

    .auth-card.login-form {
        height: 570px;
        margin-top: 30px;
    }

    .auth-card.register-form {
        height: 700px;
        margin-top: 20px;
    }
}

@media (max-width: 480px) {

    .form-side {
        padding: 20px 15px;
    }
    
    .image-side {
        height: 150px;
    }
    
    .form-wrapper h2 {
        font-size: 20px;
        margin-bottom: 20px;
    }
    
    .campus-logo {
        width: 50px;
        height: 50px;
        min-height: 50px;
    }
    
    .image-overlay h2 {
        font-size: 20px;
    }
    
    .image-overlay p {
        font-size: 14px;
    }
}
</style>