# Cryptographic Foundations

Secure user credentials with Argon2id and orchestrate identity via hardened, protocol-agnostic JWT signaling.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Security Infrastructure</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Core Core</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>Argon2id / PyJWT</strong>
  </div>
</div>

## The Challenge
Implementing robust security in FastAPI often suffers from "Infrastructure Drift":
1.  **Stale Hashing:** Many projects still use BCrypt or PBKDF2, which are increasingly vulnerable to GPU-accelerated side-channel attacks.
2.  **Secret Mismanagement:** Hardcoding secrets or failing to rotate them, often running production apps with default "example" keys.
3.  **Rigid Token Logic:** Difficulty switching from Symmetric (HS256) to Asymmetric (RS256) signing as the architecture moves toward microservices or OIDC.
4.  **Implicit Expiry:** Manual timestamp math for `exp` claims that lead to timezone bugs or permanent tokens.

## The ZCore Elegance
ZCore provides a hardened security chassis. It defaults to **Argon2id** (the winner of the Password Hashing Competition) with configurable memory costs. The JWT engine is "Signature-Aware," automatically detecting whether to use Symmetric or Asymmetric keys based on your configuration, while enforcing a mandatory "Production Secret Guard" that prevents unsafe deployments.

=== "ZCore Hardened Security"
      :::python
      from zcore.security import get_password_hash, create_token, verify_password

      # 1. High-Entropy Hashing (Argon2id)
      hashed = get_password_hash("user_password")
      is_valid = verify_password("user_password", hashed)

      # 2. Protocol-Agnostic Token Creation
      # Automatically uses RSA/ECDSA if keys are configured
      token = create_token(data={"sub": str(user.id), "scopes": ["admin"]})

=== "FastAPI Manual Security"
        :::python
        # Requires manual configuration of Passlib and PyJWT
        from passlib.context import CryptContext
        import jwt

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        def create_token(data: dict):
            to_encode = data.copy()
            # Manual expiry math
            expire = datetime.utcnow() + timedelta(minutes=30)
            to_encode.update({"exp": expire})
            # Manual algorithm and key management
            return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

---

## The Token Lifecycle

<p align="center">
  <img src="https://raw.githubusercontent.com/fastapi-zcore-framework/zcore/master/docs/assets/security.png" 
  alt="The Token Lifecycle" width="700">
</p>


---

## Boundaries & Integration
ZCore manages the cryptographic "heavy lifting" while remaining compatible with standard identity providers.

*   **OAuth2 Integration:** ZCore's `create_token` output is a standard JWT string, fully compatible with FastAPI's `OAuth2PasswordBearer` and `Security` scopes.
*   **User Independence:** The security utilities do not require a Database connection. You can use them to secure machine-to-machine (M2M) communication or external microservices.
*   **Bypass:** If your organization requires a different hashing algorithm (e.g., Scrypt), you can ignore the `hashing.py` utility. ZCore's higher-level components do not force a specific hash format on your `User` model.

---

## Under-the-Hood Spec

### 1. The Production Secret Guard
To prevent critical security oversights, ZCore’s JWT key resolver (`_get_signing_keys`) includes a fatal check [security/jwt.py]. If `ENVIRONMENT` is "production" and `SECRET_KEY` is set to the framework's insecure default value, the system raises a `RuntimeError` and **aborts application startup**. 

### 2. Argon2id Configuration
ZCore initializes the `PasswordHasher` with parameters optimized for modern server hardware [security/hashing.py]:
- **Memory Cost:** 64 MB (`65536`)
- **Time Cost:** 3 Iterations
- **Parallelism:** 4 Threads
These parameters ensure high resistance to specialized hardware (ASIC/GPU) cracking while maintaining sub-100ms verification times for users.

### 3. Dynamic Asymmetric Detection
The JWT utility is designed for scale [security/jwt.py]. If `JWT_PRIVATE_KEY` and `JWT_PUBLIC_KEY` are detected in the settings, the engine automatically switches to Asymmetric signing (e.g., `RS256`). This allows the framework to sign tokens in the Auth service that can be verified by downstream services using only the Public Key, without sharing the master secret.

!!! danger "Security Warning"
    Never store your `SECRET_KEY` or `JWT_PRIVATE_KEY` in version control. Always use environment variables or a secure secret manager (like Vault or AWS Secrets Manager) in production.