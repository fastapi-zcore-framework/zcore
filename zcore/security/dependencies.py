from zcore.security.protocols import UserProtocol

async def get_current_user_stub() -> UserProtocol:
    raise NotImplementedError("Dependency override is required for get_current_user_stub")