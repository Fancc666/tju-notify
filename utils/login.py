import time

import requests
from bs4 import BeautifulSoup

from .captcha import CaptchaHandler
from .custom_des import strEnc
from .EnvironTool import config
from .printer import print_flush, YELLOW, RESET
from urllib.parse import quote


class LoginLoader:
    REQUEST_TIMEOUT = 15
    # OCR登录流程允许重试几次
    MAX_LOGIN_ATTEMPTS = int(config.get("LOGIN_MAX_ATTEMPTS") or 3)

    def __init__(self, usr: str, pwd: str) -> None:
        self.x = requests.session()
        self.usr = usr
        self.pwd = pwd
        self.service_name = quote("https://f.tju.edu.cn/tp_up/", safe="-_.!~*'()")
        self.login_url = "https://sso.tju.edu.cn/cas/login?service=" + self.service_name

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.76",
            "Referer": "https://sso.tju.edu.cn/cas/login?service=" + self.service_name,
        }

    @staticmethod
    def _ensure_login_success(response: requests.Response) -> None:
        """确认当前页面是门户首页而不是被打回登录页。"""
        soup = BeautifulSoup(response.text, "lxml")
        if "cas/login" in response.url or soup.find(id="loginForm") is not None:
            raise Exception("Login failed, redirected back to CAS login page")

    def _fetch_form_fields(self) -> tuple[str, str]:
        """取登录页里的 lt 与 execution 两个隐藏字段。"""
        res = self.x.get(self.login_url, headers=self.headers, timeout=self.REQUEST_TIMEOUT)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "lxml")

        lt_node = soup.find(id="lt")
        lt = str(lt_node.get("value", "")) if lt_node is not None else ""

        execution_node = soup.select_one("#loginForm input[name=execution]")
        if execution_node is None:
            raise Exception("登录页里找不到 execution 字段，可能页面结构已变化")
        return lt, str(execution_node.get("value", ""))

    def _attempt_login(self) -> requests.Session:
        """取验证码 -> 提交。"""
        captcha = CaptchaHandler(session=self.x, service=self.service_name).get_final_captcha()
        lt, execution = self._fetch_form_fields()
        rsa = strEnc(self.usr + self.pwd + lt, "1", "2", "3")
        # print(rsa)
        # we only need session
        login_response = self.x.post(self.login_url, headers=self.headers, data={
            "code": captcha,
            "rsa": rsa,
            "ul": len(self.usr),
            "pl": len(self.pwd),
            "lt": lt,
            "execution": execution,
            "_eventId": "submit",
        }, timeout=self.REQUEST_TIMEOUT)
        
        home_response = self.x.get(
            "https://f.tju.edu.cn/tp_up/view?m=up#act=portal/viewhome",
            headers=self.headers,
            timeout=self.REQUEST_TIMEOUT,
        )
        self._ensure_login_success(home_response)
        return self.x

    def login(self) -> requests.Session:
        last_error: Exception | None = None
        for attempt in range(1, self.MAX_LOGIN_ATTEMPTS + 1):
            try:
                return self._attempt_login()
            except requests.RequestException as e:
                last_error = e
                print_flush(
                    f"{YELLOW}[login] 第 {attempt}/{self.MAX_LOGIN_ATTEMPTS} 次登录网络异常：{e}{RESET}"
                )
            except RuntimeError:
                raise
            except Exception as e:
                last_error = e
                print_flush(
                    f"{YELLOW}[login] 第 {attempt}/{self.MAX_LOGIN_ATTEMPTS} 次登录失败"
                    f"（{e}），换一张验证码重试{RESET}"
                )
            time.sleep(1)

        raise RuntimeError(
            f"登录失败：已尝试 {self.MAX_LOGIN_ATTEMPTS} 次，最后一次错误：{last_error}"
        )
