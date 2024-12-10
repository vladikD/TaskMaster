from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, LabelViewSet, ProjectViewSet, CommentViewSet, RegisterView, ObtainTokenView

router = DefaultRouter()
router.register(r'tasks', TaskViewSet)
router.register(r'labels', LabelViewSet)
router.register(r'projects', ProjectViewSet)
router.register(r'comments', CommentViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', ObtainTokenView.as_view(), name='login'),
]
