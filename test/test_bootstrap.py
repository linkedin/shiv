from shiv.bootstrap import import_string

from site import addsitedir
from code import interact


class TestBootstrap:
    def test_various_imports(self):
        assert import_string('site.addsitedir') == addsitedir
        assert import_string('site:addsitedir') == addsitedir
        assert import_string('code.interact') == interact
        assert import_string('code:interact') == interact

        # test things not already imported
        func = import_string('os.path:join')
        from os.path import join
        assert func == join
