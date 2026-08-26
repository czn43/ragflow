from cleaner.date_cleaner import parse_date


def test_date_formats():
    for raw in ['2024年8月26日', '2024/08/26', '2024.08.26', '2024-8-26']:
        r = parse_date(raw)
        assert r.normalized == '2024-08-26'
