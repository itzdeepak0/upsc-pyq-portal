import uuid
from django.db import models
from django.utils.text import slugify

class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=50, default='book-open')
    badge_color = models.CharField(max_length=100, default='bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Source(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    file = models.FileField(upload_to='pdf_sources/', null=True, blank=True)
    total_questions = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Source.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def update_question_count(self):
        self.total_questions = self.questions.count()
        self.save(update_fields=['total_questions'])

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']


class Question(models.Model):
    OPTION_CHOICES = [
        ('a', 'Option A'),
        ('b', 'Option B'),
        ('c', 'Option C'),
        ('d', 'Option D'),
    ]

    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]

    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='questions')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name='questions')
    question_number = models.PositiveIntegerField(help_text="Original question number in the test series")
    topic = models.CharField(max_length=255, help_text="e.g. Article 124, NITI Aayog")
    
    question_text = models.TextField(help_text="Full question text including statement list and interrogative")
    option_a = models.TextField()
    option_b = models.TextField()
    option_c = models.TextField()
    option_d = models.TextField()
    
    correct_option = models.CharField(max_length=1, choices=OPTION_CHOICES)
    explanation = models.TextField(help_text="Detailed point-by-point explanation")
    value_addition = models.TextField(blank=True, default='', help_text="Value addition notes, tables, and extra context")
    in_news = models.TextField(blank=True, default='', help_text="Current affairs news trigger")
    
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='Medium')
    is_bookmarked = models.BooleanField(default=False)
    
    times_attempted = models.PositiveIntegerField(default=0)
    times_correct = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_option_text(self, opt_key):
        opt_key = (opt_key or '').lower()
        mapping = {
            'a': self.option_a,
            'b': self.option_b,
            'c': self.option_c,
            'd': self.option_d,
        }
        return mapping.get(opt_key, '')

    @property
    def accuracy_percentage(self):
        if self.times_attempted == 0:
            return 0
        return round((self.times_correct / self.times_attempted) * 100, 1)

    def __str__(self):
        return f"Q{self.question_number}: {self.topic} ({self.source.title})"

    class Meta:
        ordering = ['source', 'question_number']
        unique_together = ('source', 'question_number')


class ExamSession(models.Model):
    MODE_CHOICES = [
        ('practice', 'Practice / Study Mode'),
        ('exam', 'Timed UPSC Mock Exam'),
    ]

    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    title = models.CharField(max_length=200, default='UPSC Prelims Mock Test')
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='exam')
    source = models.ForeignKey(Source, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    
    total_questions = models.PositiveIntegerField(default=0)
    duration_minutes = models.PositiveIntegerField(default=120)
    time_taken_seconds = models.PositiveIntegerField(default=0)
    
    is_submitted = models.BooleanField(default=False)
    score = models.FloatField(default=0.0, help_text="+2 for correct, -0.66 for wrong")
    correct_count = models.PositiveIntegerField(default=0)
    wrong_count = models.PositiveIntegerField(default=0)
    unanswered_count = models.PositiveIntegerField(default=0)
    accuracy = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def calculate_results(self):
        responses = self.responses.select_related('question').all()
        correct = 0
        wrong = 0
        unanswered = 0

        for r in responses:
            if not r.selected_option:
                unanswered += 1
            elif r.selected_option.lower() == r.question.correct_option.lower():
                correct += 1
                r.is_correct = True
                r.save(update_fields=['is_correct'])
            else:
                wrong += 1
                r.is_correct = False
                r.save(update_fields=['is_correct'])

        self.correct_count = correct
        self.wrong_count = wrong
        self.unanswered_count = unanswered
        
        # Standard UPSC Prelims marking: +2 for correct, -2/3 (~0.666) for incorrect
        self.score = round((correct * 2.0) - (wrong * 0.666), 2)
        total_attempted = correct + wrong
        self.accuracy = round((correct / total_attempted * 100), 1) if total_attempted > 0 else 0.0
        self.is_submitted = True
        self.save()

    def __str__(self):
        return f"{self.title} ({self.session_id}) - Score: {self.score}"


class ExamResponse(models.Model):
    session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.CharField(max_length=1, blank=True, default='')
    is_correct = models.BooleanField(default=False)
    is_marked_for_review = models.BooleanField(default=False)
    is_visited = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order']
        unique_together = ('session', 'question')
