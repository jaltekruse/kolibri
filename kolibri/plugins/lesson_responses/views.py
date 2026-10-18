from csp.decorators import csp_update
from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.http import HttpResponseNotFound
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET

FREE_MATH_STATIC_PATH = "lesson_responses/free_math/"


@require_GET
@xframe_options_sameorigin
# Free Math's copy of MathJax and its image editor compile code from strings
@csp_update(SCRIPT_SRC="'unsafe-eval'")
def free_math(request):
    """
    The Free Math editor, framed by the learn and coach pages, which pass it
    the work to show with postMessage. Its files are static, but its relative
    links need a base URL pointing at them.
    """
    path = finders.find(FREE_MATH_STATIC_PATH + "embed.html")
    if path is None:
        return HttpResponseNotFound(
            "Free Math is not installed, see kolibri/plugins/lesson_responses/vendor_free_math.py",
            content_type="text/plain",
        )
    with open(path, encoding="utf-8") as f:
        html = f.read()
    base_url = settings.STATIC_URL + FREE_MATH_STATIC_PATH
    html = html.replace("<head>", f'<head><base href="{base_url}">', 1)
    return HttpResponse(html)
