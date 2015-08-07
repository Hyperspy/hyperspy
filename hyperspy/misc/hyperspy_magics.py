from IPython.core.magic import Magics, magics_class, line_magic
from hyperspy.defaults_parser import preferences


@magics_class
class HyperspyMagics(Magics):

    @line_magic
    def hyperspy(self, line):
        """
        %hyperspy [-r] [toolkit]

        Load HyperSpy, numpy and matplotlib to work interactively.

        %hyperspy runs the following commands::

        >>> import numpy as np
        >>> import hyperspy.hspy as hs
        >>> %matplotlib [toolkit]
        >>> import matplotlib.pyplot as plt

        If you pass `-r`, the current input cell will be overwritten with the above specified commands. As a
        consequence, all other code in the input cell will be deleted!

        Positional arguments:
        ---------------------
            toolkit
                Name of the matplotlib backend to use. If given, the corresponding matplotlib backend is used,
                otherwise it will be the HyperSpy's default. If "none" or "None" is passed, the matplotlib
                magic is not executed.

        Optional arguments:
        -------------------
            -r
                After running the the magic as usual, overwrites the current input cell with just executed
                code that can be run directly without magic

        """
        sh = self.shell
        first_import_part = ("import numpy as np\n"
                             "import hyperspy.hspy as hs\n")
        exec(first_import_part, sh.user_ns)

        overwrite = False
        gui = False
        line = line.strip()
        if "-r" in line:
            overwrite = True
            before, after = line.split("-r")
            before, after = before.strip(), after.strip()
            if after:
                toolkit = after
            elif before:
                toolkit = before
            else:
                toolkit = preferences.General.default_toolkit

        elif line:
            toolkit = line.strip()
        else:
            toolkit = preferences.General.default_toolkit

        if toolkit not in ["None", "none"]:
            gui = True
            sh.enable_matplotlib(toolkit)

        second_import_part = "import matplotlib.pyplot as plt"
        exec(second_import_part, sh.user_ns)

        header = "\nHyperSpy imported!\nThe following commands were just executed:\n"
        header += "---------------\n"
        ans = first_import_part
        if gui:
            ans += "%matplotlib " + toolkit + "\n"
        ans += second_import_part
        print header + ans
        if overwrite:
            sh.set_next_input(
                "# %hyperspy -r " +
                toolkit +
                "\n" +
                ans +
                "\n\n",
                replace=True)
