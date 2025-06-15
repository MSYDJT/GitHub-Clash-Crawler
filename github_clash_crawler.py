import requests
import re
import time
import random
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import json
import webbrowser
from datetime import datetime
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup
import os
import math
import logging
from fake_useragent import UserAgent

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GitHubClashCrawler:
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        })
        self.search_queries = [
            "clash",
            "clash config",
            "clash subscription",
            "clash proxies",
            "clash.yaml",
            "clash.yml",
            "clash config file",
            "clash proxy"
        ]
        self.valid_links = []
        self.crawl_stats = {
            "pages_scanned": 0,
            "repos_visited": 0,
            "files_checked": 0,
            "valid_links": 0,
            "start_time": None,
            "end_time": None
        }
        self.stop_requested = False
        
    def rotate_user_agent(self):
        """随机更换User-Agent"""
        new_ua = self.ua.random
        self.session.headers.update({"User-Agent": new_ua})
        logging.info(f"更换User-Agent: {new_ua}")
    
    def simulate_human_delay(self, min_delay=1.0, max_delay=3.0):
        """模拟人类操作延迟"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
    
    def get_page(self, url):
        """获取页面内容"""
        try:
            self.rotate_user_agent()
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            # 检查是否被重定向到验证页面
            if "verify-your-account" in response.url:
                logging.warning("遇到GitHub验证页面，跳过")
                return None
            
            return response.text
        except requests.exceptions.RequestException as e:
            logging.error(f"请求页面失败: {e}")
            return None
    
    def search_github(self, query, page=1):
        """搜索GitHub"""
        url = f"https://github.com/search?q={query}&type=repositories&p={page}"
        logging.info(f"搜索: {query} - 第{page}页")
        return self.get_page(url)
    
    def parse_search_results(self, html):
        """解析搜索结果页面"""
        soup = BeautifulSoup(html, 'html.parser')
        repo_links = []
        
        # 查找仓库结果
        repo_list = soup.find('div', {'data-testid': 'results-list'})
        if not repo_list:
            repo_list = soup.find('ul', class_='repo-list')
        
        if repo_list:
            for repo_item in repo_list.find_all('li'):
                repo_link = repo_item.find('a', class_='v-align-middle')
                if repo_link and 'href' in repo_link.attrs:
                    repo_url = "https://github.com" + repo_link['href']
                    repo_links.append(repo_url)
        
        # 检查是否有下一页
        next_page = soup.find('a', class_='next_page')
        has_next = next_page and 'disabled' not in next_page.get('class', [])
        
        return repo_links, has_next
    
    def visit_repository(self, repo_url):
        """访问仓库页面并查找配置文件"""
        logging.info(f"访问仓库: {repo_url}")
        html = self.get_page(repo_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        file_links = []
        
        # 查找仓库中的文件
        file_table = soup.find('div', role='grid')
        if not file_table:
            file_table = soup.find('table', class_='files')
        
        if file_table:
            for row in file_table.find_all('div', role='row'):
                file_link = row.find('a', class_='js-navigation-open')
                if file_link and 'href' in file_link.attrs:
                    file_name = file_link.text.strip().lower()
                    if any(ext in file_name for ext in ['.yaml', '.yml', '.txt']) and "clash" in file_name:
                        file_url = "https://github.com" + file_link['href']
                        file_links.append(file_url)
        
        # 检查是否有子目录
        for link in soup.find_all('a', class_='js-navigation-open'):
            if 'title' in link.attrs and link['title'].endswith('/'):
                dir_url = "https://github.com" + link['href']
                logging.info(f"发现子目录: {dir_url}")
                file_links.extend(self.visit_repository(dir_url))
        
        return file_links
    
    def check_file(self, file_url):
        """检查文件是否为有效的Clash配置"""
        raw_url = file_url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
        logging.info(f"检查文件: {raw_url}")
        
        self.simulate_human_delay(0.5, 1.5)
        try:
            self.rotate_user_agent()
            response = self.session.get(raw_url, timeout=10)
            response.raise_for_status()
            
            content = response.text[:500]  # 只检查前500个字符
            
            # 验证是否为Clash配置
            if self.is_valid_clash_config(content):
                return raw_url, True
            
            return raw_url, False
        except requests.exceptions.RequestException as e:
            logging.error(f"检查文件失败: {e}")
            return raw_url, False
    
    def is_valid_clash_config(self, content):
        """验证内容是否为有效的Clash配置"""
        # 检查Clash关键字
        clash_keywords = [
            "proxies:", 
            "proxy-groups:", 
            "rules:", 
            "mixed-port:",
            "socks-port:",
            "port:",
            "clash",
            "proxies"
        ]
        
        content_lower = content.lower()
        return any(kw in content_lower for kw in clash_keywords)
    
    def crawl(self, max_pages=3, max_repos=10):
        """执行GitHub爬取过程"""
        self.crawl_stats = {
            "pages_scanned": 0,
            "repos_visited": 0,
            "files_checked": 0,
            "valid_links": 0,
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": None
        }
        
        self.valid_links = []
        self.stop_requested = False
        
        # 搜索GitHub
        for query in self.search_queries:
            if self.stop_requested:
                break
                
            page = 1
            has_next = True
            
            while has_next and page <= max_pages and not self.stop_requested:
                if self.crawl_stats["repos_visited"] >= max_repos:
                    break
                    
                # 执行搜索
                html = self.search_github(query, page)
                if not html:
                    break
                    
                # 解析结果
                repo_links, has_next = self.parse_search_results(html)
                self.crawl_stats["pages_scanned"] += 1
                
                # 访问仓库
                for repo_url in repo_links:
                    if self.stop_requested or self.crawl_stats["repos_visited"] >= max_repos:
                        break
                        
                    # 获取仓库中的文件
                    file_links = self.visit_repository(repo_url)
                    self.crawl_stats["repos_visited"] += 1
                    
                    # 检查文件
                    for file_url in file_links:
                        if self.stop_requested:
                            break
                            
                        file_raw_url, is_valid = self.check_file(file_url)
                        self.crawl_stats["files_checked"] += 1
                        
                        if is_valid:
                            self.valid_links.append(file_raw_url)
                            self.crawl_stats["valid_links"] = len(self.valid_links)
                            logging.info(f"找到有效配置: {file_raw_url}")
                        
                        # 随机延迟
                        self.simulate_human_delay(0.5, 1.5)
                
                page += 1
        
        self.crawl_stats["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self.valid_links


class GitHubCrawlerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GitHub Clash订阅链接爬取工具")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # 设置图标
        try:
            self.root.iconbitmap("github_icon.ico")
        except:
            pass
        
        self.crawler = GitHubClashCrawler()
        self.crawling = False
        self.create_widgets()
    
    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 控制面板
        control_frame = ttk.LabelFrame(main_frame, text="控制面板", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 搜索设置
        ttk.Label(control_frame, text="搜索页数:").grid(row=0, column=0, padx=5, sticky=tk.W)
        self.max_pages = tk.IntVar(value=3)
        ttk.Spinbox(control_frame, from_=1, to=10, textvariable=self.max_pages, width=5).grid(row=0, column=1, padx=5)
        
        ttk.Label(control_frame, text="最大仓库数:").grid(row=0, column=2, padx=5, sticky=tk.W)
        self.max_repos = tk.IntVar(value=10)
        ttk.Spinbox(control_frame, from_=1, to=50, textvariable=self.max_repos, width=5).grid(row=0, column=3, padx=5)
        
        # 按钮区域
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=0, column=4, padx=10, sticky=tk.E)
        
        self.scan_btn = ttk.Button(button_frame, text="开始爬取", command=self.start_crawling, width=12)
        self.scan_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="停止", command=self.stop_crawling, state=tk.DISABLED, width=8)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # 结果展示区域
        result_frame = ttk.LabelFrame(main_frame, text="爬取结果", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建结果文本框和滚动条
        self.result_text = scrolledtext.ScrolledText(
            result_frame, 
            wrap=tk.WORD,
            font=("Consolas", 10)
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)
        self.result_text.insert(tk.END, "就绪。点击'开始爬取'按钮在GitHub上搜索Clash订阅链接。\n")
        self.result_text.configure(state=tk.DISABLED)
        
        # 链接操作区域
        link_frame = ttk.Frame(main_frame)
        link_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(link_frame, text="复制链接", command=self.copy_link).pack(side=tk.LEFT, padx=5)
        ttk.Button(link_frame, text="打开链接", command=self.open_link).pack(side=tk.LEFT, padx=5)
        ttk.Button(link_frame, text="测试链接", command=self.test_link).pack(side=tk.LEFT, padx=5)
        
        # 底部按钮区域
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(bottom_frame, text="保存结果", command=self.save_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="清空结果", command=self.clear_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="查看统计", command=self.show_stats).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="退出", command=self.root.quit).pack(side=tk.RIGHT, padx=5)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 创建进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.root, 
            variable=self.progress_var, 
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def start_crawling(self):
        self.crawling = True
        self.crawler.stop_requested = False
        self.scan_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set("爬取中...")
        self.progress_var.set(0)
        
        self.result_text.configure(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "开始在GitHub上爬取Clash订阅链接...\n")
        self.result_text.insert(tk.END, "这可能需要几分钟时间，请耐心等待...\n\n")
        self.result_text.configure(state=tk.DISABLED)
        
        # 在新线程中运行爬虫
        self.crawling_thread = threading.Thread(target=self.run_crawler)
        self.crawling_thread.daemon = True
        self.crawling_thread.start()
    
    def run_crawler(self):
        max_pages = self.max_pages.get()
        max_repos = self.max_repos.get()
        
        try:
            valid_links = self.crawler.crawl(
                max_pages=max_pages, 
                max_repos=max_repos
            )
            
            self.result_text.configure(state=tk.NORMAL)
            if valid_links:
                self.result_text.insert(tk.END, "\n找到的有效Clash订阅链接:\n")
                for i, link in enumerate(valid_links, 1):
                    self.result_text.insert(tk.END, f"{i}. {link}\n")
                self.result_text.insert(tk.END, f"\n共找到 {len(valid_links)} 个有效链接\n")
            else:
                self.result_text.insert(tk.END, "\n未找到有效的Clash订阅链接。\n")
            
            self.result_text.configure(state=tk.DISABLED)
            self.status_var.set(f"爬取完成。找到 {len(valid_links)} 个有效链接")
        except Exception as e:
            self.status_var.set(f"爬取出错: {str(e)}")
            self.result_text.configure(state=tk.NORMAL)
            self.result_text.insert(tk.END, f"\n发生错误: {str(e)}\n")
            self.result_text.configure(state=tk.DISABLED)
        finally:
            self.scan_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.progress_var.set(100)
            self.crawling = False
    
    def stop_crawling(self):
        self.crawler.stop_requested = True
        self.status_var.set("爬取已停止")
        self.scan_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
    
    def save_results(self):
        try:
            content = self.result_text.get(1.0, tk.END)
            if not content.strip():
                messagebox.showwarning("警告", "没有可保存的内容")
                return
            
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="保存结果"
            )
            
            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo("成功", f"结果已保存到:\n{file_path}")
        except Exception as e:
            messagebox.showerror("错误", f"保存文件时出错: {str(e)}")
    
    def clear_results(self):
        self.result_text.configure(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "结果已清空。\n")
        self.result_text.configure(state=tk.DISABLED)
        self.status_var.set("就绪")
    
    def show_stats(self):
        stats = self.crawler.crawl_stats
        if not stats.get("start_time"):
            messagebox.showinfo("统计信息", "尚未执行爬取")
            return
        
        stats_text = f"爬取统计信息:\n"
        stats_text += f"开始时间: {stats['start_time']}\n"
        stats_text += f"结束时间: {stats.get('end_time', '进行中')}\n"
        stats_text += f"扫描页数: {stats.get('pages_scanned', 0)}\n"
        stats_text += f"访问仓库数: {stats.get('repos_visited', 0)}\n"
        stats_text += f"检查文件数: {stats.get('files_checked', 0)}\n"
        stats_text += f"有效链接数: {stats.get('valid_links', 0)}\n"
        
        messagebox.showinfo("爬取统计", stats_text)
    
    def get_selected_link(self):
        try:
            # 获取当前选中的文本
            if self.result_text.tag_ranges(tk.SEL):
                selected_text = self.result_text.get(tk.SEL_FIRST, tk.SEL_LAST)
                if selected_text.startswith("http"):
                    return selected_text.strip()
            
            # 如果没有选中，尝试获取光标所在行的链接
            current_line = self.result_text.index(tk.INSERT).split('.')[0]
            line_text = self.result_text.get(f"{current_line}.0", f"{current_line}.end")
            if line_text.startswith("http"):
                return line_text.strip()
            
            return None
        except:
            return None
    
    def copy_link(self):
        link = self.get_selected_link()
        if link:
            self.root.clipboard_clear()
            self.root.clipboard_append(link)
            self.status_var.set(f"已复制链接: {link[:50]}...")
        else:
            messagebox.showwarning("警告", "请先选择或定位到一个链接")
    
    def open_link(self):
        link = self.get_selected_link()
        if link:
            try:
                webbrowser.open(link)
                self.status_var.set(f"已打开链接: {link[:50]}...")
            except Exception as e:
                messagebox.showerror("错误", f"无法打开链接: {str(e)}")
        else:
            messagebox.showwarning("警告", "请先选择或定位到一个链接")
    
    def test_link(self):
        link = self.get_selected_link()
        if not link:
            messagebox.showwarning("警告", "请先选择或定位到一个链接")
            return
        
        self.status_var.set(f"测试链接: {link[:50]}...")
        threading.Thread(target=self._test_link, args=(link,), daemon=True).start()
    
    def _test_link(self, link):
        try:
            start_time = time.time()
            headers = {"User-Agent": self.ua.random}
            response = requests.get(link, headers=headers, timeout=15)
            response_time = time.time() - start_time
            
            result = f"链接测试结果:\n"
            result += f"URL: {link}\n"
            result += f"状态码: {response.status_code}\n"
            result += f"响应时间: {response_time:.2f}秒\n"
            result += f"内容类型: {response.headers.get('Content-Type', '未知')}\n"
            result += f"内容长度: {len(response.content)}字节\n"
            
            # 检查是否是有效的Clash配置
            if self.crawler.is_valid_clash_config(response.text[:500]):
                result += "有效性: 有效的Clash订阅\n"
            else:
                result += "有效性: 可能不是有效的Clash订阅\n"
            
            self.result_text.configure(state=tk.NORMAL)
            self.result_text.insert(tk.END, "\n" + result + "\n")
            self.result_text.configure(state=tk.DISABLED)
            self.result_text.see(tk.END)
            
            self.status_var.set(f"测试完成: {link[:30]}...")
        except Exception as e:
            self.result_text.configure(state=tk.NORMAL)
            self.result_text.insert(tk.END, f"\n测试链接失败: {str(e)}\n")
            self.result_text.configure(state=tk.DISABLED)
            self.status_var.set(f"测试失败: {str(e)}")


if __name__ == "__main__":
    # 检查并创建必要目录
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # 设置日志文件
    log_filename = f"logs/clash_crawler_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        filename=log_filename,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    root = tk.Tk()
    app = GitHubCrawlerApp(root)
    root.mainloop()
