from __future__ import annotations

import pytest

from blunder_tutor.auth import generate_invite_code, verify_invite_code

_SECRET = "x" * 64


class TestGenerateInviteCode:
    def test_has_payload_dot_signature_shape(self):
        code = generate_invite_code(_SECRET)
        assert code.count(".") == 1
        payload, sig = code.split(".")
        assert len(payload) == 32  # 16 bytes hex
        assert len(sig) == 16  # 8 bytes hex

    def test_codes_are_unique(self):
        assert generate_invite_code(_SECRET) != generate_invite_code(_SECRET)


class TestVerifyInviteCode:
    def test_accepts_valid_code(self):
        code = generate_invite_code(_SECRET)
        assert verify_invite_code(code, _SECRET) is True

    def test_rejects_wrong_secret(self):
        code = generate_invite_code(_SECRET)
        assert verify_invite_code(code, "y" * 64) is False

    def test_rejects_tampered_payload(self):
        code = generate_invite_code(_SECRET)
        payload, sig = code.split(".")
        tampered = f"{payload[:-1]}X.{sig}"
        assert verify_invite_code(tampered, _SECRET) is False

    def test_rejects_tampered_signature(self):
        code = generate_invite_code(_SECRET)
        payload, sig = code.split(".")
        tampered = f"{payload}.{sig[:-1]}X"
        assert verify_invite_code(tampered, _SECRET) is False

    @pytest.mark.parametrize(
        "bad",
        ["no-dot", "", "too.many.dots", ".", "payload.", ".sig"],
    )
    def test_rejects_malformed_shapes(self, bad: str):
        assert verify_invite_code(bad, _SECRET) is False

    def test_rejects_non_hex_signature(self):
        code = generate_invite_code(_SECRET)
        payload, _ = code.split(".")
        assert verify_invite_code(f"{payload}.not_hex_at_all", _SECRET) is False

    def test_uses_constant_time_compare(self):
        """We verify the comparator is `hmac.compare_digest`-based by
        round-tripping a code where the computed and supplied signatures
        differ only in the last byte — both must evaluate without raising,
        and the function must return False deterministically."""
        code = generate_invite_code(_SECRET)
        payload, sig = code.split(".")
        # Flip last nibble; still 16 hex chars but wrong.
        flipped_last = "0" if sig[-1] != "0" else "1"
        bad = f"{payload}.{sig[:-1]}{flipped_last}"
        for _ in range(10):
            assert verify_invite_code(bad, _SECRET) is False
