import re
from pathlib import Path
import yaml
from langchain_core.tools import tool

DEFAULT_RULES = {
    'banned_words': ['guaranteed', 'miracle', 'risk-free'],
    'required_disclaimers': [],
    'max_emoji_count': 6,
    'tone_words': ['clear', 'professional', 'helpful'],
}


def load_rules(path: str | None = None) -> dict:
    if path and Path(path).exists():
        return yaml.safe_load(Path(path).read_text()) or DEFAULT_RULES
    return DEFAULT_RULES


def check_brand_compliance(copy: str, rules: dict | None = None) -> dict:
    rules = rules or load_rules()
    violations: list[str] = []
    lowered = copy.lower()
    for word in rules.get('banned_words', []):
        if word.lower() in lowered:
            violations.append(f'banned_word:{word}')
    emoji_count = len(re.findall(r'[\U0001F300-\U0001FAFF]', copy))
    if emoji_count > int(rules.get('max_emoji_count', 6)):
        violations.append('too_many_emojis')
    for disclaimer in rules.get('required_disclaimers', []):
        if disclaimer.lower() not in lowered:
            violations.append(f'missing_disclaimer:{disclaimer}')
    return {'compliant': not violations, 'violations': violations}

@tool('brand_compliance_tool')
def brand_compliance_tool(copy: str, rules_path: str | None = None) -> dict:
    """Check social post copy against brand rules."""
    return check_brand_compliance(copy, load_rules(rules_path))
