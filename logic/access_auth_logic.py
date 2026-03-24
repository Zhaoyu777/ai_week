from model.access_password_model import access_password_model


class AccessAuthLogic:
    SESSION_KEY = 'access_granted'
    PUBLIC_PATHS = {'/login', '/logout'}

    def __init__(self, password_model):
        self.password_model = password_model

    def authenticate(self, password: object, session_obj, runtime_config) -> None:
        if not isinstance(password, str):
            raise ValueError('密码格式不合法')

        cleaned_password = password.strip()
        if not cleaned_password:
            raise ValueError('密码不能为空')

        configured_password = self.password_model.get_password(runtime_config)
        if cleaned_password != configured_password:
            raise ValueError('密码错误')

        session_obj[self.SESSION_KEY] = True

    def logout(self, session_obj) -> None:
        session_obj.pop(self.SESSION_KEY, None)

    def is_authenticated(self, session_obj) -> bool:
        return bool(session_obj.get(self.SESSION_KEY))

    def is_public_request(self, path: str, endpoint: str) -> bool:
        if endpoint == 'static':
            return True
        return path in self.PUBLIC_PATHS

    def is_api_request(self, path: str) -> bool:
        return path.startswith('/api/')

    def normalize_next_path(self, next_path: object) -> str:
        if not isinstance(next_path, str):
            return '/'

        cleaned_path = next_path.strip()
        if not cleaned_path or not cleaned_path.startswith('/'):
            return '/'
        if cleaned_path.startswith('//'):
            return '/'
        if cleaned_path in self.PUBLIC_PATHS:
            return '/'
        return cleaned_path


access_auth_logic = AccessAuthLogic(access_password_model)
