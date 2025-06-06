# 文件名: api_handler.py
# 功能: 负责与真实的 tanshuapi.com API进行所有交互。

import requests
import json

# --- API 配置 ---
# 警告: 在生产环境中，不建议将密钥直接写在代码里。
API_KEY = "f3a35777abb5ebfce6f5238980d964ff"
BASE_URL = "https://api.tanshuapi.com/api/isbn_base/v1/index"

def get_book_details_from_api(isbn):
    """
    根据给定的ISBN，调用真实的API并返回书籍详情。
    成功则返回包含书籍数据的字典，失败则返回None。
    """
    params = {
        'key': API_KEY,
        'isbn': isbn
    }
    
    print(f"【API Handler】正在使用ISBN '{isbn}' 请求真实API...")
    
    try:
        # 设置10秒超时，以防网络卡顿
        response = requests.get(BASE_URL, params=params, timeout=10)
        # 如果HTTP状态码不是2xx，则抛出异常
        response.raise_for_status()
        
        response_data = response.json()
        
        # 检查API业务代码是否成功
        if response_data.get("code") == 1 and response_data.get("data"):
            print(f"【API Handler】请求成功，API返回code 1。")
            return response_data["data"]
        else:
            # API返回了业务错误，例如ISBN不存在或key错误
            error_msg = response_data.get("msg", "未知错误")
            print(f"【API Handler】API业务错误: {error_msg}")
            return None

    except requests.exceptions.RequestException as e:
        # 处理网络层面的错误，如连接超时、DNS错误等
        print(f"【API Handler】网络请求异常: {e}")
        return None
    except json.JSONDecodeError:
        # 处理返回内容不是标准JSON的错误
        print("【API Handler】API返回内容非JSON格式，解析失败。")
        return None