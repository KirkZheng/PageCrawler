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
    """网站爬虫工具的图形用户界面类
    
    该类实现了一个具有图形界面的网站爬虫工具，主要功能包括：
    - 网页内容爬取和解析
    - 文章缓存管理
    - 搜索功能
    - 实时进度显示
    
    属性:
        root: tkinter根窗口对象
        is_crawling: 爬虫运行状态标志
        crawled_urls: 已爬取URL集合
        crawled_count: 已爬取文章计数
        max_articles: 最大爬取文章数限制
        articles_cache: 文章缓存字典
        search_results: 搜索结果列表
    """
    
    def __init__(self, root):
        """初始化爬虫GUI界面
        
        Args:
            root: tkinter根窗口对象
        """
        self.root = root
        self.root.title('网站爬虫工具')
        self.root.geometry('800x600')
        
        # 设置主题色 - 白色主题
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#ffffff')
        self.style.configure('TLabel', background='#ffffff', font=('微软雅黑', 12), foreground='#000000')
        self.style.configure('TButton', font=('微软雅黑', 12), foreground='#000000')
        self.style.configure('Custom.TButton', background='#4a90e2', foreground='#000000', font=('微软雅黑', 12))
        
        # 设置窗口背景色
        self.root.configure(bg='#ffffff')
        
        # 创建GUI组件
        self.create_widgets()
        
        # 爬虫状态
        self.is_crawling = False
        self.crawled_urls = set()
        self.crawled_count = 0
        self.max_articles = float('inf')  # 移除爬取数量限制
        
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
        """创建GUI界面组件
        
        该方法负责创建和配置所有GUI界面元素，包括：
        1. URL输入区域
        2. 统计信息显示区域
        3. 控制按钮和搜索框
        4. 进度显示区域
        5. 结果显示区域
        
        所有组件采用Material Design风格设计，确保良好的用户体验
        """
        # URL输入框区域
        url_frame = ttk.Frame(self.root)
        url_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(url_frame, text='网站URL:').pack(side=tk.LEFT)
        self.url_entry = ttk.Entry(url_frame, font=('微软雅黑', 12))
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.url_entry.insert(0, 'https://hwv430.blogspot.com/')  # 默认URL
        
        # 统计信息显示区域
        stats_frame = ttk.Frame(self.root)
        stats_frame.pack(fill=tk.X, padx=20, pady=5)
        
        self.stats_text = tk.StringVar()
        stats_label = ttk.Label(stats_frame, textvariable=self.stats_text, font=('微软雅黑', 12))
        stats_label.pack(pady=5)
        
        # 控制按钮和搜索框区域
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # 爬取控制按钮
        self.crawl_btn = ttk.Button(btn_frame, text='开始爬取', 
                                  command=self.start_crawling, 
                                  style='Custom.TButton')
        self.crawl_btn.pack(side=tk.LEFT, padx=5)
        
        # 搜索框和按钮
        ttk.Label(btn_frame, text='搜索:').pack(side=tk.LEFT, padx=(20, 5))
        self.search_entry = ttk.Entry(btn_frame, font=('微软雅黑', 12))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.search_entry.bind('<Return>', lambda e: self.search_articles())  # 回车触发搜索
        
        self.search_btn = ttk.Button(btn_frame, text='搜索', 
                                    command=self.search_articles, 
                                    style='Custom.TButton')
        self.search_btn.pack(side=tk.LEFT, padx=5)
        
        # 进度显示区域
        self.progress_var = tk.StringVar()
        progress_label = ttk.Label(self.root, textvariable=self.progress_var, 
                                 font=('微软雅黑', 12))
        progress_label.pack(pady=10)
        
        # 结果显示区域 - 使用Material Design卡片式布局
        result_frame = ttk.Frame(self.root)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 配置结果文本显示区域
        self.result_text = scrolledtext.ScrolledText(
            result_frame,
            height=20,
            font=('微软雅黑', 13),
            wrap=tk.WORD,
            background='#ffffff',
            foreground='#000000',
            selectbackground='#4a90e2',
            relief='flat',
            borderwidth=0,
            spacing1=2,  # 段落前空行
            spacing2=2,  # 文字行间距
            spacing3=2   # 段落后空行
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置文本样式
        self.result_text.tag_configure('link', foreground='#4a90e2', underline=True)
        self.result_text.tag_bind('link', '<Button-1>', self.on_link_click)  # 链接点击事件
        self.result_text.tag_bind('link', '<Enter>', 
                                 lambda e: self.result_text.configure(cursor='hand2'))
        self.result_text.tag_bind('link', '<Leave>', 
                                 lambda e: self.result_text.configure(cursor=''))
        
        # 配置搜索结果高亮样式
        self.result_text.tag_configure('highlight', foreground='#4a90e2')
    
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
        """爬取指定URL的页面内容
        
        该方法负责:
        1. 检查URL是否已在缓存中
        2. 发送HTTP请求获取页面内容
        3. 解析页面提取所需信息
        4. 保存文章到缓存和本地文件
        
        Args:
            url: 要爬取的网页URL
            
        Returns:
            Dict: 包含页面信息的字典，包括标题、发布时间、内容等
            None: 如果爬取失败
        """
        # 首先检查缓存中是否已存在该文章
        if url in self.articles_cache:
            print(f'从缓存中获取文章: {url}')
            article_data = self.articles_cache[url]
            return article_data
            
        try:
            # 发送HTTP请求获取页面内容
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                html = response.text
                soup = BeautifulSoup(html, 'html.parser')
                
                # 提取并处理页面标题，过长时进行截断
                title = soup.title.string if soup.title else '无标题'
                if len(title) > 30:
                    title = title[:30] + '...'
                
                # 查找并提取文章发布时间
                publish_date = ''
                date_elements = soup.find_all(['time', 'span', 'div'], class_=['date', 'time', 'published', 'post-date'])
                if date_elements:
                    publish_date = date_elements[0].get_text().strip()
                
                # 提取文章主体内容
                content = ''
                content_element = soup.find(['article', 'div'], class_=['post-content', 'entry-content', 'article-content'])
                if content_element:
                    content = content_element.get_text().strip()
                    content = ' '.join(content.split())  # 规范化空白字符
                
                # 生成文章预览内容
                preview = content[:200] + '...' if len(content) > 200 else content
                
                # 提取同域名下的相关链接
                links = set()
                base_domain = urlparse(url).netloc
                for link in soup.find_all('a'):
                    href = link.get('href')
                    if href:
                        full_url = urljoin(url, href)
                        if urlparse(full_url).netloc == base_domain:
                            links.add(full_url)
                
                # 构建文章数据结构
                article_data = {
                    'url': url,
                    'title': title,
                    'publish_date': publish_date,
                    'preview': preview,
                    'content': content,
                    'links': list(links),
                    'crawl_time': datetime.now().isoformat()
                }
                
                # 保存文章到缓存和本地文件系统
                self.save_to_cache(url, article_data)
                self.save_article_as_txt(article_data)
                
                return article_data
        except Exception as e:
            # 错误处理：在GUI中显示错误信息
            self.root.after(0, lambda: self.result_text.insert(tk.END, f'爬取 {url} 时出错: {str(e)}\n'))
        return None

    def crawl_website(self, start_url: str):
        """爬取网站内容的核心方法
        
        该方法实现网站爬取的主要逻辑：
        1. 初始化爬取队列
        2. 循环处理每个URL
        3. 提取新的链接并加入队列
        4. 更新进度显示
        5. 处理爬取结果
        
        Args:
            start_url: 起始URL地址
        """
        # 初始化URL队列
        urls_to_crawl = [start_url]
        
        # 使用线程池并发爬取
        with ThreadPoolExecutor(max_workers=5) as executor:
            while urls_to_crawl and self.is_crawling:
                # 获取下一个要爬取的URL
                current_url = urls_to_crawl.pop(0)
                if current_url in self.crawled_urls:
                    continue
                    
                # 标记URL为已爬取
                self.crawled_urls.add(current_url)
                
                # 更新进度显示
                self.crawled_count += 1
                self.root.after(0, lambda: self.progress_var.set(
                    f'正在爬取第 {self.crawled_count} 个页面: {current_url}'))
                
                # 爬取当前页面
                article_data = self.fetch_page(current_url)
                if article_data:
                    # 将新发现的链接加入队列
                    new_urls = [url for url in article_data['links'] 
                               if url not in self.crawled_urls]
                    urls_to_crawl.extend(new_urls)
                    
                    # 在GUI中显示爬取结果
                    self.root.after(0, lambda data=article_data: self.display_article(data))
                
                # 检查是否达到最大爬取数量限制
                if self.crawled_count >= self.max_articles:
                    break
                    
                # 添加延时避免请求过于频繁
                time.sleep(1)
        
        # 爬取完成后更新界面状态
        self.root.after(0, self.on_crawl_complete)

    def update_statistics(self):
        """更新统计信息
        
        该方法计算并更新显示：
        1. 总文章数量
        2. 文章平均长度
        3. 缓存使用情况
        """
        # 计算统计数据
        self.total_articles = len(self.articles_cache)
        total_length = sum(len(article['content']) 
                          for article in self.articles_cache.values())
        self.avg_article_length = total_length / self.total_articles if self.total_articles > 0 else 0
        
        # 更新统计信息显示
        stats_text = f'已缓存文章: {self.total_articles} | '
        stats_text += f'平均长度: {int(self.avg_article_length)} 字符'
        self.stats_text.set(stats_text)

    def search_articles(self):
        """搜索文章内容
        
        该方法实现文章内容的搜索功能：
        1. 获取搜索关键词
        2. 在缓存的文章中进行全文搜索
        3. 高亮显示搜索结果
        4. 提供搜索结果的预览和链接
        """
        keyword = self.search_entry.get().strip()
        if not keyword:
            return
            
        # 清空之前的搜索结果
        self.result_text.delete('1.0', tk.END)
        self.search_results.clear()
        
        # 在缓存的文章中搜索关键词
        for url, article in self.articles_cache.items():
            if keyword.lower() in article['content'].lower():
                self.search_results.append(article)
                
        # 显示搜索结果数量
        result_count = len(self.search_results)
        self.result_text.insert(tk.END, f'找到 {result_count} 个结果\n\n')
        
        # 显示每个搜索结果的预览
        for article in self.search_results:
            # 创建可点击的标题链接
            self.result_text.insert(tk.END, article['title'], 'link')
            self.result_text.insert(tk.END, f'\n发布时间: {article["publish_date"]}\n\n')
            
            # 在预览中高亮显示关键词
            preview = article['preview']
            keyword_start = preview.lower().find(keyword.lower())
            if keyword_start != -1:
                before = preview[:keyword_start]
                matched = preview[keyword_start:keyword_start + len(keyword)]
                after = preview[keyword_start + len(keyword):]
                
                self.result_text.insert(tk.END, before)
                self.result_text.insert(tk.END, matched, 'highlight')
                self.result_text.insert(tk.END, after)
            else:
                self.result_text.insert(tk.END, preview)
                
            self.result_text.insert(tk.END, '\n' + '-'*50 + '\n')

    def save_to_cache(self, url: str, article_data: Dict):
        """将文章保存到缓存
        
        该方法负责:
        1. 将文章数据添加到内存缓存
        2. 将缓存数据持久化到本地文件
        3. 更新统计信息
        
        Args:
            url: 文章URL
            article_data: 文章数据字典
        """
        # 更新内存缓存
        self.articles_cache[url] = article_data
        
        try:
            # 将缓存写入JSON文件
            cache_file = os.path.join(self.cache_dir, 'articles.json')
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.articles_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f'保存缓存出错: {str(e)}')
            
        # 更新统计信息
        self.update_statistics()
    
    def load_cache(self) -> Dict:
        """加载缓存数据
        
        从本地文件加载已缓存的文章数据。如果缓存文件不存在，则返回空字典。
        
        Returns:
            Dict: 包含已缓存文章数据的字典
        """
        cache_file = os.path.join(self.cache_dir, 'articles.json')
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f'加载缓存出错: {str(e)}')
        return {}

    def display_article(self, article_data):
        """在GUI中显示文章信息
        
        Args:
            article_data: 包含文章信息的字典
        """
        # 添加分隔线
        self.result_text.insert(tk.END, '='*50 + '\n')
        
        # 显示文章标题
        self.result_text.insert(tk.END, '标题: ', 'highlight')
        self.result_text.insert(tk.END, article_data['title'], 'link')
        self.result_text.insert(tk.END, '\n\n')
        
        # 显示URL
        self.result_text.insert(tk.END, 'URL: ', 'highlight')
        self.result_text.insert(tk.END, f'{article_data["url"]}\n\n')
        
        # 显示发布时间
        if article_data.get('publish_date'):
            self.result_text.insert(tk.END, '发布时间: ', 'highlight')
            self.result_text.insert(tk.END, f'{article_data["publish_date"]}\n\n')
        
        # 显示预览内容
        self.result_text.insert(tk.END, '预览内容: ', 'highlight')
        self.result_text.insert(tk.END, f'{article_data["preview"]}\n')
        
        # 添加底部分隔线
        self.result_text.insert(tk.END, '\n' + '='*50 + '\n\n')

    def on_link_click(self, event):
        """处理链接点击事件
        
        当用户点击文章标题时，在默认浏览器中打开对应的URL
        
        Args:
            event: 鼠标点击事件对象
        """
        try:
            # 获取点击位置的文本索引
            index = self.result_text.index(f'@{event.x},{event.y}')
            # 获取当前行的起始位置
            line_start = self.result_text.index(f'{index} linestart')
            # 向下查找最近的URL行
            next_lines = self.result_text.get(line_start, f'{line_start}+5l')
            for line in next_lines.split('\n'):
                if line.startswith('URL: '):
                    url = line[5:].strip()
                    webbrowser.open(url)
                    break
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