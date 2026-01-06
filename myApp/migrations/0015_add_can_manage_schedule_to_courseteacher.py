# Generated manually to add can_manage_schedule field
# Note: Column already exists in database, so we use SeparateDatabaseAndState
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myApp', '0014_fix_courseteacher_column_name'),
    ]

    operations = [
        # Since the column already exists in the database, we only update Django's state
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='courseteacher',
                    name='can_manage_schedule',
                    field=models.BooleanField(default=False, help_text='Can manage schedule and availability for this course'),
                ),
            ],
            database_operations=[
                # Do nothing - column already exists in database
            ],
        ),
    ]


