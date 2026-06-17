"""Flask URL map must not contain duplicate concrete route/method pairs."""

from app import create_app


def test_no_duplicate_routes():
    app = create_app({"TESTING": True})

    seen = {}
    duplicates = []
    for rule in app.url_map.iter_rules():
        methods = tuple(sorted((rule.methods or set()) - {"HEAD", "OPTIONS"}))
        key = (rule.rule, methods)
        current = rule.endpoint
        previous = seen.get(key)
        if previous:
            duplicates.append((rule.rule, methods, previous, current))
        else:
            seen[key] = current

    assert not duplicates, "\n".join(
        f"{path} {methods}: {first} conflicts with {second}"
        for path, methods, first, second in duplicates
    )
