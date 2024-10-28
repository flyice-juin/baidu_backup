"""百度云备份传感器."""
import logging
import subprocess
from datetime import datetime
import pytz
import os
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from .const import (
    DOMAIN,
    SCAN_INTERVAL,
    STATUS_MAP,
    STATUS_IDLE,
    STATUS_CHECKING,
    STATUS_UPLOADING,
    STATUS_SUCCESS,
    STATUS_FAILED,
    STATUS_ERROR,
)
from .entity import BaiduBackupEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the 百度云备份 sensors."""
    status_sensor = BaiduStatusSensor(hass)
    hass.data[DOMAIN][config_entry.entry_id]["sensors"]["status_sensor"] = status_sensor
    
    async_add_entities([
        BaiduQuotaSensor(),
        BaiduUsedSpaceSensor(),
        BaiduLastUploadSensor(hass),
        status_sensor
    ], True)

class BaiduQuotaSensor(BaiduBackupEntity, SensorEntity):
    """总容量传感器."""

    def __init__(self):
        """Initialize the sensor."""
        super().__init__("quota")
        self._attr_name = "总容量"
        self._attr_native_unit_of_measurement = "GB"
        self._attr_icon = "mdi:database"

    def update(self) -> None:
        """更新容量信息."""
        try:
            result = subprocess.run(
                ["nice", "-n", "19", "bypy", "info"],
                capture_output=True,
                text=True
            )
            output = result.stdout
            if "Quota:" in output:
                quota = output.split("Quota:")[1].split("\n")[0].strip()
                if "TB" in quota:
                    value = int(float(quota.replace("TB", "")) * 1024)
                else:
                    value = int(float(quota.replace("GB", "")))
                self._attr_native_value = value
        except Exception as e:
            _LOGGER.error("更新容量失败: %s", str(e))

class BaiduUsedSpaceSensor(BaiduBackupEntity, SensorEntity):
    """已用空间传感器."""

    def __init__(self):
        """Initialize the sensor."""
        super().__init__("used")
        self._attr_name = "已用空间"
        self._attr_native_unit_of_measurement = "GB"
        self._attr_icon = "mdi:database-check"

    def update(self) -> None:
        """更新已用空间信息."""
        try:
            result = subprocess.run(
                ["nice", "-n", "19", "bypy", "info"],
                capture_output=True,
                text=True
            )
            output = result.stdout
            if "Used:" in output:
                used = output.split("Used:")[1].split("\n")[0].strip()
                if "TB" in used:
                    value = int(float(used.replace("TB", "")) * 1024)
                else:
                    value = int(float(used.replace("GB", "")))
                self._attr_native_value = value
        except Exception as e:
            _LOGGER.error("更新已用空间失败: %s", str(e))

class BaiduLastUploadSensor(BaiduBackupEntity, SensorEntity):
    """最后上传时间传感器."""

    def __init__(self, hass):
        """Initialize the sensor."""
        super().__init__("last_upload")
        self.hass = hass
        self._attr_name = "最后上传时间"
        self._attr_device_class = "timestamp"
        self._attr_icon = "mdi:clock-check"

    def update(self) -> None:
        """更新上传时间."""
        try:
            backup_dir = os.path.join(self.hass.config.config_dir, "backups")
            result = subprocess.run(
                ["nice", "-n", "19", "bypy", "compare", "HomeAssistant备份", backup_dir],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                output = result.stdout
                local_only = 0
                remote_only = 0
                
                for line in output.split('\n'):
                    if "Local only:" in line:
                        local_only = int(line.split(':')[1].strip())
                    elif "Remote only:" in line:
                        remote_only = int(line.split(':')[1].strip())
                
                # 如果本地和远程文件数量相同，说明同步完成
                if local_only == 0:
                    # 获取最新的远程文件时间
                    list_result = subprocess.run(
                        ["nice", "-n", "19", "bypy", "list", "HomeAssistant备份"],
                        capture_output=True,
                        text=True
                    )
                    
                    if list_result.returncode == 0:
                        list_output = list_result.stdout
                        latest_time = None
                        
                        for line in list_output.split('\n'):
                            if '.tar' in line:  # 只处理备份文件
                                parts = line.split()
                                date_str = None
                                time_str = None
                                
                                for part in parts:
                                    if part.startswith("202"):  # 查找日期
                                        date_str = part.rstrip(',')
                                    elif ":" in part:  # 查找时间
                                        time_str = part
                                
                                if date_str and time_str:
                                    datetime_str = f"{date_str} {time_str}"
                                    current_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                                    if latest_time is None or current_time > latest_time:
                                        latest_time = current_time
                        
                        if latest_time:
                            latest_time = latest_time.replace(tzinfo=pytz.UTC)
                            local_tz = pytz.timezone('Asia/Shanghai')
                            local_time = latest_time.astimezone(local_tz)
                            self._attr_native_value = local_time
                
        except Exception as e:
            _LOGGER.error("更新上传时间失败: %s", str(e))

class BaiduStatusSensor(BaiduBackupEntity, SensorEntity):
    """备份状态传感器."""

    def __init__(self, hass):
        """Initialize the sensor."""
        super().__init__("status")
        self.hass = hass
        self._attr_name = "状态"
        self._attr_native_value = STATUS_IDLE
        self._attr_extra_state_attributes = {"说明": STATUS_MAP[STATUS_IDLE]}
        self._last_local_only = None
        self._is_uploading = False
        self._attr_icon = "mdi:cloud-sync"
    
    async def async_set_status(self, status: str, progress: str = None):
        """设置状态."""
        self._attr_native_value = status
        attributes = {"说明": STATUS_MAP.get(status, "未知状态")}
        if progress:
            attributes["进度"] = progress
        self._attr_extra_state_attributes = attributes
        
        # 根据状态更新图标
        if status == STATUS_IDLE:
            self._attr_icon = "mdi:cloud-sync"
        elif status == STATUS_CHECKING:
            self._attr_icon = "mdi:cloud-search"
        elif status == STATUS_UPLOADING:
            self._attr_icon = "mdi:cloud-upload"
        elif status == STATUS_SUCCESS:
            self._attr_icon = "mdi:cloud-check"
        elif status in [STATUS_FAILED, STATUS_ERROR]:
            self._attr_icon = "mdi:cloud-alert"
        
        if status == STATUS_UPLOADING:
            self._is_uploading = True
            self._last_local_only = None
        elif status in [STATUS_SUCCESS, STATUS_FAILED, STATUS_ERROR]:
            self._is_uploading = False
            self._last_local_only = None
            
        self.async_write_ha_state()
    
    def update(self) -> None:
        """更新状态."""
        try:
            # 只在上传状态下检查同步状态
            if self._is_uploading:
                backup_dir = os.path.join(self.hass.config.config_dir, "backups")
                result = subprocess.run(
                    ["nice", "-n", "19", "bypy", "compare", "HomeAssistant备份", backup_dir],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    output = result.stdout
                    local_only = 0
                    for line in output.split('\n'):
                        if "Local only:" in line:
                            try:
                                local_only = int(line.split(':')[1].strip())
                                break
                            except (ValueError, IndexError):
                                continue
                    
                    # 第一次检查，记录初始值
                    if self._last_local_only is None:
                        self._last_local_only = local_only
                        _LOGGER.debug("初始 Local only 数量: %d", local_only)
                    # Local only从不为0变为0，说明上传完成
                    elif self._last_local_only > 0 and local_only == 0:
                        self._attr_native_value = STATUS_SUCCESS
                        self._attr_extra_state_attributes = {"说明": STATUS_MAP[STATUS_SUCCESS]}
                        self._attr_icon = "mdi:cloud-check"
                        self._is_uploading = False
                        _LOGGER.info("检测到上传完成")
                    # 更新last_local_only
                    self._last_local_only = local_only
                    
        except Exception as e:
            _LOGGER.error("更新状态失败: %s", str(e))
    
    @property
    def extra_state_attributes(self):
        """返回状态说明."""
        return self._attr_extra_state_attributes