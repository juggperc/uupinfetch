const translations = {
    en: {
        appName: "Youpin CS2",
        navHome: "Home",
        navSearch: "Search",
        navPricing: "Pricing",
        navAPI: "API",
        navDashboard: "Dashboard",
        navLogin: "Sign In",
        loginTitle: "Welcome Back",
        loginSubtitle: "Sign in to access your API keys and billing",
        email: "Email",
        password: "Password",
        loginBtn: "Sign In",
        noAccount: "Don't have an account?",
        registerLink: "Sign Up",
        registerTitle: "Create Account",
        registerSubtitle: "Get your API key and start scraping in minutes",
        name: "Name",
        registerBtn: "Create Account",
        haveAccount: "Already have an account?",
        loginLink: "Sign In",
        pricingTitle: "Simple Pricing",
        pricingSubtitle: "Start free. Upgrade when you need more power.",
        getStarted: "Get Started",
        upgradePro: "Upgrade to Pro",
        contactSales: "Contact Sales",
        footer: "Youpin CS2 Scraper · Built for traders",
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
    },
    cn: {
        appName: "悠悠有品 CS2",
        navHome: "首页",
        navSearch: "搜索",
        navPricing: "价格",
        navAPI: "API文档",
        navDashboard: "控制台",
        navLogin: "登录",
        loginTitle: "欢迎回来",
        loginSubtitle: "登录以访问 API 密钥和账单",
        email: "邮箱",
        password: "密码",
        loginBtn: "登录",
        noAccount: "还没有账号？",
        registerLink: "注册",
        registerTitle: "创建账号",
        registerSubtitle: "获取 API 密钥，几分钟内开始抓取",
        name: "姓名",
        registerBtn: "创建账号",
        haveAccount: "已有账号？",
        loginLink: "登录",
        pricingTitle: "简单定价",
        pricingSubtitle: "免费开始。需要更多功能时升级。",
        getStarted: "开始使用",
        upgradePro: "升级到 Pro",
        contactSales: "联系销售",
        footer: "悠悠有品 CS2 数据 · 为交易者打造",
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
        if (texts[key]) {
            el.textContent = texts[key];
        }
    });
    
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (texts[key]) {
            el.placeholder = texts[key];
        }
    });
}

function updateLangButton() {
    const btn = document.getElementById('langBtn');
    if (btn) {
        btn.textContent = currentLang === 'en' ? 'CN' : 'EN';
    }
}

// Apply on load
document.addEventListener('DOMContentLoaded', () => {
    applyTranslations();
    updateLangButton();
});
