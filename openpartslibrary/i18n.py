"""Internationalization helpers with Flask-Babel and gettext fallbacks."""

import gettext as gettext_library
from functools import lru_cache
from pathlib import Path

from flask import current_app, has_app_context, has_request_context, request, session

try:
    from flask_babel import Babel
    from flask_babel import gettext as babel_gettext
    from flask_babel import lazy_gettext
    from flask_babel import ngettext as babel_ngettext
except ImportError:
    Babel = None
    babel_gettext = None
    babel_ngettext = None


DEFAULT_LOCALE = "en_US"
SUPPORTED_LOCALES = {
    "en_US": "English (US)",
    "de": "Deutsch",
    "fr": "Français",
    "pl": "Polski",
    "es": "Español",
    "it": "Italiano",
}


def normalize_locale(locale):
    """Normalize a requested locale to one of the supported locale IDs."""

    if not locale:
        return None

    normalized = locale.replace("-", "_")
    if normalized in SUPPORTED_LOCALES:
        return normalized

    language = normalized.split("_", 1)[0].lower()
    for supported_locale in SUPPORTED_LOCALES:
        if supported_locale.split("_", 1)[0].lower() == language:
            return supported_locale

    return None


def select_locale():
    """Choose the active locale from query string, session, or Accept-Language."""

    if not has_request_context():
        return DEFAULT_LOCALE

    requested_locale = normalize_locale(request.args.get("lang"))
    if requested_locale:
        session["locale"] = requested_locale
        return requested_locale

    session_locale = normalize_locale(session.get("locale"))
    if session_locale:
        return session_locale

    accepted_locale = request.accept_languages.best_match(list(SUPPORTED_LOCALES))
    return normalize_locale(accepted_locale) or DEFAULT_LOCALE


def compile_translation_catalogs(app):
    """Compile bundled ``.po`` files to ``.mo`` files when Babel is available."""

    try:
        from babel.messages import mofile, pofile
    except ImportError:
        return

    translations_dir = Path(app.root_path) / "translations"
    if not translations_dir.exists():
        return

    for po_path in translations_dir.glob("*/LC_MESSAGES/messages.po"):
        mo_path = po_path.with_suffix(".mo")
        with po_path.open("r", encoding="utf-8") as po_file:
            catalog = pofile.read_po(po_file)
        mo_path.parent.mkdir(parents=True, exist_ok=True)
        with mo_path.open("wb") as mo_file:
            mofile.write_mo(mo_file, catalog)


@lru_cache(maxsize=16)
def load_gettext_translation(translations_dir, locale):
    """Load and cache a gettext translation object."""

    return gettext_library.translation(
        "messages",
        localedir=translations_dir,
        languages=[locale],
        fallback=True,
    )


def get_translation():
    """Return the active gettext translation object or a null translation."""

    if not has_app_context():
        return gettext_library.NullTranslations()

    locale = select_locale()
    translations_dir = str(Path(current_app.root_path) / "translations")
    return load_gettext_translation(translations_dir, locale)


def gettext(message, **variables):
    """Translate a message and interpolate named variables."""

    if babel_gettext is not None:
        return babel_gettext(message, **variables)

    translated = get_translation().gettext(message)
    return translated % variables if variables else translated


def ngettext(singular, plural, num, **variables):
    """Translate singular/plural messages and interpolate named variables."""

    if babel_ngettext is not None:
        return babel_ngettext(singular, plural, num, **variables)

    variables.setdefault("num", num)
    translated = get_translation().ngettext(singular, plural, num)
    return translated % variables if variables else translated


class LazyString:
    """Minimal lazy translation object used when Flask-Babel is absent."""

    def __init__(self, func, *args, **kwargs):
        """Store the callable and its arguments for later rendering."""

        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        """Evaluate and stringify the lazy value."""

        return str(self.func(*self.args, **self.kwargs))

    def __html__(self):
        """Return the HTML-safe string representation used by templates."""

        return str(self)


if Babel is None:
    def lazy_gettext(message, **variables):
        """Return a lazily evaluated translation fallback."""

        return LazyString(gettext, message, **variables)


def init_i18n(app):
    """Initialize translation support and inject i18n globals into templates."""

    app.config.setdefault("BABEL_DEFAULT_LOCALE", DEFAULT_LOCALE)
    app.config.setdefault("BABEL_TRANSLATION_DIRECTORIES", "translations")
    compile_translation_catalogs(app)

    if Babel is not None:
        babel = Babel()
        try:
            babel.init_app(app, locale_selector=select_locale)
        except TypeError:
            babel.init_app(app)
            babel.localeselector(select_locale)
    else:
        babel = None

    @app.context_processor
    def inject_i18n():
        current_locale = select_locale()
        return {
            "_": gettext,
            "ngettext": ngettext,
            "current_locale": current_locale,
            "supported_locales": SUPPORTED_LOCALES,
        }

    return babel
