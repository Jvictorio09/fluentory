# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myApp', '0026_alter_liveclasssession_meeting_link_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='teacher',
            name='photo_url',
            field=models.URLField(blank=True, help_text='Profile photo URL from Cloudinary', null=True),
        ),
    ]

