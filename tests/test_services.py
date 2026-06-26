import unittest

from yue_core.services import ServiceRegistrationError, ServiceRegistry


class ServiceRegistryTests(unittest.TestCase):
    def test_register_and_remove_owner(self):
        registry = ServiceRegistry()
        service = object()
        registry.register("demo.service", service, owner="demo")
        self.assertIs(registry["demo.service"], service)
        registry.unregister_owner("demo")
        self.assertNotIn("demo.service", registry)

    def test_rejects_duplicate_name(self):
        registry = ServiceRegistry()
        registry.register("demo.service", object(), owner="one")
        with self.assertRaises(ServiceRegistrationError):
            registry.register("demo.service", object(), owner="two")


if __name__ == "__main__":
    unittest.main()

