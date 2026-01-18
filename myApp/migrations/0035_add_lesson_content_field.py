# Generated manually to add content JSONField to Lesson model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myApp', '0034_lead_infobip_channel_lead_infobip_last_synced_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='lesson',
            name='content',
            field=models.JSONField(blank=True, default=dict, help_text='Editor.js JSON blocks for rich content'),
        ),
    ]

