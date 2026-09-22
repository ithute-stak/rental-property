from app.models.payment import PaymentReferenceClaim
from app.services.payments import normalize_payment_reference


def test_payment_reference_normalization_is_case_insensitive_and_trimmed():
    assert normalize_payment_reference("  mp-abc-123  ") == "MP-ABC-123"


def test_payment_reference_claim_has_global_method_reference_uniqueness():
    constraint_names = {
        constraint.name
        for constraint in PaymentReferenceClaim.__table__.constraints
        if constraint.name is not None
    }

    assert "uq_payment_reference_method_reference" in constraint_names
