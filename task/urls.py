from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, LabelViewSet, ProjectViewSet, CommentViewSet, RegisterView, ObtainTokenView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

router = DefaultRouter()
router.register(r'tasks', TaskViewSet)
router.register(r'labels', LabelViewSet)
router.register(r'projects', ProjectViewSet)
router.register(r'comments', CommentViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', ObtainTokenView.as_view(), name='login'),
    path('auth/', include('social_django.urls', namespace='social')),

    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]
