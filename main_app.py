# 文件名: main_app.py (打包优化版)

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sqlite3
import os
import sys
import requests
from io import BytesIO
from PIL import Image, ImageTk

import isbn_utils
import api_handler

# 获取资源文件的正确路径（支持打包后的exe）
def get_resource_path(relative_path):
    """获取资源文件的绝对路径，支持开发环境和打包后的exe环境"""
    try:
        # PyInstaller会创建临时文件夹，并将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except AttributeError:
        # 如果没有_MEIPASS属性，则是在开发环境中运行
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# 使用资源路径函数获取数据库文件路径
DB_FILE_PATH = get_resource_path('books.db')
TABLE_NAME = 'books'

class BookSearchApp:
    def __init__(self, master):
        self.master = master
        master.title("书籍检索程序 (打包版)")
        master.geometry("900x600")
        
        # 设置程序图标（如果存在）
        try:
            icon_path = get_resource_path('app_icon.ico')
            if os.path.exists(icon_path):
                master.iconbitmap(icon_path)
        except Exception as e:
            print(f"无法加载图标: {e}")

        # 检查数据库文件是否存在
        if not os.path.exists(DB_FILE_PATH):
            messagebox.showerror("数据库错误", f"数据库文件未找到！\n路径: {DB_FILE_PATH}")
            master.destroy()
            return
            
        try:
            self.conn = sqlite3.connect(DB_FILE_PATH, check_same_thread=False)
            self.cursor = self.conn.cursor()
            # 测试数据库连接
            self.cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
            count = self.cursor.fetchone()[0]
            print(f"数据库连接成功，共有 {count} 条记录")
        except Exception as e:
            messagebox.showerror("数据库错误", f"无法连接到数据库！\n错误: {str(e)}")
            master.destroy()
            return

        self._create_widgets()
        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        if hasattr(self, 'conn') and self.conn: 
            self.conn.close()
        self.master.destroy()

    def update_status(self, message):
        """更新状态栏的文本"""
        self.status_var.set(message)

    def _create_widgets(self):
        # 创建顶部搜索框架
        top_frame = ttk.Frame(self.master, padding="10")
        top_frame.pack(fill=tk.X)
        
        ttk.Label(top_frame, text="查询内容:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry = ttk.Entry(top_frame, width=40)
        self.search_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        # 绑定回车键到搜索功能
        self.search_entry.bind('<Return>', lambda e: self.start_search_thread())
        
        # 搜索类型单选按钮
        self.search_var = tk.StringVar(value="ss")
        ttk.Radiobutton(top_frame, text="SS号", variable=self.search_var, value="ss").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(top_frame, text="ISBN", variable=self.search_var, value="isbn").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(top_frame, text="书名", variable=self.search_var, value="title").pack(side=tk.LEFT, padx=5)
        
        self.search_button = ttk.Button(top_frame, text="查询", command=self.start_search_thread)
        self.search_button.pack(side=tk.LEFT, padx=10)
        
        # 创建主面板（分割窗口）
        main_pane = ttk.PanedWindow(self.master, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 左侧列表框架
        list_frame = ttk.Frame(main_pane, width=350)
        self.results_listbox = tk.Listbox(list_frame, height=15)
        self.results_listbox.pack(fill=tk.BOTH, expand=True)
        self.results_listbox.bind('<<ListboxSelect>>', self.on_list_select)
        main_pane.add(list_frame, weight=1)

        # 右侧详情框架
        detail_frame = ttk.Frame(main_pane, padding="10")
        main_pane.add(detail_frame, weight=2)

        # 详情页组件
        self.detail_cover_label = ttk.Label(detail_frame, text="封面", anchor=tk.CENTER)
        self.detail_cover_label.pack(pady=5)
        
        self.detail_title_label = ttk.Label(detail_frame, text="", font=("Helvetica", 16, "bold"), wraplength=350)
        self.detail_title_label.pack(pady=(5, 2), anchor=tk.W)
        
        self.detail_author_label = ttk.Label(detail_frame, text="", font=("Helvetica", 10), wraplength=350)
        self.detail_author_label.pack(pady=2, anchor=tk.W)
        
        self.detail_publisher_label = ttk.Label(detail_frame, text="", font=("Helvetica", 10), wraplength=350)
        self.detail_publisher_label.pack(pady=2, anchor=tk.W)
        
        # 新增的API字段标签
        self.detail_pubdate_label = ttk.Label(detail_frame, text="", font=("Helvetica", 10))
        self.detail_pubdate_label.pack(pady=2, anchor=tk.W)
        
        self.detail_pages_price_label = ttk.Label(detail_frame, text="", font=("Helvetica", 10))
        self.detail_pages_price_label.pack(pady=2, anchor=tk.W)
        
        self.detail_binding_format_label = ttk.Label(detail_frame, text="", font=("Helvetica", 10))
        self.detail_binding_format_label.pack(pady=2, anchor=tk.W)
        
        self.detail_ss_isbn_label = ttk.Label(detail_frame, text="", foreground="gray")
        self.detail_ss_isbn_label.pack(pady=(5, 2), anchor=tk.W)
        
        ttk.Separator(detail_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # 简介文本框
        self.detail_summary_text = tk.Text(detail_frame, wrap=tk.WORD, state=tk.DISABLED, 
                                         height=10, relief=tk.FLAT, 
                                         background=self.master.cget('bg'))
        self.detail_summary_text.pack(fill=tk.BOTH, expand=True)
        
        # 状态栏
        self.status_var = tk.StringVar(value="准备就绪 (打包版)")
        status_bar = ttk.Label(self.master, textvariable=self.status_var, 
                             relief=tk.SUNKEN, anchor=tk.W, padding="2 5")
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def clear_details(self):
        """清空详情页所有内容"""
        self.detail_cover_label.config(image=None, text="封面")
        if hasattr(self.detail_cover_label, 'image'):
            self.detail_cover_label.image = None
        self.detail_title_label.config(text="")
        self.detail_author_label.config(text="")
        self.detail_publisher_label.config(text="")
        self.detail_pubdate_label.config(text="")
        self.detail_pages_price_label.config(text="")
        self.detail_binding_format_label.config(text="")
        self.detail_ss_isbn_label.config(text="")
        self.detail_summary_text.config(state=tk.NORMAL)
        self.detail_summary_text.delete(1.0, tk.END)
        self.detail_summary_text.config(state=tk.DISABLED)
    
    def fetch_details(self, index):
        """在后台线程中获取书籍详情"""
        try:
            local_record = self.search_results_data[index]
            self.master.after(0, self.update_status, f"正在获取 '{local_record['title']}' 的在线详情...")
        except IndexError: 
            return

        isbn_from_db = local_record['isbn']
        api_data = api_handler.get_book_details_from_api(isbn_from_db)
        
        # 如果API获取失败，尝试转换ISBN格式再次获取
        if not api_data:
            original_sanitized = isbn_utils.sanitize(isbn_from_db)
            converted_isbn = None
            if len(original_sanitized) == 10: 
                converted_isbn = isbn_utils.convert_10_to_13(original_sanitized)
            elif len(original_sanitized) == 13: 
                converted_isbn = isbn_utils.convert_13_to_10(original_sanitized)
            if converted_isbn: 
                api_data = api_handler.get_book_details_from_api(converted_isbn)

        # 下载封面图片
        photo_image = None
        if api_data and api_data.get("img"):
            try:
                response = requests.get(api_data["img"], timeout=10)
                response.raise_for_status()
                img = Image.open(BytesIO(response.content))
                img.thumbnail((180, 250))
                photo_image = ImageTk.PhotoImage(img)
            except Exception as e: 
                print(f"下载或处理图片时出错: {e}")
        
        # 在主线程中更新UI
        self.master.after(0, self.update_detail_ui, local_record, api_data, photo_image)

    def update_detail_ui(self, local_record, api_data, photo_image):
        """在主线程中安全地更新所有UI组件"""
        self.clear_details()
        
        # 设置封面图片
        if photo_image:
            self.detail_cover_label.config(image=photo_image, text="")
            self.detail_cover_label.image = photo_image
        else:
            self.detail_cover_label.config(image=None, text="无封面")

        if api_data: 
            self.update_status("在线详情加载成功。")
            self.detail_title_label.config(text=api_data.get('title', '无标题'))
            self.detail_author_label.config(text=f"作者: {api_data.get('author', '未知')}")
            self.detail_publisher_label.config(text=f"出版社: {api_data.get('publisher', '未知')}")
            
            # 填充新增的API字段信息
            pubdate = api_data.get('pubdate') or '未知'
            self.detail_pubdate_label.config(text=f"出版日期: {pubdate}")

            pages = api_data.get('pages') or '未知'
            price = api_data.get('price') or '未知'
            self.detail_pages_price_label.config(text=f"页数: {pages} | 定价: {price} 元")

            binding = api_data.get('binding') or '未知'
            format_ = api_data.get('format') or '未知'
            self.detail_binding_format_label.config(text=f"装帧: {binding} | 开本: {format_}")
            
            # 设置简介
            summary = api_data.get("summary", "暂无简介。")
            self.detail_summary_text.config(state=tk.NORMAL)
            self.detail_summary_text.delete(1.0, tk.END)
            self.detail_summary_text.insert(1.0, summary)
            self.detail_summary_text.config(state=tk.DISABLED)
        else: 
            self.update_status("在线详情获取失败，已显示本地缓存信息。")
            self.detail_title_label.config(text=local_record.get('title', '无标题'))
            self.detail_author_label.config(text=f"作者: {local_record.get('author', '未知')}")
            self.detail_publisher_label.config(text=f"出版社: {local_record.get('publisher', '未知')}")
            self.detail_summary_text.config(state=tk.NORMAL)
            self.detail_summary_text.delete(1.0, tk.END)
            self.detail_summary_text.insert(1.0, "在线简介获取失败。")
            self.detail_summary_text.config(state=tk.DISABLED)

        # 显示SS号和ISBN
        self.detail_ss_isbn_label.config(text=f"SS号: {local_record.get('ss')} | ISBN: {local_record.get('isbn')}")
    
    def perform_search(self):
        """执行搜索操作"""
        term = self.search_entry.get().strip()
        search_type = self.search_var.get()
        
        if not term: 
            self.master.after(0, self.update_status, "请输入查询内容！")
            return
            
        self.master.after(0, self.update_status, f"正在数据库中按 {search_type} 查询 '{term}'...")
        self.master.after(0, lambda: self.results_listbox.delete(0, tk.END))
        self.master.after(0, self.clear_details)
        self.search_results_data = []

        # 验证ISBN格式
        if search_type == "isbn" and not isbn_utils.is_valid_isbn(term):
            self.master.after(0, self.update_status, "错误：输入的不是一个合法的ISBN号码！")
            return

        # 构建查询语句
        query, params = "", ()
        if search_type == "ss": 
            query, params = (f"SELECT * FROM {TABLE_NAME} WHERE ss_number = ?", (term,))
        elif search_type == "isbn": 
            query, params = (f"SELECT * FROM {TABLE_NAME} WHERE isbn = ?", (isbn_utils.sanitize(term),))
        elif search_type == "title": 
            query, params = (f"SELECT * FROM {TABLE_NAME} WHERE title LIKE ?", (f"%{term}%",))

        try:
            self.cursor.execute(query, params)
            results = [{'ss': r[0], 'isbn': r[7], 'title': r[2], 'author': r[3], 'publisher': r[4]} 
                      for r in self.cursor.fetchall()]
            self.search_results_data = results
            
            if not results: 
                self.master.after(0, self.update_status, f"未在数据库中找到与 '{term}' 相关的记录。")
                return
            
            # 在主线程中更新列表框
            def update_listbox():
                for item in results: 
                    self.results_listbox.insert(tk.END, f"{item['title']} - (SS: {item['ss']})")
                self.results_listbox.select_set(0)
                self.on_list_select(None)
                self.update_status(f"查询到 {len(results)} 条结果。")
            
            self.master.after(0, update_listbox)
            
        except Exception as e:
            self.master.after(0, self.update_status, f"数据库查询错误: {str(e)}")

    def on_list_select(self, event):
        """处理列表选择事件"""
        selected_indices = self.results_listbox.curselection()
        if not selected_indices: 
            return
        
        # 在后台线程中获取详情
        thread = threading.Thread(target=self.fetch_details, args=(selected_indices[0],), daemon=True)
        thread.start()

    def start_search_thread(self):
        """启动搜索线程"""
        self.search_button.config(state='disabled')
        
        def search_wrapper():
            try:
                self.perform_search()
            finally:
                self.master.after(0, lambda: self.search_button.config(state='normal'))
        
        thread = threading.Thread(target=search_wrapper, daemon=True)
        thread.start()

def main():
    """主函数"""
    try:
        root = tk.Tk()
        app = BookSearchApp(root)
        root.mainloop()
    except Exception as e:
        # 在exe环境中显示错误对话框
        try:
            messagebox.showerror("程序错误", f"程序启动失败：\n{str(e)}")
        except:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()