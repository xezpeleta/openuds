# Generated by Django 3.1.2 on 2020-11-11 11:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('uds', '0038_auto_20200505_config'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='metapool',
            name='accessCalendars',
        ),
        migrations.RemoveField(
            model_name='servicepool',
            name='accessCalendars',
        ),
        migrations.RemoveField(
            model_name='servicepool',
            name='actionsCalendars',
        ),
    ]
