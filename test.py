import os
import time
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

SERVER_URLS = [u.strip() for u in os.getenv("WEIRDHOST_SERVER_URLS", "").split(",") if u.strip()]
EMAIL = os.getenv("WEIRDHOST_EMAIL")
PASSWORD = os.getenv("WEIRDHOST_PASSWORD")
REMEMBER_COOKIE = os.getenv("REMEMBER_WEB_COOKIE")

TZ_CN = timezone(timedelta(hours=8))


def now_cn():
    return datetime.now(TZ_CN).strftime("%Y-%m-%d %H:%M:%S")


def screenshot(page, name):
    os.makedirs("screenshots", exist_ok=True)
    path = f"screenshots/{name}.png"
    page.screenshot(path=path, full_page=True)
    print(f"📸 已保存截图: {path}")


def wait_cf_challenge(page):
    # Cloudflare 五秒盾 / 包装页
    if page.locator("text=Cloudflare").count() > 0:
        print("🛡️ 检测到 Cloudflare，等待 15 秒")
        page.wait_for_timeout(15000)


def get_expire_text(page):
    """
    获取『유통기한 xxxx』文本
    """
    selectors = [
        "text=/유통기한\\s*\\d{4}-\\d{2}-\\d{2}/",
        "text=/Expire/i",
        "text=/到期/",
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0:
                return loc.inner_text().strip()
        except:
            pass
    return None


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


def wait_server_page_ready(page):
    """
    判断是否真的进入了服务器控制页
    """
    try:
        page.wait_for_selector("button", timeout=15000)
        return True
    except PlaywrightTimeoutError:
        return False


def find_renew_button(page):
    """
    超宽松 selector，避免 WeirdHost UI / 语言变化
    """
    selectors = [
        'button:has-text("시간")',
        'button:has-text("추가")',
        'button:has-text("Add")',
        'button:has-text("Time")',
        'button svg',          # 图标按钮兜底
    ]
    for sel in selectors:
        loc = page.locator(sel)
        if loc.count() > 0:
            return loc.first
    return None


def renew_server(page, server_url):
    print(f"\n🚀 处理服务器: {server_url}")
    page.goto(server_url, timeout=60000)
    wait_cf_challenge(page)

    if not wait_server_page_ready(page):
        print("❌ 页面未加载到服务器控制页")
        screenshot(page, "page_not_ready")
        return "page_not_ready"

    before_expire = get_expire_text(page)
    print("📅 续期前到期时间:", before_expire)

    if before_expire is None:
        print("⚠️ 未读取到到期时间，截图")
        screenshot(page, "expire_not_found_before")

    renew_btn = find_renew_button(page)
    if not renew_btn:
        print("❌ 未找到续期按钮，截图")
        screenshot(page, "no_renew_button")
        return "no_button"

    popup_success = False
    expire_changed = False

    try:
        renew_btn.click()
        print("🖱️ 已点击续期按钮")
    except PlaywrightTimeoutError:
        print("❌ 点击续期按钮超时")
        screenshot(page, "click_timeout")
        return "click_failed"

    # 等待“成功”弹窗（你截图里的那个）
    try:
        page.locator("text=成功").wait_for(timeout=8000)
        popup_success = True
        print("🎉 捕获到『成功』弹窗")
    except PlaywrightTimeoutError:
        print("⚠️ 未检测到成功弹窗")

    page.wait_for_timeout(3000)
    page.reload()
    wait_cf_challenge(page)

    after_expire = get_expire_text(page)
    print("📅 续期后到期时间:", after_expire)

    if after_expire is None:
        screenshot(page, "expire_not_found_after")

    if before_expire and after_expire and before_expire != after_expire:
        popup_success = True
        expire_changed = True
        print("✅ 到期时间发生变化")

    if popup_success or expire_changed:
        return "renew_confirmed"

    screenshot(page, "renew_clicked_but_not_effective")
    return "renew_clicked_but_not_effective"


def main():
    print(f"🕒 开始执行 WeirdHost 自动续期 | {now_cn()}")

    if not SERVER_URLS:
        raise RuntimeError("❌ 未配置 WEIRDHOST_SERVER_URLS")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        login(page)

        results = {}
        for url in SERVER_URLS:
            results[url] = renew_server(page, url)

        browser.close()

    print("\n📊 执行结果汇总:")
    for k, v in results.items():
        print(f" - {k}: {v}")

    print("\n🎉 脚本执行完毕")


if __name__ == "__main__":
    main()
