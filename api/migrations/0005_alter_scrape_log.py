# Generated by Django 4.2.1 on 2023-05-14 08:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_alter_scrape_completed_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scrape',
            name='log',
            field=models.TextField(blank=True, default=None, null=True),
        ),
    ]
