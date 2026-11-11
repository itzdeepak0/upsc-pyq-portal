import json
import os
from django.core.management.base import BaseCommand
from quiz.models import Subject, Source, Question
from quiz.extractor import parse_pdf_questions

SUBJECT_METADATA = {
    'Polity & Governance': {
        'icon': 'landmark',
        'badge_color': 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
        'description': 'Constitution of India, Parliament, Judiciary, Rights, and Statutory Bodies.'
    },
    'Economy': {
        'icon': 'trending-up',
        'badge_color': 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
        'description': 'Fiscal & Monetary Policy, Banking, External Sector, and Infrastructure.'
    },
    'Environment & Ecology': {
        'icon': 'leaf',
        'badge_color': 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
        'description': 'Biodiversity, Wildlife Conservation, Climate Change, and Environmental Acts.'
    },
    'Science & Technology': {
        'icon': 'cpu',
        'badge_color': 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300',
        'description': 'Space Technology, Artificial Intelligence, Biotech, Defense, and Health.'
    },
    'Geography': {
        'icon': 'globe-2',
        'badge_color': 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/40 dark:text-cyan-300',
        'description': 'Physical, Economic and Human Geography, Rivers, Geomorphology, and Maps.'
    },
    'History & Culture': {
        'icon': 'book-open',
        'badge_color': 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
        'description': 'Ancient, Medieval, Modern Indian History, Art, and Architecture.'
    },
    'International Relations': {
        'icon': 'network',
        'badge_color': 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300',
        'description': 'Bilateral Relations, Global Multilateral Treaties, and International Bodies.'
    },
    'General Studies': {
        'icon': 'layers',
        'badge_color': 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300',
        'description': 'Cross-disciplinary Prelims Questions and Current Issues.'
    }
}


class Command(BaseCommand):
    help = 'Import UPSC Prelims questions from a PDF test series file into SQLite'

    def add_arguments(self, parser):
        parser.add_argument('pdf_path', type=str, help='Path to the PDF file')
        parser.add_argument('--title', type=str, default=None, help='Source title (e.g., "GMT - June 2026")')
        parser.add_argument('--limit', type=int, default=None, help='Limit number of questions to parse')
        parser.add_argument('--export-json', type=str, default=None, help='Path to export extracted JSON data')

    def handle(self, *args, **options):
        pdf_path = options['pdf_path']
        if not os.path.exists(pdf_path):
            self.stderr.write(self.style.ERROR(f"PDF file not found: {pdf_path}"))
            return

        title = options['title']
        if not title:
            base = os.path.basename(pdf_path)
            title = os.path.splitext(base)[0].replace('_', ' ').replace('-', ' ').strip().title()

        self.stdout.write(self.style.SUCCESS(f"Parsing PDF: {pdf_path} ({title})..."))
        limit = options.get('limit')
        questions_data = parse_pdf_questions(pdf_path, max_questions=limit)
        self.stdout.write(self.style.SUCCESS(f"Extracted {len(questions_data)} questions from PDF."))

        if options.get('export_json'):
            json_path = options['export_json']
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(questions_data, f, ensure_ascii=False, indent=2)
            self.stdout.write(self.style.SUCCESS(f"Saved JSON export to: {json_path}"))

        # Create or fetch Source
        source, created = Source.objects.get_or_create(title=title)
        if created:
            self.stdout.write(f"Created new Source: {source.title}")
        else:
            self.stdout.write(f"Updating existing Source: {source.title}")

        # Ensure Subjects exist in DB
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

        for q in questions_data:
            subj_name = q.get('subject', 'General Studies')
            subj_obj = subject_cache.get(subj_name, subject_cache.get('General Studies'))

            defaults = {
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

            obj, was_created = Question.objects.update_or_create(
                source=source,
                question_number=q['question_number'],
                defaults=defaults
            )

            if was_created:
                created_count += 1
            else:
                updated_count += 1

        source.update_question_count()

        self.stdout.write(self.style.SUCCESS(
            f"Successfully processed {title}: {created_count} created, {updated_count} updated. Total in source: {source.total_questions}"
        ))
