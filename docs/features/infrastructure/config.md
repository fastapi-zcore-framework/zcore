# Centralized Configuration Management

Type-safe, environment-aware settings with lazy resolution and seamless Dependency Injection integration.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>Configuration Utility</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Core Infrastructure</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>Pydantic Settings V2</strong>
  </div>
</div>

## The Challenge
Managing configuration in growing FastAPI projects often results in **Circular Import Hell**. This happens because nearly every module (Database, Security, Services) needs settings, but settings are often instantiated in `main.py`. If a module imported by `main.py` tries to import the settings instance from `main.py`, the app crashes. 

Furthermore, manually managing `.env` file paths and ensuring type-safety for environment variables across different deployment stages (dev, test, prod) adds unnecessary cognitive load.

## The ZCore Elegance
ZCore solves this using a **Settings Proxy** combined with the global **IoC Container**. You simply import a global `settings` object. It remains "hollow" until an attribute is accessed, at which point it dynamically resolves the configuration from the container. This eliminates circular imports and allows for easy settings overriding during testing.

=== "ZCore Lazy Configuration"
        :::python
        # Import and use anywhere - zero circular import risk
        from zcore import settings

        def get_db_url():
            # Instance is resolved lazily on first access
            return settings.DATABASE_URL

=== "FastAPI Manual Management"
        :::python
        # Standard approach often leads to circularity or manual passing
        from my_app.main import settings # Risk: main imports modules, modules import main

        # OR: Manual instantiation in every file (Expensive/Inconsistent)
        from pydantic_settings import BaseSettings
        class MySettings(BaseSettings):
            DATABASE_URL: str
        
        settings = MySettings() # Re-reading .env every time

---

## Boundaries & Integration
ZCore Configuration is a transparent wrapper around the Pydantic ecosystem.

*   **Pydantic V2 Native:** `ZCoreCoreSettings` inherits directly from `pydantic_settings.BaseSettings`. You can use all Pydantic features like `AliasPath`, `Field` validation, and complex types (SecretStr, HttpUrl) [config.py].
*   **Extensible:** You can easily extend the base settings by creating your own class. Once registered via `initialize_settings(my_inst)`, ZCore's global `settings` proxy will resolve to your custom implementation.
*   **Bypass:** If you prefer not to use the global proxy, you can instantiate your own Pydantic Settings class and use it normally. ZCore's internal modules will continue to use their registered singletons without interference.

---

## Under-the-Hood Spec

### 1. The Settings Proxy
The global `settings` object is an instance of `SettingsProxy` [config.py]. It implements `__getattr__`, which intercepts attribute access and calls `get_settings()`. This function attempts to resolve the settings instance from the `IoCContainer`. If not found, it instantiates the default `ZCoreCoreSettings`, registers it as a singleton, and returns it.

### 2. Dynamic `.env` Resolution
The `model_config` is configured to look for an environment variable named `ENV_FILE` [config.py]. If set (e.g., `ENV_FILE=.env.test`), ZCore will load that specific file. If not set, it defaults to the standard `.env` in the project root. This allows for seamless switching between environment configurations without code changes.

### 3. DI Container Registration
The `initialize_settings` function performs a "Double Registration" [config.py]. It registers the settings instance under its specific class type *and* under the base `ZCoreCoreSettings` type. This ensures that even if you provide a custom subclass (e.g., `MyAppSettings`), ZCore's internal components can still inject the base type and receive your custom instance.

!!! info "Production Security"
    ZCore's settings default to `ENVIRONMENT="production"`. In this mode, certain security-critical defaults (like the insecure `SECRET_KEY`) will trigger fatal errors in related modules like `zcore.security.jwt` to prevent accidental insecure deployments.