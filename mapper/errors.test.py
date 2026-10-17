from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import mapper  # noqa: E402

REFUSALS = ["NeedsBankCount", "NoHeader", "NotWholeBanks", "UnknownModelError"]


def reaching_back(source: str) -> list[str]:

    def inside(name: str) -> bool:
        return name.startswith(".") or name == "mapper" or name.startswith("mapper.")

    borrowed = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            borrowed += [alias.name for alias in node.names if inside(alias.name)]
        elif isinstance(node, ast.ImportFrom):
            name = "." * node.level + (node.module or "")
            if inside(name):
                borrowed.append(name)
    return borrowed


def exported_refusals() -> list[type[Exception]]:
    held = [getattr(mapper, name) for name in mapper.__all__]
    return [one for one in held if isinstance(one, type) and issubclass(one, Exception)]


class OneHomeTest(unittest.TestCase):
    def test_the_package_exports_the_refusals_it_makes(self) -> None:
        # Arrange
        expected = REFUSALS

        # Act
        found = sorted(one.__name__ for one in exported_refusals())

        # Assert
        self.assertEqual(found, expected)

    def test_every_one_of_them_lives_in_the_errors_module(self) -> None:
        # Arrange
        home = (ROOT / "mapper" / "errors.py").read_text()

        # Act
        stray = [
            one.__name__
            for one in exported_refusals()
            if one.__module__ != "mapper.errors" or f"class {one.__name__}(" not in home
        ]

        # Assert
        self.assertEqual(stray, [])

    def test_none_of_them_is_a_subclass_of_another(self) -> None:
        # Arrange
        held = exported_refusals()

        # Act
        overlapping = [
            (one.__name__, other.__name__)
            for one in held
            for other in held
            if one is not other and issubclass(one, other)
        ]

        # Assert
        self.assertEqual(overlapping, [])


class NoCycleTest(unittest.TestCase):
    def test_it_imports_nothing_from_this_package(self) -> None:
        # Arrange
        held = (ROOT / "mapper" / "errors.py").read_text()

        # Act
        found = reaching_back(held)

        # Assert
        self.assertEqual(found, [])

    def test_the_reader_of_that_names_an_absolute_import_back(self) -> None:
        # Arrange
        source = "import mapper.layout\n"

        # Act
        found = reaching_back(source)

        # Assert
        self.assertEqual(found, ["mapper.layout"])

    def test_and_a_relative_one(self) -> None:
        # Arrange
        source = "from . import layout\n"

        # Act
        found = reaching_back(source)

        # Assert
        self.assertEqual(found, ["."])

    def test_and_steps_over_one_from_outside(self) -> None:
        # Arrange
        source = "from __future__ import annotations\nimport mappertools\n"

        # Act
        found = reaching_back(source)

        # Assert
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
