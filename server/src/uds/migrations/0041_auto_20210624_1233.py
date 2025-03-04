# Generated by Django 3.2.4 on 2021-06-24 12:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('uds', '0040_auto_20210422_1340'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='config',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='service',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='uniqueid',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='userserviceproperty',
            unique_together=set(),
        ),
        migrations.AlterIndexTogether(
            name='userservice',
            index_together=set(),
        ),
        migrations.AddIndex(
            model_name='statscounters',
            index=models.Index(fields=['owner_type', 'stamp'], name='uds_stats_c_owner_t_db894d_idx'),
        ),
        migrations.AddIndex(
            model_name='statscounters',
            index=models.Index(fields=['owner_type', 'counter_type', 'stamp'], name='uds_stats_c_owner_t_a195c1_idx'),
        ),
        migrations.AddIndex(
            model_name='userservice',
            index=models.Index(fields=['deployed_service', 'cache_level', 'state'], name='uds__user_s_deploye_a38d25_idx'),
        ),
        migrations.AddConstraint(
            model_name='config',
            constraint=models.UniqueConstraint(fields=('section', 'key'), name='u_cfg_section_key'),
        ),
        migrations.AddConstraint(
            model_name='service',
            constraint=models.UniqueConstraint(fields=('provider', 'name'), name='u_srv_provider_name'),
        ),
        migrations.AddConstraint(
            model_name='uniqueid',
            constraint=models.UniqueConstraint(fields=('basename', 'seq'), name='u_uid_base_seq'),
        ),
        migrations.AddConstraint(
            model_name='userserviceproperty',
            constraint=models.UniqueConstraint(fields=('name', 'user_service'), name='u_uprop_name_userservice'),
        ),
        # Add user and groups constrains before removing old unique_together
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(fields=('manager', 'name'), name='u_usr_manager_name'),
        ),
        migrations.AddConstraint(
            model_name='group',
            constraint=models.UniqueConstraint(fields=('manager', 'name'), name='u_grp_manager_name'),
        ),
        # These must be removed after created contrains, because they are used in foreign keys
        migrations.AlterUniqueTogether(
            name='user',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='group',
            unique_together=set(),
        ),
    ]
