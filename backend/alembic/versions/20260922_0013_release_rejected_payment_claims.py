"""release rejected payment reference claims

Revision ID: 20260922_0013
Revises: 20260922_0012
Create Date: 2026-09-22
"""

from alembic import op

revision = "20260922_0013"
down_revision = "20260922_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION release_rejected_booking_payment_reference_claim()
        RETURNS trigger AS $$
        BEGIN
            IF NEW.status = 'rejected'
               AND OLD.status IS DISTINCT FROM NEW.status
               AND NEW.method IS NOT NULL
               AND NEW.reference IS NOT NULL THEN
                DELETE FROM payment_reference_claims
                WHERE method = lower(trim(NEW.method))
                  AND reference = upper(trim(NEW.reference))
                  AND source_type = 'booking'
                  AND source_id = NEW.booking_id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_release_rejected_booking_payment_reference_claim
        AFTER UPDATE OF status ON booking_payments
        FOR EACH ROW
        EXECUTE FUNCTION release_rejected_booking_payment_reference_claim();
        """
    )

    op.execute(
        """
        CREATE FUNCTION release_rejected_advert_payment_reference_claim()
        RETURNS trigger AS $$
        BEGIN
            IF NEW.status = 'payment_rejected'
               AND OLD.status IS DISTINCT FROM NEW.status
               AND NEW.payment_method IS NOT NULL
               AND NEW.payment_reference IS NOT NULL THEN
                DELETE FROM payment_reference_claims
                WHERE method = lower(trim(NEW.payment_method))
                  AND reference = upper(trim(NEW.payment_reference))
                  AND source_type = 'advert_charge'
                  AND source_id = NEW.id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_release_rejected_advert_payment_reference_claim
        AFTER UPDATE OF status ON advert_charges
        FOR EACH ROW
        EXECUTE FUNCTION release_rejected_advert_payment_reference_claim();
        """
    )

    # Clean up claims left behind by already-rejected records from earlier revisions.
    op.execute(
        """
        DELETE FROM payment_reference_claims claims
        USING booking_payments payments
        WHERE claims.source_type = 'booking'
          AND claims.source_id = payments.booking_id
          AND payments.status = 'rejected';
        """
    )
    op.execute(
        """
        DELETE FROM payment_reference_claims claims
        USING advert_charges charges
        WHERE claims.source_type = 'advert_charge'
          AND claims.source_id = charges.id
          AND charges.status = 'payment_rejected';
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_release_rejected_advert_payment_reference_claim ON advert_charges"
    )
    op.execute("DROP FUNCTION IF EXISTS release_rejected_advert_payment_reference_claim()")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_release_rejected_booking_payment_reference_claim ON booking_payments"
    )
    op.execute("DROP FUNCTION IF EXISTS release_rejected_booking_payment_reference_claim()")
