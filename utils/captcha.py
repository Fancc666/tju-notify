"""验证码识别：从 CAS 取图，交给内网 OCR 接口识别。

流程是「取图 -> 识别 -> 得到 4 位验证码」
"""

from __future__ import annotations

import json
from urllib.parse import quote

import requests

from .EnvironTool import config
from .printer import print_flush, YELLOW, RESET

# 识别接口（可用环境变量 OCR_API 覆盖）
OCR_API = (config.get("OCR_API") or "https://learning.twt.edu.cn/ocr").strip()
# 识别接口超时（秒）
OCR_TIMEOUT = int(config.get("OCR_TIMEOUT") or 10)
# 取图超时（秒）
CAPTCHA_TIMEOUT = int(config.get("CAPTCHA_TIMEOUT") or 10)
# 最多尝试几次（每次都会重新取一张图）
MAX_ATTEMPTS = int(config.get("CAPTCHA_MAX_ATTEMPTS") or 3)
# 验证码位数
CODE_LENGTH = 4

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.76"
)


def parse_ocr_response(payload: object) -> str:
    """从接口返回里取出验证码文本。

    成功形如 {"code": 200, "data": "x1rw"}；
    失败会返回 HTML（HTTP 500）异常处理。
    """
    if isinstance(payload, str):
        return payload.strip()
    if not isinstance(payload, dict):
        return ""
    data = payload.get("data")
    if isinstance(data, str) and data.strip():
        return data.strip()
    return ""


class CaptchaHandler:
    def __init__(self, session: requests.Session, service: str):
        self.x = session
        self.captcha_url = "https://sso.tju.edu.cn/cas/code"
        self.headers = {
            "User-Agent": USER_AGENT,
            "Referer": "https://sso.tju.edu.cn/cas/login?service=" + quote(service, safe="-_.!~*'()"),
        }
        self.ocr_api = OCR_API
        self.ocr_headers = {
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Connection": "keep-alive",
        }

    def fetch_image(self) -> bytes:
        """从 CAS 取一张新的验证码图片。"""
        response = self.x.get(self.captcha_url, headers=self.headers, timeout=CAPTCHA_TIMEOUT)
        response.raise_for_status()
        return response.content

    def recognize(self, image: bytes) -> str:
        """把图片发给 OCR 接口，返回识别出的文本（失败返回空串）。"""
        try:
            response = requests.post(
                self.ocr_api,
                headers=self.ocr_headers,
                files={"image": ("code.jpeg", image)},
                timeout=OCR_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            print_flush(f"{YELLOW}[captcha] OCR 接口请求失败：{e}{RESET}")
            return ""

        try:
            payload = response.json()
        except (json.JSONDecodeError, ValueError):
            # 失败时
            print_flush(
                f"{YELLOW}[captcha] OCR 接口返回非 JSON{RESET}"
            )
            return ""

        biz_code = payload.get("code") if isinstance(payload, dict) else None
        if biz_code not in (None, 200, "200"):
            print_flush(f"{YELLOW}[captcha] OCR 接口业务码异常：{biz_code}{RESET}")
            return ""

        result = parse_ocr_response(payload)
        # 验证码必须是 4 位
        if len(result) != CODE_LENGTH:
            print_flush(
                f"{YELLOW}[captcha] OCR 返回内容不是 {CODE_LENGTH} 位（{result[:60]!r}），丢弃{RESET}"
            )
            return ""
        print_flush(f"[captcha] OCR 识别结果：{result}")
        return result

    def read_captcha(self) -> str:
        """取一张图并识别。"""
        return self.recognize(self.fetch_image())

    def get_final_captcha(self) -> str:
        """循环取图识别，直到拿到 4 位验证码；始终失败则抛异常。"""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                result = self.read_captcha()
            except requests.RequestException as e:
                print_flush(f"{YELLOW}[captcha] 第 {attempt}/{MAX_ATTEMPTS} 次取图失败：{e}{RESET}")
                continue
            if len(result) == CODE_LENGTH:
                return result
            print_flush(
                f"{YELLOW}[captcha] 第 {attempt}/{MAX_ATTEMPTS} 次识别结果不可用"
                f"（{result!r}），重新取图{RESET}"
            )
        raise RuntimeError(f"验证码识别失败")
