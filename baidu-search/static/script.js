/**
 * 仿百度搜索引擎 - 前端交互逻辑
 */

// ============================================
// DOM 元素引用
// ============================================
const homeMode = document.getElementById("homeMode");
const resultMode = document.getElementById("resultMode");
const searchInput = document.getElementById("searchInput");
const searchBtn = document.getElementById("searchBtn");
const resultSearchInput = document.getElementById("resultSearchInput");
const resultSearchBtn = document.getElementById("resultSearchBtn");
const resultsList = document.getElementById("resultsList");
const searchStats = document.getElementById("searchStats");
const pagination = document.getElementById("pagination");
const loadingOverlay = document.getElementById("loadingOverlay");
const emailInput = document.getElementById("emailInput");
const sendEmailBtn = document.getElementById("sendEmailBtn");
const emailStatus = document.getElementById("emailStatus");
const topNav = document.getElementById("topNav");

// 当前状态
let currentQuery = "";
let currentPage = 1;
let allResults = []; // 缓存全部搜索结果（用于邮件发送）
let totalResults = 0;

// ============================================
// 搜索功能
// ============================================
async function performSearch(query, page = 1) {
    if (!query.trim()) return;

    currentQuery = query.trim();
    currentPage = page;

    // 显示加载动画
    showLoading(true);

    // 切换到结果模式
    homeMode.style.display = "none";
    resultMode.style.display = "block";

    try {
        const response = await fetch(
            `/api/search?q=${encodeURIComponent(currentQuery)}&page=${page}`
        );
        const data = await response.json();

        if (data.error) {
            showError(data.error);
            return;
        }

        allResults = data.results;
        totalResults = data.total;

        // 更新两个搜索框的内容
        if (page === 1) {
            resultSearchInput.value = currentQuery;
            searchInput.value = currentQuery;
        }

        renderResults(data);
        renderPagination(data);
        updateSearchStats(data);

        // 滚动到顶部
        window.scrollTo({ top: 0, behavior: "smooth" });

    } catch (err) {
        showError("搜索请求失败，请检查网络连接");
        console.error("搜索错误:", err);
    } finally {
        showLoading(false);
    }
}

// ============================================
// 渲染搜索结果
// ============================================
function renderResults(data) {
    if (!data.results || data.results.length === 0) {
        resultsList.innerHTML = `
            <div style="text-align: center; padding: 60px 20px; color: #999;">
                <p style="font-size: 48px; margin-bottom: 15px;">😕</p>
                <p style="font-size: 16px;">未找到与 "<strong>${escapeHtml(data.query)}</strong>" 相关的结果</p>
                <p style="font-size: 13px; margin-top: 8px;">请尝试更换关键词搜索</p>
            </div>`;
        return;
    }

    let html = "";
    data.results.forEach((r) => {
        html += `
        <div class="result-item">
            <div class="result-title">
                <a href="${escapeHtml(r.url)}" target="_blank" rel="noopener">
                    ${escapeHtml(r.title)}
                </a>
            </div>
            <div class="result-url">
                <cite class="url-cite">${escapeHtml(truncateUrl(r.url))}</cite>
            </div>
            <div class="result-snippet">${highlightKeyword(r.snippet, currentQuery)}</div>
        </div>`;
    });

    resultsList.innerHTML = html;
}

// ============================================
// 搜索统计信息
// ============================================
function updateSearchStats(data) {
    searchStats.innerHTML = `
        找到约 <strong>${data.total}</strong> 条结果，
        搜索关键词：<strong style="color:#c00;">${escapeHtml(data.query)}</strong>
    `;
}

// ============================================
// 分页
// ============================================
function renderPagination(data) {
    const totalPages = Math.ceil(data.total / 10);
    if (totalPages <= 1) {
        pagination.innerHTML = "";
        return;
    }

    let html = "";

    // 上一页
    html += `<button class="page-btn" ${data.page <= 1 ? "disabled" : ""}
              onclick="goToPage(${data.page - 1})">上一页</button>`;

    // 页码
    const startPage = Math.max(1, data.page - 4);
    const endPage = Math.min(totalPages, data.page + 4);

    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="page-btn ${i === data.page ? "active" : ""}"
                  onclick="goToPage(${i})">${i}</button>`;
    }

    // 下一页
    html += `<button class="page-btn" ${!data.has_more ? "disabled" : ""}
              onclick="goToPage(${data.page + 1})">下一页</button>`;

    pagination.innerHTML = html;
}

function goToPage(page) {
    performSearch(currentQuery, page);
    window.scrollTo({ top: 0, behavior: "smooth" });
}

// ============================================
// 发送邮件
// ============================================
async function sendEmail() {
    const email = emailInput.value.trim();

    if (!email) {
        showEmailStatus("请输入邮箱地址", "error");
        emailInput.focus();
        return;
    }

    if (!isValidEmail(email)) {
        showEmailStatus("请输入有效的邮箱地址", "error");
        emailInput.focus();
        return;
    }

    if (allResults.length === 0) {
        showEmailStatus("没有搜索结果可发送", "error");
        return;
    }

    // 发送中
    showEmailStatus("正在发送...", "loading");
    sendEmailBtn.disabled = true;

    try {
        const response = await fetch("/api/send-email", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                email: email,
                query: currentQuery,
                results: allResults,
            }),
        });

        const data = await response.json();

        if (data.success) {
            showEmailStatus("✅ " + data.message, "success");
            emailInput.value = "";
        } else {
            showEmailStatus("❌ " + data.message, "error");
        }
    } catch (err) {
        showEmailStatus("❌ 发送失败，请检查网络连接", "error");
        console.error("邮件发送错误:", err);
    } finally {
        sendEmailBtn.disabled = false;
    }
}

function showEmailStatus(message, type) {
    emailStatus.textContent = message;
    emailStatus.className = "email-status " + type;
}

// ============================================
// 工具函数
// ============================================
function showLoading(show) {
    loadingOverlay.style.display = show ? "flex" : "none";
}

function showError(message) {
    resultsList.innerHTML = `
        <div style="text-align: center; padding: 60px 20px; color: #ff4d4f;">
            <p style="font-size: 48px; margin-bottom: 15px;">⚠️</p>
            <p style="font-size: 16px;">${escapeHtml(message)}</p>
        </div>`;
    searchStats.innerHTML = "";
    pagination.innerHTML = "";
}

function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function truncateUrl(url) {
    if (!url) return "";
    try {
        const u = new URL(url);
        return u.hostname + u.pathname;
    } catch {
        return url.length > 70 ? url.substring(0, 67) + "..." : url;
    }
}

function highlightKeyword(text, keyword) {
    if (!text || !keyword) return escapeHtml(text);
    const escaped = escapeHtml(text);
    const words = keyword.split(/\s+/).filter(Boolean);
    let result = escaped;
    words.forEach((w) => {
        const escapedWord = escapeHtml(w);
        const regex = new RegExp(`(${escapedWord.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi");
        result = result.replace(regex, "<em>$1</em>");
    });
    return result;
}

function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// ============================================
// 事件绑定
// ============================================

// 首页搜索
searchBtn.addEventListener("click", () => {
    performSearch(searchInput.value, 1);
});

searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        performSearch(searchInput.value, 1);
    }
});

// 结果页搜索
resultSearchBtn.addEventListener("click", () => {
    performSearch(resultSearchInput.value, 1);
});

resultSearchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        performSearch(resultSearchInput.value, 1);
    }
});

// 发送邮件按钮
sendEmailBtn.addEventListener("click", sendEmail);

// 邮箱输入框回车发送
emailInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendEmail();
});

// 热门搜索词点击
document.querySelectorAll(".hot-word").forEach((el) => {
    el.addEventListener("click", (e) => {
        e.preventDefault();
        const word = el.textContent.trim();
        searchInput.value = word;
        performSearch(word, 1);
    });
});

// 同步两个搜索框
searchInput.addEventListener("input", () => {
    resultSearchInput.value = searchInput.value;
});

resultSearchInput.addEventListener("input", () => {
    searchInput.value = resultSearchInput.value;
});

// 初始化 - 自动聚焦
searchInput.focus();
