# Generated by Django 4.2.1 on 2023-06-15 08:21

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0008_remove_result_status_code"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="result",
            name="page_content_html",
        ),
    ]
