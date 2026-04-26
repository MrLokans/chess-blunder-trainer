from __future__ import annotations

import pytest

from blunder_tutor.auth import (
    CorruptCredentialError,
    InvalidEmailError,
    InvalidPasswordError,
    InvalidUsernameError,
    PasswordHash,
    hash_password,
    is_user_id_shape,
    make_email,
    make_identity_id,
    make_session_token,
    make_user_id,
    make_username,
    verify_password,
)


class TestMakeUsername:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("alice", "alice"),
            ("ALICE", "alice"),
            ("  alice  ", "alice"),
            ("a_b-c0", "a_b-c0"),
            ("abc", "abc"),
            ("x" * 32, "x" * 32),
        ],
    )
    def test_valid(self, raw: str, expected: str):
        assert make_username(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "   ",
            "a",
            "ab",
            "x" * 33,
            "alice!",
            "al ice",
            "al.ice",
            "кириллица",
        ],
    )
    def test_invalid(self, raw: str):
        with pytest.raises(InvalidUsernameError):
            make_username(raw)

    def test_exception_has_safe_message_and_offender(self):
        try:
            make_username("bad!")
        except InvalidUsernameError as exc:
            assert str(exc) == "invalid username"
            assert exc.offender == "bad!"
        else:
            pytest.fail("expected InvalidUsernameError")


class TestMakeEmail:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Alice@Example.com", "alice@example.com"),
            ("  alice@example.com  ", "alice@example.com"),
            ("a.b+tag@sub.example.co.uk", "a.b+tag@sub.example.co.uk"),
        ],
    )
    def test_valid(self, raw: str, expected: str):
        assert make_email(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "no-at-sign",
            "spaces @example.com",
            "@example.com",
            "alice@",
            # Previously-permissive cases now rejected:
            "a..b@example.com",
            "a@example..com",
            "a@example.com.",
            ".a@example.com",
            "a.@example.com",
            "a@.example.com",
            "alice@localhost",  # no dot in domain
            # Overlong local-part (RFC 5321 §4.5.3.1 — local 64, total 254)
            ("x" * 250) + "@example.com",
        ],
    )
    def test_invalid(self, raw: str):
        with pytest.raises(InvalidEmailError):
            make_email(raw)


class TestPasswordHashing:
    def test_roundtrip(self):
        h = hash_password("correct horse battery staple")
        assert verify_password("correct horse battery staple", h) is True
        assert verify_password("wrong password", h) is False

    def test_rejects_too_short_ascii(self):
        with pytest.raises(InvalidPasswordError):
            hash_password("short")

    def test_rejects_too_long_ascii(self):
        with pytest.raises(InvalidPasswordError):
            hash_password("x" * 73)

    def test_rejects_over_byte_limit_with_multibyte_chars(self):
        # 25 * 3 bytes = 75 bytes — char count would wrongly pass a 72-char
        # check but bytes count is over bcrypt's 72-byte limit.
        password = "日" * 25
        assert len(password) == 25
        assert len(password.encode("utf-8")) == 75
        with pytest.raises(InvalidPasswordError):
            hash_password(password)

    def test_accepts_ascii_boundary(self):
        assert hash_password("x" * 8)
        assert hash_password("x" * 72)

    def test_accepts_byte_boundary_with_multibyte_chars(self):
        # 24 * 3 = 72 bytes — exactly at the limit.
        password = "日" * 24
        assert len(password.encode("utf-8")) == 72
        h = hash_password(password)
        assert verify_password(password, h) is True

    def test_verify_rejects_short_without_bcrypt_call(self):
        # A well-formed hash exists but `raw` is too short — should return
        # False by length prefilter, not raise CorruptCredentialError.
        h = hash_password("password123")
        assert verify_password("short", h) is False

    def test_verify_raises_on_malformed_stored_hash(self):
        with pytest.raises(CorruptCredentialError):
            verify_password("password123", PasswordHash("not-a-bcrypt-hash"))


class TestIdFactories:
    @pytest.mark.parametrize(
        "factory,expected_len",
        [
            (make_user_id, 32),
            (make_identity_id, 32),
            (make_session_token, 64),
        ],
    )
    def test_produces_hex_of_expected_length(self, factory, expected_len):
        value = factory()
        assert isinstance(value, str)
        assert len(value) == expected_len
        int(value, 16)

    @pytest.mark.parametrize(
        "factory",
        [make_user_id, make_identity_id, make_session_token],
    )
    def test_values_are_unique(self, factory):
        assert factory() != factory()


class TestIsUserIdShape:
    def test_accepts_freshly_minted_user_id(self):
        assert is_user_id_shape(make_user_id())

    @pytest.mark.parametrize(
        "candidate",
        [
            "0" * 32,
            "a" * 32,
            "0123456789abcdef0123456789abcdef",
        ],
    )
    def test_accepts_valid_shapes(self, candidate: str):
        assert is_user_id_shape(candidate)

    @pytest.mark.parametrize(
        "candidate",
        [
            "",
            "a" * 31,  # too short
            "a" * 33,  # too long
            "A" * 32,  # uppercase — UserId is lowercase hex
            "g" * 32,  # non-hex char
            "backups",
            "README",
            "_archive",
            "0123456789abcdef0123456789abcde!",
        ],
    )
    def test_rejects_non_user_id_shapes(self, candidate: str):
        assert not is_user_id_shape(candidate)
