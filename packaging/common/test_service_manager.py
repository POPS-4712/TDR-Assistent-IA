import service_manager


def test_backup_secret_guard():
    assert service_manager._contains_sensitive_metadata({"credential": {"api_key": "value-not-printed"}})
    assert service_manager._contains_sensitive_metadata({"nested": [{"token": "value-not-printed"}]})
    assert not service_manager._contains_sensitive_metadata({"profile": {"name": "safe", "capabilities": ["news"]}})


if __name__ == "__main__":
    test_backup_secret_guard()
    print("BACKUP_SECRET_GUARD=PASS")
