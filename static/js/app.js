// Asosiy o'zgaruvchilar
let currentAdmin = null;
let currentToken = null;
let userGrowthChart = null;
let startupDistributionChart = null;
let activityChart = null;
let fullscreenChart = null;
let currentUsersPage = 1;
let currentStartupsPage = 1;
let usersTotalPages = 1;
let startupsTotalPages = 1;

// Dastlabki sozlamalar
const API_BASE_URL = window.location.origin + '/api';
const WS_URL = window.location.origin.replace('http', 'ws') + '/ws';

// Dastlabki yuklash
document.addEventListener('DOMContentLoaded', function() {
    checkAuthStatus();
    setupEventListeners();
    initTheme();
});

// Auth holatini tekshirish
async function checkAuthStatus() {
    const token = localStorage.getItem('adminToken');
    if (token) {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) {
                currentAdmin = await response.json();
                currentToken = token;
                showAdminPanel();
                loadStatistics();
                loadUserGrowthChart();
                loadStartupDistributionChart();
            } else {
                showLoginPage();
            }
        } catch (error) {
            console.error('Auth check error:', error);
            showLoginPage();
        }
    } else {
        showLoginPage();
    }
}

// Event listenerlarni sozlash
function setupEventListeners() {
    // Login form
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    
    // Parolni ko'rsatish/yashirish
    document.getElementById('togglePassword').addEventListener('click', function() {
        const passwordInput = document.getElementById('loginPassword');
        const icon = this.querySelector('i');
        if (passwordInput.type === 'password') {
            passwordInput.type = 'text';
            icon.className = 'fas fa-eye-slash';
        } else {
            passwordInput.type = 'password';
            icon.className = 'fas fa-eye';
        }
    });
    
    // Logout
    document.getElementById('logoutBtn').addEventListener('click', handleLogout);
    
    // Menu toggle
    document.getElementById('menuToggle').addEventListener('click', function() {
        document.querySelector('.sidebar').classList.toggle('collapsed');
    });
    
    // Menu items
    document.querySelectorAll('.menu li').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const page = this.dataset.page;
            if (page) {
                showPage(page);
            }
        });
    });
    
    // Theme toggle
    document.getElementById('themeToggle').addEventListener('change', function() {
        if (this.checked) {
            document.body.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        } else {
            document.body.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
        }
    });
    
    // Broadcast form
    document.getElementById('broadcastForm').addEventListener('submit', handleBroadcast);
    
    // Add admin form
    document.getElementById('addAdminForm').addEventListener('submit', handleAddAdmin);
}

// Mavzu sozlamalari
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.body.setAttribute('data-theme', savedTheme);
    document.getElementById('themeToggle').checked = savedTheme === 'dark';
}

// Login qilish
async function handleLogin(e) {
    e.preventDefault();
    
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    
    try {
        showLoading();
        
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        if (response.ok) {
            const data = await response.json();
            currentAdmin = data.admin;
            currentToken = data.access_token;
            
            localStorage.setItem('adminToken', data.access_token);
            localStorage.setItem('adminData', JSON.stringify(data.admin));
            
            showAdminPanel();
            loadStatistics();
            showToast('Muvaffaqiyatli kirildi!', 'success');
        } else {
            const error = await response.json();
            showToast(error.detail || 'Kirish muvaffaqiyatsiz', 'error');
        }
    } catch (error) {
        console.error('Login error:', error);
        showToast('Server xatosi', 'error');
    } finally {
        hideLoading();
    }
}

// Logout qilish
function handleLogout() {
    if (confirm('Chiqishni istaysizmi?')) {
        localStorage.removeItem('adminToken');
        localStorage.removeItem('adminData');
        currentAdmin = null;
        currentToken = null;
        showLoginPage();
        showToast('Chiqildi', 'info');
    }
}

// Sahifalarni ko'rsatish
function showLoginPage() {
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    document.getElementById('loginPage').classList.add('active');
}

function showAdminPanel() {
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    
    // Admin ma'lumotlarini yangilash
    if (currentAdmin) {
        document.getElementById('adminName').textContent = currentAdmin.full_name || currentAdmin.username;
        document.getElementById('adminEmail').textContent = currentAdmin.email;
        document.getElementById('adminAvatar').src = `https://ui-avatars.com/api/?name=${encodeURIComponent(currentAdmin.full_name || currentAdmin.username)}&background=4A6FA5&color=fff`;
    }
    
    document.getElementById('dashboardPage').classList.add('active');
    
    // Menuni yangilash
    document.querySelectorAll('.menu li').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector('.menu li[data-page="dashboard"]').classList.add('active');
}

function showPage(pageName) {
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    document.getElementById(`${pageName}Page`).classList.add('active');
    
    // Menuni yangilash
    document.querySelectorAll('.menu li').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.page === pageName) {
            item.classList.add('active');
        }
    });
    
    // Sahifa ma'lumotlarini yuklash
    switch(pageName) {
        case 'users':
            loadUsers();
            break;
        case 'startups':
            loadStartups();
            break;
        case 'statistics':
            loadDetailedStatistics();
            break;
        case 'admins':
            loadAdmins();
            break;
        case 'backup':
            loadBackups();
            break;
    }
}

// Statistikani yuklash
async function loadStatistics() {
    try {
        const response = await fetch(`${API_BASE_URL}/statistics`, {
            headers: {
                'Authorization': `Bearer ${currentToken}`
            }
        });
        
        if (response.ok) {
            const stats = await response.json();
            
            // Statistik kartalarni yangilash
            document.getElementById('totalUsers').textContent = stats.total_users.toLocaleString();
            document.getElementById('totalStartups').textContent = stats.total_startups.toLocaleString();
            document.getElementById('activeStartups').textContent = stats.active_startups.toLocaleString();
            document.getElementById('newToday').textContent = stats.new_users_today + stats.new_startups_today;
            
            // O'sish stavkalari
            document.getElementById('startupTrend').innerHTML = `
                <i class="fas fa-arrow-up"></i>
                <span>${stats.startup_growth_rate}% o'sish</span>
            `;
            
            document.getElementById('activeStartupCount').textContent = `${stats.active_startups} ta`;
            document.getElementById('newUsersToday').textContent = `${stats.new_users_today} user`;
            
            // Faollik darajasi
            const activityRate = stats.user_growth_rate;
            document.getElementById('activityRate').textContent = `${activityRate}%`;
            document.getElementById('activityProgress').style.width = `${Math.min(activityRate, 100)}%`;
            
            // Chart markazidagi raqam
            document.getElementById('totalStartupsChart').textContent = stats.total_startups;
            
            // Legendani yangilash
            updateDistributionLegend(stats);
        }
    } catch (error) {
        console.error('Stats load error:', error);
    }
}

// Foydalanuvchi o'sishi grafigi
async function loadUserGrowthChart() {
    try {
        const period = document.getElementById('growthFilter').value;
        const response = await fetch(`${API_BASE_URL}/statistics/chart/user_growth?period=${period}`, {
            headers: {
                'Authorization': `Bearer ${currentToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            
            const ctx = document.getElementById('userGrowthChart').getContext('2d');
            
            // Avvalgi grafikni yo'q qilish
            if (userGrowthChart) {
                userGrowthChart.destroy();
            }
            
            userGrowthChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels.map(date => formatDate(date)),
                    datasets: [{
                        label: 'Foydalanuvchilar',
                        data: data.data,
                        borderColor: '#4A6FA5',
                        backgroundColor: 'rgba(74, 111, 165, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.3,
                        pointBackgroundColor: '#4A6FA5',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                label: function(context) {
                                    return `Foydalanuvchilar: ${context.parsed.y.toLocaleString()}`;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            grid: {
                                color: 'rgba(0, 0, 0, 0.05)'
                            },
                            ticks: {
                                callback: function(value) {
                                    return value.toLocaleString();
                                }
                            }
                        },
                        x: {
                            grid: {
                                color: 'rgba(0, 0, 0, 0.05)'
                            }
                        }
                    },
                    interaction: {
                        intersect: false,
                        mode: 'nearest'
                    }
                }
            });
        }
    } catch (error) {
        console.error('Chart load error:', error);
    }
}

// Startap taqsimoti grafigi
async function loadStartupDistributionChart() {
    try {
        const response = await fetch(`${API_BASE_URL}/statistics/chart/startup_distribution`, {
            headers: {
                'Authorization': `Bearer ${currentToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            
            const ctx = document.getElementById('startupDistributionChart').getContext('2d');
            
            // Avvalgi grafikni yo'q qilish
            if (startupDistributionChart) {
                startupDistributionChart.destroy();
            }
            
            startupDistributionChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: data.labels,
                    datasets: [{
                        data: data.data,
                        backgroundColor: data.colors,
                        borderWidth: 0,
                        hoverOffset: 15
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = Math.round((context.parsed / total) * 100);
                                    return `${context.label}: ${context.parsed} (${percentage}%)`;
                                }
                            }
                        }
                    },
                    cutout: '70%'
                }
            });
            
            // Legendani yangilash
            updateDistributionLegendFromChart(data);
        }
    } catch (error) {
        console.error('Distribution chart error:', error);
    }
}

// Faollik grafigi
async function loadActivityChart() {
    try {
        const period = document.getElementById('statsPeriod').value;
        const response = await fetch(`${API_BASE_URL}/statistics/chart/activity?period=${period}`, {
            headers: {
                'Authorization': `Bearer ${currentToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            
            const ctx = document.getElementById('activityChart').getContext('2d');
            
            // Avvalgi grafikni yo'q qilish
            if (activityChart) {
                activityChart.destroy();
            }
            
            activityChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels.map(date => formatDate(date)),
                    datasets: data.datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(0, 0, 0, 0.05)'
                            }
                        },
                        x: {
                            grid: {
                                color: 'rgba(0, 0, 0, 0.05)'
                            }
                        }
                    }
                }
            });
        }
    } catch (error) {
        console.error('Activity chart error:', error);
    }
}

// Legendani yangilash
function updateDistributionLegend(stats) {
    const legend = document.getElementById('distributionLegend');
    const statuses = [
        { label: 'Faol', value: stats.active_startups, color: '#4A6FA5', type: 'active' },
        { label: 'Kutilayotgan', value: stats.pending_startups, color: '#FF9F40', type: 'pending' },
        { label: 'Yakunlangan', value: stats.completed_startups, color: '#6DC5A3', type: 'completed' },
        { label: 'Rad etilgan', value: stats.rejected_startups, color: '#E74C3C', type: 'rejected' }
    ];
    
    let html = '';
    const total = stats.total_startups;
    
    statuses.forEach(status => {
        if (status.value > 0) {
            const percentage = Math.round((status.value / total) * 100);
            html += `
                <div class="dist-item" onclick="filterStartups('${status.type}')">
                    <span class="dist-color" style="background-color: ${status.color};"></span>
                    <div class="dist-info">
                        <span class="dist-label">${status.label}</span>
                        <span class="dist-value">${status.value} (${percentage}%)</span>
                    </div>
                    <button class="dist-action">
                        <i class="fas fa-chevron-right"></i>
                    </button>
                </div>
            `;
        }
    });
    
    legend.innerHTML = html || '<div class="empty-state"><p>Ma\'lumot yo\'q</p></div>';
}

function updateDistributionLegendFromChart(data) {
    const legend = document.getElementById('distributionLegend');
    let html = '';
    const total = data.data.reduce((a, b) => a + b, 0);
    
    data.labels.forEach((label, index) => {
        const value = data.data[index];
        const color = data.colors[index];
        const percentage = Math.round((value / total) * 100);
        
        html += `
            <div class="dist-item" onclick="filterStartups('${label.toLowerCase()}')">
                <span class="dist-color" style="background-color: ${color};"></span>
                <div class="dist-info">
                    <span class="dist-label">${label}</span>
                    <span class="dist-value">${value} (${percentage}%)</span>
                </div>
                <button class="dist-action">
                    <i class="fas fa-chevron-right"></i>
                    </button>
                </div>
        `;
    });
    
    legend.innerHTML = html || '<div class="empty-state"><p>Ma\'lumot yo\'q</p></div>';
}

// Foydalanuvchilarni yuklash
async function loadUsers(page = 1) {
    try {
        currentUsersPage = page;
        const search = document.getElementById('userSearch').value;
        const filter = document.getElementById('userFilter').value;
        
        let url = `${API_BASE_URL}/users?page=${page}&limit=20`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        if (filter !== 'all') url += `&status=${filter}`;
        
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${currentToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            
            // Jadvalni yangilash
            const tableBody = document.getElementById('usersTableBody');
            tableBody.innerHTML = '';
            
            if (data.users.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="7" class="empty-cell">
                            <i class="fas fa-users"></i>
                            <p>Foydalanuvchilar topilmadi</p>
                        </td>
                    </tr>
                `;
            } else {
                data.users.forEach(user => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${user.user_id}</td>
                        <td>${user.first_name || '-'}</td>
                        <td>${user.last_name || '-'}</td>
                        <td>${user.phone || '-'}</td>
                        <td>${formatDate(user.joined_at)}</td>
                        <td><span class="status-badge ${user.status}">${user.status}</span></td>
                        <td>
                            <button class="action-btn view-btn" onclick="viewUser(${user.user_id})" title="Ko'rish">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button class="action-btn edit-btn" onclick="editUserStatus(${user.user_id})" title="Tahrirlash">
                                <i class="fas fa-edit"></i>
                            </button>
                        </td>
                    `;
                    tableBody.appendChild(row);
                });
            }
            
            // Paginationni yangilash
            usersTotalPages = data.pagination.pages;
            updatePagination('usersPagination', page, usersTotalPages, loadUsers);
        }
    } catch (error) {
        console.error('Users load error:', error);
        showToast('Foydalanuvchilarni yuklashda xatolik', 'error');
    }
}

// Startaplarni yuklash
async function loadStartups(page = 1) {
    try {
        currentStartupsPage = page;
        const search = document.getElementById('startupSearch').value;
        const filter = document.getElementById('startupFilter').value;
        
        let url = `${API_BASE_URL}/startups?page=${page}&limit=20`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        if (filter !== 'all') url += `&status=${filter}`;
        
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${currentToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            
            // Jadvalni yangilash
            const tableBody = document.getElementById('startupsTableBody');
            tableBody.innerHTML = '';
            
            if (data.startups.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="7" class="empty-cell">
                            <i class="fas fa-rocket"></i>
                            <p>Startaplar topilmadi</p>
                        </td>
                    </tr>
                `;
            } else {
                data.startups.forEach(startup => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${startup.startup_id}</td>
                        <td>${startup.name}</td>
                        <td>${startup.first_name} ${startup.last_name || ''}</td>
                        <td><span class="status-badge ${startup.status}">${startup.status}</span></td>
                        <td>${formatDate(startup.created_at)}</td>
                        <td>${startup.member_count}</td>
                        <td>
                            <button class="action-btn view-btn" onclick="viewStartup(${startup.startup_id})" title="Ko'rish">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button class="action-btn edit-btn" onclick="editStartup(${startup.startup_id})" title="Tahrirlash">
                                <i class="fas fa-edit"></i>
                            </button>
                            ${currentAdmin.role === 'superadmin' ? `
                            <button class="action-btn delete-btn" onclick="deleteStartup(${startup.startup_id})" title="O'chirish">
                                <i class="fas fa-trash"></i>
                            </button>
                            ` : ''}
                        </td>
                    `;
                    tableBody.appendChild(row);
                });
            }
            
            // Paginationni yangilash
            startupsTotalPages = data.pagination.pages;
            updatePagination('startupsPagination', page, startupsTotalPages, loadStartups);
        }
    } catch (error) {
        console.error('Startups load error:', error);
        showToast('Startaplarni yuklashda xatolik', 'error');
    }
}

// Batafsil statistikani yuklash
async function loadDetailedStatistics() {
    try {
        const period = document.getElementById('statsPeriod').value;
        
        // Umumiy statistikani yuklash
        const statsResponse = await fetch(`${API_BASE_URL}/statistics`, {
            headers: {
                'Authorization': `Bearer ${currentToken}`
            }
        });
        
        if (statsResponse.ok) {
            const stats = await statsResponse.json();
            
            // Foydalanuvchi statistikasi
            document.getElementById('detailedTotalUsers').textContent = stats.total_users.toLocaleString();
            document.getElementById('detailedActiveUsers').textContent = stats.total_users.toLocaleString(); // Assuming all are active
            document.getElementById('detailedNewUsers').textContent = stats.new_users_today.toLocaleString();
            document.getElementById('detailedAvgDailyUsers').textContent = Math.round(stats.users_last_month / 30).toLocaleString();
            
            // Startap statistikasi
            document.getElementById('detailedTotalStartups').textContent = stats.total_startups.toLocaleString();
            document.getElementById('detailedActiveStartups').textContent = stats.active_startups.toLocaleString();
            document.getElementById('detailedNewStartups').textContent = stats.new_startups_today.toLocaleString();
            
            const successRate = stats.total_startups > 0 ? 
                Math.round((stats.completed_startups / stats.total_startups) * 100) : 0;
            document.getElementById('detailedSuccessRate').textContent = `${successRate}%`;
            
            // Faollik grafigini yuklash
            loadActivityChart();
        }
    } catch (error) {
        console.error('Detailed stats error:', error);
    }
}

// Adminlarni yuklash
async function loadAdmins() {
    try {
        const response = await fetch(`${API_BASE_URL}/admins`, {
            headers: {
                'Authorization': `Bearer ${currentToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            
            const tableBody = document.getElementById('adminsTableBody');
            tableBody.innerHTML = '';
            
            if (data.admins.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="7" class="empty-cell">
                            <i class="fas fa-user-shield"></i>
                            <p>Adminlar topilmadi</p>
                        </td>
                    </tr>
                `;
            } else {
                data.admins.forEach(admin => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${admin.id}</td>
                        <td>${admin.username}</td>
                        <td>${admin.full_name}</td>
                        <td>${admin.email}</td>
                        <td><span class="role-badge ${admin.role}">${admin.role}</span></td>
                        <td>${admin.last_login ? formatDate(admin.last_login) : 'Hali kirish yo\'q'}</td>
                        <td>
                            ${currentAdmin.role === 'superadmin' && admin.id !== currentAdmin.id ? `
                            <button class="action-btn delete-btn" onclick="deleteAdmin(${admin.id})" title="O'chirish">
                                <i class="fas fa-trash"></i>
                            </button>
                            ` : '-'}
                        </td>
                    `;
                    tableBody.appendChild(row);
                });
            }
        }
    } catch (error) {
        console.error('Admins load error:', error);
        showToast('Adminlarni yuklashda xatolik', 'error');
    }
}

// Backup yaratish
async function createBackup() {
    if (!confirm('Backup yaratilsinmi?')) return;
    
    try {
        showLoading();
        
        const response = await fetch(`${API_BASE_URL}/backup`, {
            headers: {
                'Authorization': `Bearer ${currentToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            showToast('Backup muvaffaqiyatli yaratildi', 'success');
            
            // Backup ro'yxatini yangilash
            loadBackups();
            
            // Yuklab olish havolasini ochish
            setTimeout(() => {
                window.open(data.download_url, '_blank');
            }, 1000);
        } else {
            const error = await response.json();
            showToast(error.detail || 'Backup yaratish muvaffaqiyatsiz', 'error');
        }
    } catch (error) {
        console.error('Backup error:', error);
        showToast('Server xatosi', 'error');
    } finally {
        hideLoading();
    }
}

// Backup ro'yxatini yuklash
async function loadBackups() {
    // Bu yerda backup fayllar ro'yxatini ko'rsatish mumkin
    // Lekin hozircha oddiy xabar ko'rsatamiz
    document.getElementById('backupHistory').innerHTML = `
        <div class="backup-item">
            <i class="fas fa-database"></i>
            <div class="backup-info">
                <h4>Backup yaratish</h4>
                <p>Backup yaratish uchun yuqoridagi tugmani bosing</p>
            </div>
        </div>
    `;
}

// Xabar yuborish
async function handleBroadcast(e) {
    e.preventDefault();
    
    const message = document.getElementById('messageText').value;
    const userType = document.getElementById('messageType').value;
    
    if (!message.trim()) {
        showToast('Xabar matnini kiriting', 'warning');
        return;
    }
    
    if (!confirm(`Xabar ${getUserTypeName(userType)}ga yuborilsinmi?`)) return;
    
    try {
        showLoading();
        
        const response = await fetch(`${API_BASE_URL}/broadcast`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${currentToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                user_type: userType
            })
        });
        
        if (response.ok) {
            showToast('Xabar yuborish boshlandi', 'success');
            clearMessageForm();
            
            // Xabarlar tarixiga qo'shish
            addToMessageHistory(message, userType);
        } else {
            const error = await response.json();
            showToast(error.detail || 'Xabar yuborish muvaffaqiyatsiz', 'error');
        }
    } catch (error) {
        console.error('Broadcast error:', error);
        showToast('Server xatosi', 'error');
    } finally {
        hideLoading();
    }
}

// Yangi admin qo'shish
async function handleAddAdmin(e) {
    e.preventDefault();
    
    const username = document.getElementById('newAdminUsername').value;
    const password = document.getElementById('newAdminPassword').value;
    const fullName = document.getElementById('newAdminFullName').value;
    const email = document.getElementById('newAdminEmail').value;
    const role = document.getElementById('newAdminRole').value;
    
    try {
        const response = await fetch(`${API_BASE_URL}/admins`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${currentToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username,
                password,
                full_name: fullName,
                email,
                role
            })
        });
        
        if (response.ok) {
            showToast('Admin muvaffaqiyatli qo\'shildi', 'success');
            closeModal();
            loadAdmins();
        } else {
            const error = await response.json();
            showToast(error.detail || 'Admin qo\'shish muvaffaqiyatsiz', 'error');
        }
    } catch (error) {
        console.error('Add admin error:', error);
        showToast('Server xatosi', 'error');
    }
}

// Foydalanuvchini ko'rish
async function viewUser(userId) {
    try {
        const response = await fetch(`${API_BASE_URL}/users/${userId}`, {
            headers: {
                'Authorization': `Bearer ${currentToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            
            const modalContent = document.getElementById('userDetailContent');
            modalContent.innerHTML = `
                <div class="user-detail">
                    <div class="user-header">
                        <div class="user-avatar-large">
                            <img src="https://ui-avatars.com/api/?name=${encodeURIComponent(data.user.first_name + ' ' + data.user.last_name)}&background=4A6FA5&color=fff" alt="User">
                        </div>
                        <div class="user-info-large">
                            <h3>${data.user.first_name} ${data.user.last_name || ''}</h3>
                            <p>ID: ${data.user.user_id}</p>
                            <p>Username: @${data.user.username || 'N/A'}</p>
                        </div>
                    </div>
                    
                    <div class="user-details-grid">
                        <div class="detail-item">
                            <span class="detail-label">Telefon:</span>
                            <span class="detail-value">${data.user.phone || 'N/A'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Jins:</span>
                            <span class="detail-value">${data.user.gender || 'N/A'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Tug'ilgan sana:</span>
                            <span class="detail-value">${data.user.birth_date || 'N/A'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Ro'yxatdan o'tgan sana:</span>
                            <span class="detail-value">${formatDate(data.user.joined_at)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Holati:</span>
                            <span class="detail-value"><span class="status-badge ${data.user.status}">${data.user.status}</span></span>
                        </div>
                    </div>
                    
                    <div class="user-bio">
                        <h4>Bio:</h4>
                        <p>${data.user.bio || 'Bio mavjud emas'}</p>
                    </div>
                    
                    ${data.startups.length > 0 ? `
                    <div class="user-startups">
                        <h4>Startaplar (${data.startups.length}):</h4>
                        <div class="startups-list">
                            ${data.startups.map(startup => `
                                <div class="startup-item">
                                    <span class="startup-name">${startup.name}</span>
                                    <span class="startup-status ${startup.status}">${startup.status}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    ` : ''}
                    
                    <div class="user-actions">
                        <button class="action-btn edit-btn" onclick="editUserStatus(${data.user.user_id})">
                            <i class="fas fa-edit"></i> Holatni o'zgartirish
                        </button>
                    </div>
                </div>
            `;
            
            openModal('userDetailModal');
        }
    } catch (error) {
        console.error('View user error:', error);
        showToast('Foydalanuvchi ma\'lumotlarini yuklashda xatolik', 'error');
    }
}

// Startapni ko'rish
async function viewStartup(startupId) {
    try {
        const response = await fetch(`${API_BASE_URL}/startups/${startupId}`, {
            headers: {
                'Authorization': `Bearer ${currentToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            
            const modalContent = document.getElementById('startupDetailContent');
            modalContent.innerHTML = `
                <div class="startup-detail">
                    <div class="startup-header">
                        <h3>${data.startup.name}</h3>
                        <span class="status-badge ${data.startup.status}">${data.startup.status}</span>
                    </div>
                    
                    <div class="startup-meta">
                        <div class="meta-item">
                            <i class="fas fa-user"></i>
                            <span>Muallif: ${data.startup.first_name} ${data.startup.last_name || ''}</span>
                        </div>
                        <div class="meta-item">
                            <i class="fas fa-calendar"></i>
                            <span>Yaratilgan: ${formatDate(data.startup.created_at)}</span>
                        </div>
                        <div class="meta-item">
                            <i class="fas fa-link"></i>
                            <span>Guruh: <a href="${data.startup.group_link}" target="_blank">${data.startup.group_link}</a></span>
                        </div>
                    </div>
                    
                    <div class="startup-description">
                        <h4>Tavsif:</h4>
                        <p>${data.startup.description || 'Tavsif mavjud emas'}</p>
                    </div>
                    
                    <div class="startup-members">
                        <h4>A'zolar (${data.members.length}):</h4>
                        ${data.members.length > 0 ? `
                        <div class="members-list">
                            ${data.members.map(member => `
                                <div class="member-item">
                                    <span class="member-name">${member.first_name} ${member.last_name || ''}</span>
                                    <span class="member-status ${member.member_status}">${member.member_status}</span>
                                </div>
                            `).join('')}
                        </div>
                        ` : '<p>A\'zolar yo\'q</p>'}
                    </div>
                    
                    <div class="startup-actions">
                        <button class="action-btn edit-btn" onclick="editStartup(${data.startup.startup_id})">
                            <i class="fas fa-edit"></i> Tahrirlash
                        </button>
                        ${currentAdmin.role === 'superadmin' ? `
                        <button class="action-btn delete-btn" onclick="deleteStartup(${data.startup.startup_id})">
                            <i class="fas fa-trash"></i> O'chirish
                        </button>
                        ` : ''}
                    </div>
                </div>
            `;
            
            openModal('startupDetailModal');
        }
    } catch (error) {
        console.error('View startup error:', error);
        showToast('Startap ma\'lumotlarini yuklashda xatolik', 'error');
    }
}

// Admin o'chirish
async function deleteAdmin(adminId) {
    if (!confirm('Adminni o\'chirishni istaysizmi?')) return;
    
    showToast('Bu funksiya hozirda ishlamaydi', 'info');
}

// Startap o'chirish
async function deleteStartup(startupId) {
    if (!confirm('Startapni o\'chirishni istaysizmi?')) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/startups/${startupId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${currentToken}`
            }
        });
        
        if (response.ok) {
            showToast('Startap o\'chirildi', 'success');
            closeModal();
            loadStartups();
        } else {
            const error = await response.json();
            showToast(error.detail || 'O\'chirish muvaffaqiyatsiz', 'error');
        }
    } catch (error) {
        console.error('Delete startup error:', error);
        showToast('Server xatosi', 'error');
    }
}

// Foydalanuvchi holatini o'zgartirish
async function editUserStatus(userId) {
    const newStatus = prompt('Yangi holatni tanlang (active, inactive, banned):');
    if (!newStatus || !['active', 'inactive', 'banned'].includes(newStatus)) {
        showToast('Noto\'g\'ri holat', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/users/${userId}/status`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${currentToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: newStatus })
        });
        
        if (response.ok) {
            showToast('Holat o\'zgartirildi', 'success');
            loadUsers();
            closeModal();
        } else {
            const error = await response.json();
            showToast(error.detail || 'O\'zgartirish muvaffaqiyatsiz', 'error');
        }
    } catch (error) {
        console.error('Edit user error:', error);
        showToast('Server xatosi', 'error');
    }
}

// Startapni tahrirlash
async function editStartup(startupId) {
    const newStatus = prompt('Yangi holatni tanlang (pending, active, completed, rejected):');
    if (!newStatus || !['pending', 'active', 'completed', 'rejected'].includes(newStatus)) {
        showToast('Noto\'g\'ri holat', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/startups/${startupId}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${currentToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: newStatus })
        });
        
        if (response.ok) {
            showToast('Startap holati o\'zgartirildi', 'success');
            loadStartups();
            closeModal();
        } else {
            const error = await response.json();
            showToast(error.detail || 'O\'zgartirish muvaffaqiyatsiz', 'error');
        }
    } catch (error) {
        console.error('Edit startup error:', error);
        showToast('Server xatosi', 'error');
    }
}

// Modal funksiyalari
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
    document.getElementById('modalOverlay').style.display = 'flex';
}

function closeModal() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.style.display = 'none';
    });
    document.getElementById('modalOverlay').style.display = 'none';
}

function openAddAdminModal() {
    document.getElementById('addAdminForm').reset();
    openModal('addAdminModal');
}

// To'liq ekran grafik
function openFullscreenChart(chartId, title) {
    const canvas = document.getElementById(chartId);
    const fullscreenCanvas = document.getElementById('fullscreenChart');
    const ctx = fullscreenCanvas.getContext('2d');
    
    // Grafikni ko'chirish
    fullscreenCanvas.width = canvas.width;
    fullscreenCanvas.height = canvas.height;
    
    // Asl grafikni chiqarish
    const chart = chartId === 'userGrowthChart' ? userGrowthChart : 
                  chartId === 'startupDistributionChart' ? startupDistributionChart :
                  activityChart;
    
    if (chart) {
        fullscreenChart = new Chart(ctx, JSON.parse(JSON.stringify(chart.config)));
    }
    
    document.getElementById('fullscreenChartTitle').textContent = title;
    document.getElementById('fullscreenChartModal').classList.add('active');
}

function closeFullscreenChart() {
    document.getElementById('fullscreenChartModal').classList.remove('active');
    if (fullscreenChart) {
        fullscreenChart.destroy();
        fullscreenChart = null;
    }
}

// Qo'shimcha funksiyalar
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('uz-UZ', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function getUserTypeName(type) {
    const types = {
        'all': 'barcha foydalanuvchilar',
        'startup_owners': 'startap mualliflari',
        'startup_members': 'startap a\'zolari',
        'active': 'faol foydalanuvchilar'
    };
    return types[type] || type;
}

function filterStartups(status) {
    document.getElementById('startupFilter').value = status;
    showPage('startups');
    loadStartups();
}

function clearMessageForm() {
    document.getElementById('messageText').value = '';
}

function addToMessageHistory(message, type) {
    const history = document.getElementById('messageHistory');
    const historyItem = document.createElement('div');
    historyItem.className = 'history-item';
    historyItem.innerHTML = `
        <div class="history-content">
            <p>${message.substring(0, 100)}${message.length > 100 ? '...' : ''}</p>
            <small>${getUserTypeName(type)} • ${new Date().toLocaleTimeString()}</small>
        </div>
    `;
    history.insertBefore(historyItem, history.firstChild);
}

function updatePagination(elementId, currentPage, totalPages, callback) {
    const pagination = document.getElementById(elementId);
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    let html = '';
    
    // Oldingi tugma
    if (currentPage > 1) {
        html += `<button class="pagination-btn" onclick="${callback.name}(${currentPage - 1})"><i class="fas fa-chevron-left"></i></button>`;
    }
    
    // Sahifa raqamlari
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, startPage + 4);
    
    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="pagination-btn ${i === currentPage ? 'active' : ''}" onclick="${callback.name}(${i})">${i}</button>`;
    }
    
    // Keyingi tugma
    if (currentPage < totalPages) {
        html += `<button class="pagination-btn" onclick="${callback.name}(${currentPage + 1})"><i class="fas fa-chevron-right"></i></button>`;
    }
    
    pagination.innerHTML = html;
}

function searchUsers() {
    loadUsers(1);
}

function searchStartups() {
    loadStartups(1);
}

function exportChart(chartType) {
    showToast('Eksport qilish tez orada qo\'shiladi', 'info');
}

function exportUsers() {
    showToast('Foydalanuvchilarni eksport qilish tez orada qo\'shiladi', 'info');
}

function exportStartups() {
    showToast('Startaplarni eksport qilish tez orada qo\'shiladi', 'info');
}

function showLoading() {
    document.getElementById('loadingScreen').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingScreen').style.display = 'none';
}

function showToast(message, type = 'info') {
    const backgroundColor = {
        'success': '#27AE60',
        'error': '#E74C3C',
        'warning': '#F39C12',
        'info': '#3498DB'
    }[type];
    
    Toastify({
        text: message,
        duration: 3000,
        gravity: "top",
        position: "right",
        backgroundColor: backgroundColor,
        stopOnFocus: true
    }).showToast();
}

// Window eventlari
window.addEventListener('click', function(e) {
    if (e.target === document.getElementById('modalOverlay')) {
        closeModal();
    }
    
    if (e.target === document.getElementById('fullscreenChartModal')) {
        closeFullscreenChart();
    }
});

// WebSocket ulanishi (agar kerak bo'lsa)
function connectWebSocket() {
    const ws = new WebSocket(WS_URL);
    
    ws.onopen = function() {
        console.log('WebSocket connected');
    };
    
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log('WebSocket message:', data);
        // Real-time yangilanishlar uchun
    };
    
    ws.onclose = function() {
        console.log('WebSocket disconnected');
        // 5 sekunddan keyin qayta ulanish
        setTimeout(connectWebSocket, 5000);
    };
    
    ws.onerror = function(error) {
        console.error('WebSocket error:', error);
    };
}

// Dastlabki WebSocket ulanishi
// connectWebSocket();