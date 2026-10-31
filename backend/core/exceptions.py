class ContextBankException(Exception):
    """Base exception for Context Bank."""
    def __init__(self, message: str, code: str = "ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class TriggerNotFoundError(ContextBankException):
    def __init__(self, trigger: str):
        super().__init__(
            f"No exact context registered for trigger: '{trigger}'. Exact trigger match required.",
            code="TRIGGER_NOT_FOUND"
        )
        self.trigger = trigger


class TriggerAlreadyExistsError(ContextBankException):
    def __init__(self, trigger: str, context_id: str):
        super().__init__(
            f"Trigger '{trigger}' is already registered to context '{context_id}' in your namespace.",
            code="TRIGGER_ALREADY_EXISTS"
        )
        self.trigger = trigger
        self.context_id = context_id


class ContextNotFoundError(ContextBankException):
    def __init__(self, context_id: str):
        super().__init__(f"Context with ID '{context_id}' not found.", code="CONTEXT_NOT_FOUND")
        self.context_id = context_id


class VersionNotFoundError(ContextBankException):
    def __init__(self, context_id: str, version_id: str):
        super().__init__(
            f"Version '{version_id}' not found for context '{context_id}'.",
            code="VERSION_NOT_FOUND"
        )
        self.context_id = context_id
        self.version_id = version_id


class UnauthorizedAccessError(ContextBankException):
    def __init__(self, resource: str = "context"):
        super().__init__(
            f"You are not authorized to view or modify this {resource}.",
            code="UNAUTHORIZED"
        )


class ValidationDomainError(ContextBankException):
    def __init__(self, details: str):
        super().__init__(f"Validation error: {details}", code="VALIDATION_ERROR")
