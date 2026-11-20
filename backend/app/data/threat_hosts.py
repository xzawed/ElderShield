"""Curated scam-ad / phishing host seeds for DNS denylist merge (Phase 2C P3).

Hosts are intentionally synthetic/example-style for OSS trees — operators replace
or extend via this module before production NextDNS sync.
"""

# Lowercase FQDNs only (no wildcards). Merged into denylist domains.
THREAT_HOSTS: frozenset[str] = frozenset(
    {
        "scam-ad-landing.example",
        "fake-prize-popup.example",
        "crypto-airdrop-claim.example",
        "support-refund-verify.example",
        "bank-secure-login.example",
        "delivery-fee-pay.example",
        "account-locked-reset.example",
        "tax-refund-urgent.example",
        "parcel-customs-pay.example",
        "wallet-connect-phish.example",
        "free-giftcard-claim.example",
        "norton-renewal-fake.example",
        "microsoft-alert-verify.example",
        "kakao-secure-check.example",
        "toss-verify-login.example",
        "ad-click-jack.example",
        "overlay-offer-wall.example",
        "install-helper-apk.example",
        "remote-assist-scam.example",
        "gov-subsidy-form.example",
    }
)
