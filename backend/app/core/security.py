"""
安全相关功能
包括JWT token生成/验证、密码哈希等
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# ===== JWT配置 =====
ALGORITHM = settings.JWT_ALGORITHM
SECRET_KEY = settings.JWT_SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS


# ===== 密码哈希 =====
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码

    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码

    Returns:
        bool: 密码是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    生成密码哈希

    Args:
        password: 明文密码

    Returns:
        str: 哈希后的密码
    """
    return pwd_context.hash(password)


# ===== JWT Token =====
def create_access_token(
    subject: str,
    additional_claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建访问Token

    Args:
        subject: Token主体（通常是用户ID）
        additional_claims: 额外的声明
        expires_delta: 过期时间增量

    Returns:
        str: JWT Token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }

    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    subject: str,
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    创建刷新Token

    Args:
        subject: Token主体（通常是用户ID）
        additional_claims: 额外的声明

    Returns:
        str: JWT Token
    """
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }

    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    解码访问Token

    Args:
        token: JWT Token

    Returns:
        Dict[str, Any]: Token载荷

    Raises:
        JWTError: Token无效或过期
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # 验证token类型
        if payload.get("type") != "access":
            raise JWTError("无效的token类型")

        return payload

    except JWTError as e:
        raise JWTError(f"Token解码失败: {str(e)}")


def decode_refresh_token(token: str) -> Dict[str, Any]:
    """
    解码刷新Token

    Args:
        token: JWT Token

    Returns:
        Dict[str, Any]: Token载荷

    Raises:
        JWTError: Token无效或过期
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # 验证token类型
        if payload.get("type") != "refresh":
            raise JWTError("无效的token类型")

        return payload

    except JWTError as e:
        raise JWTError(f"Token解码失败: {str(e)}")


# ===== 企业微信验证 =====
def verify_wechat_signature(
    signature: str,
    timestamp: str,
    nonce: str,
    msg_encrypt: str
) -> bool:
    """
    验证企业微信消息签名

    Args:
        signature: 签名
        timestamp: 时间戳
        nonce: 随机字符串
        msg_encrypt: 加密消息

    Returns:
        bool: 签名是否有效
    """
    from hashlib import sha1
    import string

    # 排序
    arr = [settings.WECHAT_TOKEN, timestamp, nonce, msg_encrypt]
    arr.sort()

    # 拼接
    tmp_str = "".join(arr)

    # SHA1加密
    signature_calc = sha1(tmp_str.encode()).hexdigest()

    return signature_calc == signature


# ===== 敏感信息脱敏 =====
def mask_email(email: str) -> str:
    """
    脱敏邮箱

    Args:
        email: 邮箱地址

    Returns:
        str: 脱敏后的邮箱
    """
    if "@" not in email:
        return email

    name, domain = email.split("@", 1)
    if len(name) <= 2:
        masked_name = name[0] + "***"
    else:
        masked_name = name[:2] + "***"

    return f"{masked_name}@{domain}"


def mask_phone(phone: str) -> str:
    """
    脱敏手机号

    Args:
        phone: 手机号

    Returns:
        str: 脱敏后的手机号
    """
    if len(phone) < 7:
        return phone

    return phone[:3] + "****" + phone[-4:]
