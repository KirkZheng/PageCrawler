import tkinter as tk
from tkinter import ttk, scrolledtext
import requests
import threading
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import threading
from typing import List, Dict, Set
import time
import webbrowser
import json
import os
from datetime import datetime

class WebCrawlerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title('网站爬虫工具')
        self.root.geometry('800x600')
        
        # 设置主题色 - 红黑风格
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#1a1a1a')
        self.style.configure('TLabel', background='#1a1a1a', font=('微软雅黑', 10), foreground='#ffffff')
        self.style.configure('TButton', font=('微软雅黑', 10), foreground='#ffffff')
        self.style.configure('Custom.TButton', background='#ff3333', foreground='#ffffff')
        
        # 设置窗口背景色
        self.root.configure(bg='#1a1a1a')
        
        # 创建GUI组件
        self.create_widgets()
        
        # 爬虫状态
        self.is_crawling = False
        self.crawled_urls = set()
        self.crawled_count = 0
        self.max_articles = 50  # 增加爬取数量限制
        
        # 统计信息
        self.total_articles = 0
        self.total_views = 0
        self.avg_article_length = 0
        
        # 缓存相关
        self.cache_dir = 'cache'
        os.makedirs(self.cache_dir, exist_ok=True)
        self.articles_cache = self.load_cache()
        
        # 搜索相关
        self.search_results = []
        
        # 更新统计信息
        self.update_statistics()
    
    def create_widgets(self):
        # URL输入框
        url_frame = ttk.Frame(self.root)
        url_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(url_frame, text='网站URL:').pack(side=tk.LEFT)
        self.url_entry = ttk.Entry(url_frame, font=('微软雅黑', 10))
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.url_entry.insert(0, 'https://hwv430.blogspot.com/')
        
        # 统计信息显示区域
        stats_frame = ttk.Frame(self.root)
        stats_frame.pack(fill=tk.X, padx=20, pady=5)
        
        self.stats_text = tk.StringVar()
        stats_label = ttk.Label(stats_frame, textvariable=self.stats_text, font=('微软雅黑', 10))
        stats_label.pack(pady=5)
        
        # 控制按钮和搜索框
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.crawl_btn = ttk.Button(btn_frame, text='开始爬取', command=self.start_crawling, style='Custom.TButton')
        self.crawl_btn.pack(side=tk.LEFT, padx=5)
        
        # 搜索框
        ttk.Label(btn_frame, text='搜索:').pack(side=tk.LEFT, padx=(20, 5))
        self.search_entry = ttk.Entry(btn_frame, font=('微软雅黑', 10))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.search_entry.bind('<Return>', lambda e: self.search_articles())
        
        self.search_btn = ttk.Button(btn_frame, text='搜索', command=self.search_articles, style='Custom.TButton')
        self.search_btn.pack(side=tk.LEFT, padx=5)
        
        # 进度显示
        self.progress_var = tk.StringVar()
        progress_label = ttk.Label(self.root, textvariable=self.progress_var, font=('微软雅黑', 10, 'bold'))
        progress_label.pack(pady=10)
        
        # 结果显示区域 - 使用Material Design卡片式布局
        result_frame = ttk.Frame(self.root)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.result_text = scrolledtext.ScrolledText(
            result_frame,
            height=20,
            font=('微软雅黑', 12),  # 增大字体
            wrap=tk.WORD,
            background='#000000',
            foreground='#ffffff',
            selectbackground='#ff3333',
            relief='flat',
            borderwidth=0
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置链接样式
        self.result_text.tag_configure('link', foreground='#ffffff', underline=True)
        self.result_text.tag_bind('link', '<Button-1>', self.on_link_click)
        self.result_text.tag_bind('link', '<Enter>', lambda e: self.result_text.configure(cursor='hand2'))
        self.result_text.tag_bind('link', '<Leave>', lambda e: self.result_text.configure(cursor=''))
        
        # 配置高亮样式
        self.result_text.tag_configure('highlight', foreground='#4a90e2')  # 修改高亮颜色为柔和的蓝色
    
    def start_crawling(self):
        if self.is_crawling:
            self.is_crawling = False
            self.crawl_btn.configure(text='开始爬取')
            return
        
        url = self.url_entry.get().strip()
        if not url:
            self.result_text.insert(tk.END, '请输入有效的URL\n')
            return
        
        self.is_crawling = True
        self.crawl_btn.configure(text='停止爬取')
        self.crawled_urls.clear()
        self.crawled_count = 0
        self.result_text.delete('1.0', tk.END)
        
        # 在新线程中启动爬虫
        threading.Thread(target=lambda: self.crawl_website(url), daemon=True).start()
    
    def save_article_as_txt(self, article_data: Dict):
        # 创建articles目录用于存储txt文件
        articles_dir = os.path.join(self.cache_dir, 'articles')
        os.makedirs(articles_dir, exist_ok=True)
        
        # 处理文件名，移除不合法字符
        title = ''.join(c for c in article_data['title'] if c.isalnum() or c in (' ', '-', '_'))
        file_name = f"{title}.txt"
        file_path = os.path.join(articles_dir, file_name)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"标题: {article_data['title']}\n\n")
                f.write(f"发布时间: {article_data['publish_date']}\n")
                f.write(f"原文链接: {article_data['url']}\n\n")
                f.write("正文内容:\n")
                f.write(article_data['content'])
            print(f'文章已保存: {file_path}')
        except Exception as e:
            print(f'保存文章出错: {str(e)}')

    def fetch_page(self, url: str) -> Dict:
        # 首先检查缓存中是否已存在该文章
        if url in self.articles_cache:
            print(f'从缓存中获取文章: {url}')
            article_data = self.articles_cache[url]
            # 保存为txt文件
            self.save_article_as_txt(article_data)
            return article_data
            
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                html = response.text
                soup = BeautifulSoup(html, 'html.parser')
                
                # 提取并简化标题
                title = soup.title.string if soup.title else '无标题'
                if len(title) > 30:
                    title = title[:30] + '...'
                
                # 提取发布时间
                publish_date = ''
                date_elements = soup.find_all(['time', 'span', 'div'], class_=['date', 'time', 'published', 'post-date'])
                if date_elements:
                    publish_date = date_elements[0].get_text().strip()
                    # 尝试解析日期字符串为datetime对象
                    try:
                        from dateutil import parser
                        publish_date = parser.parse(publish_date).isoformat()
                    except:
                        pass
                
                # 提取完整内容
                content = ''
                content_element = soup.find(['article', 'div'], class_=['post-content', 'entry-content', 'article-content'])
                if content_element:
                    content = content_element.get_text().strip()
                    content = ' '.join(content.split())
                
                # 提取预览内容
                preview = content[:200] + '...' if len(content) > 200 else content
                
                # 提取链接并按日期排序
                links = set()
                base_domain = urlparse(url).netloc
                for link in soup.find_all('a'):
                    href = link.get('href')
                    if href:
                        full_url = urljoin(url, href)
                        if urlparse(full_url).netloc == base_domain:
                            links.add(full_url)
                
                article_data = {
                    'url': url,
                    'title': title,
                    'publish_date': publish_date,
                    'preview': preview,
                    'content': content,
                    'links': list(links),
                    'crawl_time': datetime.now().isoformat()
                }
                
                # 保存到缓存
                self.save_to_cache(url, article_data)
                
                # 保存为txt文件
                self.save_article_as_txt(article_data)
                
                return article_data
        except Exception as e:
            self.root.after(0, lambda: self.result_text.insert(tk.END, f'爬取 {url} 时出错: {str(e)}\n'))
        return None

    def crawl_website(self, start_url: str):
        to_visit = {start_url}
        with ThreadPoolExecutor(max_workers=5) as executor:
            while self.is_crawling and to_visit and self.crawled_count < self.max_articles:
                # 并发爬取多个页面
                urls_to_crawl = set()
                futures = []
                
                # 从缓存中获取已知的文章发布时间
                url_dates = []
                for url in to_visit:
                    if url in self.articles_cache and self.articles_cache[url].get('publish_date'):
                        url_dates.append((url, self.articles_cache[url]['publish_date']))
                    else:
                        url_dates.append((url, ''))
                
                # 按发布时间排序，未知时间的放在后面
                url_dates.sort(key=lambda x: x[1] if x[1] else '', reverse=True)
                
                # 选择要爬取的URL
                while len(futures) < 5 and url_dates:  # 最多同时爬取5个页面
                    url, _ = url_dates.pop(0)
                    if url not in self.crawled_urls:
                        futures.append(executor.submit(self.fetch_page, url))
                        urls_to_crawl.add(url)
                        to_visit.remove(url)
                
                if not futures:
                    break
                
                # 处理结果
                for future in futures:
                    if not self.is_crawling:
                        break
                    
                    result = future.result()
                    if result:
                        self.crawled_urls.add(result['url'])
                        self.crawled_count += 1
                        
                        # 更新界面
                        self.root.after(0, lambda r=result: self.update_ui(r))
                        
                        # 添加新的URL到待访问集合
                        if self.crawled_count < self.max_articles:
                            to_visit.update(set(result['links']) - self.crawled_urls)
                
                # 限速
                time.sleep(0.5)
        
        self.is_crawling = False
        self.root.after(0, lambda: self.crawl_btn.configure(text='开始爬取'))
    
    def update_ui(self, result: Dict):
        self.progress_var.set(f'已爬取: {self.crawled_count}/{self.max_articles} 篇文章')
        # 添加标题
        self.result_text.insert(tk.END, '标题: ')
        self.result_text.insert(tk.END, f'{result["title"]}\n')
        
        # 添加URL，设置为可点击的链接
        self.result_text.insert(tk.END, 'URL: ')
        url_start = self.result_text.index('end-1c')
        self.result_text.insert(tk.END, f'{result["url"]}\n')
        url_end = self.result_text.index('end-2c')
        self.result_text.tag_add('link', url_start, url_end)
        
        # 添加发布时间
        if result['publish_date']:
            self.result_text.insert(tk.END, f'发布时间: {result["publish_date"]}\n')
        
        # 添加预览内容
        if result['preview']:
            self.result_text.insert(tk.END, f'预览: {result["preview"]}\n')
        
        self.result_text.insert(tk.END, '\n')
        self.result_text.see(tk.END)
    
    def load_cache(self) -> Dict:
        cache = {}
        cache_file = os.path.join(self.cache_dir, 'articles.json')
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 验证缓存数据格式
                    if isinstance(data, dict):
                        for url, article in data.items():
                            if isinstance(article, dict) and all(key in article for key in ['url', 'title', 'content']):
                                cache[url] = article
                    if not cache:
                        print('缓存数据格式无效，将重新创建缓存')
            except json.JSONDecodeError as e:
                print(f'缓存文件格式错误: {str(e)}')
            except Exception as e:
                print(f'加载缓存出错: {str(e)}')
            
            # 如果缓存文件损坏，创建备份并重新初始化
            if not cache and os.path.exists(cache_file):
                backup_file = f"{cache_file}.bak"
                try:
                    os.rename(cache_file, backup_file)
                    print(f'已创建损坏的缓存文件备份: {backup_file}')
                except Exception as e:
                    print(f'创建缓存备份失败: {str(e)}')
        return cache
    
    def update_statistics(self):
        # 更新显示
        self.stats_text.set(f'文章数量: {len(self.articles_cache)}')
        
        # 更新统计信息
        self.total_articles = len(self.articles_cache)
        
        # 更新显示
        stats_text = f'统计信息 - 文章总数: {self.total_articles}'
        self.stats_text.set(stats_text)

    def save_to_cache(self, url: str, article_data: Dict):
        if not isinstance(article_data, dict) or not all(key in article_data for key in ['url', 'title', 'content']):
            print('无效的文章数据格式，跳过缓存保存')
            return
            
        cache_file = os.path.join(self.cache_dir, 'articles.json')
        temp_file = f"{cache_file}.tmp"
        
        try:
            # 创建临时字典并更新数据
            temp_cache = dict(self.articles_cache)
            temp_cache[url] = article_data
            
            # 将临时字典写入临时文件
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(temp_cache, f, ensure_ascii=False, indent=2)
            
            # 成功写入后替换原文件
            if os.path.exists(cache_file):
                os.replace(temp_file, cache_file)
            else:
                os.rename(temp_file, cache_file)
            
            # 更新内存中的缓存
            self.articles_cache = temp_cache
            # 更新统计信息
            self.update_statistics()
        except Exception as e:
            print(f'保存缓存出错: {str(e)}')
            # 清理临时文件
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
    
    def search_articles(self):
        keyword = self.search_entry.get().strip()
        if not keyword:
            self.result_text.delete('1.0', tk.END)
            self.result_text.insert(tk.END, '请输入搜索关键词\n')
            return
        
        # 清空之前的搜索结果
        self.result_text.delete('1.0', tk.END)
        self.search_results.clear()
        
        # 在缓存中搜索
        for url, article in self.articles_cache.items():
            if (keyword.lower() in article['title'].lower() or
                keyword.lower() in article['content'].lower()):
                self.search_results.append(article)
        
        # 显示搜索结果
        if self.search_results:
            self.result_text.insert(tk.END, f'找到 {len(self.search_results)} 个结果:\n\n')
            for article in self.search_results:
                # 添加标题
                self.result_text.insert(tk.END, '标题: ')
                self.result_text.insert(tk.END, f'{article["title"]}\n')
                
                # 添加URL，设置为可点击的链接
                self.result_text.insert(tk.END, 'URL: ')
                url_start = self.result_text.index('end-1c')
                self.result_text.insert(tk.END, f'{article["url"]}\n')
                url_end = self.result_text.index('end-2c')
                self.result_text.tag_add('link', url_start, url_end)
                
                # 添加发布时间
                if article['publish_date']:
                    self.result_text.insert(tk.END, f'发布时间: {article["publish_date"]}\n')
                
                # 添加预览内容
                if article['preview']:
                    preview_start = self.result_text.index('end-1c')
                    self.result_text.insert(tk.END, f'预览: {article["preview"]}\n')
                    preview_end = self.result_text.index('end-1c')
                    # 高亮预览中的关键字
                    self.highlight_keyword(preview_start, preview_end, keyword)
                
                self.result_text.insert(tk.END, '\n')
        else:
            self.result_text.insert(tk.END, '未找到匹配的结果\n')
    
    def on_link_click(self, event):
        try:
            index = self.result_text.index(f'@{event.x},{event.y}')
            line_start = self.result_text.index(f'{index} linestart')
            line = self.result_text.get(line_start, f'{line_start} lineend')
            
            if line.startswith('URL: '):
                url = line[5:].strip()
                webbrowser.open(url)
        except Exception as e:
            print(f'打开URL时出错: {str(e)}')
    
    def highlight_keyword(self, start, end, keyword):
        content = self.result_text.get(start, end).lower()
        keyword = keyword.lower()
        
        idx = 0
        while True:
            idx = content.find(keyword, idx)
            if idx == -1:
                break
            start_pos = f"{start}+{idx}c"
            end_pos = f"{start}+{idx + len(keyword)}c"
            self.result_text.tag_add('highlight', start_pos, end_pos)
            idx += len(keyword)


if __name__ == '__main__':
    root = tk.Tk()
    app = WebCrawlerGUI(root)
    root.mainloop()