from .base import BasePlugin, TestPlugin
from .metrixplusplus import MetrixPlusPlusPlugin
from .clangtidy import ClangTidyPlugin
from .valgrind import ValgrindPlugin
from .cppcheck import CppcheckPlugin
from .doctest import DoctestPlugin

__all__ = [
    "BasePlugin", "TestPlugin", "MetrixPlusPlusPlugin",
    "ClangTidyPlugin", "ValgrindPlugin", "CppcheckPlugin"
]

metric_plugins = {
    "clangtidy": ClangTidyPlugin(),
    "valgrind": ValgrindPlugin(),
    "metrixplusplus": MetrixPlusPlusPlugin(),
    "cppcheck": CppcheckPlugin(),
}

test_plugins = {
    "doctest": DoctestPlugin(),
}