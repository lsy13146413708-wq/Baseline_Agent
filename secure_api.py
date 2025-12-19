# -*- coding: utf-8 -*-
"""
API Key 安全模块：
- 优先从 .env 文件读取指定 Key（推荐）
- 可选从加密文件读取，使用口令解密（支持 cryptography.Fernet，加密文件不应提交到仓库）
- 仍支持从环境变量读取作为兜底
"""

import os
import base64
import json
import hashlib
from typing import Optional, Dict


def _derive_fernet_key(passphrase: str) -> bytes:
    # 通过 SHA256 派生 32 字节 key，并转换为 urlsafe_b64 供 Fernet 使用
    digest = hashlib.sha256(passphrase.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _parse_env_file(env_file: str) -> Dict[str, str]:
    # 解析简单 .env 文件（KEY=VALUE，支持引号与注释），返回字典
    data: Dict[str, str] = {}
    with open(env_file, "r", encoding="utf-8") as fr:
        for line in fr:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if "=" not in s:
                continue
            k, v = s.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            data[k] = v
    return data


def load_api_key(api_key_env: str = "DEEPSEEK_API_KEY", encrypted_file: Optional[str] = None, pass_env: str = "DEEPSEEK_KEY_PASSPHRASE", env_file: Optional[str] = None, key_name: str = "DEEPSEEK_API_KEY") -> str:
    # 读取 API Key：优先 .env 文件；其次加密文件；最后环境变量
    if env_file and os.path.exists(env_file):
        envs = _parse_env_file(env_file)
        val = envs.get(key_name)
        if val:
            return val

    if encrypted_file and os.path.exists(encrypted_file):
        passphrase = os.getenv(pass_env)
        if not passphrase:
            raise RuntimeError(f"未找到用于解密的口令环境变量 {pass_env}")
        try:
            from cryptography.fernet import Fernet

            fkey = _derive_fernet_key(passphrase)
            f = Fernet(fkey)
            token = open(encrypted_file, "rb").read()
            decrypted = f.decrypt(token)
            return decrypted.decode("utf-8")
        except Exception:
            data = json.loads(open(encrypted_file, "r", encoding="utf-8").read())
            salt = base64.b64decode(data["salt"])  # bytes
            payload = base64.b64decode(data["data"])  # bytes
            k = hashlib.sha256(salt + passphrase.encode("utf-8")).digest()
            plain_bytes = bytes([b ^ k[i % len(k)] for i, b in enumerate(payload)])
            return plain_bytes.decode("utf-8")

    # 兜底：环境变量
    key = os.getenv(api_key_env) or os.getenv(key_name)
    if key:
        return key
    raise RuntimeError(
        f"未找到 API Key。请在 .env 中设置 {key_name}，或提供 --key_file 加密文件并设置口令环境变量，或设置环境变量 {api_key_env}/{key_name}。"
    )


def save_encrypted_api_key(api_key: str, outfile: str, passphrase: str) -> None:
    # 将 API Key 加密保存到文件（优先 Fernet，失败回退轻量混淆）
    try:
        from cryptography.fernet import Fernet

        fkey = _derive_fernet_key(passphrase)
        f = Fernet(fkey)
        token = f.encrypt(api_key.encode("utf-8"))
        with open(outfile, "wb") as fw:
            fw.write(token)
    except Exception:
        import secrets

        salt = secrets.token_bytes(16)
        k = hashlib.sha256(salt + passphrase.encode("utf-8")).digest()
        payload = bytes([b ^ k[i % len(k)] for i, b in enumerate(api_key.encode("utf-8"))])
        record = {
            "salt": base64.b64encode(salt).decode("ascii"),
            "data": base64.b64encode(payload).decode("ascii"),
        }
        with open(outfile, "w", encoding="utf-8") as fw:
            json.dump(record, fw, ensure_ascii=False)
