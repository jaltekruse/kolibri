from kolibri.plugins import KolibriPluginBase


class LessonResponses(KolibriPluginBase):
    untranslated_view_urls = "api_urls"
    translated_view_urls = "urls"
