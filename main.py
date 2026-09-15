# ---
# 单元测试
from utils.EnvironTool import config
from utils.login import LoginLoader
import requests
from pathlib import Path
import json

cache_file = Path(__file__).parent / "data" / "cache.json"

def get_session() -> requests.Session:
    sess = requests.session()
    sess.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.76', 
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Encoding': 'gzip, deflate', 
        'Connection': 'keep-alive',
        'Origin': 'https://f.tju.edu.cn',
        'Referer': 'https://f.tju.edu.cn/tp_up/view?m=up'
    })
    cache_valid = False
    if cache_file.is_file():
        with open(cache_file, "r", encoding="utf-8") as f:
            cookies = json.loads(f.read())
            for k, v in cookies.items():
                sess.cookies.set(k, v)
            home_response = sess.get(
                "https://f.tju.edu.cn/tp_up/view?m=up#act=portal/viewhome",
                timeout=15,
            )
            try:
                LoginLoader._ensure_login_success(home_response)
                cache_valid = True
            except Exception as e:
                print("Cache Exception", e)
                cache_valid = False
    if not cache_valid:
        loader = LoginLoader(config.get("USER_NAME", ""), config.get("USER_PWD", ""))
        login_sess = loader.login()
        new_cookies = login_sess.cookies.get_dict()
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(new_cookies))
        for k, v in new_cookies.items():
            sess.cookies.set(k, v)
    return sess

if __name__ == "__main__":
    sess = get_session()
    response = sess.post(
        "https://f.tju.edu.cn/tp_up/up/messages/getAllPimList",
        json = {
            'LIMIT_SIZE': 30,
            'PIM_TITLE': ''
        }
    )
    response.encoding = "utf-8"
    print(response.text)
