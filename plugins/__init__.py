from .base import BasePlugin
from .metrixplusplus import MetrixPlusPlusPlugin
from .clangtidy import ClangTidyPlugin
from .valgrind import ValgrindPlugin
from .cppcheck import CppcheckPlugin

__all__ = [
    "BasePlugin", "MetrixPlusPlusPlugin", "ClangTidyPlugin", 
    "ValgrindPlugin", "CppcheckPlugin"
]

plugin_list = {
    "metrixplusplus": MetrixPlusPlusPlugin(),
    "clangtidy": ClangTidyPlugin(),
    "valgrind": ValgrindPlugin(),
    "cppcheck": CppcheckPlugin(),
}