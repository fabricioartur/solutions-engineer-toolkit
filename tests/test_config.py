"""Tests for shared configuration loading."""

import os
import unittest

from tools.config import Config, ToolkitError


class TestConfig(unittest.TestCase):

    def test_load_raises_without_api_key(self):
        env = os.environ.copy()
        os.environ.pop("OPENAI_API_KEY", None)
        try:
            with self.assertRaises(ToolkitError):
                Config.load()
        finally:
            os.environ.update(env)

    def test_load_uses_default_model(self):
        os.environ["OPENAI_API_KEY"] = "test-key"
        os.environ.pop("OPENAI_MODEL", None)
        config = Config.load()
        self.assertEqual(config.model, "gpt-5.4-mini")

    def test_load_respects_model_override(self):
        os.environ["OPENAI_API_KEY"] = "test-key"
        os.environ["OPENAI_MODEL"] = "gpt-5.5"
        config = Config.load()
        self.assertEqual(config.model, "gpt-5.5")

    def tearDown(self):
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("OPENAI_MODEL", None)
