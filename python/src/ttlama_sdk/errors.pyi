"""Stub for the TTLama SDK errors."""
class TTLamaError(Exception): ... # pylint: disable=C0115

class APIError(TTLamaError): # pylint: disable=C0115
    status_code: int | None
    lease_id: int | None

    def __init__(
        self,
        message: str, # pylint: disable=W0613
        *,
        status_code: int | None = None, # pylint: disable=W0613
        lease_id: int | None = None, # pylint: disable=W0613
    ) -> None: ...

class AuthenticationError(APIError): ... # pylint: disable=C0115
class AuthorizationError(APIError): ... # pylint: disable=C0115
class ValidationError(APIError): ... # pylint: disable=C0115
class NotFoundError(APIError): ... # pylint: disable=C0115
class ConflictError(APIError): ... # pylint: disable=C0115
class ProvisioningError(APIError): ... # pylint: disable=C0115
