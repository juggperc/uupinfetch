const translations = {
    en: {
        appName: "Youpin CS2",
        navHome: "Home",
        navSearch: "Search",
        navAPI: "API",
        heroTitle1: "Track CS2 Skin Prices",
        heroTitle2: "Across Markets",
        heroSubtitle: "Real-time price data from Youpin and Buff163. Built for traders who need the edge.",
        ctaSearch: "Search Items",
        ctaAPI: "API Docs",
        cardYoupinDesc: "Lease & trade CS2 skins on China's leading rental marketplace",
        cardBuffDesc: "China's largest CS2 skin trading platform with deep liquidity",
        cardAPIDesc: "Clean REST API with auto-generated docs. Deploy anywhere.",
        featuresTitle: "What You Get",
        featPriceTitle: "Price History",
        featPriceDesc: "Track price trends over time with interactive charts. Spot the perfect buy and sell moments.",
        featSearchTitle: "Smart Search",
        featSearchDesc: "Search across multiple marketplaces instantly. Find the best deals without switching tabs.",
        featDeployTitle: "Easy Deploy",
        featDeployDesc: "One Docker command and you're live. Run on your machine or any VPS worldwide.",
        featI18nTitle: "CN / EN",
        featI18nDesc: "Built for Chinese and Western traders. Switch languages instantly with one click.",
        apiPreviewTitle: "Simple API",
        apiPreviewDesc: "Get started in seconds. No API keys required for basic usage.",
        popularTitle: "Trending Now",
        ctaTitle: "Ready to trade smarter?",
        ctaSubtitle: "Deploy your own instance in under 60 seconds.",
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
        navAPI: "API文档",
        heroTitle1: "追踪 CS2 饰品价格",
        heroTitle2: "跨平台比价",
        heroSubtitle: "实时获取悠悠有品和 Buff163 价格数据。为追求优势的 traders 打造。",
        ctaSearch: "搜索饰品",
        ctaAPI: "API 文档",
        cardYoupinDesc: "在中国领先的饰品租赁平台上租赁和交易 CS2 饰品",
        cardBuffDesc: "中国最大的 CS2 饰品交易平台，流动性深厚",
        cardAPIDesc: "简洁的 REST API，自动生成文档。随处部署。",
        featuresTitle: "功能亮点",
        featPriceTitle: "价格历史",
        featPriceDesc: "通过交互式图表追踪价格趋势。把握最佳买卖时机。",
        featSearchTitle: "智能搜索",
        featSearchDesc: "瞬间跨平台搜索。无需切换标签页即可找到最优交易。",
        featDeployTitle: "轻松部署",
        featDeployDesc: "一条 Docker 命令即可上线。在你的电脑或任何 VPS 上运行。",
        featI18nTitle: "中 / 英",
        featI18nDesc: "为中西方 traders 打造。一键切换语言。",
        apiPreviewTitle: "简洁 API",
        apiPreviewDesc: "几秒钟即可上手。基础使用无需 API 密钥。",
        popularTitle: "热门趋势",
        ctaTitle: "准备更聪明地交易？",
        ctaSubtitle: "60 秒内部署你自己的实例。",
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
