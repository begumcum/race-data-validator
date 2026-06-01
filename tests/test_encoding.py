"""Tests for race_validator.checks.encoding."""

from pathlib import Path

import pytest

from race_validator.checks.base import ValidationContext
from race_validator.checks.encoding import (
    Utf8EncodingCheck,
    NoBomCheck,
    UnixLineEndingsCheck,
)


def ctx_with(content: bytes) -> ValidationContext:
    return ValidationContext(file_path=Path("dummy.csv"), file_bytes=content)


class TestUtf8EncodingCheck:
    def test_ascii_passes(self):
        assert Utf8EncodingCheck().run(ctx_with(b"a,b,c\n1,2,3\n")) == []

    def test_utf8_passes(self):
        content = "driver_full_name_raw\nNicolás Varrone\n".encode("utf-8")
        assert Utf8EncodingCheck().run(ctx_with(content)) == []

    def test_latin1_fails(self):
        # Latin-1 byte for 'á' is 0xE1, invalid UTF-8 start byte alone
        content = b"driver_full_name_raw\nNicol\xe1s Varrone\n"
        results = Utf8EncodingCheck().run(ctx_with(content))
        assert len(results) == 1
        assert "UTF-8" in results[0].message


class TestNoBomCheck:
    def test_no_bom_passes(self):
        assert NoBomCheck().run(ctx_with(b"a,b,c\n")) == []

    def test_bom_fails(self):
        content = b"\xef\xbb\xbf" + b"a,b,c\n"
        results = NoBomCheck().run(ctx_with(content))
        assert len(results) == 1
        assert "BOM" in results[0].message


class TestUnixLineEndingsCheck:
    def test_lf_passes(self):
        assert UnixLineEndingsCheck().run(ctx_with(b"a\nb\nc\n")) == []

    def test_crlf_fails(self):
        results = UnixLineEndingsCheck().run(ctx_with(b"a\r\nb\r\nc\r\n"))
        assert len(results) == 1
        assert "Windows" in results[0].message

    def test_classic_mac_fails(self):
        results = UnixLineEndingsCheck().run(ctx_with(b"a\rb\rc\r"))
        assert len(results) == 1
        assert "Mac" in results[0].message
