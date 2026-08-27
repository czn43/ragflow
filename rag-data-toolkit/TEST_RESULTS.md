# v1.8 Test Results

## Automated tests

```text
python -m pytest -q
........................ [100%]
24 passed
```

## Compile check

```text
python -m compileall -q .
PASS
```

## CLI version check

```text
python main.py --version
1.8.0
```

## Supplied SZNEWS HTML validation

Using `config/sites/sznews.yaml` against the supplied snippets:

```text
Initial list HTML     : 10 cards
After load-more HTML : 20 cards
```

Detail extraction:

```text
Title        : “贴身管家”爬楼拿药 “果园熟手”2秒摘果
Source       : 深圳晚报
Publish time : 2026-08-27
Content chars: 337
Method       : rule
```

The content rule uses `.article-content`, so the right-side AI section and QR-code area are not part of the extracted article body.
