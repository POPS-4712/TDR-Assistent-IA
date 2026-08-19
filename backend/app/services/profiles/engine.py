"""Pure personalization logic for mapping a safe profile context to automation defaults."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


def _unique(values: Iterable[str]) -> List[str]:
    """Return non-empty strings once, preserving their input order."""
    result: List[str] = []
    seen = set()
    for value in values:
        item = value.strip() if isinstance(value, str) else ""
        key = item.casefold()
        if item and key not in seen:
            result.append(item)
            seen.add(key)
    return result


def merge_configuration(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Merge an explicit profile override into an engine-generated configuration."""
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_configuration(merged[key], value)
        else:
            merged[key] = value
    return merged


class PersonalizationEngine:
    """Build automation-neutral context and domain defaults from profile metadata."""

    def build_automation_defaults(self, profile: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Create generic defaults keyed by automation capability, never by profession."""
        profession = profile.get("profession", {})
        interests = profile.get("interests", [])
        interest_names = [item.get("name", "") for item in sorted(interests, key=lambda item: item.get("weight", 0), reverse=True)]
        topics = _unique([*profile.get("topics", []), *interest_names])
        companies = _unique(profile.get("companies", []))
        languages = _unique(profile.get("languages", []))
        locations = _unique([location.get("value", "") for location in profile.get("locations", [])])
        skills = _unique(profile.get("skills", []))
        goals = _unique(profile.get("goals", []))
        preferences = profile.get("preferences", {})
        primary_language = languages[0] if languages else ""
        profession_name = profession.get("name", "")
        sector = profession.get("sector", "")

        common = {
            "profile_name": profile.get("name", ""),
            "profession": profession_name,
            "sector": sector,
            "goals": goals,
            "languages": languages,
        }
        return {
            "news": {
                **common,
                "topics": topics,
                "keywords": _unique([*topics, *companies]),
                "companies": companies,
                "excluded_topics": _unique(profile.get("excluded_topics", [])),
                "frequency": preferences.get("news_frequency", "daily"),
                "language": primary_language,
                "priority": preferences.get("relevance_level", "high"),
                "sources": _unique(preferences.get("sources", [])),
            },
            "jobs": {
                **common,
                "roles": _unique([profession_name]),
                "skills": skills,
                "locations": locations,
                "keywords": _unique([profession_name, sector, *skills, *topics]),
                "remote": any(location.get("remote", False) for location in profile.get("locations", [])),
            },
            "email": {
                **common,
                "language": primary_language,
                "priority": preferences.get("relevance_level", "high"),
            },
            "personal_brand": {
                **common,
                "topics": topics,
                "audience_sector": sector,
                "language": primary_language,
            },
        }
