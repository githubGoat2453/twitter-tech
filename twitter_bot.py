import os
import json
import asyncio
import random
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from rich.live import Live
from rich.table import Table
from rich.console import Console

console = Console()

class TwitterBotEngine:
    def __init__(self, cookie_dir="."):
        self.cookie_dir = cookie_dir
        self.accounts = {}

    def discover_accounts(self):
        files = [f for f in os.listdir(self.cookie_dir) if f.endswith(".json") and f != "cookies.json"]
        return files

    def sanitize_cookies(self, raw_cookies):
        cleaned = []
        for c in raw_cookies:
            cookie = {
                "name": c["name"],
                "value": c["value"],
                "domain": c.get("domain", ".x.com"),
                "path": c.get("path", "/"),
            }
            if "secure" in c and c["secure"] is not None:
                cookie["secure"] = bool(c["secure"])
            if "httpOnly" in c and c["httpOnly"] is not None:
                cookie["httpOnly"] = bool(c["httpOnly"])
            if "expirationDate" in c and c["expirationDate"] is not None:
                cookie["expires"] = float(c["expirationDate"])

            same_site = c.get("sameSite")
            if same_site in ["Strict", "Lax"]:
                cookie["sameSite"] = same_site
            elif same_site in ["None", "no_restriction"]:
                cookie["sameSite"] = "None"
            cleaned.append(cookie)
        return cleaned

    def generate_dashboard(self):
        table = Table(title="🐦 X (Twitter) Autonomous Broadcast Engine", style="blue", header_style="bold cyan", expand=True)
        table.add_column("Account File", width=22)
        table.add_column("Current Status", width=44)
        table.add_column("Retries", justify="center", width=8)
        table.add_column("Outcome", style="green", width=25)

        for acc, data in self.accounts.items():
            table.add_row(acc, data["status"], str(data["retries"]), data["outcome"])
        return table

    async def post_tweet(self, browser, account_file, tweet_text, media_path=None, live_display=None, max_retries=3):
        self.accounts[account_file] = {"status": "Initializing session...", "retries": 0, "outcome": "Pending"}
        
        context = await browser.new_context()
        try:
            cookie_path = os.path.join(self.cookie_dir, account_file)
            with open(cookie_path, "r", encoding="utf-8") as f:
                raw_cookies = json.load(f)
                cookies = self.sanitize_cookies(raw_cookies)
                await context.add_cookies(cookies)

            page = await context.new_page()
            stealth = Stealth()
            await stealth.apply_stealth_async(page)

            for attempt in range(1, max_retries + 1):
                self.accounts[account_file]["status"] = f"Navigating to X Home (Attempt {attempt}/{max_retries})"
                self.accounts[account_file]["retries"] = attempt - 1
                if live_display: live_display.update(self.generate_dashboard())

                await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(random.uniform(3.0, 5.0))

                if "login" in page.url or "i/flow/login" in page.url:
                    self.accounts[account_file]["status"] = "[red]Session Expired (Login Required)[/red]"
                    self.accounts[account_file]["outcome"] = "Failed"
                    if live_display: live_display.update(self.generate_dashboard())
                    await context.close()
                    return {"account": account_file, "success": False, "error": "Login required"}

                self.accounts[account_file]["status"] = "Locating post composer..."
                if live_display: live_display.update(self.generate_dashboard())
                
                composer = page.locator('div[aria-label="Post text"], div[aria-label="Tweet text"]').first
                await composer.wait_for(state="visible", timeout=20000)
                await composer.click(force=True)
                await asyncio.sleep(0.5)

                # Word-by-word embedding to trigger blue hashtag formatting
                self.accounts[account_file]["status"] = "Typing text and embedding hashtags..."
                if live_display: live_display.update(self.generate_dashboard())
                
                words = tweet_text.split(" ")
                for word in words:
                    await page.keyboard.type(word + " ", delay=random.randint(40, 90))
                    if word.startswith("#"):
                        # Brief pause to let X's autocomplete/hashtag parser lock in the blue token
                        await asyncio.sleep(random.uniform(0.8, 1.5))
                        try:
                            # Optional check for dropdown menu selection if autocomplete appears
                            dropdown_items = page.locator('[data-testid="TypeaheadUser"], [role="listbox"] div')
                            if await dropdown_items.count() > 0:
                                await page.keyboard.press("Enter")
                        except Exception:
                            pass
                    await asyncio.sleep(random.uniform(0.2, 0.5))

                await asyncio.sleep(random.uniform(1.0, 2.0))

                if media_path and os.path.exists(media_path):
                    self.accounts[account_file]["status"] = "Attaching media payload..."
                    if live_display: live_display.update(self.generate_dashboard())
                    
                    file_input = page.locator('input[type="file"]').first
                    await file_input.set_input_files(media_path)
                    await asyncio.sleep(random.uniform(5.0, 8.0))

                self.accounts[account_file]["status"] = "Triggering broadcast..."
                if live_display: live_display.update(self.generate_dashboard())
                
                post_btn = page.locator('[data-testid="tweetButton"], [data-testid="tweetButtonInline"]').first
                await post_btn.click(force=True)
                await asyncio.sleep(random.uniform(4.0, 6.0))

                self.accounts[account_file]["status"] = "[green]Successfully Published![/green]"
                self.accounts[account_file]["outcome"] = "Live"
                if live_display: live_display.update(self.generate_dashboard())
                
                await context.close()
                return {"account": account_file, "success": True, "outcome": "Published"}

        except Exception as e:
                self.accounts[account_file]["status"] = f"[red]Error: {str(e)[:30]}[/red]"
                self.accounts[account_file]["outcome"] = "Error"
                if live_display: live_display.update(self.generate_dashboard())
                await context.close()
                return {"account": account_file, "success": False, "error": str(e)}

    async def broadcast_macro(self, tweet_text, media_path=None):
        account_files = self.discover_accounts()
        if not account_files:
            console.print("[red]❌ No X account JSON cookie files discovered in directory.[/red]")
            return

        console.print(f"[bold cyan]🚀 Initializing broadcast across {len(account_files)} X account(s)...[/bold cyan]")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage", "--no-sandbox"]
            )

            with Live(self.generate_dashboard(), refresh_per_second=4) as live_display:
                for file in account_files:
                    await self.post_tweet(browser, file, tweet_text, media_path, live_display)
                    cooldown = random.uniform(15.0, 30.0)
                    self.accounts[file]["status"] = f"Account complete. Cooldown ({cooldown:.1f}s)..."
                    live_display.update(self.generate_dashboard())
                    await asyncio.sleep(cooldown)

            await browser.close()
        console.print("[bold green]✨ All X broadcast tasks completed.[/bold green]")
