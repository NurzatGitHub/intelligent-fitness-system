from drf_yasg.inspectors import SwaggerAutoSchema

class JWTAutoSchema(SwaggerAutoSchema):
    def get_security_definitions(self):
        security_definitions = super().get_security_definitions() or {}
        security_definitions['Bearer'] = {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'JWT Authorization header using the Bearer scheme. Example: "Authorization: Bearer {token}"'
        }
        return security_definitions
    
    def get_security_requirements(self):
        security = super().get_security_requirements()
        if security is None:
            security = []
        
        # Добавляем JWT аутентификацию для всех эндпоинтов, кроме публичных
        view = self.view
        if hasattr(view, 'permission_classes'):
            if any('IsAuthenticated' in str(p) for p in view.permission_classes):
                security.append({'Bearer': []})
        
        return security