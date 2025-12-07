# Generated migration to truncate post descriptions to 1000 characters

from django.db import migrations


def truncate_descriptions(apps, schema_editor):
    """Truncate all post descriptions to 1000 characters."""
    Post = apps.get_model('app', 'Post')
    for post in Post.objects.all():
        if len(post.description) > 1000:
            post.description = post.description[:1000]
            post.save(update_fields=['description'])


def reverse_truncate(apps, schema_editor):
    """This operation cannot be reversed (data loss is irreversible)."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0010_post_hidden_from'),
    ]

    operations = [
        migrations.RunPython(truncate_descriptions, reverse_truncate),
    ]
