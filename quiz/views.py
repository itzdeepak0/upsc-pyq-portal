import os
import glob
import json
import random
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.conf import settings

from .models import Subject, Source, Question, ExamSession, ExamResponse
from .extractor import parse_pdf_questions, detect_edition_title
from .management.commands.import_pyq import SUBJECT_METADATA

def home(request):
    total_questions = Question.objects.count()
    sources = Source.objects.annotate(q_count=Count('questions')).all()
    subjects = Subject.objects.annotate(q_count=Count('questions')).filter(q_count__gt=0)
    bookmarked_count = Question.objects.filter(is_bookmarked=True).count()
    recent_attempts = ExamSession.objects.filter(is_submitted=True).order_by('-completed_at')[:5]

    context = {
        'total_questions': total_questions,
        'sources': sources,
        'subjects': subjects,
        'bookmarked_count': bookmarked_count,
        'recent_attempts': recent_attempts,
    }
    return render(request, 'quiz/home.html', context)


def practice_view(request):
    subject_slug = request.GET.get('subject')
    source_slug = request.GET.get('source')
    query = request.GET.get('q', '').strip()
    bookmarked = request.GET.get('bookmarked') == '1'

    questions = Question.objects.select_related('subject', 'source').all()

    current_subject = None
    if subject_slug:
        current_subject = get_object_or_404(Subject, slug=subject_slug)
        questions = questions.filter(subject=current_subject)

    current_source = None
    if source_slug:
        current_source = get_object_or_404(Source, slug=source_slug)
        questions = questions.filter(source=current_source)

    if bookmarked:
        questions = questions.filter(is_bookmarked=True)

    if query:
        questions = questions.filter(
            Q(topic__icontains=query) |
            Q(question_text__icontains=query) |
            Q(explanation__icontains=query) |
            Q(in_news__icontains=query)
        )

    paginator = Paginator(questions, 1)  # 1 question per card
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    all_subjects = Subject.objects.annotate(q_count=Count('questions')).filter(q_count__gt=0)
    all_sources = Source.objects.all()

    context = {
        'page_obj': page_obj,
        'current_subject': current_subject,
        'current_source': current_source,
        'all_subjects': all_subjects,
        'all_sources': all_sources,
        'query': query,
        'bookmarked': bookmarked,
        'total_matched': paginator.count,
    }
    return render(request, 'quiz/practice.html', context)


def question_explorer(request):
    subject_slug = request.GET.get('subject')
    source_slug = request.GET.get('source')
    query = request.GET.get('q', '').strip()
    difficulty = request.GET.get('difficulty')

    questions = Question.objects.select_related('subject', 'source').all()

    if subject_slug:
        questions = questions.filter(subject__slug=subject_slug)
    if source_slug:
        questions = questions.filter(source__slug=source_slug)
    if difficulty:
        questions = questions.filter(difficulty=difficulty)
    if query:
        questions = questions.filter(
            Q(topic__icontains=query) |
            Q(question_text__icontains=query) |
            Q(explanation__icontains=query)
        )

    paginator = Paginator(questions, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    all_subjects = Subject.objects.annotate(q_count=Count('questions')).filter(q_count__gt=0)
    all_sources = Source.objects.all()

    context = {
        'page_obj': page_obj,
        'all_subjects': all_subjects,
        'all_sources': all_sources,
        'selected_subject': subject_slug,
        'selected_source': source_slug,
        'selected_difficulty': difficulty,
        'query': query,
        'total_matched': paginator.count,
    }
    return render(request, 'quiz/explorer.html', context)


def exam_setup(request):
    subjects = Subject.objects.annotate(q_count=Count('questions')).filter(q_count__gt=0)
    sources = Source.objects.annotate(q_count=Count('questions')).all()
    total_available = Question.objects.count()

    if request.method == 'POST':
        source_id = request.POST.get('source_id')
        subject_id = request.POST.get('subject_id')
        num_questions = int(request.POST.get('num_questions', 50))
        duration = int(request.POST.get('duration', 60))
        randomize = request.POST.get('randomize') == '1'

        questions = Question.objects.all()
        source_obj = None
        subject_obj = None
        test_title = "UPSC Prelims Mock Exam"

        if source_id:
            source_obj = Source.objects.filter(id=source_id).first()
            if source_obj:
                questions = questions.filter(source=source_obj)
                test_title = f"Mock Exam - {source_obj.title}"

        if subject_id:
            subject_obj = Subject.objects.filter(id=subject_id).first()
            if subject_obj:
                questions = questions.filter(subject=subject_obj)
                test_title = f"Subject Test - {subject_obj.name}"

        q_list = list(questions)
        if randomize:
            random.shuffle(q_list)

        q_subset = q_list[:num_questions]
        if not q_subset:
            return redirect('quiz:exam_setup')

        session = ExamSession.objects.create(
            title=test_title,
            mode='exam',
            source=source_obj,
            subject=subject_obj,
            total_questions=len(q_subset),
            duration_minutes=duration
        )

        responses = [
            ExamResponse(session=session, question=q, order=idx + 1)
            for idx, q in enumerate(q_subset)
        ]
        ExamResponse.objects.bulk_create(responses)

        return redirect('quiz:exam_runner', session_id=session.session_id)

    context = {
        'subjects': subjects,
        'sources': sources,
        'total_available': total_available,
    }
    return render(request, 'quiz/exam_setup.html', context)


def exam_runner(request, session_id):
    session = get_object_or_404(ExamSession, session_id=session_id)
    if session.is_submitted:
        return redirect('quiz:exam_results', session_id=session.session_id)

    responses = session.responses.select_related('question', 'question__subject').order_by('order')

    questions_payload = []
    for r in responses:
        q = r.question
        questions_payload.append({
            'response_id': r.id,
            'order': r.order,
            'id': q.id,
            'topic': q.topic,
            'subject': q.subject.name if q.subject else 'General Studies',
            'subject_badge': q.subject.badge_color if q.subject else 'bg-slate-100 text-slate-800',
            'question_text': q.question_text,
            'option_a': q.option_a,
            'option_b': q.option_b,
            'option_c': q.option_c,
            'option_d': q.option_d,
            'selected_option': r.selected_option,
            'is_marked': r.is_marked_for_review,
            'is_visited': r.is_visited,
        })

    context = {
        'session': session,
        'questions_json': json.dumps(questions_payload),
        'total_questions': len(questions_payload),
    }
    return render(request, 'quiz/exam_runner.html', context)


@require_POST
def exam_submit(request, session_id):
    session = get_object_or_404(ExamSession, session_id=session_id)
    if session.is_submitted:
        return JsonResponse({'status': 'already_submitted', 'redirect_url': f'/exam/results/{session.session_id}/'})

    try:
        data = json.loads(request.body)
        answers = data.get('answers', {})
        time_taken = data.get('time_taken', 0)

        responses = {r.id: r for r in session.responses.all()}
        for resp_id_str, ans_info in answers.items():
            resp_id = int(resp_id_str)
            if resp_id in responses:
                r = responses[resp_id]
                r.selected_option = (ans_info.get('option') or '').lower()
                r.is_marked_for_review = bool(ans_info.get('marked', False))
                r.is_visited = True
                r.save(update_fields=['selected_option', 'is_marked_for_review', 'is_visited'])

        session.time_taken_seconds = time_taken
        session.completed_at = timezone.now()
        session.calculate_results()

        return JsonResponse({'status': 'ok', 'redirect_url': f'/exam/results/{session.session_id}/'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


def exam_results(request, session_id):
    session = get_object_or_404(ExamSession, session_id=session_id)
    responses = session.responses.select_related('question', 'question__subject').order_by('order')

    subject_stats = {}
    for r in responses:
        subj_name = r.question.subject.name if r.question.subject else 'General Studies'
        if subj_name not in subject_stats:
            subject_stats[subj_name] = {'total': 0, 'correct': 0, 'wrong': 0, 'unanswered': 0}
        
        subject_stats[subj_name]['total'] += 1
        if not r.selected_option:
            subject_stats[subj_name]['unanswered'] += 1
        elif r.is_correct:
            subject_stats[subj_name]['correct'] += 1
        else:
            subject_stats[subj_name]['wrong'] += 1

    for subj, stats in subject_stats.items():
        att = stats['correct'] + stats['wrong']
        stats['accuracy'] = round((stats['correct'] / att * 100), 1) if att > 0 else 0

    minutes = session.time_taken_seconds // 60
    seconds = session.time_taken_seconds % 60
    time_display = f"{minutes}m {seconds}s"

    context = {
        'session': session,
        'responses': responses,
        'subject_stats': subject_stats,
        'time_display': time_display,
    }
    return render(request, 'quiz/exam_results.html', context)


@require_POST
def toggle_bookmark(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    question.is_bookmarked = not question.is_bookmarked
    question.save(update_fields=['is_bookmarked'])
    return JsonResponse({
        'status': 'ok',
        'question_id': question.id,
        'is_bookmarked': question.is_bookmarked
    })


def upload_pdf(request):
    """
    Dedicated view to ingest future test series PDFs with month/year support,
    drag-and-drop, and automatic title detection.
    """
    import_result = None

    if request.method == 'POST' and request.FILES.get('pdf_file'):
        uploaded_file = request.FILES['pdf_file']
        month = request.POST.get('month', '').strip()
        year = request.POST.get('year', '2026').strip()
        custom_title = request.POST.get('title', '').strip()

        # Temporary save to media/uploads/
        upload_dir = settings.MEDIA_ROOT / 'uploads'
        os.makedirs(upload_dir, exist_ok=True)
        temp_path = upload_dir / uploaded_file.name

        with open(temp_path, 'wb+') as dest:
            for chunk in uploaded_file.chunks():
                dest.write(chunk)

        # Determine Title
        if custom_title:
            title = custom_title
        elif month and month != 'auto':
            title = f"GMT - {month} {year}"
        else:
            title = detect_edition_title(str(temp_path))

        # Parse questions
        questions_data = parse_pdf_questions(str(temp_path))

        # Save backup JSON
        backup_dir = settings.BASE_DIR / 'backups'
        os.makedirs(backup_dir, exist_ok=True)
        slug_name = title.lower().replace(' ', '-').replace('--', '-')
        with open(backup_dir / f"{slug_name}.json", 'w', encoding='utf-8') as f:
            json.dump(questions_data, f, ensure_ascii=False, indent=2)

        source, _ = Source.objects.get_or_create(title=title)
        
        # Ensure subjects exist
        subject_cache = {}
        for subj_name, meta in SUBJECT_METADATA.items():
            subj_obj, _ = Subject.objects.get_or_create(
                name=subj_name,
                defaults={
                    'icon': meta['icon'],
                    'badge_color': meta['badge_color'],
                    'description': meta['description']
                }
            )
            subject_cache[subj_name] = subj_obj

        created_count = 0
        updated_count = 0
        subject_breakdown = {}

        for q in questions_data:
            s_name = q.get('subject', 'General Studies')
            subj_obj = subject_cache.get(s_name, subject_cache.get('General Studies'))
            subject_breakdown[s_name] = subject_breakdown.get(s_name, 0) + 1

            _, was_created = Question.objects.update_or_create(
                source=source,
                question_number=q['question_number'],
                defaults={
                    'subject': subj_obj,
                    'topic': q['topic'],
                    'question_text': q['question_text'],
                    'option_a': q['option_a'],
                    'option_b': q['option_b'],
                    'option_c': q['option_c'],
                    'option_d': q['option_d'],
                    'correct_option': q['correct_option'],
                    'explanation': q['explanation'],
                    'value_addition': q.get('value_addition', ''),
                    'in_news': q.get('in_news', ''),
                    'difficulty': q.get('difficulty', 'Medium'),
                }
            )
            if was_created:
                created_count += 1
            else:
                updated_count += 1

        source.update_question_count()

        import_result = {
            'success': True,
            'title': title,
            'total_parsed': len(questions_data),
            'created_count': created_count,
            'updated_count': updated_count,
            'subject_breakdown': subject_breakdown,
            'source_slug': source.slug,
        }

    # Check incoming_pdfs folder status
    inbox_dir = settings.BASE_DIR / 'incoming_pdfs'
    pending_pdfs = [os.path.basename(f) for f in glob.glob(str(inbox_dir / '*.pdf'))]
    recent_sources = Source.objects.all()[:10]

    context = {
        'import_result': import_result,
        'pending_pdfs': pending_pdfs,
        'recent_sources': recent_sources,
    }
    return render(request, 'quiz/upload.html', context)


@require_POST
def scan_inbox_api(request):
    """
    Triggers automatic import of all PDFs currently sitting in incoming_pdfs/
    """
    inbox_dir = settings.BASE_DIR / 'incoming_pdfs'
    pdf_files = list(glob.glob(str(inbox_dir / '*.pdf')))

    if not pdf_files:
        return JsonResponse({'status': 'empty', 'message': 'No PDFs found in incoming_pdfs/ folder.'})

    imported_titles = []
    total_q_added = 0

    subject_cache = {}
    for subj_name, meta in SUBJECT_METADATA.items():
        subj_obj, _ = Subject.objects.get_or_create(
            name=subj_name,
            defaults={
                'icon': meta['icon'],
                'badge_color': meta['badge_color'],
                'description': meta['description']
            }
        )
        subject_cache[subj_name] = subj_obj

    for pdf_path in pdf_files:
        title = detect_edition_title(pdf_path)
        questions_data = parse_pdf_questions(pdf_path)
        source, _ = Source.objects.get_or_create(title=title)

        for q in questions_data:
            s_name = q.get('subject', 'General Studies')
            subj_obj = subject_cache.get(s_name, subject_cache.get('General Studies'))
            Question.objects.update_or_create(
                source=source,
                question_number=q['question_number'],
                defaults={
                    'subject': subj_obj,
                    'topic': q['topic'],
                    'question_text': q['question_text'],
                    'option_a': q['option_a'],
                    'option_b': q['option_b'],
                    'option_c': q['option_c'],
                    'option_d': q['option_d'],
                    'correct_option': q['correct_option'],
                    'explanation': q['explanation'],
                    'value_addition': q.get('value_addition', ''),
                    'in_news': q.get('in_news', ''),
                }
            )

        source.update_question_count()
        imported_titles.append(f"{title} ({len(questions_data)} Qs)")
        total_q_added += len(questions_data)

    return JsonResponse({
        'status': 'ok',
        'imported_count': len(pdf_files),
        'total_questions': total_q_added,
        'details': imported_titles
    })


def editions_manager(request):
    """
    Overview of all monthly editions, with question counts, export JSON and delete actions.
    """
    sources = Source.objects.annotate(q_count=Count('questions')).order_by('-created_at')
    context = {
        'sources': sources,
    }
    return render(request, 'quiz/editions.html', context)


def export_edition_json(request, slug):
    source = get_object_or_404(Source, slug=slug)
    questions = source.questions.select_related('subject').all()
    data = []
    for q in questions:
        data.append({
            'question_number': q.question_number,
            'topic': q.topic,
            'subject': q.subject.name if q.subject else 'General Studies',
            'question_text': q.question_text,
            'options': {
                'a': q.option_a,
                'b': q.option_b,
                'c': q.option_c,
                'd': q.option_d,
            },
            'correct_option': q.correct_option,
            'explanation': q.explanation,
            'value_addition': q.value_addition,
            'in_news': q.in_news,
        })
    response = HttpResponse(
        json.dumps(data, ensure_ascii=False, indent=2),
        content_type='application/json'
    )
    response['Content-Disposition'] = f'attachment; filename="{source.slug}.json"'
    return response


@require_POST
def delete_edition(request, slug):
    source = get_object_or_404(Source, slug=slug)
    title = source.title
    source.delete()
    return redirect('quiz:editions')


def api_questions(request):
    questions = Question.objects.select_related('subject', 'source').all()[:100]
    data = []
    for q in questions:
        data.append({
            'id': q.id,
            'number': q.question_number,
            'source': q.source.title,
            'subject': q.subject.name if q.subject else 'General Studies',
            'topic': q.topic,
            'question_text': q.question_text,
            'options': {
                'a': q.option_a,
                'b': q.option_b,
                'c': q.option_c,
                'd': q.option_d,
            },
            'correct_option': q.correct_option,
            'explanation': q.explanation,
            'value_addition': q.value_addition,
            'in_news': q.in_news,
            'is_bookmarked': q.is_bookmarked,
        })
    return JsonResponse({'count': len(data), 'results': data})
