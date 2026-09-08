"""Local python-for-android recipe override for freetype.

GNU Savannah's download server (the upstream python-for-android recipe's
source) has been consistently unreachable (502/504) from GitHub Actions'
network across multiple separate build attempts - not a one-off blip.

A first attempt redirected the download to FreeType's GitHub tag archive,
which fetched fine but broke the build differently: GitHub's automatic
tag-archive export does not include git submodule content, and FreeType
2.14.x's build needs its `subprojects/dlg` submodule (a logging helper)
to already be present as real files - only GNU's officially *prepared*
release tarball (built via `make dist`) bundles that in directly.

SourceForge has mirrored FreeType's official prepared release tarballs
for years, so this points there instead: same file GNU Savannah would
have served, reachable from GitHub Actions' network. Everything else
(build_arch, get_recipe_env, install_libraries, harfbuzz handling) is
inherited unchanged from upstream python-for-android.
"""

from pythonforandroid.recipes.freetype import FreetypeRecipe


class FreetypeRecipeMirror(FreetypeRecipe):
    @property
    def versioned_url(self):
        return (
            "https://downloads.sourceforge.net/project/freetype/freetype2/"
            f"{self.version}/freetype-{self.version}.tar.gz"
        )


recipe = FreetypeRecipeMirror()
