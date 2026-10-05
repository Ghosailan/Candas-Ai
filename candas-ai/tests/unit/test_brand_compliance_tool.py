from app.agents.tools.brand_compliance_tool import check_brand_compliance

def test_brand_compliance_flags_banned_word():
    result = check_brand_compliance('This is guaranteed to work')
    assert not result['compliant']
    assert 'banned_word:guaranteed' in result['violations']
