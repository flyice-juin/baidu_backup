"""百度云备份按钮."""
from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from .entity import BaiduBackupEntity
import subprocess
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the 百度云备份 button."""
    async_add_entities([
        BaiduUploadButton(hass),
        BaiduLogoutButton(hass, config_entry)
    ], True)

class BaiduUploadButton(BaiduBackupEntity, ButtonEntity):
    """开始上传按钮."""

    def __init__(self, hass):
        """初始化按钮."""
        super().__init__("upload_button")
        self.hass = hass
        self._attr_name = "开始备份"
        self._attr_icon = "mdi:cloud-upload"

    async def async_press(self) -> None:
        """处理按钮按下事件."""
        await self.hass.services.async_call("baidu_backup", "upload", {})

class BaiduLogoutButton(BaiduBackupEntity, ButtonEntity):
    """退出账号按钮."""

    def __init__(self, hass, config_entry):
        """初始化按钮."""
        super().__init__("logout_button")
        self.hass = hass
        self.config_entry = config_entry
        self._attr_name = "退出账号"
        self._attr_icon = "mdi:logout"

    def logout(self):
        """执行退出操作."""
        process = subprocess.Popen(
            ["bypy", "-c"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        
        if process.returncode == 0 and "Token file" in stdout and "removed" in stdout:
            return True
        return False

    async def async_press(self) -> None:
        """处理按钮按下事件."""
        try:
            success = await self.hass.async_add_executor_job(self.logout)
            
            if success:
                _LOGGER.info("百度云账号已退出")
                # 重新加载配置项
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            else:
                _LOGGER.error("退出账号失败")
        except Exception as e:
            _LOGGER.error("退出账号时发生错误: %s", str(e))