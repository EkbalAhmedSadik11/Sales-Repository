"""Local python-for-android recipe override for python3.

Two independent problems, both fixed here.

1. Android's Bionic libc doesn't implement grp.h's iterator functions
   setgrent()/getgrent()/endgrent() (only the lookup functions
   getgrgid()/getgrnam() exist). CPython's Modules/grpmodule.c calls
   them with no configure-time guard around it - confirmed by setting
   ac_cv_func_setgrent/getgrent/endgrent=no as job-level environment
   variables against a guaranteed-fresh `./configure` run (after busting
   the build-dir cache) and seeing the exact same compile error, so
   autoconf detection isn't what gates this. The NDK's clang then treats
   the implicit declaration as a hard error
   (-Werror -Wimplicit-function-declaration), failing the build:

       grpmodule.c:281:5: error: implicit declaration of function
       'setgrent' is invalid in C99 [-Werror,-Wimplicit-function-declaration]

   Fixed by neutralizing those three calls directly in the extracted C
   source before it's compiled, via prebuild_arch - a standard
   python-for-android recipe hook for exactly this ("patch source before
   building") purpose. Only setgrent/getgrent/endgrent become no-ops;
   getgrgid/getgrnam (actual lookups, the only grp functionality this
   app or its dependencies could plausibly touch) are untouched.

2. Subclassing Python3Recipe alone breaks its `patches` list: p4a's
   get_recipe_dir() resolves against wherever it found a folder named
   "python3" on the recipe search path - for a local override that's
   this folder, not upstream's, so the inherited relative patch paths
   ("patches/...") 404 (hit this on an earlier attempt). Overriding
   get_recipe_dir() to point back at the real upstream recipe directory
   fixes that without needing to copy any of its files here.
"""

import os

import pythonforandroid.recipes.python3 as _upstream_python3_pkg
from pythonforandroid.recipes.python3 import Python3Recipe

_UPSTREAM_RECIPE_DIR = os.path.dirname(_upstream_python3_pkg.__file__)

_GRP_FIX_MARKER = "/* sales_repository: android grp.h iterator shim */"
_GRP_FIX_SHIM = (
    _GRP_FIX_MARKER + "\n"
    "#define setgrent() ((void)0)\n"
    "#define getgrent() (NULL)\n"
    "#define endgrent() ((void)0)\n"
)


class Python3RecipeAndroidGrpFix(Python3Recipe):
    def get_recipe_dir(self):
        return _UPSTREAM_RECIPE_DIR

    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        grp_path = os.path.join(self.get_build_dir(arch.arch), "Modules", "grpmodule.c")
        if not os.path.isfile(grp_path):
            return
        with open(grp_path, "r", encoding="utf-8") as f:
            source = f.read()
        if _GRP_FIX_MARKER in source:
            return  # prebuild_arch can run more than once; stay idempotent
        with open(grp_path, "w", encoding="utf-8") as f:
            f.write(_GRP_FIX_SHIM + source)


recipe = Python3RecipeAndroidGrpFix()
