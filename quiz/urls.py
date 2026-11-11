from django.urls import path
from . import views

app_name = 'quiz'

urlpatterns = [
    path('', views.home, name='home'),
    path('practice/', views.practice_view, name='practice'),
    path('explorer/', views.question_explorer, name='explorer'),
    path('exam/setup/', views.exam_setup, name='exam_setup'),
    path('exam/<uuid:session_id>/', views.exam_runner, name='exam_runner'),
    path('exam/<uuid:session_id>/submit/', views.exam_submit, name='exam_submit'),
    path('exam/results/<uuid:session_id>/', views.exam_results, name='exam_results'),
    path('upload/', views.upload_pdf, name='upload_pdf'),
    path('upload/scan-inbox/', views.scan_inbox_api, name='scan_inbox_api'),
    path('editions/', views.editions_manager, name='editions'),
    path('editions/<slug:slug>/export/', views.export_edition_json, name='export_edition_json'),
    path('editions/<slug:slug>/delete/', views.delete_edition, name='delete_edition'),
    path('api/bookmark/<int:question_id>/', views.toggle_bookmark, name='toggle_bookmark'),
    path('api/questions/', views.api_questions, name='api_questions'),
]
