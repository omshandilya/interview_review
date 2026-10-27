# Generated manually for the role-based interview feature.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interview_core', '0007_remove_resume_file'),
    ]

    operations = [
        migrations.CreateModel(
            name='RoleInterviewSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(max_length=100)),
                ('role_slug', models.CharField(max_length=64)),
                ('experience_level', models.CharField(max_length=20)),
                ('focus_area', models.CharField(blank=True, max_length=64)),
                ('job_description', models.TextField(blank=True)),
                ('difficulty', models.CharField(default='medium', max_length=10)),
                ('question_count', models.PositiveSmallIntegerField(default=4)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='role_interviews', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='roleinterviewsession',
            index=models.Index(fields=['user', 'created_at'], name='interview_c_user_id_06b59b_idx'),
        ),
        migrations.AddIndex(
            model_name='roleinterviewsession',
            index=models.Index(fields=['user', 'role_slug'], name='interview_c_user_id_f9a39a_idx'),
        ),
        migrations.AddField(
            model_name='interviewquestion',
            name='role_session',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='questions', to='interview_core.roleinterviewsession'),
        ),
    ]
