#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Weirdhost 续期 + 启动（最终排错截图版）
- 每个关键步骤自动截图
- 用于 GitHub Actions 精准排错
"""

import os
import sys
import time
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright, TimeoutError


class WeirdhostAuto:
    def __init__(self):
        self.url = os.getenv('WEIRDHOST_URL', 'https://hub.weirdhost.xyz')
        self.server_urls = os.getenv('WEIRDHOST_SERVER_URLS', '')
        self.login_url = os.getenv('WEIRDHOST_LOGIN_URL', 'https://hub.weirdhost.xyz/auth/login')

        self.remember_web_cookie = os.getenv('REMEMBER_WEB_COOKIE', '')
        self.email = os.getenv('WEIRDHOST_EMAIL', '')
        self.password = os.getenv('WEIRDHOST_PASSWORD', '')

        self.headless = os.getenv('HEADLESS', 'true').lower() == 'true'

        self.server_list = [u.strip() for u in self.server_urls.split(',') if u.strip()]
        self.server_results = {}

    # ---------- 工具 ----------

    def log(self, msg, level="INFO"):
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {level}: {msg}")

    def screenshot(self, page, name):
        try:
            os.makedirs("screenshots", exist_ok=True)
            path = f"screenshots/{name}.png"
            page.screenshot(path=path, full_page=True)
            self.log(f"📸 截图保存: {path}")
        except Exception as e:
            self.log(f"截图失败: {e}", "WARNING")

    # ---------- 登录 ----------

    def login_with_cookie(self, context, page):
        self.log("尝试 Cookie 登录")
        context.add_cookies([{
            'name': 'remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d',
            'value': self.remember_web_cookie,
            'domain': 'hub.weirdhost.xyz',
            'path': '/',
            'secure': True,
            'httpOnly': True
        }])
        page.goto(self.url, wait_until="domcontentloaded")
        time.sleep(5)
        self.screenshot(page, "login_home")
        return "login" not in page.url and "auth" not in page.url

    # ---------- 服务器操作 ----------

    def renew_server(self, page, server_url):
        sid = server_url.split("/")[-1]
        self.log(f"开始续期 {sid}")

        page.goto(server_url, wait_until="networkidle")
        time.sleep(3)
        self.screenshot(page, f"server_{sid}_01_loaded")

        button = page.locator('button:has-text("시간")')
        if not button.count():
            self.screenshot(page, f"server_{sid}_02_no_renew_button")
            return "no_renew_button"

        self.screenshot(page, f"server_{sid}_02_renew_button_found")

        button.first.hover()
        time.sleep(1)
        self.screenshot(page, f"server_{sid}_03_before_renew_click")

        button.first.click()
        time.sleep(5)
        self.screenshot(page, f"server_{sid}_04_after_renew_click")

        page.reload(wait_until="networkidle")
        time.sleep(3)
        self.screenshot(page, f"server_{sid}_05_after_reload")

        return "renew_clicked"

    def start_server(self, page, server_url):
        sid = server_url.split("/")[-1]
        self.log(f"开始启动 {sid}")

        page.reload(wait_until="networkidle")
        time.sleep(3)
        self.screenshot(page, f"server_{sid}_06_start_before")

        button = page.locator('button:has-text("Start")')
        if not button.count():
            self.screenshot(page, f"server_{sid}_06_no_start_button")
            return "no_start_button"

        button.first.hover()
        time.sleep(1)
        button.first.click()
        time.sleep(5)

        self.screenshot(page, f"server_{sid}_07_start_after")
        return "start_clicked"

    # ---------- 主流程 ----------

    def process_server(self, page, url):
        sid = url.split("/")[-1]
        self.server_results[sid] = {}

        self.server_results[sid]['renew'] = self.renew_server(page, url)
        time.sleep(5)
        self.server_results[sid]['start'] = self.start_server(page, url)

    def run(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()

            if not self.login_with_cookie(context, page):
                self.log("❌ Cookie 登录失败", "ERROR")
                sys.exit(1)

            for url in self.server_list:
                self.process_server(page, url)
                time.sleep(8)

            browser.close()


# ---------- 入口 ----------

def main():
    auto = WeirdhostAuto()

    if not auto.remember_web_cookie:
        print("❌ 未设置 REMEMBER_WEB_COOKIE")
        sys.exit(1)

    if not auto.server_list:
        print("❌ 未设置 WEIRDHOST_SERVER_URLS")
        sys.exit(1)

    auto.run()

    print("\n📊 执行结果：")
    for sid, r in auto.server_results.items():
        print(f"{sid} | renew={r['renew']} | start={r['start']}")

    print("\n🎯 截图目录：screenshots/")
    print("👉 请在 GitHub Actions 下载 screenshots 进行人工核对")


if __name__ == "__main__":
    main()
