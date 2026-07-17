import unittest

from garmin_running_data_normalizer import IMPLEMENTATION_STATUS, __version__


class PackageIdentityTest(unittest.TestCase):
    def test_local_implementation_identity(self) -> None:
        self.assertEqual(__version__, "0.1.0")
        self.assertEqual(IMPLEMENTATION_STATUS, "LOCAL_IMPLEMENTATION_NOT_PUBLICATION_READY")


if __name__ == "__main__":
    unittest.main()
