from .base import BasePlugin
from .metrixplusplus import MetrixPlusPlusPlugin
from .clangtidy import ClangTidyPlugin

__all__ = ["BasePlugin", "MetrixPlusPlusPlugin", "ClangTidyPlugin"]

plugin_list = {
    "metrixplusplus": MetrixPlusPlusPlugin(),
    "clangtidy": ClangTidyPlugin(),
}