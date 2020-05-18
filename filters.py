import re
from jinja2 import evalcontextfilter
from markupsafe import Markup, escape


def do_datetime(dt, format=None):
    """Jinja template filter to format a datetime object with date & time."""
    if dt is None:
        # By default, render an empty string.
        return ''
    if format is None:
        # No format is given in the template call. Use a default format.
        #
        # Format time in its own strftime call in order to:
        # 1. Left-strip leading 0 in hour display.
        # 2. Use 'am' and 'pm' (lower case) instead of 'AM' and 'PM'.
        formatted_date = dt.strftime('%Y-%m-%d - %A')
        formatted_time = dt.strftime('%I:%M%p').lstrip('0').lower()
        formatted = f'{formatted_date} at {formatted_time}'
    else:
        formatted = dt.strftime(format)
    return formatted


def do_date(dt, format='%Y-%m-%d - %A'):
    """Jinja template filter to format a datetime object with date only."""
    if dt is None:
        return ''
    # Only difference with do_datetime is the default format, but that is
    # convenient enough to warrant its own template filter.
    return dt.strftime(format)


def do_duration(seconds):
    """Jinja template filter to format seconds to humanized duration.

    3600 becomes "1 hour".
    258732 becomes "2 days, 23 hours, 52 minutes, 12 seconds".
    """
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    tokens = []
    if d > 1:
        tokens.append('{d} days')
    elif d:
        tokens.append('{d} day')
    if h > 1:
        tokens.append('{h} hours')
    elif h:
        tokens.append('{h} hour')
    if m > 1:
        tokens.append('{m} minutes')
    elif m:
        tokens.append('{m} minute')
    if s > 1:
        tokens.append('{s} seconds')
    elif s:
        tokens.append('{s} second')
    template = ', '.join(tokens)
    return template.format(d=d, h=h, m=m, s=s)


_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')


@evalcontextfilter
def do_nl2br(context, value):
    """Render newline \n characters as HTML line breaks <br />.

    By default, HTML normalizes all whitespace on display. This filter allows
    text with line breaks entered into a textarea input to later display in
    HTML with line breaks.

    The context argument is Jinja's state for template rendering, which
    includes configuration. This filter inspects the context to determine
    whether to auto-escape content, e.g. convert <script> to &lt;script&gt;.
    """
    formatted = u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', Markup('<br>\n'))
                             for p in _paragraph_re.split(escape(value)))
    if context.autoescape:
        formatted = Markup(formatted)
    return formatted
