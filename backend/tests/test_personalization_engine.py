from app.services.profiles.engine import PersonalizationEngine, merge_configuration


def _profile(name: str, profession: str, sector: str, topics: list[str], skills: list[str]) -> dict:
    return {
        "name": name,
        "profession": {"name": profession, "sector": sector, "level": ""},
        "interests": [{"name": item, "weight": 10 - index} for index, item in enumerate(topics)],
        "skills": skills,
        "companies": ["Example Organization"],
        "locations": [{"value": "Madrid", "remote": True}],
        "languages": ["Spanish", "English"],
        "topics": topics,
        "excluded_topics": ["Unrelated"],
        "goals": ["Follow industry news", "Find jobs"],
        "preferences": {"news_frequency": "daily", "relevance_level": "high", "sources": ["Official"]},
    }


def test_news_configuration_is_derived_from_profile_context() -> None:
    engine = PersonalizationEngine()
    context = engine.build_automation_defaults(
        _profile("Derecho", "Lawyer", "Legal", ["Legislation", "Jurisprudence"], ["Legal research"])
    )

    news = context["news"]
    assert news["topics"] == ["Legislation", "Jurisprudence"]
    assert news["companies"] == ["Example Organization"]
    assert news["excluded_topics"] == ["Unrelated"]
    assert news["frequency"] == "daily"
    assert news["language"] == "Spanish"


def test_jobs_configuration_is_generic_and_uses_profile_fields() -> None:
    engine = PersonalizationEngine()
    aerospace = engine.build_automation_defaults(
        _profile("Aeroespacial", "Aerospace Engineer", "Aerospace", ["Aviation", "Space"], ["Aerodynamics", "Python"])
    )
    economics = engine.build_automation_defaults(
        _profile("Economía", "Economist", "Finance", ["Inflation", "Markets"], ["Financial analysis"])
    )

    assert aerospace["jobs"]["roles"] == ["Aerospace Engineer"]
    assert aerospace["jobs"]["skills"] == ["Aerodynamics", "Python"]
    assert economics["jobs"]["roles"] == ["Economist"]
    assert economics["jobs"]["keywords"] != aerospace["jobs"]["keywords"]
    assert aerospace["jobs"]["remote"] is True


def test_explicit_automation_override_merges_without_mutating_defaults() -> None:
    generated = {"topics": ["Space"], "frequency": "daily", "filter": {"language": "English"}}
    merged = merge_configuration(generated, {"frequency": "weekly", "filter": {"minimum_score": 8}})

    assert merged == {
        "topics": ["Space"],
        "frequency": "weekly",
        "filter": {"language": "English", "minimum_score": 8},
    }
    assert generated["frequency"] == "daily"
