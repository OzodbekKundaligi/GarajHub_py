// Asosiy o'zgaruvchilar
let currentAdmin = null
let currentToken = null
let userGrowthChart = null
let startupDistributionChart = null
let activityChart = null
let fullscreenChart = null
let currentUsersPage = 1
let currentStartupsPage = 1
let usersTotalPages = 1
let startupsTotalPages = 1

// Dastlabki sozlamalar
const API_BASE_URL =
	process.env.NEXT_PUBLIC_API_URL || window.location.origin + '/api'
const WS_URL = window.location.origin.replace('http', 'ws') + '/ws'

// Dastlabki yuklash
document.addEventListener('DOMContentLoaded', function () {
	checkAuthStatus()
	setupEventListeners()
	initTheme()
})

// Auth holatini tekshirish
async function checkAuthStatus() {
	const token = localStorage.getItem('adminToken')
	if (token) {
		try {
			const response = await fetch(`${API_BASE_URL}/auth/me`, {
				headers: {
					Authorization: `Bearer ${token}`,
				},
			})

			if (response.ok) {
				currentAdmin = await response.json()
				currentToken = token
				showAdminPanel()
				loadStatistics()
				loadUserGrowthChart()
				loadStartupDistributionChart()
			} else {
				showLoginPage()
			}
		} catch (error) {
			console.error('Auth check error:', error)
			showLoginPage()
		}
	} else {
		showLoginPage()
	}
}

// Event listenerlarni sozlash
function setupEventListeners() {
	// Login form
	document.getElementById('loginForm').addEventListener('submit', handleLogin)

	// Parolni ko'rsatish/yashirish
	document
		.getElementById('togglePassword')
		.addEventListener('click', function () {
			const passwordInput = document.getElementById('loginPassword')
			const icon = this.querySelector('i')
			if (passwordInput.type === 'password') {
				passwordInput.type = 'text'
				icon.className = 'fas fa-eye-slash'
			} else {
				passwordInput.type = 'password'
				icon.className = 'fas fa-eye'
			}
		})

	// Logout
	document.getElementById('logoutBtn').addEventListener('click', handleLogout)

	// Menu toggle
	document.getElementById('menuToggle').addEventListener('click', function () {
		document.querySelector('.sidebar').classList.toggle('collapsed')
	})

	// Menu items
	document.querySelectorAll('.menu li').forEach(item => {
		item.addEventListener('click', function (e) {
			e.preventDefault()
			const page = this.dataset.page
			if (page) {
				showPage(page)
			}
		})
	})

	// Theme toggle
	document
		.getElementById('themeToggle')
		.addEventListener('change', function () {
			if (this.checked) {
				document.body.setAttribute('data-theme', 'dark')
				localStorage.setItem('theme', 'dark')
			} else {
				document.body.setAttribute('data-theme', 'light')
				localStorage.setItem('theme', 'light')
			}
		})

	// Broadcast form
	document
		.getElementById('broadcastForm')
		.addEventListener('submit', handleBroadcast)

	// Add admin form
	document
		.getElementById('addAdminForm')
		.addEventListener('submit', handleAddAdmin)
}

// Mavzu sozlamalari
function initTheme() {
	const savedTheme = localStorage.getItem('theme') || 'light'
	document.body.setAttribute('data-theme', savedTheme)
	document.getElementById('themeToggle').checked = savedTheme === 'dark'
}

// Login qilish
async function handleLogin(e) {
	e.preventDefault()

	const username = document.getElementById('loginUsername').value
	const password = document.getElementById('loginPassword').value

	try {
		showLoading()

		const response = await fetch(`${API_BASE_URL}/auth/login`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify({ username, password }),
		})

		if (response.ok) {
			const data = await response.json()
			currentAdmin = data.admin
			currentToken = data.access_token

			localStorage.setItem('adminToken', data.access_token)
			localStorage.setItem('adminData', JSON.stringify(data.admin))

			showAdminPanel()
			loadStatistics()
			showToast('Muvaffaqiyatli kirildi!', 'success')
		} else {
			const error = await response.json()
			showToast(error.detail || 'Kirish muvaffaqiyatsiz', 'error')
		}
	} catch (error) {
		console.error('Login error:', error)
		showToast('Server xatosi', 'error')
	} finally {
		hideLoading()
	}
}

// (rest of app.js unchanged)
