import re

EMAIL_RE = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
PHONE_RE = re.compile(r'(\+?\d[\d\s().-]{7,}\d)')

try:
    from presidio_analyzer import AnalyzerEngine
    _analyzer = AnalyzerEngine()
except Exception:  # pragma: no cover
    _analyzer = None


def redact_pii(text: str) -> str:
    redacted = EMAIL_RE.sub('[REDACTED_EMAIL]', text)
    redacted = PHONE_RE.sub('[REDACTED_PHONE]', redacted)
    if _analyzer:
        try:
            for item in sorted(_analyzer.analyze(text=redacted, language='en'), key=lambda x: x.start, reverse=True):
                redacted = redacted[:item.start] + f'[REDACTED_{item.entity_type}]' + redacted[item.end:]
        except Exception:
            pass
    return redacted
