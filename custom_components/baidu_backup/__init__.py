"""百度云备份集成."""
import logging
import os
import asyncio
import subprocess
from datetime import datetime
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from .const import DOMAIN, STATUS_CHECKING, STATUS_UPLOADING, STATUS_SUCCESS, STATUS_FAILED, STATUS_ERROR, STATUS_MAP

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR, Platform.BUTTON]

def check_login():
    """检查登录状态."""
    try:
        result = subprocess.run(
            ["bypy", "info"],
            capture_output=True,
            text=True
        )
        return "Quota" in result.stdout
    except Exception as e:
        _LOGGER.error("检查百度云登录状态失败: %s", str(e))
        return False

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up baidu_backup from a config entry."""
    # 检查是否已登录
    try:
        is_logged_in = await hass.async_add_executor_job(check_login)
        if not is_logged_in:
            _LOGGER.warning("百度云未登录，需要重新授权")
            return False
            
    except Exception as e:
        _LOGGER.error("检查百度云登录状态失败: %s", str(e))
        return False

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "config": dict(entry.data),
        "sensors": {}
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def get_latest_backup(backup_dir: str) -> str:
        """获取最新的备份文件."""
        try:
            backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.tar')]
            if not backup_files:
                raise FileNotFoundError("没有找到备份文件")
            
            latest_backup = max(
                backup_files,
                key=lambda x: os.path.getmtime(os.path.join(backup_dir, x))
            )
            
            return os.path.join(backup_dir, latest_backup)
        except Exception as e:
            _LOGGER.error("获取最新备份文件失败: %s", str(e))
            raise

    async def check_sync_status(backup_dir: str) -> bool:
        """检查同步状态."""
        try:
            result = subprocess.run(
                ["nice", "-n", "19", "bypy", "compare", "HomeAssistant备份", backup_dir],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                output = result.stdout
                if "Local only: 0" in output and "Remote only: 0" in output:
                    return True
            return False
        except Exception as e:
            _LOGGER.error("检查同步状态失败: %s", str(e))
            return False

    async def upload_to_baidu(call):
        """上传最新备份文件到百度云盘."""
        try:
            status_sensor = None
            for entry_id, data in hass.data[DOMAIN].items():
                if "sensors" in data and "status_sensor" in data["sensors"]:
                    status_sensor = data["sensors"]["status_sensor"]
                    break
            
            if status_sensor:
                await status_sensor.async_set_status(STATUS_CHECKING)
            
            backup_dir = os.path.join(hass.config.config_dir, "backups")
            if not os.path.exists(backup_dir):
                raise FileNotFoundError("备份目录不存在")
            
            backup_file = await get_latest_backup(backup_dir)
            backup_filename = os.path.basename(backup_file)
            
            if status_sensor:
                await status_sensor.async_set_status(STATUS_UPLOADING)
            
            process = await asyncio.create_subprocess_exec(
                "nice", "-n", "19",
                "ionice", "-c", "2", "-n", "7",
                "bypy", "upload", backup_file, f"/HomeAssistant备份/{backup_filename}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                _LOGGER.info("备份文件 %s 上传成功", backup_filename)
                if status_sensor:
                    await status_sensor.async_set_status(STATUS_SUCCESS)
            else:
                _LOGGER.error("上传失败: %s", stderr.decode())
                if status_sensor:
                    await status_sensor.async_set_status(STATUS_FAILED)
            
        except FileNotFoundError as e:
            _LOGGER.error(str(e))
            if status_sensor:
                await status_sensor.async_set_status(STATUS_ERROR)
        except Exception as e:
            _LOGGER.error("上传失败: %s", str(e))
            if status_sensor:
                await status_sensor.async_set_status(STATUS_ERROR)

    hass.services.async_register(DOMAIN, "upload", upload_to_baidu)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok