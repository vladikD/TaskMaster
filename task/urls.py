from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, LabelViewSet, ProjectViewSet, CommentViewSet, RegisterView, ObtainTokenView, \
    ProjectDetailNestedView, ColumnViewSet, InvitationCreateView, InvitationAcceptView
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
router.register(r'columns', ColumnViewSet)

project_add_user = ProjectViewSet.as_view({
    'post': 'add_user'
})
project_remove_user = ProjectViewSet.as_view({
    'delete': 'remove_user'
})

task_assign_user = TaskViewSet.as_view({
    'patch': 'assign_user'
})
task_unassign_user = TaskViewSet.as_view({
    'delete': 'unassign'
})

urlpatterns = [
    path('api/', include(router.urls)),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', ObtainTokenView.as_view(), name='login'),
    path('auth/', include('social_django.urls', namespace='social')),

    path('invitations/create/', InvitationCreateView.as_view(), name='invitation-create'),
    path('invitations/accept/', InvitationAcceptView.as_view(), name='invitation-accept'),

    path('api/projects/<int:pk>/add-user/', project_add_user, name='project-add-user'),
    path('api/projects/<int:pk>/remove-user/<int:user_id>/', project_remove_user, name='project-remove-user'),

    path('api/tasks/<int:pk>/assign/', task_assign_user, name='task-assign-user'),
    path('api/tasks/<int:pk>/unassign/', task_unassign_user, name='task-unassign-user'),

    path('project/<int:pk>/full/', ProjectDetailNestedView.as_view(), name='project-detail-nested'),

    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]
