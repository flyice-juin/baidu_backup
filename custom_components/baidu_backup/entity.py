"""Base entity for baidu_backup."""
from homeassistant.helpers.entity import Entity, DeviceInfo
from .const import DOMAIN, DEFAULT_NAME

class BaiduBackupEntity(Entity):
    """Base entity for baidu_backup."""

    _attr_has_entity_name = True
    
    def __init__(self, unique_id_suffix: str) -> None:
        """Initialize the entity."""
        self._attr_unique_id = f"{DOMAIN}_{unique_id_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, DOMAIN)},
            name=DEFAULT_NAME,
            manufacturer="知识便利贴",
            model="云备份",
        )