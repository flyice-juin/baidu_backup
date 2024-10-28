"""Constants for baidu_backup."""
from datetime import timedelta

DOMAIN = "baidu_backup"
SCAN_INTERVAL = timedelta(minutes=1)
DEFAULT_NAME = "百度云盘"

# 状态
STATUS_IDLE = "idle"
STATUS_CHECKING = "checking"
STATUS_UPLOADING = "uploading"
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"
STATUS_ERROR = "error"

STATUS_MAP = {
    STATUS_IDLE: "空闲",
    STATUS_CHECKING: "检查中",
    STATUS_UPLOADING: "上传中",
    STATUS_SUCCESS: "上传成功",
    STATUS_FAILED: "上传失败",
    STATUS_ERROR: "发生错误"
}