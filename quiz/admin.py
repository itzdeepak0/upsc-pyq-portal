from django.contrib import admin
from .models import Subject, Source, Question, ExamSession, ExamResponse

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'total_questions', 'created_at')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title',)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_number', 'topic', 'source', 'subject', 'correct_option', 'difficulty', 'is_bookmarked')
    list_filter = ('source', 'subject', 'difficulty', 'is_bookmarked')
    search_fields = ('topic', 'question_text', 'explanation', 'in_news')
    ordering = ('source', 'question_number')

@admin.register(ExamSession)
class ExamSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'mode', 'score', 'correct_count', 'wrong_count', 'accuracy', 'is_submitted', 'created_at')
    list_filter = ('mode', 'is_submitted')
    readonly_fields = ('session_id', 'created_at', 'completed_at')

@admin.register(ExamResponse)
class ExamResponseAdmin(admin.ModelAdmin):
    list_display = ('session', 'question', 'selected_option', 'is_correct', 'is_marked_for_review')
