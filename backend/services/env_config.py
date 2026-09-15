import os
import sys

def validate_environment():
    """Validate critical environment variables at startup.
    
    Fails loudly with clear error messages if critical secrets are missing
    or insecure defaults are used in non-development environments.
    """
    errors = []
    warnings = []

    # 1. Critical AI Keys — At least one must be supplied
    google_key = os.getenv("GOOGLE_API_KEY", "").strip()
    
    if (not google_key or google_key == "dummy_test_key"):
        warnings.append(
            "GOOGLE_API_KEY is not configured with a valid key. "
            "AI VLM classifications will fall back to rule-based defaults."
        )

    # 2. JWT Security Key
    jwt_secret = os.getenv("JWT_SECRET_KEY", "").strip()
    insecure_defaults = [
        "",
        "eng-drawing-jwt-secret-key-change-in-prod-2026",
        "change_this_to_a_secure_random_64_character_string_in_production",
        "secret",
        "12345"
    ]
    is_prod = os.getenv("ENVIRONMENT", "development").lower() in ("production", "prod")
    if not jwt_secret:
        errors.append("JWT_SECRET_KEY environment variable is missing or empty.")
    elif is_prod and jwt_secret in insecure_defaults:
        errors.append("JWT_SECRET_KEY is using an insecure default value in a production environment.")

    # 3. Database Credentials
    db_host = os.getenv("POSTGRES_HOST", "").strip()
    db_user = os.getenv("POSTGRES_USER", "").strip()
    db_name = os.getenv("POSTGRES_DATABASE", "").strip()
    
    if not db_host:
        errors.append("POSTGRES_HOST environment variable is missing.")
    if not db_user:
        errors.append("POSTGRES_USER environment variable is missing.")
    if not db_name:
        errors.append("POSTGRES_DATABASE environment variable is missing.")

    # Print warnings if any
    for w in warnings:
        print(f"[config WARNING] {w}")

    # Fail loudly if critical errors exist
    if errors:
        print("\n" + "=" * 70)
        print("CRITICAL CONFIGURATION ERROR: MISSING/INVALID ENVIRONMENT VARIABLES")
        print("=" * 70)
        for err in errors:
            print(f" ERROR: {err}")
        print("\nPlease check your .env file or deployment environment settings.")
        print("Refer to .env.example for required variable definitions.")
        print("=" * 70 + "\n")
        raise RuntimeError("Environment validation failed: " + "; ".join(errors))
