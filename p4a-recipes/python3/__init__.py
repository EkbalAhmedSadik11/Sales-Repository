"""Local python-for-android recipe override for python3.

Android's Bionic libc does not implement the grp.h iterator functions
setgrent()/getgrent()/endgrent() (only the lookup functions getgrgid()/
getgrnam() exist). CPython's ./configure otherwise detects them as
present, so Modules/grpmodule.c tries to call them, and the NDK's
clang treats an implicit declaration as a hard error
(-Werror -Wimplicit-function-declaration), failing the whole build:

    grpmodule.c:281:5: error: implicit declaration of function
    'setgrent' is invalid in C99 [-Werror,-Wimplicit-function-declaration]

Autoconf lets you override a cached check result via environment
variables (ac_cv_func_<name>). Setting these to "no" before configure
runs makes CPython treat those three functions as unavailable, so
grpmodule.c stops trying to wrap them - the rest of the grp module
(and everything else) is unaffected.
"""

from pythonforandroid.recipes.python3 import Python3Recipe


class Python3RecipeAndroidGrpFix(Python3Recipe):
    def get_recipe_env(self, *args, **kwargs):
        env = super().get_recipe_env(*args, **kwargs)
        env["ac_cv_func_setgrent"] = "no"
        env["ac_cv_func_getgrent"] = "no"
        env["ac_cv_func_endgrent"] = "no"
        return env


recipe = Python3RecipeAndroidGrpFix()
