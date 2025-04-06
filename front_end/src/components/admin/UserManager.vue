<template>
  <base-manager
    title="用户管理"
    resource-name="users"
    item-name="用户"
    :columns="columns"
    :default-form-data="defaultFormData"
  >
    <template #form="{ form, mode }">
      <el-form :model="form" label-width="x100p">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
        
        <el-form-item label="手机号">
          <el-input v-model="form.phone" placeholder="请输入手机号" />
        </el-form-item>
        
        <el-form-item label="角色">
          <el-select v-model="form.role" placeholder="请选择角色">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        
        <el-form-item v-if="mode === 'add'" label="密码" required>
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
      </el-form>
    </template>
  </base-manager>
</template>

<script setup>
import { ref } from 'vue'
import BaseManager from './BaseManager.vue'

// 表格列定义
const columns = [
  { prop: 'username', label: '用户名', width: '200' },
  { prop: 'email', label: '邮箱', width: '250' },
  { prop: 'phone', label: '手机号', width: '200' },
  { prop: 'role', label: '权限', width: '150', 
    formatter: (row) => row.role === 'admin' ? '管理员' : '普通用户' },
  { prop: 'register_time', label: '注册时间',
    formatter: (row) => new Date(row.register_time).toLocaleString() }
]

// 默认表单数据
const defaultFormData = {
  username: '',
  email: '',
  phone: '',
  role: 'user',
  password: ''
}
</script>
