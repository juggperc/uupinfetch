const translations = {
    en: {
        appName: "CS2 Price Scraper",
        navHome: "Home",
        navSearch: "Search",
        navAPI: "API",
        navDashboard: "Dashboard",
        heroTitle1: "CS2 Price Data",
        heroTitle2: "For Your Bot",
        heroSubtitle: "Open-source scraper that feeds your trading bot real-time prices from Youpin, Buff163, and Steam. Run it locally or on a VPS.",
        ctaSearch: "Search Items",
        ctaAPI: "API Docs",
        cardYoupinDesc: "Lease & trade CS2 skins on China's leading rental marketplace",
        cardBuffDesc: "China's largest CS2 skin trading platform with deep liquidity",
        cardSteamDesc: "Official Steam Community Market - fully public, no auth needed",
        featuresTitle: "Built for Bot Developers",
        featOpenTitle: "Open API",
        featOpenDesc: "No API keys, no rate limits, no auth walls. Just start querying. Perfect for trading bots.",
        featLocalTitle: "Run Local",
        featLocalDesc: "Keep your data private. Run on your machine, a VPS, or a Raspberry Pi. SQLite database included.",
        featCleanTitle: "Clean Code",
        featCleanDesc: "FastAPI + SQLAlchemy + Pydantic. Well-structured, typed, and easy to extend with your own scrapers.",
        featI18nTitle: "CN / EN",
        featI18nDesc: "Built for Chinese and Western traders. Switch languages instantly with one click.",
        apiPreviewTitle: "Simple API",
        apiPreviewDesc: "Zero config. Zero auth. Just query and go.",
        quickStartTitle: "Get Running in 30 Seconds",
        popularTitle: "Trending Now",
        footer: "CS2 Price Scraper · Open source for traders",
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
        appName: "CS2 价格抓取器",
        navHome: "首页",
        navSearch: "搜索",
        navAPI: "API文档",
        navDashboard: "控制台",
        heroTitle1: "CS2 价格数据",
        heroTitle2: "为您的机器人服务",
        heroSubtitle: "开源抓取器，为您的交易机器人提供来自 Youpin、Buff163 和 Steam 的实时价格。本地或 VPS 运行。",
        ctaSearch: "搜索饰品",
        ctaAPI: "API 文档",
        cardYoupinDesc: "在中国领先的饰品租赁平台上租赁和交易 CS2 饰品",
        cardBuffDesc: "中国最大的 CS2 饰品交易平台，流动性深厚",
        cardSteamDesc: "官方 Steam 社区市场 - 完全公开，无需认证",
        featuresTitle: "为机器人开发者打造",
        featOpenTitle: "开放 API",
        featOpenDesc: "无需 API 密钥，无速率限制，无认证墙。直接开始查询。非常适合交易机器人。",
        featLocalTitle: "本地运行",
        featLocalDesc: "保护您的数据隐私。在您的电脑、VPS 或树莓派上运行。内置 SQLite 数据库。",
        featCleanTitle: "整洁代码",
        featCleanDesc: "FastAPI + SQLAlchemy + Pydantic。结构良好、类型安全，易于扩展您自己的抓取器。",
        featI18nTitle: "中 / 英",
        featI18nDesc: "为中西方交易者打造。一键切换语言。",
        apiPreviewTitle: "简洁 API",
        apiPreviewDesc: "零配置。零认证。直接查询即可。",
        quickStartTitle: "30 秒内启动运行",
        popularTitle: "热门趋势",
        footer: "CS2 价格抓取器 · 开源交易工具",
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

document.addEventListener('DOMContentLoaded', () => {
    applyTranslations();
    updateLangButton();
});
