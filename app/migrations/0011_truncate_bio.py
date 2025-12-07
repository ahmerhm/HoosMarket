from django.db import migrations


def truncate_bios(apps, schema_editor):
    Profile = apps.get_model('app', 'Profile')
    for p in Profile.objects.all():
        try:
            if p.bio and len(p.bio) > 1000:
                p.bio = p.bio[:1000]
                p.save(update_fields=['bio'])
        except Exception:
            # be resilient to unexpected profile data
            continue


def noop_reverse(apps, schema_editor):
    # cannot reverse truncation
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0010_post_hidden_from'),
    ]

    operations = [
        migrations.RunPython(truncate_bios, reverse_code=noop_reverse),
    ]
