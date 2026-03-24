class AccessPasswordModel:
    """Read access password from runtime configuration."""

    def get_password(self, runtime_config) -> str:
        password = runtime_config.get('APP_ACCESS_PASSWORD', '')
        if not isinstance(password, str):
            raise ValueError('访问密码配置不合法')

        password = password.strip()
        if not password:
            raise ValueError('访问密码未配置')
        return password


access_password_model = AccessPasswordModel()
