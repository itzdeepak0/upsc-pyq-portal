import os
import glob
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from quiz.models import Subject, Source, Question
from quiz.extractor import parse_pdf_questions, detect_edition_title
from quiz.management.commands.import_pyq import SUBJECT_METADATA

class Command(BaseCommand):
    help = 'Scan the incoming_pdfs/ directory and automatically import any new monthly PDF test series'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force re-import even if already imported')

    def handle(self, *args, **options):
        inbox_dir = settings.BASE_DIR / 'incoming_pdfs'
        pdf_files = list(glob.glob(str(inbox_dir / '*.pdf')))

        if not pdf_files:
            self.stdout.write(self.style.WARNING(f"No PDF files found in {inbox_dir}. Drop upcoming monthly PDFs there!"))
            return

        self.stdout.write(self.style.SUCCESS(f"Found {len(pdf_files)} PDF file(s) in incoming folder."))
        force = options['force']

        # Ensure Subjects exist
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
            self.stdout.write(f"\nProcessing: {os.path.basename(pdf_path)} -> Title: '{title}'")

            source, created = Source.objects.get_or_create(title=title)
            if not created and not force and source.total_questions > 0:
                self.stdout.write(self.style.NOTICE(f"Source '{title}' already has {source.total_questions} questions. Skipping (use --force to re-import)."))
                continue

            questions_data = parse_pdf_questions(pdf_path)
            self.stdout.write(f"Parsed {len(questions_data)} questions.")

            # Save backup JSON
            backup_file = settings.BASE_DIR / 'backups' / f"{source.slug}.json"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(questions_data, f, ensure_ascii=False, indent=2)

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
                _, was_created = Question.objects.update_or_create(
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
                f"Successfully loaded '{title}': {created_count} added, {updated_count} updated. Total: {source.total_questions}"
            ))
