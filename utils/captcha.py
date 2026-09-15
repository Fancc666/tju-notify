import random

import ddddocr
import requests
from urllib.parse import quote


class CaptchaHandler:
    def __init__(self, session: requests.Session, service: str):
        self.img_byte = None
        self.x = session
        self.captcha_id = random.random()
        self.captcha_url = "https://sso.tju.edu.cn/cas/code"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.76",
            "Referer": "https://sso.tju.edu.cn/cas/login?service=" + quote(service, safe="-_.!~*'()"),
        }

    @staticmethod
    def get_captcha(code: bytes) -> str:
        ocr = ddddocr.DdddOcr(show_ad=False, beta=True)
        res = ocr.classification(code)
        if isinstance(res, str):
            return res
        return str(res)

    def read_captcha(self):
        code = self.x.get(self.captcha_url, headers=self.headers)
        result = self.get_captcha(code.content)
        return result

    def get_final_captcha(self):
        res = ""
        while len(res) != 4:
            res = self.read_captcha()
        return res
