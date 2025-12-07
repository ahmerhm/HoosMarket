from django.db import migrations


def truncate_post_descriptions(apps, schema_editor):
    Post = apps.get_model('app', 'Post')
    for p in Post.objects.all():
        try:
            if p.description and len(p.description) > 1000:
                p.description = p.description[:1000]
                p.save(update_fields=['description'])
        except Exception:
            continue


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0011_truncate_bio'),
    ]

    operations = [
        migrations.RunPython(truncate_post_descriptions, reverse_code=noop_reverse),
    ]
