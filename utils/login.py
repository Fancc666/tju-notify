import time

import requests
from bs4 import BeautifulSoup

from .captcha import CaptchaHandler
from .des import strEnc


class LoginLoader:
    REQUEST_TIMEOUT = 15

    def __init__(self, usr: str, pwd: str) -> None:
        self.x = None
        self.usr = usr
        self.pwd = pwd
        self.captcha_url = None
        self.captcha_path = None
        self.captcha_id = None
        self.login_url = "https://sso.tju.edu.cn/cas/login?service=http%3A%2F%2Fclasses.tju.edu.cn%2Feams%2FhomeExt.action"

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.76",
            "Referer": "https://sso.tju.edu.cn/cas/login?service=http%3A%2F%2Fzhjw.tju.edu.cn%2Flogin.jsp",
        }

    @staticmethod
    def _ensure_login_success(response: requests.Response) -> None:
        soup = BeautifulSoup(response.text, "lxml")
        if "cas/login" in response.url or soup.find(id="loginForm") is not None:
            raise Exception("Login failed, redirected back to CAS login page")

    def login(self) -> requests.session:
        self.x = requests.session()

        captcha = CaptchaHandler(session=self.x).get_final_captcha()
        res = self.x.get(self.login_url, headers=self.headers, timeout=self.REQUEST_TIMEOUT)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "lxml")

        lt = soup.find(id="lt").get("value")

        execution = soup.select("#loginForm > input[type=hidden]:nth-child(6)")[0]
        if execution is None:
            raise Exception("execution not found")
        execution = execution.get("value")

        rsa = strEnc(self.usr + self.pwd + lt, "1", "2", "3")

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
            "https://classes.tju.edu.cn/eams/homeExt.action",
            headers=self.headers,
            timeout=self.REQUEST_TIMEOUT,
        )
        self._ensure_login_success(home_response)
        time.sleep(1)

        return self.x
