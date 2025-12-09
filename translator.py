"""
腾讯云翻译 API 封装模块
使用腾讯云机器翻译服务进行文本翻译
"""
import json
import hashlib
import hmac
import time
from datetime import datetime
import threading
import logging
from typing import Optional, Callable

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.warning("requests 模块未安装，翻译功能将不可用")


class TencentTranslator:
    """腾讯云翻译器"""
    
    def __init__(self, secret_id: str = "", secret_key: str = ""):
        """
        初始化翻译器
        
        Args:
            secret_id: 腾讯云 SecretId
            secret_key: 腾讯云 SecretKey
        """
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.endpoint = "tmt.tencentcloudapi.com"
        self.service = "tmt"
        self.version = "2018-03-21"
        self.region = "ap-guangzhou"
        
        # 翻译状态
        self._cancel_flag = False
        self._current_thread: Optional[threading.Thread] = None
        
    def set_credentials(self, secret_id: str, secret_key: str):
        """设置 API 凭证"""
        self.secret_id = secret_id
        self.secret_key = secret_key
    
    def is_configured(self) -> bool:
        """检查是否已配置 API 凭证"""
        return bool(self.secret_id and self.secret_key)
    
    def _sign(self, params: dict, timestamp: int, date: str) -> str:
        """
        生成 TC3-HMAC-SHA256 签名
        """
        # 步骤1：拼接规范请求串
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""
        payload = json.dumps(params)
        
        # 注意：header name 小写，header value 保持原样
        canonical_headers = (
            f"content-type:application/json; charset=utf-8\n"
            f"host:{self.endpoint}\n"
        )
        signed_headers = "content-type;host"
        hashed_request_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        
        canonical_request = (
            f"{http_request_method}\n"
            f"{canonical_uri}\n"
            f"{canonical_querystring}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{hashed_request_payload}"
        )
        
        # 步骤2：拼接待签名字符串
        algorithm = "TC3-HMAC-SHA256"
        credential_scope = f"{date}/{self.service}/tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        
        string_to_sign = (
            f"{algorithm}\n"
            f"{timestamp}\n"
            f"{credential_scope}\n"
            f"{hashed_canonical_request}"
        )
        
        # 步骤3：计算签名
        def _hmac_sha256(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()
        
        secret_date = _hmac_sha256(("TC3" + self.secret_key).encode("utf-8"), date)
        secret_service = _hmac_sha256(secret_date, self.service)
        secret_signing = _hmac_sha256(secret_service, "tc3_request")
        signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        
        # 步骤4：拼接 Authorization
        authorization = (
            f"{algorithm} "
            f"Credential={self.secret_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )
        
        return authorization
    
    def translate(
        self, 
        text: str, 
        source: str = "auto", 
        target: str = "zh",
        on_success: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None
    ) -> Optional[str]:
        """
        翻译文本（同步方式）
        
        Args:
            text: 待翻译文本
            source: 源语言（auto 自动检测）
            target: 目标语言（zh 中文, en 英文等）
            on_success: 成功回调
            on_error: 错误回调
            on_cancel: 取消回调
            
        Returns:
            翻译结果，失败返回 None
        """
        if not REQUESTS_AVAILABLE:
            error_msg = "requests 模块未安装"
            if on_error:
                on_error(error_msg)
            return None
        
        if not self.is_configured():
            error_msg = "翻译 API 未配置"
            if on_error:
                on_error(error_msg)
            return None
        
        if self._cancel_flag:
            if on_cancel:
                on_cancel()
            return None
        
        try:
            # 准备请求参数
            timestamp = int(time.time())
            date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
            
            params = {
                "SourceText": text,
                "Source": source,
                "Target": target,
                "ProjectId": 0
            }
            
            # 生成签名
            authorization = self._sign(params, timestamp, date)
            
            # 发送请求
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Host": self.endpoint,
                "X-TC-Action": "TextTranslate",
                "X-TC-Version": self.version,
                "X-TC-Timestamp": str(timestamp),
                "X-TC-Region": self.region,
                "Authorization": authorization
            }
            
            # 检查取消标志
            if self._cancel_flag:
                if on_cancel:
                    on_cancel()
                return None
            
            print(f"[翻译] 发送请求到 {self.endpoint}")
            print(f"[翻译] 待翻译文本: {text[:50]}..." if len(text) > 50 else f"[翻译] 待翻译文本: {text}")
            
            response = requests.post(
                f"https://{self.endpoint}",
                headers=headers,
                json=params,
                timeout=10
            )
            
            # 检查取消标志
            if self._cancel_flag:
                if on_cancel:
                    on_cancel()
                return None
            
            if response.status_code == 200:
                result = response.json()
                print(f"[翻译] API 响应: {result}")  # 调试输出
                if "Response" in result:
                    if "Error" in result["Response"]:
                        error_code = result["Response"]["Error"].get("Code", "")
                        error_msg = result["Response"]["Error"].get("Message", "未知错误")
                        
                        # 如果是语言识别错误且源语言是 auto，使用英语重试
                        if error_code == "FailedOperation.LanguageRecognitionErr" and source == "auto":
                            print(f"[翻译] 语言识别失败，使用英语重试...")
                            return self.translate(text, "en", target, on_success, on_error, on_cancel)
                        
                        full_error = f"{error_code}: {error_msg}"
                        print(f"[翻译] API 错误: {full_error}")
                        logging.error(f"翻译 API 错误: {full_error}")
                        if on_error:
                            on_error(full_error)
                        return None
                    
                    translated = result["Response"].get("TargetText", "")
                    print(f"[翻译] 成功: {translated[:50]}...")  # 调试输出
                    if on_success:
                        on_success(translated)
                    return translated
            
            error_msg = f"HTTP 错误: {response.status_code}"
            print(f"[翻译] {error_msg}, 响应: {response.text[:200]}")
            logging.error(error_msg)
            if on_error:
                on_error(error_msg)
            return None
            
        except requests.Timeout:
            error_msg = "翻译请求超时"
            print(f"[翻译] {error_msg}")
            logging.error(error_msg)
            if on_error:
                on_error(error_msg)
            return None
        except requests.RequestException as e:
            error_msg = f"网络请求失败: {str(e)}"
            print(f"[翻译] {error_msg}")
            logging.error(error_msg)
            if on_error:
                on_error(error_msg)
            return None
        except Exception as e:
            error_msg = f"翻译失败: {str(e)}"
            print(f"[翻译] {error_msg}")
            import traceback
            traceback.print_exc()
            logging.error(error_msg)
            if on_error:
                on_error(error_msg)
            return None
    
    def translate_async(
        self,
        text: str,
        source: str = "auto",
        target: str = "zh",
        on_success: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None
    ) -> threading.Thread:
        """
        异步翻译文本
        
        Args:
            text: 待翻译文本
            source: 源语言
            target: 目标语言
            on_success: 成功回调（在后台线程中执行）
            on_error: 错误回调（在后台线程中执行）
            on_cancel: 取消回调（在后台线程中执行）
            
        Returns:
            翻译线程
        """
        self._cancel_flag = False
        
        def _translate_worker():
            self.translate(text, source, target, on_success, on_error, on_cancel)
        
        self._current_thread = threading.Thread(target=_translate_worker, daemon=True)
        self._current_thread.start()
        return self._current_thread
    
    def cancel(self):
        """取消当前翻译"""
        self._cancel_flag = True
    
    def reset(self):
        """重置取消标志"""
        self._cancel_flag = False


# 支持的语言列表
SUPPORTED_LANGUAGES = {
    "auto": "自动检测",
    "zh": "中文",
    "en": "英语",
    "ja": "日语",
    "ko": "韩语",
    "fr": "法语",
    "de": "德语",
    "es": "西班牙语",
    "it": "意大利语",
    "ru": "俄语",
    "pt": "葡萄牙语",
    "vi": "越南语",
    "th": "泰语",
    "ar": "阿拉伯语",
}


# 全局翻译器实例
_translator_instance: Optional[TencentTranslator] = None


def get_translator() -> TencentTranslator:
    """获取全局翻译器实例"""
    global _translator_instance
    if _translator_instance is None:
        _translator_instance = TencentTranslator()
    return _translator_instance


if __name__ == "__main__":
    # 测试代码
    translator = TencentTranslator(
        secret_id="YOUR_SECRET_ID",
        secret_key="YOUR_SECRET_KEY"
    )
    
    if translator.is_configured():
        result = translator.translate("Hello, World!", target="zh")
        print(f"翻译结果: {result}")
    else:
        print("请配置 API 凭证")

