# Data migration: örnek blog yazısı (test için)

from django.db import migrations
from django.utils import timezone


def create_sample_post(apps, schema_editor):
    User = apps.get_model("users", "User")
    BlogPost = apps.get_model("blog", "BlogPost")

    author = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not author:
        return

    if BlogPost.objects.filter(slug="marifetli-bloga-hosgeldiniz").exists():
        return

    BlogPost.objects.create(
        title="Marifetli Blog'a Hoş Geldiniz",
        slug="marifetli-bloga-hosgeldiniz",
        excerpt="Blog sayfamız yayında. El işleri, örgü, dikiş ve topluluk güncellemeleri burada.",
        content="""<p>Merhaba!</p>
<p>Marifetli blog sayfamız artık yayında. Burada el işleri, örgü, dikiş, nakış ve diğer topluluk konularında yazılar paylaşacağız.</p>
<p>İstediğiniz konularda soru sorabilir, deneyimlerinizi paylaşabilir ve birbirinizden ilham alabilirsiniz. Yorumlarınızı ve beğenilerinizi kullanmayı unutmayın.</p>
<p>İyi okumalar,<br>Marifetli Ekibi</p>""",
        author=author,
        is_published=True,
        published_at=timezone.now(),
    )


def remove_sample_post(apps, schema_editor):
    BlogPost = apps.get_model("blog", "BlogPost")
    BlogPost.objects.filter(slug="marifetli-bloga-hosgeldiniz").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_sample_post, remove_sample_post),
    ]
