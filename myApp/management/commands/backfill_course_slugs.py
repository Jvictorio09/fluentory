"""
Management command to backfill empty course slugs
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.db.models import Q
from myApp.models import Course


class Command(BaseCommand):
    help = 'Backfill empty course slugs by generating them from titles'

    def handle(self, *args, **options):
        self.stdout.write('Backfilling course slugs...')
        
        # Find all courses with empty or None slugs
        courses_without_slugs = Course.objects.filter(
            Q(slug__isnull=True) | Q(slug='')
        )
        
        count = 0
        for course in courses_without_slugs:
            # Use the model's generate_unique_slug method to ensure consistency
            if course.title:
                # Generate slug from title using model's method
                course.slug = course.generate_unique_slug(exclude_id=course.pk)
                course.save(update_fields=['slug'])
                count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Fixed slug for course "{course.title}": {course.slug}'))
            else:
                # No title, use course ID as fallback
                course.slug = course.generate_unique_slug(base_slug=f'course-{course.id}', exclude_id=course.pk)
                course.save(update_fields=['slug'])
                count += 1
                self.stdout.write(self.style.WARNING(f'⚠ Fixed slug for course ID {course.id} (no title): {course.slug}'))
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No courses with empty slugs found.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Successfully backfilled {count} course slug(s)!'))

