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
        // Bot page
        botTitle: "Trading Bot",
        botSubtitle: "Live market analysis, arbitrage & investment signals",
        botRunning: "Running",
        botIdle: "Idle",
        botScanNow: "Scan Now",
        botScanning: "Scanning...",
        botArbitrage: "Arbitrage Ops",
        botRecommendations: "Recommendations",
        botHighConfidence: "High Confidence",
        botAvgRoi: "Avg Expected ROI",
        botMarketInsights: "Market Insights",
        botArbitrageOpps: "Arbitrage Opportunities",
        botInvestmentSignals: "Investment Signals",
        botAllTypes: "All Types",
        botCases: "Cases",
        botStickers: "Stickers",
        botSkins: "Skins",
        botNoInsights: "No insights yet. The bot is warming up and analyzing market data...",
        botNoArbitrage: "No arbitrage opportunities right now. The bot scans every minute for price gaps across marketplaces.",
        botNoRecommendations: "No recommendations yet. The bot is analyzing cases, stickers, and skin trends.",
        botWatchlist: "Price Watchlist",
        botAddWatchlist: "Add to Watchlist",
        botWatchlistEmpty: "Your watchlist is empty. Add items to get price alerts.",
        botExportCsv: "Export CSV",
        botHistory: "Opportunity History",
        botHistoryEmpty: "No history recorded yet. Run a scan to start tracking.",
        botHelpTitle: "How It Works",
        botHelpText: "The trading bot scans Steam, Buff163, Youpin, and Skinport for price differences and investment opportunities. Results update automatically every 30 seconds.",
        botLastScan: "Last scan",
        botScanNumber: "Scan #",
        // Dashboard
        dashTitle: "Dashboard",
        dashSubtitle: "Monitor scraper status and test API endpoints",
        dashScraperStatus: "Scraper Status",
        dashDbItems: "Items in DB",
        dashVersion: "Server Version",
        dashQuickLinks: "Quick Links",
        dashSearchItems: "Search Items",
        dashSearchDesc: "Browse CS2 skins across marketplaces",
        dashApiDocs: "API Docs",
        dashApiDesc: "Explore endpoints and try requests",
        dashGithub: "GitHub",
        dashGithubDesc: "Source code, issues, and bot examples",
        dashApiTest: "Quick API Test",
        dashSendRequest: "Send Request",
        dashBotIntegration: "Trading Bot Integration",
        dashBotIntegrationDesc: "Connect your trading bot to this API. All endpoints are open — no auth required.",
        dashScraperHealth: "Scraper Health",
        // Item detail
        itemAddWatchlist: "Add to Watchlist",
        itemCopyName: "Copy Name",
        itemViewOnMarket: "View on Marketplace",
        itemNoPriceHistory: "No price history available for this source.",
        itemStats: "Item Stats",
        // Search
        searchQuick: "Quick Search",
        searchResultsFor: "Results for",
        searchSortBy: "Sort by",
        searchSortPriceAsc: "Price: Low to High",
        searchSortPriceDesc: "Price: High to Low",
        searchSortName: "Name",
        searchVolume: "listings",
        // Watchlist
        watchItemName: "Item Name",
        watchTargetPrice: "Target Price",
        watchCondition: "Condition",
        watchBelow: "Below",
        watchAbove: "Above",
        watchAdd: "Add Alert",
        watchRemove: "Remove",
        // Generic
        errorGeneric: "Something went wrong. Please try again.",
        successSaved: "Saved successfully.",
        successDeleted: "Deleted successfully.",
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
        // Bot page
        botTitle: "交易机器人",
        botSubtitle: "实时市场分析、套利与投资信号",
        botRunning: "运行中",
        botIdle: "待机",
        botScanNow: "立即扫描",
        botScanning: "扫描中...",
        botArbitrage: "套利机会",
        botRecommendations: "投资建议",
        botHighConfidence: "高置信度",
        botAvgRoi: "平均预期收益",
        botMarketInsights: "市场洞察",
        botArbitrageOpps: "套利机会",
        botInvestmentSignals: "投资信号",
        botAllTypes: "全部类型",
        botCases: "武器箱",
        botStickers: "印花",
        botSkins: "皮肤",
        botNoInsights: "暂无洞察。机器人正在预热并分析市场数据...",
        botNoArbitrage: "当前无套利机会。机器人每分钟扫描跨平台价差。",
        botNoRecommendations: "暂无建议。机器人正在分析武器箱、印花和皮肤趋势。",
        botWatchlist: "价格监控",
        botAddWatchlist: "添加监控",
        botWatchlistEmpty: "监控列表为空。添加物品以接收价格提醒。",
        botExportCsv: "导出 CSV",
        botHistory: "机会历史",
        botHistoryEmpty: "尚无记录。运行扫描以开始追踪。",
        botHelpTitle: "工作原理",
        botHelpText: "交易机器人扫描 Steam、Buff163、悠悠有品和 Skinport 的价格差异和投资机会。结果每 30 秒自动更新。",
        botLastScan: "上次扫描",
        botScanNumber: "扫描 #",
        // Dashboard
        dashTitle: "控制台",
        dashSubtitle: "监控抓取器状态并测试 API 接口",
        dashScraperStatus: "抓取器状态",
        dashDbItems: "数据库物品",
        dashVersion: "服务器版本",
        dashQuickLinks: "快捷入口",
        dashSearchItems: "搜索饰品",
        dashSearchDesc: "浏览跨平台的 CS2 皮肤",
        dashApiDocs: "API 文档",
        dashApiDesc: "探索接口并测试请求",
        dashGithub: "GitHub",
        dashGithubDesc: "源代码、问题和机器人示例",
        dashApiTest: "快速 API 测试",
        dashSendRequest: "发送请求",
        dashBotIntegration: "交易机器人集成",
        dashBotIntegrationDesc: "将您的交易机器人连接到此 API。所有接口均为开放 — 无需认证。",
        dashScraperHealth: "抓取器健康",
        // Item detail
        itemAddWatchlist: "添加监控",
        itemCopyName: "复制名称",
        itemViewOnMarket: "前往市场",
        itemNoPriceHistory: "该来源暂无价格历史。",
        itemStats: "物品属性",
        // Search
        searchQuick: "快速搜索",
        searchResultsFor: "搜索结果",
        searchSortBy: "排序方式",
        searchSortPriceAsc: "价格从低到高",
        searchSortPriceDesc: "价格从高到低",
        searchSortName: "名称",
        searchVolume: "个在售",
        // Watchlist
        watchItemName: "物品名称",
        watchTargetPrice: "目标价格",
        watchCondition: "条件",
        watchBelow: "低于",
        watchAbove: "高于",
        watchAdd: "添加提醒",
        watchRemove: "删除",
        // Generic
        errorGeneric: "出错了，请重试。",
        successSaved: "保存成功。",
        successDeleted: "删除成功。",
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
    // Update tooltips that use i18n
    document.querySelectorAll('[data-i18n-tooltip]').forEach(el => {
        const key = el.getAttribute('data-i18n-tooltip');
        if (texts[key]) el.setAttribute('data-tooltip', texts[key]);
    });
}

function updateLangButton() {
    const btns = [document.getElementById('langBtn'), document.getElementById('langBtnMobile')];
    btns.forEach(btn => { if (btn) btn.textContent = currentLang === 'en' ? 'CN' : 'EN'; });
}

function getText(key) {
    return translations[currentLang]?.[key] || translations['en']?.[key] || key;
}

document.addEventListener('DOMContentLoaded', () => {
    applyTranslations();
    updateLangButton();
});