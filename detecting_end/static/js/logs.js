// 检查socket是否已经被定义，防止重复声明
let socket;
if (typeof socket === 'undefined') {
    // 连接WebSocket服务器
    socket = io();
    console.log('Socket已初始化');
} else {
    console.log('Socket已存在，跳过重新初始化');
}

// 日志页面状态
const logState = {
    currentPage: 1,
    totalPages: 1,
    logsPerPage: 50,
    currentFilter: 'all',
    logs: []
};

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
        
        // 请求日志数据
        fetchLogs();
    });
    
    socket.on('disconnect', function() {
        console.log('与服务器断开连接');
        const serverStatus = document.getElementById('server-status');
        if (serverStatus) {
            serverStatus.textContent = '已断开';
            serverStatus.className = 'badge bg-danger';
        }
    });
    
    // 处理实时日志更新
    socket.on('new_log', function(data) {
        // 添加新日志条目到内存中的日志数组
        logState.logs.unshift(data);
        
        // 如果当前在第一页，则更新UI
        if (logState.currentPage === 1) {
            displayLogs();
        }
    });
    
    // 处理统计数据更新
    socket.on('stats_update', function(data) {
        updateStatistics(data);
    });
    
    // 绑定按钮事件
    const refreshBtn = document.getElementById('refresh-logs');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', fetchLogs);
    }
    
    const clearBtn = document.getElementById('clear-logs');
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            const logEntries = document.getElementById('log-entries');
            if (logEntries) {
                logEntries.innerHTML = '<tr><td colspan="4" class="text-center py-3 text-muted">日志已清空</td></tr>';
                document.getElementById('log-count').textContent = '0';
            }
        });
    }
    
    // 绑定日志级别过滤器
    const logLevelSelect = document.getElementById('log-level');
    if (logLevelSelect) {
        logLevelSelect.addEventListener('change', function() {
            logState.currentFilter = this.value;
            logState.currentPage = 1;
            displayLogs();
        });
    }
    
    // 绑定分页按钮
    const prevPageBtn = document.getElementById('prev-page');
    const nextPageBtn = document.getElementById('next-page');
    
    if (prevPageBtn) {
        prevPageBtn.addEventListener('click', function() {
            if (logState.currentPage > 1) {
                logState.currentPage--;
                displayLogs();
            }
        });
    }
    
    if (nextPageBtn) {
        nextPageBtn.addEventListener('click', function() {
            if (logState.currentPage < logState.totalPages) {
                logState.currentPage++;
                displayLogs();
            }
        });
    }
    
    // 初始获取日志
    fetchLogs();
    
    // 获取统计数据
    fetchStatistics();
});

// 获取日志数据
function fetchLogs() {
    fetch('/api/logs')
        .then(response => {
            if (!response.ok) {
                throw new Error('网络响应不正常');
            }
            return response.json();
        })
        .then(data => {
            logState.logs = data;
            logState.currentPage = 1;
            displayLogs();
        })
        .catch(error => {
            console.error('获取日志失败:', error);
            const logEntries = document.getElementById('log-entries');
            if (logEntries) {
                logEntries.innerHTML = `<tr><td colspan="4" class="text-center py-3 text-danger">获取日志失败: ${error.message}</td></tr>`;
            }
        });
}

// 获取统计数据
function fetchStatistics() {
    fetch('/api/logs/stats')
        .then(response => {
            if (!response.ok) {
                throw new Error('网络响应不正常');
            }
            return response.json();
        })
        .then(data => {
            updateStatistics(data);
        })
        .catch(error => {
            console.error('获取统计数据失败:', error);
        });
}

// 更新统计数据显示
function updateStatistics(data) {
    const todayCount = document.getElementById('today-count');
    const totalCount = document.getElementById('total-count');
    const maxCount = document.getElementById('max-count');
    const avgCount = document.getElementById('avg-count');
    
    if (todayCount) todayCount.textContent = data.today_count || '-';
    if (totalCount) totalCount.textContent = data.total_count || '-';
    if (maxCount) maxCount.textContent = data.max_count || '-';
    if (avgCount) avgCount.textContent = data.avg_count ? data.avg_count.toFixed(1) : '-';
}

// 根据过滤器和当前页面显示日志
function displayLogs() {
    const logEntries = document.getElementById('log-entries');
    const logCount = document.getElementById('log-count');
    const currentPageElem = document.getElementById('current-page');
    const totalPagesElem = document.getElementById('total-pages');
    const prevPageBtn = document.getElementById('prev-page');
    const nextPageBtn = document.getElementById('next-page');
    
    if (!logEntries) return;
    
    // 根据过滤器筛选日志
    let filteredLogs = logState.logs;
    if (logState.currentFilter !== 'all') {
        filteredLogs = logState.logs.filter(log => log.level === logState.currentFilter);
    }
    
    // 更新总页数
    logState.totalPages = Math.max(1, Math.ceil(filteredLogs.length / logState.logsPerPage));
    
    // 确保当前页面有效
    if (logState.currentPage > logState.totalPages) {
        logState.currentPage = logState.totalPages;
    }
    
    // 更新UI元素
    if (currentPageElem) currentPageElem.textContent = logState.currentPage;
    if (totalPagesElem) totalPagesElem.textContent = logState.totalPages;
    if (logCount) logCount.textContent = filteredLogs.length;
    
    // 更新分页按钮状态
    if (prevPageBtn) prevPageBtn.disabled = logState.currentPage <= 1;
    if (nextPageBtn) nextPageBtn.disabled = logState.currentPage >= logState.totalPages;
    
    // 如果没有日志
    if (filteredLogs.length === 0) {
        logEntries.innerHTML = '<tr><td colspan="4" class="text-center py-3 text-muted">没有日志记录</td></tr>';
        return;
    }
    
    // 计算当前页的日志范围
    const startIndex = (logState.currentPage - 1) * logState.logsPerPage;
    const endIndex = Math.min(startIndex + logState.logsPerPage, filteredLogs.length);
    const currentPageLogs = filteredLogs.slice(startIndex, endIndex);
    
    // 清空现有内容
    logEntries.innerHTML = '';
    
    // 添加日志条目
    currentPageLogs.forEach(log => {
        const tr = document.createElement('tr');
        
        // 根据日志级别设置样式
        if (log.level === 'error') {
            tr.className = 'table-danger';
        } else if (log.level === 'warning') {
            tr.className = 'table-warning';
        } else if (log.level === 'detection') {
            tr.className = 'table-success';
        } else {
            tr.className = 'table-info';
        }
        
        // 设置图标
        let icon = 'info-circle';
        if (log.level === 'error') icon = 'exclamation-triangle';
        else if (log.level === 'warning') icon = 'exclamation-circle';
        else if (log.level === 'detection') icon = 'people';
        
        // 转换日志级别文本
        let levelText = log.level;
        if (log.level === 'info') levelText = '信息';
        else if (log.level === 'error') levelText = '错误';
        else if (log.level === 'warning') levelText = '警告';
        else if (log.level === 'detection') levelText = '检测';
        
        tr.innerHTML = `
            <td><i class="bi bi-clock me-1"></i>${log.timestamp}</td>
            <td><i class="bi bi-${icon} me-1"></i>${levelText}</td>
            <td>${log.source || '-'}</td>
            <td>${log.message}</td>
        `;
        
        logEntries.appendChild(tr);
    });
}
    const detectionLogsContainer = document.getElementById('detection-logs');
    
    if (detectionLogsContainer) {
        // 显示加载中
        detectionLogsContainer.innerHTML = `
            <tr>
                <td colspan="4" class="text-center">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">加载中...</span>
                    </div>
                    <p class="mt-2">正在加载检测记录...</p>
                </td>
            </tr>
        `;
        
        // 从服务器获取检测记录
        fetch('/api/detection_logs')
            .then(response => {
                if (!response.ok) {
                    throw new Error('获取检测记录失败');
                }
                return response.json();
            })
            .then(logs => {
                if (logs.length === 0) {
                    detectionLogsContainer.innerHTML = `
                        <tr>
                            <td colspan="4" class="text-center text-muted py-5">
                                <i class="bi bi-inbox display-6 d-block mb-3"></i>
                                暂无检测记录
                            </td>
                        </tr>
                    `;
                    return;
                }
                
                // 清空容器
                detectionLogsContainer.innerHTML = '';
                
                // 添加检测记录
                logs.forEach(log => {
                    const tr = document.createElement('tr');
                    
                    // 根据状态设置样式
                    if (log.status.includes('失败') || log.status.includes('错误')) {
                        tr.className = 'table-danger';
                    } else if (log.status.includes('警告')) {
                        tr.className = 'table-warning';
                    } else if (log.status.includes('成功') || log.status.includes('已上传')) {
                        tr.className = 'table-success';
                    }
                    
                    tr.innerHTML = `
                        <td><i class="bi bi-clock me-1"></i>${log.time}</td>
                        <td><i class="bi bi-camera me-1"></i>${log.camera}</td>
                        <td><i class="bi bi-people me-1"></i>${log.count}</td>
                        <td><i class="bi bi-cloud-arrow-up me-1"></i>${log.status}</td>
                    `;
                    
                    detectionLogsContainer.appendChild(tr);
                });
            })
            .catch(error => {
                console.error('获取检测记录失败:', error);
                detectionLogsContainer.innerHTML = `
                    <tr>
                        <td colspan="4" class="text-center text-danger">
                            <i class="bi bi-exclamation-triangle display-6 d-block mb-3"></i>
                            获取检测记录失败: ${error.message}
                        </td>
                    </tr>
                `;
            });
    }
}

// 过滤日志
function filterLogs() {
    const logLevelSelect = document.getElementById('log-level');
    const selectedLevel = logLevelSelect ? logLevelSelect.value : 'all';
    
    const logRows = document.querySelectorAll('#system-logs tr');
    
    logRows.forEach(row => {
        if (selectedLevel === 'all') {
            row.style.display = '';
        } else {
            const levelCell = row.querySelector('td:nth-child(2)');
            if (levelCell && !levelCell.textContent.includes(selectedLevel)) {
                row.style.display = 'none';
            } else {
                row.style.display = '';
            }
        }
    });
}

// 清空日志
function clearLogs() {
    if (confirm('确定要清空检测记录吗？此操作不可撤销。')) {
        const detectionLogsContainer = document.getElementById('detection-logs');
        
        if (detectionLogsContainer) {
            detectionLogsContainer.innerHTML = `
                <tr>
                    <td colspan="4" class="text-center text-muted py-5">
                        <i class="bi bi-inbox display-6 d-block mb-3"></i>
                        暂无检测记录
                    </td>
                </tr>
            `;
        }
        
        // 可选：发送请求到服务器清空日志
        fetch('/api/clear_detection_logs', {
            method: 'POST'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('清空日志失败');
            }
            return response.json();
        })
        .then(data => {
            console.log('日志已清空:', data);
        })
        .catch(error => {
            console.error('清空日志失败:', error);
            // 显示错误通知
        });
    }
}
