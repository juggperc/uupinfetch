const translations = {
    en: {
        appName: "CS2 Scraper",
        navSearch: "Search",
        navAPI: "API",
        navDashboard: "Dashboard",
        searchTitle: "Search CS2 Items",
        searchPlaceholder: "Search for AK-47, knives, gloves...",
        searchBtn: "Search",
        sourceAll: "All Sources",
        loading: "Loading...",
        noResults: "No items found. Try a different search.",
        prev: "Previous",
        next: "Next",
        price: "Price",
        leasePrice: "Lease Price",
        deposit: "Deposit",
        seller: "Seller",
        priceHistory: "Price History",
        priceCompare: "Price Comparison",
        compareNote: "Cross-market comparison requires auth for Buff/Youpin",
        lowestPrice: "Lowest Price",
        paintSeed: "Paint Seed",
        paintIndex: "Paint Index",
        wear: "Wear",
        backToSearch: "Back to Search",
        itemNotFound: "Item not found.",
        loginTitle: "Welcome Back",
        loginSubtitle: "Sign in to access your dashboard",
        email: "Email",
        password: "Password",
        loginBtn: "Sign In",
        noAccount: "Don't have an account?",
        registerLink: "Sign Up",
        registerTitle: "Create Account",
        registerSubtitle: "Get started with the scraper",
        name: "Name",
        registerBtn: "Create Account",
        haveAccount: "Already have an account?",
        loginLink: "Sign In",
    },
    cn: {
        appName: "CS2 抓取器",
        navSearch: "搜索",
        navAPI: "API文档",
        navDashboard: "控制台",
        searchTitle: "搜索 CS2 饰品",
        searchPlaceholder: "搜索 AK-47、匕首、手套...",
        searchBtn: "搜索",
        sourceAll: "全部来源",
        loading: "加载中...",
        noResults: "未找到物品。尝试其他搜索。",
        prev: "上一页",
        next: "下一页",
        price: "价格",
        leasePrice: "租赁价格",
        deposit: "押金",
        seller: "卖家",
        priceHistory: "价格历史",
        priceCompare: "价格对比",
        compareNote: "Buff/Youpin 跨平台比价需要登录认证",
        lowestPrice: "最低价格",
        paintSeed: "图案种子",
        paintIndex: "图案编号",
        wear: "磨损度",
        backToSearch: "返回搜索",
        itemNotFound: "未找到物品。",
        loginTitle: "欢迎回来",
        loginSubtitle: "登录以访问控制台",
        email: "邮箱",
        password: "密码",
        loginBtn: "登录",
        noAccount: "还没有账号？",
        registerLink: "注册",
        registerTitle: "创建账号",
        registerSubtitle: "开始使用抓取器",
        name: "姓名",
        registerBtn: "创建账号",
        haveAccount: "已有账号？",
        loginLink: "登录",
    }
};

let currentLang = localStorage.getItem('lang') || 'en';

function toggleLang() {
    currentLang = currentLang === 'en' ? 'cn' : 'en';
    localStorage.setItem('lang', currentLang);
    applyTranslations();
    updateLangButton();
}

function applyTranslations() {
    const texts = translations[currentLang];
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (texts[key]) el.textContent = texts[key];
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (texts[key]) el.placeholder = texts[key];
    });
}

function updateLangButton() {
    const btn = document.getElementById('langBtn');
    if (btn) btn.textContent = currentLang === 'en' ? 'CN' : 'EN';
}

document.addEventListener('DOMContentLoaded', () => {
    applyTranslations();
    updateLangButton();
});
