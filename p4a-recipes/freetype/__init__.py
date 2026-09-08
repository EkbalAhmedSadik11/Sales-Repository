"""Local python-for-android recipe override for freetype.

GNU Savannah's download server (the upstream python-for-android recipe's
source) has been consistently unreachable (502/504) from GitHub Actions'
network across multiple separate build attempts - not a one-off blip.
This subclasses the real freetype recipe and only swaps the download
source to FreeType's official GitHub mirror, which sits on the same
network GitHub Actions runners use. Everything else (build_arch,
get_recipe_env, install_libraries, harfbuzz handling) is inherited
unchanged from upstream python-for-android.
"""

from pythonforandroid.recipes.freetype import FreetypeRecipe


class FreetypeRecipeGitHubMirror(FreetypeRecipe):
    @property
    def versioned_url(self):
        tag = "VER-" + self.version.replace(".", "-")
        return f"https://github.com/freetype/freetype/archive/refs/tags/{tag}.tar.gz"


recipe = FreetypeRecipeGitHubMirror()
