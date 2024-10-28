"""Config flow for 百度云备份."""
import logging
import subprocess
import sys
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

_LOGGER = logging.getLogger(__name__)
DOMAIN = "baidu_backup"

def install_bypy():
    """安装 bypy."""
    try:
        subprocess.check_call([
            sys.executable, 
            "-m", 
            "pip", 
            "install", 
            "bypy", 
            "--index-url", 
            "https://pypi.tuna.tsinghua.edu.cn/simple"
        ])
        return True
    except subprocess.CalledProcessError as e:
        _LOGGER.error("安装 bypy 失败: %s", str(e))
        return False

def check_bypy_installed():
    """检查 bypy 是否已安装."""
    try:
        subprocess.run(["bypy", "--help"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

class BaiduBackupConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for 百度云备份."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return BaiduBackupOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            # 检查并安装 bypy
            is_installed = await self.hass.async_add_executor_job(check_bypy_installed)
            if not is_installed:
                _LOGGER.info("正在安装 bypy...")
                success = await self.hass.async_add_executor_job(install_bypy)
                if not success:
                    return self.async_show_form(
                        step_id="user",
                        errors={"base": "install_failed"}
                    )
            
            return await self.async_step_auth()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
        )

    async def async_step_auth(self, user_input=None):
        """Handle authorization step."""
        errors = {}
        
        if user_input is not None:
            try:
                # 验证token
                process = subprocess.run(
                    ["bypy", "info"],
                    input=f"{user_input['token']}\n",
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                if "Quota" in process.stdout:
                    return self.async_create_entry(
                        title="百度云备份",
                        data={"token": user_input["token"]}
                    )
                else:
                    errors["base"] = "invalid_token"
            
            except subprocess.CalledProcessError as e:
                _LOGGER.error("Token验证失败: %s", str(e))
                errors["base"] = "token_failed"
            except Exception as e:
                _LOGGER.error("未知错误: %s", str(e))
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="auth",
            data_schema=vol.Schema({
                vol.Required("token"): str,
            }),
            description_placeholders={
                "auth_url": "https://openapi.baidu.com/oauth/2.0/authorize?client_id=q8WE4EpCsau1oS0MplgMKNBn&response_type=code&redirect_uri=oob&scope=basic+netdisk"
            },
            errors=errors,
        )

class BaiduBackupOptionsFlow(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_auth()

    async def async_step_auth(self, user_input=None):
        """Handle authorization options."""
        errors = {}
        
        if user_input is not None:
            try:
                # 验证token
                process = subprocess.run(
                    ["bypy", "info"],
                    input=f"{user_input['token']}\n",
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                if "Quota" in process.stdout:
                    # 更新配置项数据
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data={"token": user_input["token"]}
                    )
                    
                    # 重新加载集成
                    await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                    
                    return self.async_create_entry(title="", data={})
                else:
                    errors["base"] = "invalid_token"
            
            except subprocess.CalledProcessError as e:
                _LOGGER.error("Token验证失败: %s", str(e))
                errors["base"] = "token_failed"
            except Exception as e:
                _LOGGER.error("未知错误: %s", str(e))
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="auth",
            data_schema=vol.Schema({
                vol.Required("token"): str,
            }),
            description_placeholders={
                "auth_url": "https://openapi.baidu.com/oauth/2.0/authorize?client_id=q8WE4EpCsau1oS0MplgMKNBn&response_type=code&redirect_uri=oob&scope=basic+netdisk"
            },
            errors=errors,
        )