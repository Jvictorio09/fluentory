from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from myApp.models import (
    UserProfile, Category, Course, Module, Lesson,
    Quiz, Question, Answer, Enrollment, LessonProgress,
    Certificate, FAQ, SiteSettings
)
from django.utils import timezone
from django.utils.text import slugify
import random


class Command(BaseCommand):
    help = 'Seed the database with sample data for Fluentory'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')
        
        # Create Site Settings
        self.create_site_settings()
        
        # Create Categories
        categories = self.create_categories()
        
        # Create Users
        admin_user, instructor, students = self.create_users()
        
        # Create Courses
        courses = self.create_courses(categories, instructor)
        
        # Create Placement Quiz
        self.create_placement_quiz()
        
        # Create FAQs
        self.create_faqs()
        
        # Create sample enrollments for the first student
        if students and courses:
            self.create_enrollments(students[0], courses)
        
        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Test Accounts:'))
        self.stdout.write(f'  Admin: admin / admin123')
        self.stdout.write(f'  Instructor: instructor / instructor123')
        self.stdout.write(f'  Student: student / student123')

    def create_site_settings(self):
        settings, created = SiteSettings.objects.get_or_create(pk=1)
        if created:
            settings.site_name = 'Fluentory'
            settings.tagline = 'Global Learning Platform'
            settings.hero_headline = 'The Modern Way To Learn Globally.'
            settings.hero_subheadline = 'Placement-based learning. Milestone quizzes. Verified certification. Built for outcomes.'
            settings.announcement_text = 'New: Certificates now include QR verification'
            settings.show_announcement = True
            settings.save()
            self.stdout.write(f'  Created site settings')

    def create_categories(self):
        categories_data = [
            {'name': 'Data Science', 'slug': 'data-science', 'icon': 'fa-database'},
            {'name': 'Web Development', 'slug': 'web-development', 'icon': 'fa-code'},
            {'name': 'Machine Learning', 'slug': 'machine-learning', 'icon': 'fa-brain'},
            {'name': 'Business', 'slug': 'business', 'icon': 'fa-briefcase'},
            {'name': 'Language', 'slug': 'language', 'icon': 'fa-language'},
            {'name': 'Design', 'slug': 'design', 'icon': 'fa-paint-brush'},
        ]
        
        categories = []
        for i, data in enumerate(categories_data):
            cat, created = Category.objects.get_or_create(
                slug=data['slug'],
                defaults={
                    'name': data['name'],
                    'icon': data['icon'],
                    'order': i
                }
            )
            categories.append(cat)
            if created:
                self.stdout.write(f'  Created category: {cat.name}')
        
        return categories

    def create_users(self):
        # Admin user
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@fluentory.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            admin.profile.role = 'admin'
            admin.profile.save()
            self.stdout.write(f'  Created admin user: admin')
        
        # Instructor
        instructor, created = User.objects.get_or_create(
            username='instructor',
            defaults={
                'email': 'instructor@fluentory.com',
                'first_name': 'Sarah',
                'last_name': 'Johnson',
            }
        )
        if created:
            instructor.set_password('instructor123')
            instructor.save()
            instructor.profile.role = 'instructor'
            instructor.profile.bio = 'Data Science expert with 10+ years of experience'
            instructor.profile.save()
            self.stdout.write(f'  Created instructor user: instructor')
        
        # Students
        students = []
        student_names = [
            ('student', 'John', 'Doe'),
            ('student2', 'Jane', 'Smith'),
            ('student3', 'Mike', 'Wilson'),
        ]
        
        for username, first, last in student_names:
            student, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'first_name': first,
                    'last_name': last,
                }
            )
            if created:
                student.set_password('student123')
                student.save()
                student.profile.current_streak = random.randint(1, 30)
                student.profile.total_learning_minutes = random.randint(100, 5000)
                student.profile.save()
                self.stdout.write(f'  Created student user: {username}')
            students.append(student)
        
        return admin, instructor, students

    def create_courses(self, categories, instructor):
        courses_data = [
            {
                'title': 'Introduction to Data Science',
                'category': categories[0],  # Data Science
                'level': 'beginner',
                'price': 49.99,
                'estimated_hours': 40,
                'outcome': 'Master the fundamentals of data analysis and visualization',
                'description': '''
                This comprehensive course will teach you the fundamentals of data science from scratch.
                
                You'll learn how to collect, clean, and analyze data using Python and popular libraries like Pandas and NumPy. By the end of this course, you'll be able to create compelling visualizations and derive insights from complex datasets.
                
                Topics covered:
                - Introduction to Python for Data Science
                - Data Collection and Cleaning
                - Exploratory Data Analysis
                - Data Visualization with Matplotlib and Seaborn
                - Statistical Analysis
                - Introduction to Machine Learning
                ''',
                'modules': [
                    {
                        'title': 'Module 1: Foundations',
                        'lessons': [
                            ('Introduction to Data Science', 'video', 15),
                            ('Setting Up Your Environment', 'video', 20),
                            ('Python Basics Review', 'text', 30),
                        ]
                    },
                    {
                        'title': 'Module 2: Data Analysis',
                        'lessons': [
                            ('Working with Pandas', 'video', 25),
                            ('Data Cleaning Techniques', 'video', 30),
                            ('Data Visualization Basics', 'video', 25),
                        ]
                    },
                    {
                        'title': 'Module 3: Advanced Topics',
                        'lessons': [
                            ('Statistical Analysis', 'video', 35),
                            ('Introduction to ML', 'video', 40),
                            ('Final Project', 'assignment', 60),
                        ]
                    },
                ]
            },
            {
                'title': 'Full Stack Web Development',
                'category': categories[1],  # Web Development
                'level': 'intermediate',
                'price': 79.99,
                'estimated_hours': 60,
                'outcome': 'Build modern web applications from front to back',
                'description': '''
                Learn to build complete web applications using modern technologies.
                
                This course covers both frontend and backend development, teaching you HTML, CSS, JavaScript, React, Node.js, and databases. You'll build several real-world projects throughout the course.
                ''',
                'modules': [
                    {
                        'title': 'Frontend Fundamentals',
                        'lessons': [
                            ('HTML5 & Semantic Markup', 'video', 20),
                            ('CSS3 & Flexbox/Grid', 'video', 30),
                            ('JavaScript Essentials', 'video', 40),
                        ]
                    },
                    {
                        'title': 'React Development',
                        'lessons': [
                            ('React Fundamentals', 'video', 35),
                            ('State Management', 'video', 30),
                            ('React Hooks', 'video', 25),
                        ]
                    },
                ]
            },
            {
                'title': 'Machine Learning Mastery',
                'category': categories[2],  # Machine Learning
                'level': 'advanced',
                'price': 99.99,
                'estimated_hours': 80,
                'outcome': 'Build and deploy production-ready ML models',
                'description': '''
                Take your data science skills to the next level with this advanced machine learning course.
                
                You'll learn supervised and unsupervised learning, deep learning, and how to deploy models to production.
                ''',
                'modules': [
                    {
                        'title': 'ML Foundations',
                        'lessons': [
                            ('Types of Machine Learning', 'video', 25),
                            ('Linear Regression', 'video', 35),
                            ('Classification Algorithms', 'video', 40),
                        ]
                    },
                ]
            },
            {
                'title': 'Business English Communication',
                'category': categories[4],  # Language
                'level': 'beginner',
                'price': 0,
                'is_free': True,
                'estimated_hours': 20,
                'outcome': 'Speak confidently in business meetings',
                'description': '''
                Improve your business English communication skills with this practical course.
                ''',
                'modules': [
                    {
                        'title': 'Business Vocabulary',
                        'lessons': [
                            ('Essential Business Terms', 'video', 20),
                            ('Email Writing', 'video', 25),
                            ('Meeting Phrases', 'video', 20),
                        ]
                    },
                ]
            },
            {
                'title': 'UI/UX Design Fundamentals',
                'category': categories[5],  # Design
                'level': 'beginner',
                'price': 59.99,
                'estimated_hours': 35,
                'outcome': 'Design beautiful and user-friendly interfaces',
                'description': '''
                Learn the principles of great design and user experience.
                ''',
                'modules': [
                    {
                        'title': 'Design Principles',
                        'lessons': [
                            ('Introduction to UI/UX', 'video', 20),
                            ('Color Theory', 'video', 25),
                            ('Typography', 'video', 20),
                        ]
                    },
                ]
            },
            {
                'title': 'Project Management Essentials',
                'category': categories[3],  # Business
                'level': 'intermediate',
                'price': 69.99,
                'estimated_hours': 30,
                'outcome': 'Lead projects successfully using agile methodologies',
                'description': '''
                Master project management with modern methodologies.
                ''',
                'modules': [
                    {
                        'title': 'PM Fundamentals',
                        'lessons': [
                            ('Introduction to PM', 'video', 20),
                            ('Agile Methodology', 'video', 30),
                            ('Scrum Framework', 'video', 25),
                        ]
                    },
                ]
            },
        ]
        
        courses = []
        for data in courses_data:
            slug = slugify(data['title'])
            course, created = Course.objects.get_or_create(
                slug=slug,
                defaults={
                    'title': data['title'],
                    'category': data['category'],
                    'level': data['level'],
                    'price': data['price'],
                    'is_free': data.get('is_free', False),
                    'estimated_hours': data['estimated_hours'],
                    'outcome': data['outcome'],
                    'short_description': data['outcome'],
                    'description': data['description'],
                    'instructor': instructor,
                    'status': 'published',
                    'published_at': timezone.now(),
                    'enrolled_count': random.randint(100, 2000),
                    'average_rating': round(random.uniform(4.0, 5.0), 1),
                }
            )
            
            if created:
                self.stdout.write(f'  Created course: {course.title}')
                
                # Create modules and lessons
                lesson_count = 0
                for m_order, module_data in enumerate(data.get('modules', [])):
                    module = Module.objects.create(
                        course=course,
                        title=module_data['title'],
                        order=m_order
                    )
                    
                    for l_order, (title, content_type, minutes) in enumerate(module_data['lessons']):
                        Lesson.objects.create(
                            module=module,
                            title=title,
                            content_type=content_type,
                            estimated_minutes=minutes,
                            order=l_order,
                            is_preview=(l_order == 0),  # First lesson is preview
                            text_content=f'This is the content for {title}...'
                        )
                        lesson_count += 1
                
                # Update lesson count
                course.lessons_count = lesson_count
                course.save()
                
                # Create a quiz for the course
                Quiz.objects.create(
                    title=f'{course.title} - Final Assessment',
                    quiz_type='final',
                    course=course,
                    passing_score=70,
                    max_attempts=3
                )
            
            courses.append(course)
        
        return courses

    def create_placement_quiz(self):
        quiz, created = Quiz.objects.get_or_create(
            quiz_type='placement',
            defaults={
                'title': 'Fluentory Placement Test',
                'description': 'Discover your learning level and get personalized course recommendations.',
                'passing_score': 0,  # No passing score for placement
                'max_attempts': 99,
            }
        )
        
        if created:
            self.stdout.write(f'  Created placement quiz')
            
            questions_data = [
                {
                    'text': 'What is your experience level with programming?',
                    'answers': [
                        ('Complete beginner - never written code', False),
                        ('Some experience - completed tutorials', False),
                        ('Intermediate - built small projects', True),
                        ('Advanced - professional experience', False),
                    ]
                },
                {
                    'text': 'How comfortable are you with data analysis?',
                    'answers': [
                        ('Not familiar at all', False),
                        ('Basic spreadsheet skills', False),
                        ('Comfortable with basic statistics', True),
                        ('Advanced statistical analysis', False),
                    ]
                },
                {
                    'text': 'What is a variable in programming?',
                    'answers': [
                        ('A fixed value that never changes', False),
                        ('A container for storing data values', True),
                        ('A type of programming language', False),
                        ('A mathematical equation', False),
                    ]
                },
                {
                    'text': 'What does HTML stand for?',
                    'answers': [
                        ('Hyper Text Markup Language', True),
                        ('High Tech Modern Language', False),
                        ('Home Tool Markup Language', False),
                        ('Hyperlinks and Text Markup Language', False),
                    ]
                },
                {
                    'text': 'Which of these is a relational database?',
                    'answers': [
                        ('MongoDB', False),
                        ('Redis', False),
                        ('PostgreSQL', True),
                        ('Elasticsearch', False),
                    ]
                },
            ]
            
            for i, q_data in enumerate(questions_data):
                question = Question.objects.create(
                    quiz=quiz,
                    question_text=q_data['text'],
                    question_type='multiple_choice',
                    order=i,
                    points=1
                )
                
                for j, (text, is_correct) in enumerate(q_data['answers']):
                    Answer.objects.create(
                        question=question,
                        answer_text=text,
                        is_correct=is_correct,
                        order=j
                    )

    def create_faqs(self):
        faqs_data = [
            {
                'question': 'How does the placement test work?',
                'answer': 'Our AI-powered placement test assesses your current knowledge level through a series of questions. Based on your responses, we recommend the most suitable courses and starting points for your learning journey.',
                'category': 'Getting Started',
            },
            {
                'question': 'Are certificates internationally recognized?',
                'answer': 'Yes! Each Fluentory certificate includes a unique QR code for instant verification. Our certificates are designed for employers and institutions worldwide, featuring secure verification technology.',
                'category': 'Certificates',
            },
            {
                'question': 'Can I learn in my own language?',
                'answer': 'Absolutely! Fluentory supports multiple languages. You can change your language preference in settings, and our AI tutor can explain concepts in your preferred language.',
                'category': 'Languages',
            },
            {
                'question': 'Is this suitable for beginners?',
                'answer': 'Yes! We have courses for all levels, from complete beginners to advanced learners. Our placement test helps you find the perfect starting point.',
                'category': 'Getting Started',
            },
            {
                'question': 'How does the AI tutor work?',
                'answer': 'Our AI tutor is available 24/7 to answer your questions, explain concepts, and help you understand difficult topics. It\'s context-aware, meaning it knows which lesson you\'re studying.',
                'category': 'Features',
            },
            {
                'question': 'What payment methods do you accept?',
                'answer': 'We accept all major credit cards, PayPal, and bank transfers. Payments are processed securely through Stripe.',
                'category': 'Payments',
            },
        ]
        
        for i, data in enumerate(faqs_data):
            faq, created = FAQ.objects.get_or_create(
                question=data['question'],
                defaults={
                    'answer': data['answer'],
                    'category': data['category'],
                    'order': i,
                    'is_featured': True,
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(f'  Created FAQ: {faq.question[:50]}...')

    def create_enrollments(self, student, courses):
        if not courses:
            return
            
        # Enroll in first course with progress
        course = courses[0]
        enrollment, created = Enrollment.objects.get_or_create(
            user=student,
            course=course,
            defaults={
                'status': 'active',
                'progress_percentage': 72,
            }
        )
        
        if created:
            self.stdout.write(f'  Created enrollment: {student.username} -> {course.title}')
            
            # Set current lesson
            first_module = course.modules.first()
            if first_module:
                lessons = first_module.lessons.all()
                if lessons.exists():
                    enrollment.current_module = first_module
                    enrollment.current_lesson = lessons[min(2, lessons.count()-1)]
                    enrollment.save()
                    
                    # Create some lesson progress
                    for i, lesson in enumerate(lessons[:3]):
                        LessonProgress.objects.create(
                            enrollment=enrollment,
                            lesson=lesson,
                            completed=(i < 2),
                            completed_at=timezone.now() if i < 2 else None,
                            time_spent=random.randint(300, 1800)
                        )



