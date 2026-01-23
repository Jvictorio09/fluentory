"""
Management command to seed Help Center with initial data
"""
from django.core.management.base import BaseCommand
from myApp.models import HelpCategory, HelpArticle


class Command(BaseCommand):
    help = 'Seed Help Center with initial categories and articles'

    def handle(self, *args, **options):
        self.stdout.write('Seeding Help Center data...')
        
        # Create categories
        getting_started, _ = HelpCategory.objects.get_or_create(
            slug='getting-started',
            defaults={
                'title': 'Getting Started',
                'description': 'Learn the basics of using Fluentory',
                'icon': 'fa-graduation-cap',
                'order': 1,
            }
        )
        
        courses_learning, _ = HelpCategory.objects.get_or_create(
            slug='courses-learning',
            defaults={
                'title': 'Courses & Learning',
                'description': 'Everything about courses and lessons',
                'icon': 'fa-book',
                'order': 2,
            }
        )
        
        certificates, _ = HelpCategory.objects.get_or_create(
            slug='certificates',
            defaults={
                'title': 'Certificates',
                'description': 'Information about certificates',
                'icon': 'fa-certificate',
                'order': 3,
            }
        )
        
        # Create articles
        articles_data = [
            {
                'slug': 'how-to-take-placement-test',
                'title': 'How to Take the Placement Test',
                'category': getting_started,
                'excerpt': 'Step-by-step guide to getting started with your learning journey',
                'content': '''
                    <h2>What is the Placement Test?</h2>
                    <p>The placement test helps us determine your current skill level so we can recommend the best courses for you.</p>
                    
                    <h2>How to Access the Placement Test</h2>
                    <ol>
                        <li>Log in to your Fluentory account</li>
                        <li>Navigate to the Placement Test page</li>
                        <li>Click "Start Placement Test"</li>
                    </ol>
                    
                    <h2>What to Expect</h2>
                    <p>The test consists of multiple-choice questions covering various topics. Take your time and answer honestly.</p>
                ''',
                'is_featured': True,
                'order': 1,
            },
            {
                'slug': 'account-setup',
                'title': 'Account Setup',
                'category': getting_started,
                'excerpt': 'Learn how to set up and customize your Fluentory account',
                'content': '''
                    <h2>Creating Your Account</h2>
                    <p>To create an account, click the "Sign Up" button and fill in your information.</p>
                    
                    <h2>Profile Settings</h2>
                    <p>You can customize your profile by adding a profile picture, bio, and learning preferences.</p>
                ''',
                'is_featured': False,
                'order': 2,
            },
            {
                'slug': 'resetting-password',
                'title': 'Resetting Your Password',
                'category': getting_started,
                'excerpt': 'How to reset your password if you forget it',
                'content': '''
                    <h2>Forgot Password?</h2>
                    <p>If you've forgotten your password, click "Forgot Password" on the login page.</p>
                    
                    <h2>Reset Process</h2>
                    <ol>
                        <li>Enter your email address</li>
                        <li>Check your email for a reset link</li>
                        <li>Click the link and set a new password</li>
                    </ol>
                ''',
                'is_featured': False,
                'order': 3,
            },
            {
                'slug': 'understanding-progress',
                'title': 'Understanding Your Progress',
                'category': courses_learning,
                'excerpt': 'Track your learning journey effectively and see your achievements',
                'content': '''
                    <h2>Progress Tracking</h2>
                    <p>Your progress is tracked automatically as you complete lessons and quizzes.</p>
                    
                    <h2>Viewing Your Progress</h2>
                    <p>Navigate to the "Learning" section to see your progress across all enrolled courses.</p>
                    
                    <h2>Milestones</h2>
                    <p>Celebrate your achievements as you reach learning milestones!</p>
                ''',
                'is_featured': True,
                'order': 1,
            },
            {
                'slug': 'enrolling-in-course',
                'title': 'Enrolling in a Course',
                'category': courses_learning,
                'excerpt': 'Learn how to enroll in courses and start learning',
                'content': '''
                    <h2>Finding Courses</h2>
                    <p>Browse available courses from the Courses page or use the search function.</p>
                    
                    <h2>Enrollment Process</h2>
                    <ol>
                        <li>Click on a course to view details</li>
                        <li>Click "Enroll Now" or "Purchase"</li>
                        <li>Complete the payment if required</li>
                        <li>Start learning!</li>
                    </ol>
                ''',
                'is_featured': False,
                'order': 2,
            },
            {
                'slug': 'completing-lessons',
                'title': 'Completing Lessons',
                'category': courses_learning,
                'excerpt': 'How to complete lessons and track your progress',
                'content': '''
                    <h2>Accessing Lessons</h2>
                    <p>Lessons are available once you enroll in a course.</p>
                    
                    <h2>Completing a Lesson</h2>
                    <p>Watch videos, read content, and complete exercises. Mark the lesson as complete when finished.</p>
                ''',
                'is_featured': False,
                'order': 3,
            },
            {
                'slug': 'taking-quizzes',
                'title': 'Taking Quizzes',
                'category': courses_learning,
                'excerpt': 'Learn how to take quizzes and understand your results',
                'content': '''
                    <h2>Quiz Format</h2>
                    <p>Quizzes consist of multiple-choice questions based on course content.</p>
                    
                    <h2>Taking a Quiz</h2>
                    <ol>
                        <li>Navigate to the quiz from your course</li>
                        <li>Answer all questions</li>
                        <li>Submit your answers</li>
                        <li>Review your results</li>
                    </ol>
                ''',
                'is_featured': False,
                'order': 4,
            },
            {
                'slug': 'earning-certificates',
                'title': 'Earning Certificates',
                'category': certificates,
                'excerpt': 'Learn how to earn and download your certificates',
                'content': '''
                    <h2>Certificate Requirements</h2>
                    <p>To earn a certificate, you must complete all course requirements including lessons and quizzes.</p>
                    
                    <h2>Downloading Certificates</h2>
                    <p>Once earned, certificates are available in your Certificates section for download.</p>
                ''',
                'is_featured': True,
                'order': 1,
            },
            {
                'slug': 'verifying-certificate',
                'title': 'Verifying Your Certificate',
                'category': certificates,
                'excerpt': 'How to verify and share your certificates',
                'content': '''
                    <h2>Certificate Verification</h2>
                    <p>Each certificate has a unique verification link that can be shared with employers or institutions.</p>
                    
                    <h2>Sharing Certificates</h2>
                    <p>Use the verification link to prove the authenticity of your certificate.</p>
                ''',
                'is_featured': False,
                'order': 2,
            },
            {
                'slug': 'contacting-support',
                'title': 'Contacting Support',
                'category': getting_started,
                'excerpt': 'Get help from our support team',
                'content': '''
                    <h2>Support Options</h2>
                    <p>We offer multiple ways to get support:</p>
                    <ul>
                        <li>Email: support@fluentory.com</li>
                        <li>Help Center: Browse articles and FAQs</li>
                        <li>Contact Form: Submit a support request</li>
                    </ul>
                ''',
                'is_featured': False,
                'order': 4,
            },
        ]
        
        for article_data in articles_data:
            article, created = HelpArticle.objects.get_or_create(
                slug=article_data['slug'],
                defaults=article_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created article: {article.title}'))
            else:
                self.stdout.write(f'Article already exists: {article.title}')
        
        self.stdout.write(self.style.SUCCESS('Successfully seeded Help Center data!'))

