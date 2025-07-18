// 连接WebSocket服务器
const socket = io();

// 当前配置
let currentConfig = {
    mode: 'pull',
    interval: 1,
    preload_model: true,
    save_image: true,
    cameras: {},
    server_url: 'https://smarthit.top/api/upload/'
};

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    // 加载当前配置
    loadConfig();
    
    // 绑定表单提交事件
    document.getElementById('config-form').addEventListener('submit', function(e) {
        e.preventDefault();
        saveConfig();
    });
    
    // 绑定重置按钮
    document.getElementById('reset-config').addEventListener('click', function() {
        loadConfig();
    });
    
    // 绑定添加摄像头按钮
    document.getElementById('add-camera').addEventListener('click', function() {
        addCameraField();
    });
    
    // 模式变更监听
    document.querySelectorAll('input[name="mode"]').forEach(function(radio) {
        radio.addEventListener('change', function() {
            toggleIntervalVisibility();
        });
    });
    
    // 初始化切换间隔设置可见性
    toggleIntervalVisibility();
    
    // 配置更新成功监听
    socket.on('config_updated', function(data) {
        if (data.success) {
            showAlert('配置已成功保存，部分更改可能需要重启系统才能生效。', 'success');
        } else {
            showAlert('配置保存失败：' + (data.message || '未知错误'), 'danger');
        }
    });
});

// 加载当前配置
function loadConfig() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            // 更新当前配置
            currentConfig.mode = data.mode || 'push';
            
            // 设置表单值
            const modeElement = document.getElementById('mode-' + currentConfig.mode);
            if (modeElement) {
                modeElement.checked = true;
            } else {
                // 默认选择被动模式
                document.getElementById('mode-push').checked = true;
            }
            
            document.getElementById('pull-interval').value = currentConfig.interval || 1;
            document.getElementById('preload-model').checked = currentConfig.preload_model !== false;
            document.getElementById('save-image').checked = currentConfig.save_image !== false;
            document.getElementById('server-url').value = currentConfig.server_url || 'https://smarthit.top/api/upload/';
            
            // 加载摄像头配置
            loadCameras(data.cameras || {});
            
            // 更新UI
            toggleIntervalVisibility();
        })
        .catch(error => {
            console.error('加载配置失败:', error);
            showAlert('加载配置失败，请刷新页面重试。', 'danger');
        });
}

// 加载摄像头配置
function loadCameras(cameras) {
    const container = document.getElementById('cameras-container');
    container.innerHTML = '';
    
    if (Object.keys(cameras).length === 0) {
        // 如果没有摄像头，添加一个空白配置
        addCameraField();
        return;
    }
    
    // 添加每个摄像头配置字段
    for (const [id, url] of Object.entries(cameras)) {
        addCameraField(id, url);
    }
}

// 添加摄像头配置字段
function addCameraField(id = '', url = '') {
    const container = document.getElementById('cameras-container');
    const index = container.children.length;
    
    const cameraDiv = document.createElement('div');
    cameraDiv.className = 'camera-config-item';
    cameraDiv.innerHTML = `
        <button type="button" class="btn-close remove-camera" aria-label="删除"></button>
        <div class="row">
            <div class="col-md-3">
                <div class="mb-3">
                    <label class="form-label">摄像头ID</label>
                    <input type="number" class="form-control camera-id" value="${id}" min="1" required>
                </div>
            </div>
            <div class="col-md-9">
                <div class="mb-3">
                    <label class="form-label">摄像头URL</label>
                    <input type="text" class="form-control camera-url" value="${url}" required>
                    <div class="form-text">例如: http://192.168.1.100:81</div>
                </div>
            </div>
        </div>
    `;
    
    container.appendChild(cameraDiv);
    
    // 绑定删除按钮
    cameraDiv.querySelector('.remove-camera').addEventListener('click', function() {
        container.removeChild(cameraDiv);
    });
}

// 保存配置
function saveConfig() {
    // 收集表单数据
    const config = {
        mode: document.querySelector('input[name="mode"]:checked').value,
        interval: parseFloat(document.getElementById('pull-interval').value),
        preload_model: document.getElementById('preload-model').checked,
        save_image: document.getElementById('save-image').checked,
        server_url: document.getElementById('server-url').value,
        cameras: {}
    };
    
    // 收集摄像头配置
    const cameraItems = document.querySelectorAll('.camera-config-item');
    cameraItems.forEach(function(item) {
        const id = item.querySelector('.camera-id').value.trim();
        const url = item.querySelector('.camera-url').value.trim();
        
        if (id && url) {
            config.cameras[id] = url;
        }
    });
    
    // 发送到服务器
    fetch('/api/config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // 更新当前配置
            currentConfig = config;
            
            if (data.restart_required) {
                showAlert('配置已保存，但需要重启系统才能完全生效。', 'warning', true);
            } else {
                showAlert('配置已成功保存并应用。', 'success');
            }
        } else {
            showAlert('保存配置失败：' + (data.message || '未知错误'), 'danger');
        }
    })
    .catch(error => {
        console.error('保存配置失败:', error);
        showAlert('保存配置失败，请重试。', 'danger');
    });
}

// 切换间隔设置可见性
function toggleIntervalVisibility() {
    const mode = document.querySelector('input[name="mode"]:checked').value;
    const intervalContainer = document.getElementById('interval-container');
    
    if (mode === 'pull') {
        intervalContainer.style.display = 'block';
    } else {
        intervalContainer.style.display = 'none';
    }
}

// 显示提示消息
function showAlert(message, type, isImportant = false) {
    // 检查是否已存在提示
    let alertElement = document.querySelector('.alert-floating');
    
    if (!alertElement) {
        alertElement = document.createElement('div');
        alertElement.className = `alert alert-${type} alert-floating`;
        alertElement.style.position = 'fixed';
        alertElement.style.top = '20px';
        alertElement.style.right = '20px';
        alertElement.style.zIndex = '9999';
        alertElement.style.maxWidth = '400px';
        document.body.appendChild(alertElement);
    } else {
        alertElement.className = `alert alert-${type} alert-floating`;
    }
    
    alertElement.textContent = message;
    
    // 如果是重要提示，添加重启按钮
    if (isImportant) {
        const restartBtn = document.createElement('button');
        restartBtn.className = 'btn btn-sm btn-danger ms-2';
        restartBtn.textContent = '重启系统';
        restartBtn.onclick = function() {
            if (confirm('确定要重启系统吗？这将中断当前的所有操作。')) {
                // 发送重启请求
                fetch('/api/restart', { method: 'POST' })
                .then(response => {
                    showAlert('系统重启命令已发送，请稍候...', 'info');
                })
                .catch(error => {
                    showAlert('重启请求失败: ' + error, 'danger');
                });
            }
        };
        
        alertElement.appendChild(document.createElement('br'));
        alertElement.appendChild(restartBtn);
    }
    
    // 自动关闭（非重要提示）
    if (!isImportant) {
        setTimeout(function() {
            alertElement.remove();
        }, 5000);
    }
}
