import time

import requests
from bs4 import BeautifulSoup

from .captcha import CaptchaHandler
from .custom_des import strEnc
from urllib.parse import quote


class LoginLoader:
    REQUEST_TIMEOUT = 15

    def __init__(self, usr: str, pwd: str) -> None:
        self.x = None
        self.usr = usr
        self.pwd = pwd
        self.captcha_url = None
        self.captcha_path = None
        self.captcha_id = None
        self.service_name = quote("https://f.tju.edu.cn/tp_up/", safe="-_.!~*'()")
        self.login_url = "https://sso.tju.edu.cn/cas/login?service=" + self.service_name

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.76",
            "Referer": "https://sso.tju.edu.cn/cas/login?service=" + self.service_name,
        }

    @staticmethod
    def _ensure_login_success(response: requests.Response) -> None:
        soup = BeautifulSoup(response.text, "lxml")
        if "cas/login" in response.url or soup.find(id="loginForm") is not None:
            raise Exception("Login failed, redirected back to CAS login page")

    def login(self) -> requests.Session:
        self.x = requests.session()
        captcha = CaptchaHandler(session=self.x, service=self.service_name).get_final_captcha()
        res = self.x.get(self.login_url, headers=self.headers, timeout=self.REQUEST_TIMEOUT)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "lxml")
        lt = soup.find(id="lt")
        if lt is not None:
            lt = str(lt.get("value", ""))
        else:
            lt = ""
        execution = soup.select("#loginForm > input[type=hidden]:nth-child(6)")[0]
        if execution is None:
            raise Exception("execution not found")
        execution = execution.get("value")
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
        time.sleep(1)
        return self.x
