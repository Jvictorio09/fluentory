from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from myApp.models import (
    Category, Course, Module, Lesson, Quiz, Question, Answer
)
from django.utils import timezone
from django.utils.text import slugify
import random


class Command(BaseCommand):
    help = 'Seed the database with a comprehensive video course'

    def handle(self, *args, **options):
        self.stdout.write('Seeding video course...')
        
        # Get or create a category
        category, _ = Category.objects.get_or_create(
            slug='video-production',
            defaults={
                'name': 'Video Production',
                'icon': 'fa-video',
                'order': 10
            }
        )
        
        # Get or create an instructor
        instructor, created = User.objects.get_or_create(
            username='video_instructor',
            defaults={
                'email': 'instructor@fluentory.com',
                'first_name': 'Alex',
                'last_name': 'Martinez',
            }
        )
        if created:
            instructor.set_password('instructor123')
            instructor.save()
            instructor.profile.role = 'instructor'
            instructor.profile.bio = 'Award-winning video producer with 15+ years of experience in film and digital media'
            instructor.profile.save()
            self.stdout.write(f'  Created instructor: {instructor.username}')
        
        # Video URLs provided by user
        video_urls = [
            'https://drive.google.com/file/d/1vjh0c7ReJn4YjFsgcBCSJKW4xhJg3JOp/view?usp=sharing',  # 1st
            'https://drive.google.com/file/d/15LLxGCE3gzMPpo4j7K5yyzaQmt9sTKHd/view?usp=sharing',  # 2nd
            'https://drive.google.com/file/d/1c4DpGIwhRJo5ZrasVnRM4JJZdFLupvaw/view?usp=sharing',  # 3rd
            'https://drive.google.com/file/d/1ItvLVPWsmdb9yoKDINcyIyOoa1IMCtcT/view?usp=sharing',  # 4th
            'https://drive.google.com/file/d/15cB6GJwybTMijjGf6CPU2ixBQ6V8EUI1/view?usp=sharing',  # 5th
            'https://drive.google.com/file/d/1z7NwNXfgEtZdLouj8b2wZu-YHHpfl2Nm/view?usp=sharing',  # 6th
            'https://drive.google.com/file/d/1Wv06ZSdCzzb4TwdydHM_UF_I9bdhNsk3/view?usp=sharing',  # 7th
            'https://drive.google.com/file/d/1paEt7fjQAc3MD_82JWA-oOZzJ7_MD82f/view?usp=sharing',  # 8th
            'https://drive.google.com/file/d/1geHiehW3AOx80b2p2_TGSXLAjjcWBryX/view?usp=sharing',  # 9th
            'https://drive.google.com/file/d/1-bCMwhgBrAW80en5lWIYURBh-XOWWBrn/view?usp=sharing',  # 10th
            'https://drive.google.com/file/d/1tyNbO0k1QgL5thBxAndEWr8fLHyAMNjZ/view?usp=sharing',  # 11th
            'https://drive.google.com/file/d/1sxRMfRi70UmEetf4bbSELMehXM8C38K4/view?usp=sharing',  # 12th
            'https://drive.google.com/file/d/1rvZR8uldp-dTgwsx7rbPkKmYFeUq2N5x/view?usp=sharing',  # 13th
        ]
        
        # Course structure with engaging module and lesson titles
        course_data = {
            'title': 'Master Video Production: From Concept to Final Cut',
            'category': category,
            'level': 'intermediate',
            'price': 89.99,
            'estimated_hours': 15,
            'outcome': 'Create professional-quality videos from start to finish, mastering storytelling, cinematography, and post-production',
            'short_description': 'Transform your video ideas into compelling visual stories. Learn professional techniques used by industry experts.',
            'description': '''
            Welcome to the ultimate video production course! Whether you're creating content for YouTube, social media, or professional projects, this comprehensive program will take you from a beginner to a confident video creator.

            **What You'll Master:**
            - Professional video planning and pre-production
            - Cinematic shooting techniques and camera work
            - Advanced editing and post-production workflows
            - Color grading and visual storytelling
            - Audio enhancement and sound design
            - Exporting and delivery for multiple platforms

            **Why This Course?**
            This isn't just another tutorial series. We've structured this course to follow a real-world production workflow, so you'll learn exactly how professionals approach video projects. Each module builds on the previous one, creating a complete learning journey.

            **What Makes This Special:**
            - 13 comprehensive video lessons covering every aspect of production
            - Real-world examples and case studies
            - Practical exercises you can complete alongside the course
            - Industry-standard techniques and workflows
            - Tips and tricks from years of professional experience

            By the end of this course, you'll have the skills and confidence to create videos that captivate audiences and tell powerful stories. Let's bring your vision to life!
            ''',
            'modules': [
                {
                    'title': 'Module 1: Foundation & Planning',
                    'description': 'Lay the groundwork for successful video production. Learn how to plan, script, and prepare for your shoot.',
                    'lessons': [
                        {
                            'title': 'Introduction to Video Production',
                            'video_url': video_urls[0],
                            'estimated_minutes': 25,
                            'description': 'Get an overview of the video production process and understand the key stages from concept to delivery.'
                        },
                        {
                            'title': 'Pre-Production Planning & Scripting',
                            'video_url': video_urls[1],
                            'estimated_minutes': 30,
                            'description': 'Learn how to plan your video project effectively, write compelling scripts, and organize your production.'
                        },
                        {
                            'title': 'Storyboarding & Visual Planning',
                            'video_url': video_urls[2],
                            'estimated_minutes': 28,
                            'description': 'Master the art of storyboarding and learn how to visualize your shots before you start filming.'
                        },
                    ]
                },
                {
                    'title': 'Module 2: Shooting & Cinematography',
                    'description': 'Master the art of capturing stunning footage. Learn camera techniques, composition, and lighting fundamentals.',
                    'lessons': [
                        {
                            'title': 'Camera Basics & Settings',
                            'video_url': video_urls[3],
                            'estimated_minutes': 35,
                            'description': 'Understand camera settings, exposure, focus, and how to get the best image quality from your equipment.'
                        },
                        {
                            'title': 'Composition & Framing Techniques',
                            'video_url': video_urls[4],
                            'estimated_minutes': 32,
                            'description': 'Learn the rules of composition, framing techniques, and how to create visually appealing shots.'
                        },
                        {
                            'title': 'Lighting Fundamentals',
                            'video_url': video_urls[5],
                            'estimated_minutes': 40,
                            'description': 'Discover how to work with natural and artificial light to create mood and enhance your storytelling.'
                        },
                        {
                            'title': 'Advanced Shooting Techniques',
                            'video_url': video_urls[6],
                            'estimated_minutes': 38,
                            'description': 'Explore advanced techniques including camera movement, depth of field, and creative shot types.'
                        },
                    ]
                },
                {
                    'title': 'Module 3: Post-Production Mastery',
                    'description': 'Transform your raw footage into polished, professional videos. Learn editing, color grading, and audio enhancement.',
                    'lessons': [
                        {
                            'title': 'Video Editing Fundamentals',
                            'video_url': video_urls[7],
                            'estimated_minutes': 45,
                            'description': 'Master the basics of video editing, including cutting, transitions, and building your narrative.'
                        },
                        {
                            'title': 'Advanced Editing Techniques',
                            'video_url': video_urls[8],
                            'estimated_minutes': 42,
                            'description': 'Take your editing skills to the next level with advanced techniques, effects, and workflow optimization.'
                        },
                        {
                            'title': 'Color Grading & Correction',
                            'video_url': video_urls[9],
                            'estimated_minutes': 38,
                            'description': 'Learn professional color grading techniques to enhance mood, correct exposure, and create cinematic looks.'
                        },
                        {
                            'title': 'Audio Enhancement & Sound Design',
                            'video_url': video_urls[10],
                            'estimated_minutes': 35,
                            'description': 'Discover how to improve audio quality, add music, sound effects, and create immersive soundscapes.'
                        },
                    ]
                },
                {
                    'title': 'Module 4: Finalization & Delivery',
                    'description': 'Complete your projects and deliver them to the world. Learn export settings, optimization, and distribution strategies.',
                    'lessons': [
                        {
                            'title': 'Exporting & Compression',
                            'video_url': video_urls[11],
                            'estimated_minutes': 30,
                            'description': 'Master export settings, compression techniques, and how to optimize your videos for different platforms.'
                        },
                        {
                            'title': 'Final Review & Project Delivery',
                            'video_url': video_urls[12],
                            'estimated_minutes': 28,
                            'description': 'Learn how to conduct final reviews, gather feedback, and deliver professional video projects to clients.'
                        },
                    ]
                },
            ]
        }
        
        # Create the course
        slug = slugify(course_data['title'])
        course, created = Course.objects.get_or_create(
            slug=slug,
            defaults={
                'title': course_data['title'],
                'category': course_data['category'],
                'level': course_data['level'],
                'price': course_data['price'],
                'estimated_hours': course_data['estimated_hours'],
                'outcome': course_data['outcome'],
                'short_description': course_data['short_description'],
                'description': course_data['description'],
                'instructor': instructor,
                'status': 'published',
                'published_at': timezone.now(),
                'course_type': 'recorded',
                'enrolled_count': random.randint(150, 500),
                'average_rating': round(random.uniform(4.5, 5.0), 1),
                'has_certificate': True,
                'has_ai_tutor': True,
                'has_quizzes': True,
                'preview_video': video_urls[0],  # First video as preview
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Created course: {course.title}'))
            
            # Create modules and lessons
            lesson_count = 0
            for m_order, module_data in enumerate(course_data['modules']):
                module = Module.objects.create(
                    course=course,
                    title=module_data['title'],
                    description=module_data.get('description', ''),
                    order=m_order
                )
                self.stdout.write(f'    ✓ Created module: {module.title}')
                
                for l_order, lesson_data in enumerate(module_data['lessons']):
                    lesson = Lesson.objects.create(
                        module=module,
                        title=lesson_data['title'],
                        content_type='video',
                        video_url=lesson_data['video_url'],
                        estimated_minutes=lesson_data['estimated_minutes'],
                        description=lesson_data.get('description', ''),
                        order=l_order,
                        is_preview=(m_order == 0 and l_order == 0),  # First lesson is preview
                        text_content=lesson_data.get('description', '')
                    )
                    lesson_count += 1
                    self.stdout.write(f'      ✓ Created lesson: {lesson.title}')
                
                # Create a module quiz
                module_quiz = Quiz.objects.create(
                    title=f'{module.title} - Knowledge Check',
                    quiz_type='module',
                    course=course,
                    module=module,
                    passing_score=70,
                    max_attempts=3,
                    description=f'Test your understanding of {module.title.lower()} concepts.'
                )
                
                # Add sample questions to module quiz
                self.create_sample_questions(module_quiz, module.title)
            
            # Update lesson count
            course.lessons_count = lesson_count
            course.save()
            
            # Create final assessment quiz
            final_quiz = Quiz.objects.create(
                title=f'{course.title} - Final Assessment',
                quiz_type='final',
                course=course,
                passing_score=75,
                max_attempts=3,
                description='Comprehensive assessment covering all course material. Pass this quiz to earn your certificate!'
            )
            
            # Add comprehensive questions to final quiz
            self.create_final_quiz_questions(final_quiz)
            
            self.stdout.write(self.style.SUCCESS(f'\n  ✓ Course created successfully with {lesson_count} lessons!'))
            self.stdout.write(f'  ✓ Created {course.modules.count()} modules')
            self.stdout.write(f'  ✓ Created {course.quizzes.count()} quizzes')
        else:
            self.stdout.write(self.style.WARNING(f'  Course "{course.title}" already exists. Skipping...'))
        
        self.stdout.write(self.style.SUCCESS('\n✓ Video course seeding completed!'))

    def create_sample_questions(self, quiz, module_title):
        """Create sample questions for module quizzes"""
        questions_data = [
            {
                'text': f'What is the most important aspect of {module_title.lower()}?',
                'answers': [
                    ('Planning and preparation', True),
                    ('Having expensive equipment', False),
                    ('Using the latest software', False),
                    ('Following trends', False),
                ]
            },
            {
                'text': 'Which technique helps improve video quality the most?',
                'answers': [
                    ('Proper lighting', True),
                    ('High resolution', False),
                    ('Fast editing', False),
                    ('Many effects', False),
                ]
            },
        ]
        
        for i, q_data in enumerate(questions_data):
            question = Question.objects.create(
                quiz=quiz,
                question_text=q_data['text'],
                question_type='multiple_choice',
                order=i,
                points=1,
                explanation='Review the lesson materials to understand the key concepts.'
            )
            
            for j, (text, is_correct) in enumerate(q_data['answers']):
                Answer.objects.create(
                    question=question,
                    answer_text=text,
                    is_correct=is_correct,
                    order=j
                )

    def create_final_quiz_questions(self, quiz):
        """Create comprehensive questions for the final assessment"""
        questions_data = [
            {
                'text': 'What are the three main stages of video production?',
                'answers': [
                    ('Pre-production, Production, Post-production', True),
                    ('Planning, Shooting, Editing', False),
                    ('Scripting, Filming, Exporting', False),
                    ('Concept, Creation, Completion', False),
                ],
                'explanation': 'The three main stages are Pre-production (planning), Production (shooting), and Post-production (editing and finishing).'
            },
            {
                'text': 'Which camera setting controls the amount of light entering the lens?',
                'answers': [
                    ('Aperture', True),
                    ('Shutter speed', False),
                    ('ISO', False),
                    ('White balance', False),
                ],
                'explanation': 'Aperture controls the size of the lens opening, which determines how much light enters the camera.'
            },
            {
                'text': 'What is the purpose of color grading?',
                'answers': [
                    ('To enhance mood and correct color issues', True),
                    ('To make videos brighter', False),
                    ('To add special effects', False),
                    ('To compress file size', False),
                ],
                'explanation': 'Color grading is used to enhance the mood, correct color issues, and create a consistent visual style throughout the video.'
            },
            {
                'text': 'Why is audio quality important in video production?',
                'answers': [
                    ('Poor audio can ruin an otherwise great video', True),
                    ('It makes videos load faster', False),
                    ('It reduces file size', False),
                    ('It is required by law', False),
                ],
                'explanation': 'Audio quality is crucial because viewers are more likely to forgive poor video quality than poor audio quality.'
            },
            {
                'text': 'What should you consider when exporting a video for different platforms?',
                'answers': [
                    ('Resolution, format, and compression settings', True),
                    ('Only the file size', False),
                    ('Only the resolution', False),
                    ('Only the format', False),
                ],
                'explanation': 'Different platforms have different requirements for resolution, format, and file size, so you need to optimize for each platform.'
            },
        ]
        
        for i, q_data in enumerate(questions_data):
            question = Question.objects.create(
                quiz=quiz,
                question_text=q_data['text'],
                question_type='multiple_choice',
                order=i,
                points=2,
                explanation=q_data.get('explanation', 'Review the course materials for detailed explanations.')
            )
            
            for j, (text, is_correct) in enumerate(q_data['answers']):
                Answer.objects.create(
                    question=question,
                    answer_text=text,
                    is_correct=is_correct,
                    order=j
                )

