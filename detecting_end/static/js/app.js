// 检查socket是否已经被定义，防止重复声明
let socket;
if (typeof socket === 'undefined') {
    // 连接WebSocket服务器
    socket = io();
    console.log('Socket已初始化');
} else {
    console.log('Socket已存在，跳过重新初始化');
}

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    // 连接状态处理
    socket.on('connect', function() {
        console.log('已连接到服务器');
        const serverStatus = document.getElementById('server-status');
        if (serverStatus) {
            serverStatus.textContent = '已连接';
            serverStatus.className = 'badge bg-success';
        }
        
        // 请求系统状态
        socket.emit('request_status');
    });
    
    socket.on('disconnect', function() {
        console.log('与服务器断开连接');
        const serverStatus = document.getElementById('server-status');
        if (serverStatus) {
            serverStatus.textContent = '已断开';
            serverStatus.className = 'badge bg-danger';
        }
    });
    
    // 系统状态更新
    socket.on('system_status', function(data) {
        updateSystemStatus(data);
    });
    
    // 系统消息
    socket.on('system_message', function(data) {
        addDetectionLog({
            time: getCurrentTime(),
            camera: 'System',
            count: '-',
            status: data.message,
            type: 'info'
        });
    });
    
    // 系统错误
    socket.on('system_error', function(data) {
        addDetectionLog({
            time: getCurrentTime(),
            camera: 'System',
            count: '-',
            status: data.message,
            type: 'error'
        });
    });
    
    // 资源使用更新
    socket.on('system_resources', function(data) {
        updateResources(data);
    });
    
    // 摄像头状态更新
    socket.on('camera_status', function(data) {
        updateCameraStatus(data);
    });
    
    // 检测结果更新
    socket.on('detection_result', function(data) {
        updateDetectionResult(data);
        addDetectionLog({
            time: data.time,
            camera: 'Camera ' + data.camera_id,
            count: data.count,
            status: '已上传',
            type: 'success'
        });
    });
    
    // 模型状态更新
    socket.on('system_update', function(data) {
        if (data.model_loaded !== undefined) {
            const modelStatus = document.getElementById('model-status');
            if (modelStatus) {
                if (data.model_loaded) {
                    modelStatus.textContent = '已加载';
                    modelStatus.className = 'badge bg-success';
                } else {
                    modelStatus.textContent = '未加载';
                    modelStatus.className = 'badge bg-danger';
                }
            }
        }
    });
    
    // 获取初始系统状态
    fetch('/api/status')
        .then(response => {
            if (!response.ok) {
                throw new Error('网络响应不正常');
            }
            return response.json();
        })
        .then(data => {
            updateSystemStatus(data);
        })
        .catch(error => {
            console.error('获取系统状态失败:', error);
        });
    
    // 每秒更新运行时间
    setInterval(updateUptime, 1000);
    
    // 绑定模式控制按钮
    const startPushBtn = document.getElementById('start-push');
    const stopPushBtn = document.getElementById('stop-push');
    const startPullBtn = document.getElementById('start-pull');
    const stopPullBtn = document.getElementById('stop-pull');
    
    if (startPushBtn) {
        startPushBtn.addEventListener('click', function() {
            controlDetectionMode('start', 'push');
        });
    }
    
    if (stopPushBtn) {
        stopPushBtn.addEventListener('click', function() {
            controlDetectionMode('stop', 'push');
        });
    }
    
    if (startPullBtn) {
        startPullBtn.addEventListener('click', function() {
            controlDetectionMode('start', 'pull');
        });
    }
    
    if (stopPullBtn) {
        stopPullBtn.addEventListener('click', function() {
            controlDetectionMode('stop', 'pull');
        });
    }
});

// 生成随机颜色
function getRandomColor() {
    const letters = '0123456789ABCDEF';
    let color = '#';
    for (let i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

// 更新系统状态
function updateSystemStatus(data) {
    // 首先检查data是否存在
    if (!data) {
        console.error('收到无效的系统状态数据');
        return;
    }
    
    // 更新运行模式 - 检查元素是否存在
    const modeStatus = document.getElementById('mode-status');
    if (modeStatus) {
        // 避免在同一函数中重复声明变量
        if (data.mode === 'pull') {
            modeStatus.textContent = '主动拉取模式';
        } else if (data.mode === 'push') {
            modeStatus.textContent = '被动接收模式';
        } else if (data.mode === 'both') {
            modeStatus.textContent = '双模式';
        }
    }
    
    // 更新模型状态
    const modelStatus = document.getElementById('model-status');
    if (modelStatus) {
        if (data.model_loaded) {
            modelStatus.textContent = '已加载';
            modelStatus.className = 'badge bg-success';
        } else {
            modelStatus.textContent = '未加载';
            modelStatus.className = 'badge bg-danger';
        }
    }
    
    // 更新启动时间
    const startTimeElem = document.getElementById('start-time');
    if (startTimeElem) {
        startTimeElem.textContent = data.started_at;
    }
    
    // 更新摄像头状态
    updateCameraContainer(data.cameras, data.detection_count, data.last_update);
    
    // 更新资源使用
    updateResources({
        cpu: data.cpu_usage,
        memory: data.memory_usage
    });
    
    // 更新运行状态 - 修复：传递正确的参数
    updateControlButtons(data);
    
    const runningStatus = document.getElementById('running-status');
    if (runningStatus) {
        if (data.running) {
            runningStatus.textContent = '运行中';
            runningStatus.className = 'badge bg-success';
        } else {
            runningStatus.textContent = '已停止';
            runningStatus.className = 'badge bg-danger';
        }
    }
    
    // 更新被动模式状态
    const pushStatusLabel = document.getElementById('push-status');
    if (pushStatusLabel) {
        if (data.push_running) {
            pushStatusLabel.textContent = '被动模式: 运行中';
            pushStatusLabel.className = 'badge bg-success';
        } else {
            pushStatusLabel.textContent = '被动模式: 已停止';
            pushStatusLabel.className = 'badge bg-danger';
        }
    }
    
    // 更新主动模式状态
    const pullStatusLabel = document.getElementById('pull-status');
    if (pullStatusLabel) {
        if (data.pull_running) {
            pullStatusLabel.textContent = '主动模式: 运行中';
            pullStatusLabel.className = 'badge bg-success';
        } else {
            pullStatusLabel.textContent = '主动模式: 已停止';
            pullStatusLabel.className = 'badge bg-danger';
        }
    }
}

// 更新摄像头容器
function updateCameraContainer(cameras, counts, updates) {
    const container = document.getElementById('camera-container');
    if (!container) {
        console.warn('找不到摄像头容器元素');
        return;
    }
    
    // 清空容器
    container.innerHTML = '';
    
    // 检查是否有摄像头
    if (!cameras || Object.keys(cameras).length === 0) {
        container.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-camera-video-off display-4 text-muted"></i>
                <p class="mt-3 text-muted">未配置摄像头</p>
            </div>
        `;
        return;
    }
    
    // 创建摄像头网格布局
    const row = document.createElement('div');
    row.className = 'row g-3';
    container.appendChild(row);
    
    // 添加每个摄像头
    for (const [id, status] of Object.entries(cameras)) {
        const count = counts[id] || 0;
        const lastUpdate = updates[id] || '未知';
        
        const cameraCol = document.createElement('div');
        cameraCol.className = 'col-md-6 col-lg-4';
        
        const cameraCard = document.createElement('div');
        cameraCard.className = `card h-100 ${status.toLowerCase() === '在线' ? 'border-success' : status.toLowerCase() === '离线' ? 'border-danger' : 'border-warning'}`;
        cameraCard.id = `camera-${id}`;
        
        let statusBadge = '';
        let statusIcon = '';
        if (status === '在线') {
            statusBadge = '<span class="badge bg-success">在线</span>';
            statusIcon = '<i class="bi bi-camera-video text-success"></i>';
        } else if (status === '离线') {
            statusBadge = '<span class="badge bg-danger">离线</span>';
            statusIcon = '<i class="bi bi-camera-video-off text-danger"></i>';
        } else if (status === '错误') {
            statusBadge = '<span class="badge bg-warning">错误</span>';
            statusIcon = '<i class="bi bi-exclamation-triangle text-warning"></i>';
        } else {
            statusBadge = '<span class="badge bg-secondary">未知</span>';
            statusIcon = '<i class="bi bi-question-circle text-secondary"></i>';
        }
        
        cameraCard.innerHTML = `
            <div class="card-header d-flex justify-content-between align-items-center">
                <div class="d-flex align-items-center">
                    ${statusIcon}
                    <strong class="ms-2">摄像头 ${id}</strong>
                </div>
                ${statusBadge}
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <h5 class="card-title text-center display-4" id="count-${id}">${count}</h5>
                    <p class="card-text text-center text-muted">当前检测人数</p>
                </div>
                <div class="d-flex justify-content-between align-items-center">
                    <small class="text-muted"><i class="bi bi-clock-history me-1"></i> 最后更新:</small>
                    <small class="text-muted" id="update-${id}">${lastUpdate}</small>
                </div>
            </div>
        `;
        
        cameraCol.appendChild(cameraCard);
        row.appendChild(cameraCol);
    }
}

// 更新摄像头状态
function updateCameraStatus(data) {
    const cameraCard = document.getElementById(`camera-${data.id}`);
    if (!cameraCard) return;
    
    // 更新卡片边框
    if (data.status === '在线') {
        cameraCard.className = 'card h-100 border-success';
    } else if (data.status === '离线') {
        cameraCard.className = 'card h-100 border-danger';
    } else {
        cameraCard.className = 'card h-100 border-warning';
    }
    
    // 更新状态徽章
    const statusElement = cameraCard.querySelector('.badge');
    if (statusElement) {
        statusElement.textContent = data.status;
        
        if (data.status === '在线') {
            statusElement.className = 'badge bg-success';
        } else if (data.status === '离线') {
            statusElement.className = 'badge bg-danger';
        } else if (data.status === '错误') {
            statusElement.className = 'badge bg-warning';
        } else {
            statusElement.className = 'badge bg-secondary';
        }
    }
    
    // 更新图标
    const iconElement = cameraCard.querySelector('.bi');
    if (iconElement) {
        if (data.status === '在线') {
            iconElement.className = 'bi bi-camera-video text-success';
        } else if (data.status === '离线') {
            iconElement.className = 'bi bi-camera-video-off text-danger';
        } else if (data.status === '错误') {
            iconElement.className = 'bi bi-exclamation-triangle text-warning';
        } else {
            iconElement.className = 'bi bi-question-circle text-secondary';
        }
    }
    
    // 如果有错误消息
    if (data.error) {
        addDetectionLog({
            time: getCurrentTime(),
            camera: 'Camera ' + data.id,
            count: '-',
            status: data.error,
            type: 'error'
        });
    }
}

// 更新检测结果
function updateDetectionResult(data) {
    // 更新摄像头卡片中的计数
    const countElement = document.getElementById(`count-${data.camera_id}`);
    if (countElement) {
        // 添加动画效果
        countElement.classList.add('highlight');
        // 更新数值
        countElement.textContent = data.count;
        // 延迟移除高亮效果
        setTimeout(() => {
            countElement.classList.remove('highlight');
        }, 1000);
    }
    
    // 更新最后更新时间
    const updateElement = document.getElementById(`update-${data.camera_id}`);
    if (updateElement) {
        updateElement.textContent = data.time;
    }
}

// 更新资源使用
function updateResources(data) {
    const cpuElement = document.getElementById('cpu-usage');
    const memoryElement = document.getElementById('memory-usage');
    const cpuPercentElement = document.querySelector('.cpu-percent');
    const memoryPercentElement = document.querySelector('.memory-percent');
    
    if (cpuElement && cpuPercentElement) {
        cpuElement.style.width = `${data.cpu}%`;
        cpuElement.setAttribute('aria-valuenow', data.cpu);
        cpuPercentElement.textContent = `${data.cpu.toFixed(1)}%`;
        
        // 根据使用率改变颜色
        if (data.cpu > 80) {
            cpuElement.className = 'progress-bar bg-danger';
        } else if (data.cpu > 50) {
            cpuElement.className = 'progress-bar bg-warning';
        } else {
            cpuElement.className = 'progress-bar bg-primary';
        }
    }
    
    if (memoryElement && memoryPercentElement) {
        memoryElement.style.width = `${data.memory}%`;
        memoryElement.setAttribute('aria-valuenow', data.memory);
        memoryPercentElement.textContent = `${data.memory.toFixed(1)}%`;
        
        // 根据使用率改变颜色
        if (data.memory > 80) {
            memoryElement.className = 'progress-bar bg-danger';
        } else if (data.memory > 50) {
            memoryElement.className = 'progress-bar bg-warning';
        } else {
            memoryElement.className = 'progress-bar bg-success';
        }
    }
}

// 添加检测日志
function addDetectionLog(log) {
    const tbody = document.getElementById('detection-logs');
    if (!tbody) return;
    
    const logCountElement = document.getElementById('log-count');
    
    // 如果是第一条记录，清空"暂无记录"提示
    if (tbody.querySelector('td[colspan="4"]')) {
        tbody.innerHTML = '';
    }
    
    // 限制日志条数
    const rows = tbody.querySelectorAll('tr');
    if (rows.length >= 10) {
        tbody.removeChild(rows[rows.length - 1]);
    }
    
    // 创建新行
    const tr = document.createElement('tr');
    if (log.type === 'error') {
        tr.className = 'table-danger';
    } else if (log.type === 'warning') {
        tr.className = 'table-warning';
    } else if (log.type === 'success') {
        tr.className = 'table-success';
    } else {
        tr.className = 'table-info';
    }
    
    tr.innerHTML = `
        <td><i class="bi bi-clock me-1"></i>${log.time}</td>
        <td><i class="bi bi-camera me-1"></i>${log.camera}</td>
        <td><i class="bi bi-people me-1"></i>${log.count}</td>
        <td><i class="bi bi-cloud-arrow-up me-1"></i>${log.status}</td>
    `;
    
    // 插入到表格顶部
    tbody.insertBefore(tr, tbody.firstChild);
    
    // 更新日志计数
    if (logCountElement) {
        logCountElement.textContent = tbody.querySelectorAll('tr').length;
    }
}

// 更新运行时间
function updateUptime() {
    const startTimeElement = document.getElementById('start-time');
    const uptimeElement = document.getElementById('uptime');
    
    if (!startTimeElement || !uptimeElement || !startTimeElement.textContent || startTimeElement.textContent === '加载中...') {
        return;
    }
    
    const startTime = new Date(startTimeElement.textContent);
    const now = new Date();
    const diff = Math.floor((now - startTime) / 1000);
    
    const hours = Math.floor(diff / 3600);
    const minutes = Math.floor((diff % 3600) / 60);
    const seconds = diff % 60;
    
    uptimeElement.textContent = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// 获取当前时间字符串
function getCurrentTime() {
    const now = new Date();
    return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
}

// 控制特定模式
function controlDetectionMode(action, mode) {
    // 防止重复点击
    const startPushBtn = document.getElementById('start-push');
    const stopPushBtn = document.getElementById('stop-push');
    const startPullBtn = document.getElementById('start-pull');
    const stopPullBtn = document.getElementById('stop-pull');
    
    // 根据操作类型禁用按钮
    if (action === 'start' && mode === 'push' && startPushBtn) {
        startPushBtn.disabled = true;
    } else if (action === 'stop' && mode === 'push' && stopPushBtn) {
        stopPushBtn.disabled = true;
    } else if (action === 'start' && mode === 'pull' && startPullBtn) {
        startPullBtn.disabled = true;
    } else if (action === 'stop' && mode === 'pull' && stopPullBtn) {
        stopPullBtn.disabled = true;
    }

    fetch('/api/control', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action: action, mode: mode })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('网络响应不正常');
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            addDetectionLog({
                time: getCurrentTime(),
                camera: 'System',
                count: '-',
                status: data.message,
                type: 'success'
            });
        } else {
            addDetectionLog({
                time: getCurrentTime(),
                camera: 'System',
                count: '-',
                status: data.message,
                type: 'error'
            });
        }
        
        // 重新启用按钮
        if (action === 'start' && mode === 'push' && startPushBtn) {
            startPushBtn.disabled = false;
        } else if (action === 'stop' && mode === 'push' && stopPushBtn) {
            stopPushBtn.disabled = false;
        } else if (action === 'start' && mode === 'pull' && startPullBtn) {
            startPullBtn.disabled = false;
        } else if (action === 'stop' && mode === 'pull' && stopPullBtn) {
            stopPullBtn.disabled = false;
        }
        
        // 请求更新系统状态
        fetch('/api/status')
            .then(response => response.json())
            .then(statusData => {
                updateSystemStatus(statusData);
            })
            .catch(error => {
                console.error('获取系统状态失败:', error);
            });
    })
    .catch(error => {
        console.error('控制请求失败:', error);
        addDetectionLog({
            time: getCurrentTime(),
            camera: 'System',
            count: '-',
            status: '控制请求失败: ' + error,
            type: 'error'
        });
        
        // 出错时也重新启用按钮
        if (action === 'start' && mode === 'push' && startPushBtn) {
            startPushBtn.disabled = false;
        } else if (action === 'stop' && mode === 'push' && stopPushBtn) {
            stopPushBtn.disabled = false;
        } else if (action === 'start' && mode === 'pull' && startPullBtn) {
            startPullBtn.disabled = false;
        } else if (action === 'stop' && mode === 'pull' && stopPullBtn) {
            stopPullBtn.disabled = false;
        }
    });
}

// 更新控制按钮状态
function updateControlButtons(data) {
    // 检查data是否存在及包含必要属性
    if (!data || typeof data.push_running === 'undefined' || typeof data.pull_running === 'undefined') {
        console.warn('更新按钮状态时数据不完整');
        return;
    }
    
    const startPushBtn = document.getElementById('start-push');
    const stopPushBtn = document.getElementById('stop-push');
    const startPullBtn = document.getElementById('start-pull');
    const stopPullBtn = document.getElementById('stop-pull');
    
    if (startPushBtn && stopPushBtn) {
        startPushBtn.disabled = data.push_running;
        stopPushBtn.disabled = !data.push_running;
    }
    
    if (startPullBtn && stopPullBtn) {
        startPullBtn.disabled = data.pull_running;
        stopPullBtn.disabled = !data.pull_running;
    }
}


// 添加检测日志
function addDetectionLog(log) {
    const tbody = document.getElementById('detection-logs');
    if (!tbody) return;
    
    const logCountElement = document.getElementById('log-count');
    
    // 如果是第一条记录，清空"暂无记录"提示
    if (tbody.querySelector('td[colspan="4"]')) {
        tbody.innerHTML = '';
    }
    
    // 限制日志条数
    const rows = tbody.querySelectorAll('tr');
    if (rows.length >= 10) {
        tbody.removeChild(rows[rows.length - 1]);
    }
    
    // 创建新行
    const tr = document.createElement('tr');
    if (log.type === 'error') {
        tr.className = 'table-danger';
    } else if (log.type === 'warning') {
        tr.className = 'table-warning';
    } else if (log.type === 'success') {
        tr.className = 'table-success';
    } else {
        tr.className = 'table-info';
    }
    
    tr.innerHTML = `
        <td><i class="bi bi-clock me-1"></i>${log.time}</td>
        <td><i class="bi bi-camera me-1"></i>${log.camera}</td>
        <td><i class="bi bi-people me-1"></i>${log.count}</td>
        <td><i class="bi bi-cloud-arrow-up me-1"></i>${log.status}</td>
    `;
    
    // 插入到表格顶部
    tbody.insertBefore(tr, tbody.firstChild);
    
    // 更新日志计数
    if (logCountElement) {
        logCountElement.textContent = tbody.querySelectorAll('tr').length;
    }
}

// 更新运行时间
function updateUptime() {
    const startTimeElement = document.getElementById('start-time');
    const uptimeElement = document.getElementById('uptime');
    
    if (!startTimeElement || !uptimeElement || !startTimeElement.textContent || startTimeElement.textContent === '加载中...') {
        return;
    }
    
    const startTime = new Date(startTimeElement.textContent);
    const now = new Date();
    const diff = Math.floor((now - startTime) / 1000);
    
    const hours = Math.floor(diff / 3600);
    const minutes = Math.floor((diff % 3600) / 60);
    const seconds = diff % 60;
    
    uptimeElement.textContent = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// 获取当前时间字符串
function getCurrentTime() {
    const now = new Date();
    return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
}

// 添加控制检测的函数
function controlDetection(action) {
    fetch('/api/control', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action: action })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            addDetectionLog({
                time: getCurrentTime(),
                camera: 'System',
                count: '-',
                status: data.message,
                type: 'success'
            });
            
            // 更新控制按钮状态
            updateControlButtons(action === 'start' || action === 'restart');
        } else {
            addDetectionLog({
                time: getCurrentTime(),
                camera: 'System',
                count: '-',
                status: data.message,
                type: 'error'
            });
        }
    })
    .catch(error => {
        console.error('控制请求失败:', error);
        addDetectionLog({
            time: getCurrentTime(),
            camera: 'System',
            count: '-',
            status: '控制请求失败: ' + error,
            type: 'error'
        });
    });
}

// 控制特定模式
function controlDetectionMode(action, mode) {
    // 防止重复点击
    const startPushBtn = document.getElementById('start-push');
    const stopPushBtn = document.getElementById('stop-push');
    const startPullBtn = document.getElementById('start-pull');
    const stopPullBtn = document.getElementById('stop-pull');
    
    // 根据操作类型禁用按钮
    if (action === 'start' && mode === 'push' && startPushBtn) {
        startPushBtn.disabled = true;
    } else if (action === 'stop' && mode === 'push' && stopPushBtn) {
        stopPushBtn.disabled = true;
    } else if (action === 'start' && mode === 'pull' && startPullBtn) {
        startPullBtn.disabled = true;
    } else if (action === 'stop' && mode === 'pull' && stopPullBtn) {
        stopPullBtn.disabled = true;
    }

    fetch('/api/control', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action: action, mode: mode })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('网络响应不正常');
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            addDetectionLog({
                time: getCurrentTime(),
                camera: 'System',
                count: '-',
                status: data.message,
                type: 'success'
            });
        } else {
            addDetectionLog({
                time: getCurrentTime(),
                camera: 'System',
                count: '-',
                status: data.message,
                type: 'error'
            });
        }
        
        // 重新启用按钮
        if (action === 'start' && mode === 'push' && startPushBtn) {
            startPushBtn.disabled = false;
        } else if (action === 'stop' && mode === 'push' && stopPushBtn) {
            stopPushBtn.disabled = false;
        } else if (action === 'start' && mode === 'pull' && startPullBtn) {
            startPullBtn.disabled = false;
        } else if (action === 'stop' && mode === 'pull' && stopPullBtn) {
            stopPullBtn.disabled = false;
        }
        
        // 请求更新系统状态
        fetch('/api/status')
            .then(response => response.json())
            .then(statusData => {
                updateSystemStatus(statusData);
            })
            .catch(error => {
                console.error('获取系统状态失败:', error);
            });
    })
    .catch(error => {
        console.error('控制请求失败:', error);
        addDetectionLog({
            time: getCurrentTime(),
            camera: 'System',
            count: '-',
            status: '控制请求失败: ' + error,
            type: 'error'
        });
        
        // 出错时也重新启用按钮
        if (action === 'start' && mode === 'push' && startPushBtn) {
            startPushBtn.disabled = false;
        } else if (action === 'stop' && mode === 'push' && stopPushBtn) {
            stopPushBtn.disabled = false;
        } else if (action === 'start' && mode === 'pull' && startPullBtn) {
            startPullBtn.disabled = false;
        } else if (action === 'stop' && mode === 'pull' && stopPullBtn) {
            stopPullBtn.disabled = false;
        }
    });
}

// 更新控制按钮状态
function updateControlButtons(data) {
    // 检查data是否存在及包含必要属性
    if (!data || typeof data.push_running === 'undefined' || typeof data.pull_running === 'undefined') {
        console.warn('更新按钮状态时数据不完整');
        return;
    }
    
    const startPushBtn = document.getElementById('start-push');
    const stopPushBtn = document.getElementById('stop-push');
    const startPullBtn = document.getElementById('start-pull');
    const stopPullBtn = document.getElementById('stop-pull');
    
    if (startPushBtn && stopPushBtn) {
        startPushBtn.disabled = data.push_running;
        stopPushBtn.disabled = !data.push_running;
    }
    
    if (startPullBtn && stopPullBtn) {
        startPullBtn.disabled = data.pull_running;
        stopPullBtn.disabled = !data.pull_running;
    }
}


// 更新资源使用
function updateResources(data) {
    const cpuElement = document.getElementById('cpu-usage');
    const memoryElement = document.getElementById('memory-usage');
    const cpuPercentElement = document.querySelector('.cpu-percent');
    const memoryPercentElement = document.querySelector('.memory-percent');
    
    if (cpuElement && cpuPercentElement) {
        cpuElement.style.width = `${data.cpu}%`;
        cpuElement.setAttribute('aria-valuenow', data.cpu);
        cpuPercentElement.textContent = `${data.cpu.toFixed(1)}%`;
        
        // 根据使用率改变颜色
        if (data.cpu > 80) {
            cpuElement.className = 'progress-bar bg-danger';
        } else if (data.cpu > 50) {
            cpuElement.className = 'progress-bar bg-warning';
        } else {
            cpuElement.className = 'progress-bar bg-primary';
        }
    }
    
    if (memoryElement && memoryPercentElement) {
        memoryElement.style.width = `${data.memory}%`;
        memoryElement.setAttribute('aria-valuenow', data.memory);
        memoryPercentElement.textContent = `${data.memory.toFixed(1)}%`;
        
        // 根据使用率改变颜色
        if (data.memory > 80) {
            memoryElement.className = 'progress-bar bg-danger';
        } else if (data.memory > 50) {
            memoryElement.className = 'progress-bar bg-warning';
        } else {
            memoryElement.className = 'progress-bar bg-success';
        }
    }
}

// 添加检测日志
function addDetectionLog(log) {
    const tbody = document.getElementById('detection-logs');
    const logCountElement = document.getElementById('log-count');
    
    // 如果是第一条记录，清空"暂无记录"提示
    if (tbody.querySelector('td[colspan="4"]')) {
        tbody.innerHTML = '';
    }
    
    // 限制日志条数
    const rows = tbody.querySelectorAll('tr');
    if (rows.length >= 10) {
        tbody.removeChild(rows[rows.length - 1]);
    }
    
    // 创建新行
    const tr = document.createElement('tr');
    if (log.type === 'error') {
        tr.className = 'table-danger';
    } else if (log.type === 'warning') {
        tr.className = 'table-warning';
    } else if (log.type === 'success') {
        tr.className = 'table-success';
    } else {
        tr.className = 'table-info';
    }
    
    tr.innerHTML = `
        <td><i class="bi bi-clock me-1"></i>${log.time}</td>
        <td><i class="bi bi-camera me-1"></i>${log.camera}</td>
        <td><i class="bi bi-people me-1"></i>${log.count}</td>
        <td><i class="bi bi-cloud-arrow-up me-1"></i>${log.status}</td>
    `;
    
    // 插入到表格顶部
    tbody.insertBefore(tr, tbody.firstChild);
    
    // 更新日志计数
    if (logCountElement) {
        logCountElement.textContent = tbody.querySelectorAll('tr').length;
    }
}

// 更新运行时间
function updateUptime() {
    const startTimeElement = document.getElementById('start-time');
    const uptimeElement = document.getElementById('uptime');
    
    if (!startTimeElement || !startTimeElement.textContent || startTimeElement.textContent === '加载中...') {
        return;
    }
    
    const startTime = new Date(startTimeElement.textContent);
    const now = new Date();
    const diff = Math.floor((now - startTime) / 1000);
    
    const hours = Math.floor(diff / 3600);
    const minutes = Math.floor((diff % 3600) / 60);
    const seconds = diff % 60;
    
    uptimeElement.textContent = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// 获取当前时间字符串
function getCurrentTime() {
    const now = new Date();
    return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
}

// 添加控制检测的函数
function controlDetection(action) {
    fetch('/api/control', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action: action })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            addDetectionLog({
                time: getCurrentTime(),
                camera: 'System',
                count: '-',
                status: data.message,
                type: 'success'
            });
            
            // 更新控制按钮状态
            updateControlButtons(action === 'start' || action === 'restart');
        } else {
            addDetectionLog({
                time: getCurrentTime(),
                camera: 'System',
                count: '-',
                status: data.message,
                type: 'error'
            });
        }
    })
    .catch(error => {
        console.error('控制请求失败:', error);
        addDetectionLog({
            time: getCurrentTime(),
            camera: 'System',
            count: '-',
            status: '控制请求失败: ' + error,
            type: 'error'
        });
    });
}

// 控制特定模式
function controlDetectionMode(action, mode) {
    // 防止重复点击
    const startPushBtn = document.getElementById('start-push');
    const stopPushBtn = document.getElementById('stop-push');
    const startPullBtn = document.getElementById('start-pull');
    const stopPullBtn = document.getElementById('stop-pull');
    
    // 根据操作类型禁用按钮
    if (action === 'start' && mode === 'push' && startPushBtn) {
        startPushBtn.disabled = true;
    } else if (action === 'stop' && mode === 'push' && stopPushBtn) {
        stopPushBtn.disabled = true;
    } else if (action === 'start' && mode === 'pull' && startPullBtn) {
        startPullBtn.disabled = true;
    } else if (action === 'stop' && mode === 'pull' && stopPullBtn) {
        stopPullBtn.disabled = true;
    }

    fetch('/api/control', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action: action, mode: mode })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('网络响应不正常');
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            addDetectionLog({
                time: getCurrentTime(),
                camera: 'System',
                count: '-',
                status: data.message,
                type: 'success'
            });
        } else {
            addDetectionLog({
                time: getCurrentTime(),
                camera: 'System',
                count: '-',
                status: data.message,
                type: 'error'
            });
        }
        
        // 重新启用按钮
        if (action === 'start' && mode === 'push' && startPushBtn) {
            startPushBtn.disabled = false;
        } else if (action === 'stop' && mode === 'push' && stopPushBtn) {
            stopPushBtn.disabled = false;
        } else if (action === 'start' && mode === 'pull' && startPullBtn) {
            startPullBtn.disabled = false;
        } else if (action === 'stop' && mode === 'pull' && stopPullBtn) {
            stopPullBtn.disabled = false;
        }
        
        // 请求更新系统状态
        fetch('/api/status')
            .then(response => response.json())
            .then(statusData => {
                updateSystemStatus(statusData);
            })
            .catch(error => {
                console.error('获取系统状态失败:', error);
            });
    })
    .catch(error => {
        console.error('控制请求失败:', error);
        addDetectionLog({
            time: getCurrentTime(),
            camera: 'System',
            count: '-',
            status: '控制请求失败: ' + error,
            type: 'error'
        });
        
        // 出错时也重新启用按钮
        if (action === 'start' && mode === 'push' && startPushBtn) {
            startPushBtn.disabled = false;
        } else if (action === 'stop' && mode === 'push' && stopPushBtn) {
            stopPushBtn.disabled = false;
        } else if (action === 'start' && mode === 'pull' && startPullBtn) {
            startPullBtn.disabled = false;
        } else if (action === 'stop' && mode === 'pull' && stopPullBtn) {
            stopPullBtn.disabled = false;
        }
    });
}

// 更新控制按钮状态
function updateControlButtons(data) {
    // 检查data是否存在及包含必要属性
    if (!data || typeof data.push_running === 'undefined' || typeof data.pull_running === 'undefined') {
        console.warn('更新按钮状态时数据不完整');
        return;
    }
    
    const startPushBtn = document.getElementById('start-push');
    const stopPushBtn = document.getElementById('stop-push');
    const startPullBtn = document.getElementById('start-pull');
    const stopPullBtn = document.getElementById('stop-pull');
    
    if (startPushBtn && stopPushBtn) {
        startPushBtn.disabled = data.push_running;
        stopPushBtn.disabled = !data.push_running;
    }
    
    if (startPullBtn && stopPullBtn) {
        startPullBtn.disabled = data.pull_running;
        stopPullBtn.disabled = !data.pull_running;
    }
}
