import os
import time
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

SERVER_URLS = os.getenv("WEIRDHOST_SERVER_URLS", "").split(",")
EMAIL = os.getenv("WEIRDHOST_EMAIL")
PASSWORD = os.getenv("WEIRDHOST_PASSWORD")
REMEMBER_COOKIE = os.getenv("REMEMBER_WEB_COOKIE")

TZ_CN = timezone(timedelta(hours=8))


def now_cn():
    return datetime.now(TZ_CN).strftime("%Y-%m-%d %H:%M:%S")


def get_expire_text(page):
    """
    获取服务器页面上的到期时间文本
    ⚠️ WeirdHost 页面结构可能变，这里多 selector 兜底
    """
    selectors = [
        "text=/유통기한/i",
        "text=/Expire/i",
        "text=/到期/i",
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0:
                return loc.inner_text().strip()
        except:
            pass
    return None


def wait_cf_challenge(page):
    """
    Cloudflare 五秒盾处理
    """
    if page.locator("text=Cloudflare").count() > 0:
        print("🛡️ 检测到 Cloudflare，等待通过...")
        page.wait_for_timeout(15000)


def login(page):
    page.goto("https://hub.weirdhost.xyz/login", timeout=60000)
    wait_cf_challenge(page)

    if REMEMBER_COOKIE:
        print("🍪 使用 Cookie 登录")
        page.context.add_cookies([{
            "name": "remember_web",
            "value": REMEMBER_COOKIE,
            "domain": "hub.weirdhost.xyz",
            "path": "/",
            "httpOnly": True,
            "secure": True
        }])
        page.goto("https://hub.weirdhost.xyz", timeout=60000)
        wait_cf_challenge(page)
        return

    print("🔐 使用账号密码登录")
    page.fill('input[name="email"]', EMAIL)
    page.fill('input[name="password"]', PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_timeout(5000)


def renew_server(page, server_url):
    print(f"\n🚀 处理服务器: {server_url}")
    page.goto(server_url, timeout=60000)
    wait_cf_challenge(page)

    before_expire = get_expire_text(page)
    print("📅 续期前到期时间:", before_expire)

    renew_btn = page.locator('button:has-text("시간추가")')

    if renew_btn.count() == 0:
        print("❌ 未找到续期按钮")
        return "no_button"

    # === 关键修改点 1：监听成功弹窗 ===
    popup_success = False
    expire_changed = False

    try:
        renew_btn.first.click()
        print("🖱️ 已点击续期按钮")
    except PlaywrightTimeoutError:
        print("❌ 点击续期按钮超时")
        return "click_failed"

    # === 关键修改点 2：等待「成功」弹窗 ===
    try:
        page.locator("text=成功").wait_for(timeout=8000)
        popup_success = True
        print("🎉 捕获到『成功』弹窗")
    except PlaywrightTimeoutError:
        print("⚠️ 未检测到成功弹窗")

    # === 关键修改点 3：强制刷新并对比到期时间 ===
    page.wait_for_timeout(3000)
    page.reload()
    wait_cf_challenge(page)

    after_expire = get_expire_text(page)
    print("📅 续期后到期时间:", after_expire)

    if before_expire and after_expire and before_expire != after_expire:
        expire_changed = True
        print("✅ 到期时间发生变化")

    # === 最终判定逻辑（核心） ===
    if popup_success or expire_changed:
        return "renew_confirmed"

    return "renew_clicked_but_not_effective"


def main():
    print(f"🕒 开始执行 WeirdHost 自动续期 | {now_cn()}")

    if not SERVER_URLS or not SERVER_URLS[0]:
        raise RuntimeError("❌ 未配置 WEIRDHOST_SERVER_URLS")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        login(page)

        results = {}

        for url in SERVER_URLS:
            url = url.strip()
            result = renew_server(page, url)
            results[url] = result

        browser.close()

    print("\n📊 执行结果汇总:")
    for k, v in results.items():
        print(f" - {k}: {v}")

    print("\n🎉 脚本执行完毕")


if __name__ == "__main__":
    main()
