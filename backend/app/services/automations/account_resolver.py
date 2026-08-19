"""Safe account and n8n credential compatibility resolution for automations."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping

from .manifest_manager import Manifest


class AccountResolver:
    """Resolve manifest requirements using credential metadata only.

    The resolver never reads secure-store material and never returns credential
    IDs, n8n IDs, tokens, passwords, headers, or provider payloads. Internal
    references are used only to determine whether an already-created n8n
    credential can be assigned to an imported workflow copy.
    """

    MISSING_MAPPING_PREFIX = "MISSING COMPATIBLE N8N CREDENTIAL MAPPING"

    def resolve(self, manifest: Manifest, credentials: Iterable[Any]) -> Dict[str, Any]:
        """Return a deterministic, public-safe readiness report for a manifest."""
        records_by_provider: Dict[str, List[Any]] = defaultdict(list)
        for credential in credentials:
            provider = self._value(credential, "provider")
            if provider:
                records_by_provider[str(provider)].append(credential)

        requirement_by_provider = {item.provider: item for item in manifest.requirements}
        mapped_types_by_provider: Dict[str, List[str]] = defaultdict(list)
        for credential_type, provider in manifest.n8n.credential_mapping.items():
            mapped_types_by_provider[provider].append(credential_type)

        provider_names = list(dict.fromkeys([
            *requirement_by_provider.keys(),
            *mapped_types_by_provider.keys(),
        ]))
        account_results: List[Dict[str, Any]] = []
        mapping_results: List[Dict[str, Any]] = []
        missing_requirements: List[str] = []

        for provider in provider_names:
            requirement = requirement_by_provider.get(provider)
            required_scopes = sorted(set(requirement.scopes if requirement else []))
            records = records_by_provider.get(provider, [])
            account_result, provider_missing = self._resolve_provider(
                provider=provider,
                required_scopes=required_scopes,
                records=records,
            )
            account_results.append(account_result)
            missing_requirements.extend(provider_missing)

            for credential_type in sorted(set(mapped_types_by_provider.get(provider, []))):
                mapping_result, mapping_missing = self._resolve_mapping(
                    provider=provider,
                    required_scopes=required_scopes,
                    credential_type=credential_type,
                    records=records,
                )
                mapping_results.append(mapping_result)
                missing_requirements.extend(mapping_missing)

        unique_missing = list(dict.fromkeys(missing_requirements))
        return {
            "accounts": account_results,
            "credential_mappings": mapping_results,
            "missing_requirements": unique_missing,
            "ready": not unique_missing,
        }

    def _resolve_provider(
        self,
        *,
        provider: str,
        required_scopes: List[str],
        records: List[Any],
    ) -> tuple[Dict[str, Any], List[str]]:
        """Resolve one provider requirement while exposing only allowed fields."""
        eligible = [record for record in records if self._effective_status(record) == "active"]
        scoped = [record for record in eligible if self._has_scopes(record, required_scopes)]
        selected = scoped[0] if scoped else (eligible[0] if eligible else (records[0] if records else None))
        granted_scopes = sorted(set(self._value(selected, "scopes") or [])) if selected else []
        missing: List[str] = []

        if not records:
            validation_status = "missing"
            account_status = "missing"
            missing.append(f"{provider}: account not connected")
        elif not eligible:
            account_status = self._effective_status(selected)
            validation_status = "invalid"
            missing.append(f"{provider}: account status is {account_status}")
        elif not scoped:
            account_status = "active"
            validation_status = "blocked"
            absent_scopes = sorted(set(required_scopes) - set(granted_scopes))
            missing.append(f"{provider}: missing scopes: {', '.join(absent_scopes)}")
        else:
            account_status = "active"
            validation_status = "valid"

        return ({
            "provider": provider,
            "account": self._value(selected, "account_identifier") if selected else None,
            "status": account_status,
            "scopes": {
                "required": required_scopes,
                "granted": granted_scopes,
            },
            "validation_status": validation_status,
            "missing_requirements": missing,
            "compatible": validation_status == "valid",
        }, missing)

    def _resolve_mapping(
        self,
        *,
        provider: str,
        required_scopes: List[str],
        credential_type: str,
        records: List[Any],
    ) -> tuple[Dict[str, Any], List[str]]:
        """Resolve one exact n8n node credential type without returning its ID."""
        candidate = next(
            (
                record for record in records
                if self._effective_status(record) == "active"
                and self._has_scopes(record, required_scopes)
                and self._value(record, "n8n_credential_id")
                and self._n8n_type(record) == credential_type
            ),
            None,
        )
        if candidate:
            return ({
                "provider": provider,
                "required_n8n_type": credential_type,
                "account": self._value(candidate, "account_identifier"),
                "status": "compatible",
                "compatible": True,
                "missing_requirements": [],
            }, [])

        message = f"{self.MISSING_MAPPING_PREFIX}: {provider} -> {credential_type}"
        account = next((self._value(record, "account_identifier") for record in records), None)
        return ({
            "provider": provider,
            "required_n8n_type": credential_type,
            "account": account,
            "status": "missing_compatible_mapping",
            "compatible": False,
            "missing_requirements": [message],
        }, [message])

    @staticmethod
    def _value(record: Any, key: str) -> Any:
        if record is None:
            return None
        if isinstance(record, Mapping):
            return record.get(key)
        return getattr(record, key, None)

    def _effective_status(self, record: Any) -> str:
        status = str(self._value(record, "status") or "missing")
        expires_at = self._value(record, "expires_at")
        if status == "active" and expires_at and expires_at <= datetime.utcnow():
            return "reauth_required"
        return status

    def _has_scopes(self, record: Any, required_scopes: List[str]) -> bool:
        granted_scopes = set(self._value(record, "scopes") or [])
        return set(required_scopes).issubset(granted_scopes)

    def _n8n_type(self, record: Any) -> str | None:
        metadata = self._value(record, "credential_metadata") or {}
        return metadata.get("_n8n_credential_type") if isinstance(metadata, Mapping) else None
