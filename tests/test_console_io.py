import builtins
import io

from mockito import ANY, mock, when

from nextlabs_sdk._auth._token_cache._console_io import ConsoleIO


class TestConsoleIOMessage:
    def test_writes_single_line_to_dev_tty(self):
        # given a writable controlling terminal
        writer = io.StringIO()
        handle = mock()
        when(handle).__enter__().thenReturn(writer)
        when(handle).__exit__(ANY, ANY, ANY).thenReturn(False)
        when(builtins).open("/dev/tty", "w", encoding="utf-8").thenReturn(handle)
        # when a message is emitted
        ConsoleIO().message("heads up")
        # then exactly one newline-terminated line lands on the terminal
        assert writer.getvalue() == "heads up\n"

    def test_oserror_opening_tty_is_non_interactive(self):
        # given a controlling terminal that cannot be opened
        when(builtins).open("/dev/tty", "w", encoding="utf-8").thenRaise(OSError())
        # when a message is emitted then it neither aborts nor crashes
        ConsoleIO().message("heads up")
