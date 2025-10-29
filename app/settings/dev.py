from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-c56)3yn9)i#+^i7p)a49e+pphfiw9rogzys=@bx)_jpis1n%9n"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost','127.0.0.1','salty-shore-01968-bbd1b2057491.herokuapp.com']

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/
STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / 'media'

if os.getenv("USE_S3", "true").lower() == "true":
    from .prod import *