"""Unit tests for metadata placeholder detection utilities."""

from __future__ import annotations

from pywiim.metadata import is_valid_image_url, is_valid_metadata_value


class TestMetadataValidation:
    def test_is_valid_metadata_value_rejects_placeholders(self):
        assert is_valid_metadata_value("Unknown") is False
        assert is_valid_metadata_value("un_known") is False
        assert is_valid_metadata_value("  n/a  ") is False
        assert is_valid_metadata_value("(null)") is False
        assert is_valid_metadata_value("") is False
        assert is_valid_metadata_value(None) is False

    def test_is_valid_metadata_value_accepts_real_strings(self):
        assert is_valid_metadata_value("Daft Punk") is True
        assert is_valid_metadata_value("0") is True  # keep tight filter; don't over-reject

    def test_is_valid_image_url_strict(self):
        assert is_valid_image_url("https://example.com/a.jpg") is True
        assert is_valid_image_url("http://192.168.1.2:49152/cover.jpg") is True

        assert is_valid_image_url("un_known") is False
        assert is_valid_image_url("http://192.168.1.2:49152/un_known") is False
        assert is_valid_image_url("file:///tmp/a.jpg") is False
        assert is_valid_image_url("") is False
        assert is_valid_image_url(None) is False
