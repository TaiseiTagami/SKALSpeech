import typer

from .commands.convert import convert_command
from .commands.slice import slice_command
from .version import version_command

app = typer.Typer(help="Tools for speech recordings and Praat TextGrids.")

app.command("version")(version_command)
app.command("slice")(slice_command)
app.command("convert")(convert_command)
app.command("textgrid-to-csv")(convert_command)
