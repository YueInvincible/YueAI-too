class YueCoreError(Exception):
    """Base class for expected core errors."""


class ConfigurationError(YueCoreError):
    pass


class SchemaValidationError(YueCoreError):
    pass


class ToolRegistrationError(YueCoreError):
    pass


class PluginLoadError(YueCoreError):
    pass


class LifecycleError(YueCoreError):
    pass

